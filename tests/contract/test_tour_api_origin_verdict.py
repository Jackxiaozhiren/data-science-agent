"""The tour's bundle-freshness rule, exercised on forged origin sets.

`apps/web/scripts/regression.mjs` refuses to tour a bundle it cannot attribute to this tree. Its first form
compared every origin in the built chunks against `--api-port` and rejected any mismatch. That is wrong on a
quiet day: `apps/web/lib/api.ts` compiles `(configuredApiUrl || "http://localhost:8000")`, and minification
keeps the fallback literal even when `NEXT_PUBLIC_API_URL` is set, so a build baked for :8010 carries BOTH
`http://127.0.0.1:8010` and `http://localhost:8000`. Measured on a real build: `--api-port 8010` exited 1 and
told the operator to do the rebuild that had just been done. The refusal was therefore self-defeating, and the
CI job -- which always uses the default port -- could never see it.

Widening that rule to "any origin the source names" would have made the guard weaker than useless: a bundle
carrying no loopback origin at all would pass by absence. So the rule is two-sided, and this file pins both
edges -- the accept case the old code refused, and three refuses a one-sided allow-list would have let through.

The driver imports the module by ``file://`` URL, so it needs no ``node_modules`` and no particular cwd: this
module has no dependencies, which is the reason the rule lives in its own file rather than inline.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULE = ROOT / "apps" / "web" / "scripts" / "api-origin-verdict.mjs"
TOUR = ROOT / "apps" / "web" / "scripts" / "regression.mjs"

DRIVER = """
import { originsIn, verdict } from %s;
const cases = JSON.parse(process.argv[2]);
const out = cases.map((c) =>
  c.text !== undefined
    ? { kind: "scan", origins: originsIn(c.text) }
    : { kind: "verdict", ...verdict({ chunkOrigins: c.chunk, sourceOrigins: c.source, apiPort: c.port }) },
);
process.stdout.write(JSON.stringify(out));
"""


def _ask(tmp_path: Path, cases: list[dict]) -> list[dict]:
    """Run the real module. The driver lands in tmp_path, never beside the instruments it imports -- a file
    dropped into ``apps/web/scripts/`` mid-run is visible to whatever else reads that directory."""
    assert RULE.exists(), f"{RULE} is gone, so this test certifies nothing the tour uses"
    script = tmp_path / "origin_driver.mjs"
    script.write_text(DRIVER % json.dumps(RULE.as_uri()), encoding="utf-8")
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["node", str(script), json.dumps(cases)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"node exited {proc.returncode}: {proc.stderr.strip()[:300]}"
    return json.loads(proc.stdout)


def test_the_accept_side_is_the_one_the_old_rule_refused(tmp_path: Path) -> None:
    """A :8010 build that also carries the source's own :8000 fallback is a correct build."""
    (result,) = _ask(
        tmp_path,
        [
            {
                "chunk": ["http://127.0.0.1:8010", "http://localhost:8000"],
                "source": ["http://localhost:8000"],
                "port": 8010,
            }
        ],
    )
    assert result["ok"] is True, (
        "the guard refused a bundle built for the port it was given -- this is the self-defeating form "
        "that made the tour's own advice unreachable"
    )


def test_the_default_port_still_passes(tmp_path: Path) -> None:
    """The path CI takes must keep working, or the fix trades one red for another."""
    (result,) = _ask(
        tmp_path,
        [{"chunk": ["http://localhost:8000"], "source": ["http://localhost:8000"], "port": 8000}],
    )
    assert result["ok"] is True, result


def test_absence_of_the_guarded_port_is_a_refusal_not_a_pass(tmp_path: Path) -> None:
    """What the widened allow-list would have let through: a bundle that never mentions the port at all."""
    (result,) = _ask(
        tmp_path,
        [
            {
                "chunk": ["http://127.0.0.1:8010", "http://localhost:8000"],
                "source": ["http://localhost:8000"],
                "port": 8020,
            }
        ],
    )
    assert result["ok"] is False, result
    assert result["code"] == "no-baked-origin", result
    assert result["detail"]["apiPort"] == 8020, result


def test_a_bundle_for_a_non_loopback_api_is_refused(tmp_path: Path) -> None:
    """Zero loopback origins used to satisfy a rule written as "reject the others"."""
    (result,) = _ask(
        tmp_path, [{"chunk": ["https://demo.example.com"], "source": [], "port": 8000}]
    )
    assert result["ok"] is False and result["code"] == "no-baked-origin", result


def test_an_origin_the_source_never_names_is_refused(tmp_path: Path) -> None:
    """The keep-the-stale-bake case, with the port itself present so the first edge cannot excuse it."""
    (result,) = _ask(
        tmp_path,
        [
            {
                "chunk": ["http://localhost:8000", "http://localhost:9999"],
                "source": ["http://localhost:8000"],
                "port": 8000,
            }
        ],
    )
    assert result["ok"] is False, result
    assert result["code"] == "origin-not-in-source", result
    assert result["detail"]["foreign"] == ["http://localhost:9999"], (
        f"named the wrong origin as the intruder: {result['detail']}"
    )


def test_an_endpoint_with_a_path_is_not_read_as_an_origin(tmp_path: Path) -> None:
    """`http://localhost:11434/v1` is Ollama placeholder copy on the settings page, not a configured API."""
    (result,) = _ask(
        tmp_path, [{"text": 'fetch("http://localhost:11434/v1") // + "http://localhost:8000"'}]
    )
    assert result["origins"] == ["http://localhost:8000"], result["origins"]


def test_https_loopback_counts_for_the_port_it_carries(tmp_path: Path) -> None:
    (result,) = _ask(tmp_path, [{"chunk": ["https://localhost:8443"], "source": [], "port": 8443}])
    assert result["ok"] is True, result


def test_the_tour_imports_the_rule_this_file_pins() -> None:
    """Otherwise a green suite here would certify a module nobody calls."""
    imports = [
        line
        for line in TOUR.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("import ")
    ]
    assert any("api-origin-verdict.mjs" in line for line in imports), (
        "regression.mjs no longer imports the verdict module, so the rule under test is dead code"
    )
