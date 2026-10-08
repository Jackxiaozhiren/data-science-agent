"""§139: the SBOM gate verifies the published dependency claim, and writes nothing while doing it.

`ci.yml:109` ran `uv run python scripts/generate_sbom.py && test -f release/sbom.json`. That is a smoke
test with a side effect: the generator's only output path was the tracked `release/sbom.json` and
`release/sbom.cyclonedx.json`, so every run rewrote two committed supply-chain artifacts in place. Running
the documented local gate runner did exactly that in this session -- 457 changed lines across the two files,
left in the tree for the next person to commit by reflex.

Two things were wrong with that, and they are different. The mutation is the smaller one: a check that
trashes the tree is a trap, and `--out DIR` / `--check` removes it. The larger one is what the gate never
asked. The SBOM asserts which packages this release depends on; the generator derived that set from
`uv.lock` and the workspace manifests and then *overwrote* the file instead of comparing. So a dependency
change could ship with an SBOM naming components the revision no longer contains, and the step that touches
the SBOM on every push would report success either way -- `test -f` asks only that the file exists.

The check compares `(package, version)` pairs and the release version. It does not compare `generated` (a
wall-clock stamp) or `license` (a PyPI lookup that improves between runs -- 57 components gained a real
license identifier in the regeneration above without any dependency changing), because neither is a claim
about what the revision depends on, and a gate that fires on those gets muted rather than read.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_sbom.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
RUNNER = ROOT / "scripts" / "run_gates.sh"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("generate_sbom_under_test", str(SCRIPT))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sbom(version: str, packages: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "version": version,
        "generated": "2026-01-01T00:00:00+00:00",
        "components": [
            {
                "package": name,
                "version": ver,
                "license": "MIT",
                "source": "x",
                "purl": f"pkg:pypi/{name}",
            }
            for name, ver in packages
        ],
    }


def _write_committed(root: Path, sbom: dict[str, Any]) -> None:
    (root / "release").mkdir(parents=True, exist_ok=True)
    (root / "release" / "sbom.json").write_text(json.dumps(sbom), encoding="utf-8")


def test_a_matching_component_set_passes(tmp_path: Path) -> None:
    module = _load()
    packages = [("alpha", "1.0.0"), ("beta", "2.1.0")]
    _write_committed(tmp_path, _sbom("4.4.0", packages))
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", packages)) == 0


def test_a_component_the_revision_no_longer_depends_on_fails(tmp_path: Path) -> None:
    """The regression this gate exists for: the SBOM still naming a dropped dependency."""
    module = _load()
    _write_committed(tmp_path, _sbom("4.4.0", [("alpha", "1.0.0"), ("ghost", "9.9.9")]))
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.0.0")])) == 1


def test_a_dependency_missing_from_the_committed_sbom_fails(tmp_path: Path) -> None:
    module = _load()
    _write_committed(tmp_path, _sbom("4.4.0", [("alpha", "1.0.0")]))
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.0.0"), ("newthing", "0.2.0")])) == 1


def test_a_version_pinned_differently_fails_not_just_a_name(tmp_path: Path) -> None:
    """Same package, different version: a name-only comparison would wave this through."""
    module = _load()
    _write_committed(tmp_path, _sbom("4.4.0", [("alpha", "1.0.0")]))
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.1.0")])) == 1


def test_the_release_version_is_part_of_the_claim(tmp_path: Path) -> None:
    module = _load()
    _write_committed(tmp_path, _sbom("4.3.0", [("alpha", "1.0.0")]))
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.0.0")])) == 1


def test_a_license_correction_alone_does_not_fail_the_check(tmp_path: Path) -> None:
    """`license` is a lookup, not a dependency claim: the committed file may legitimately lag."""
    module = _load()
    committed = _sbom("4.4.0", [("alpha", "1.0.0")])
    committed["components"][0]["license"] = "Unknown"
    committed["generated"] = "2020-01-01T00:00:00+00:00"
    _write_committed(tmp_path, committed)
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.0.0")])) == 0


def test_a_missing_committed_sbom_is_a_failure_not_an_empty_pass(tmp_path: Path) -> None:
    module = _load()
    module.ROOT = tmp_path

    assert module._verify(_sbom("4.4.0", [("alpha", "1.0.0")])) == 1


# --- the gate shape, checked on the shipped commands -------------------------------------------

_SBOM_INVOCATION = re.compile(r"generate_sbom\.py[^\n\"']*")


def _invocations(text: str) -> list[str]:
    return _SBOM_INVOCATION.findall(text)


def test_every_sbom_invocation_in_the_gate_surface_is_a_check() -> None:
    """A write-mode invocation in a gate is how the tracked artifact gets rewritten under someone."""
    found = _invocations(CI.read_text(encoding="utf-8")) + _invocations(
        RUNNER.read_text(encoding="utf-8")
    )
    assert found, "the SBOM step has vanished from both ci.yml and the gate runner"
    for invocation in found:
        assert "--check" in invocation, f"{invocation!r} runs the generator in write mode"


def test_checking_the_shipped_sbom_passes_and_writes_nothing() -> None:
    """The live claim, run through the real entry point, with the tracked bytes held up as evidence."""
    tracked = {
        name: (ROOT / "release" / name).read_bytes()
        for name in ("sbom.json", "sbom.cyclonedx.json")
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SBOM CHECK OK" in result.stdout, result.stdout
    for name, before in tracked.items():
        assert (ROOT / "release" / name).read_bytes() == before, (
            f"--check rewrote release/{name}; the gate that is supposed to leave the tree alone did not"
        )


def test_deriving_to_another_directory_leaves_the_tracked_copy_alone(tmp_path: Path) -> None:
    """`--out` exists so the generator can be exercised at all without touching the committed file."""
    out = tmp_path / "sbom-run"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (out / "sbom.json").is_file() and (out / "sbom.cyclonedx.json").is_file()
    derived = json.loads((out / "sbom.json").read_text(encoding="utf-8"))
    committed = json.loads((ROOT / "release" / "sbom.json").read_text(encoding="utf-8"))

    assert {tuple(sorted((c["package"], c["version"]) for c in derived["components"]))} == {
        tuple(sorted((c["package"], c["version"]) for c in committed["components"]))
    }
    assert derived["version"] == committed["version"]


def test_the_control_deriving_the_sbom_at_all_is_not_a_no_op(tmp_path: Path) -> None:
    """If the generator produced nothing, every comparison above would pass on an empty file."""
    out = tmp_path / "control"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    derived = json.loads((out / "sbom.json").read_text(encoding="utf-8"))

    assert len(derived["components"]) > 100, len(derived["components"])
    names = {c["package"] for c in derived["components"]}
    assert names & {"numpy", "fastapi"}, sorted(names)[:12]
