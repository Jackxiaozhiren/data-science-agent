"""§127, Phase 4 target 1: every declared lint exemption must be reachable, or it is removed.

`pyproject.toml` carried **118** `(pattern, rule)` per-file-ignore entries plus a global
`ignore = ["S101", "E501"]`. A suppression nobody can observe is worse than no suppression: it reads
as a decision, costs the next reader a lookup, and can silently be widened. Measured here with the
project's own settings -- one ruff invocation per pattern, each with that pattern's entry deleted from
an otherwise-identical config -- **75 of the 118 hide nothing at all**: the rule does not occur in
that tree, or the same rule is already ignored globally, or the rule is listed twice in the same
pattern (`tests/**/*` declares `S110` twice, `packages/tools/**/*` declares `SIM103` and `UP046`
twice). `packages/mcp/**/*` was inert in all seven of its entries.

The method matters more than the number. `ruff check --isolated` was the obvious first probe and it
lies: isolated drops `line-length = 100`, so `E501` fires 29 times in `apps/jupyter` at 88 columns and
zero at the project's real width, which would have made three live-looking entries look dead. Every
count below comes from a config that differs from the shipped one only in the entry being tested.

Red on arrival: the shipped pyproject fails this file with the 75 inert entries named.
"""

from __future__ import annotations

import collections
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _ruff() -> Path:
    """The ruff the venv installed, resolved the same way the CI lint step resolves it."""
    candidate = Path(sys.executable).parent / "ruff"
    if candidate.is_file():
        return candidate
    found = shutil.which("ruff")
    assert found, "no ruff binary to probe with -- this gate would be checking nothing"
    return Path(found)


def _config() -> dict:
    return tomllib.load(open(ROOT / "pyproject.toml", "rb"))["tool"]["ruff"]


def _to_ruff_toml(cfg: dict) -> str:
    """Render `[tool.ruff]` as a standalone ruff.toml, preserving the project's real settings."""
    lines = []
    for key in ("line-length", "target-version"):
        if key in cfg:
            value = cfg[key]
            lines.append(f"{key} = {json.dumps(value)}")
    if "extend-exclude" in cfg:
        lines.append("extend-exclude = " + json.dumps(cfg["extend-exclude"]))
    lint = cfg.get("lint", {})
    lines.append("[lint]")
    for key in ("select", "ignore"):
        if key in lint:
            lines.append(f"{key} = " + json.dumps(lint[key]))
    if lint.get("per-file-ignores"):
        lines.append("[lint.per-file-ignores]")
        for pattern, rules in lint["per-file-ignores"].items():
            lines.append(f"{json.dumps(pattern)} = " + json.dumps(rules))
    return "\n".join(lines) + "\n"


def _path_for(pattern: str) -> str:
    return pattern.replace("/**/*", "").replace("/*", "")


def _fired_codes(tmp_path: Path, cfg: dict, target: str) -> collections.Counter:
    text = _to_ruff_toml(cfg)
    handle = tmp_path / "ruff-probe.toml"
    handle.write_text(text, encoding="utf-8")
    proc = subprocess.run(
        [str(_ruff()), "check", "--config", str(handle), "--output-format", "json", target],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1), f"ruff could not evaluate the probe: {proc.stderr[:400]}"
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - a broken probe must not read as clean
        raise AssertionError(
            f"ruff printed no JSON for {target}: {exc}: {proc.stdout[:200]}"
        ) from exc
    return collections.Counter(row["code"] for row in rows if row.get("code"))


def inert_entries(tmp_path: Path, cfg: dict) -> list[str]:
    """Declared per-file entries whose removal would not expose a single finding."""
    found: list[str] = []
    for pattern, rules in cfg["lint"].get("per-file-ignores", {}).items():
        stripped = json.loads(json.dumps(cfg))
        stripped["lint"]["per-file-ignores"].pop(pattern)
        fired = _fired_codes(tmp_path, stripped, _path_for(pattern))
        for rule in dict.fromkeys(rules):
            if not fired.get(rule):
                found.append(f"{pattern} -> {rule}")
    return found


def test_every_declared_per_file_ignore_hides_a_real_finding(tmp_path: Path) -> None:
    cfg = _config()
    declared = sum(len(dict.fromkeys(v)) for v in cfg["lint"]["per-file-ignores"].values())
    assert declared >= 30, f"only {declared} entries parsed -- the reader broke, not the config"
    inert = inert_entries(tmp_path, cfg)
    assert not inert, "inert lint exemptions (remove them):\n  " + "\n  ".join(sorted(inert))


def test_no_rule_is_declared_twice_in_one_pattern() -> None:
    offenders = []
    for pattern, rules in _config()["lint"].get("per-file-ignores", {}).items():
        for rule, count in collections.Counter(rules).items():
            if count > 1:
                offenders.append(f"{pattern}: {rule} declared {count}x")
    assert not offenders, offenders


def test_no_per_file_ignore_duplicates_a_globally_ignored_rule() -> None:
    """A rule the whole project already ignores needs no per-tree entry on top of it."""
    globally = set(_config()["lint"].get("ignore", []))
    offenders = [
        f"{pattern} -> {rule}"
        for pattern, rules in _config()["lint"].get("per-file-ignores", {}).items()
        for rule in rules
        if rule in globally
    ]
    assert not offenders, f"shadowed by lint.ignore: {sorted(set(offenders))}"


def test_each_global_ignore_also_hides_something(tmp_path: Path) -> None:
    cfg = _config()
    globally = cfg["lint"].get("ignore", [])
    assert globally, "no global ignore to test -- the guard would pass on nothing"
    stripped = json.loads(json.dumps(cfg))
    stripped["lint"]["ignore"] = []
    total = collections.Counter()
    for target in ("packages", "apps/api", "tests", "src", "apps/jupyter", "scripts"):
        total.update(_fired_codes(tmp_path, stripped, target))
    silent = [rule for rule in globally if not total.get(rule)]
    assert not silent, f"global ignores that hide nothing anywhere: {silent}"
    for rule in globally:
        assert total[rule] > 0


def test_the_control_a_planted_inert_entry_is_reported_and_a_live_one_is_not(
    tmp_path: Path,
) -> None:
    """The guard above must be able to say both no and yes.

    `packages/tools` is the fixture tree because §127 measured its live set exactly: `F401` fires
    there, `E402` does not.
    """
    cfg = json.loads(json.dumps(_config()))
    tools = cfg["lint"]["per-file-ignores"].get("packages/tools/**/*", [])
    assert "F401" in tools and "E402" not in tools, (
        f"§127's fixture premise moved: {sorted(set(tools))}"
    )
    cfg["lint"]["per-file-ignores"]["packages/tools/**/*"] = ["E402"]
    assert inert_entries(tmp_path, cfg) == ["packages/tools/**/* -> E402"], (
        "a planted inert entry was not reported -- the guard is decorative"
    )

    cfg2 = json.loads(json.dumps(_config()))
    cfg2["lint"]["per-file-ignores"]["packages/tools/**/*"] = ["F401"]
    reported = inert_entries(tmp_path, cfg2)
    assert "packages/tools/**/* -> F401" not in reported, reported


def test_the_removed_entries_are_not_still_declared_somewhere_else() -> None:
    """The 75 §127 deleted must stay deleted: the census is a floor on what is gone, not a snapshot.

    `debt.suppressionDirectives` counts inline `# noqa`-style suppressions in shipped code; nothing
    counted the size of the *config-level* exemption surface, so a re-widening of per-file-ignores
    would have been invisible to every gate. Asserting the live-set's shape here keeps the direction
    of travel one-way without gating a raw count that moves whenever an honest fix removes an entry.
    """
    cfg = _config()
    kept = {
        pattern: set(dict.fromkeys(rules))
        for pattern, rules in cfg["lint"].get("per-file-ignores", {}).items()
    }
    for pattern, rules in (
        ("apps/api/src/dsa_api/routers/*", {"B008"}),
        (
            "tests/**/*",
            {
                "S108",
                "B017",
                "S602",
                "S603",
                "S607",
                "F841",
                "I001",
                "SIM105",
                "S110",
                "F401",
                "SIM102",
                "SIM103",
            },
        ),
        ("packages/agent/src/dsa_agent/*", {"SIM102", "S608", "UP042"}),
        ("packages/plugins/**/*", {"S112", "F841", "SIM108", "F401"}),
        ("packages/datasets/**/*", {"S608", "UP042", "F841"}),
        (
            "packages/evaluation/**/*",
            {"S110", "F841", "B905", "SIM105", "UP042", "S311", "SIM210", "SIM108", "S603"},
        ),
        ("packages/evidence/**/*", {"S608"}),
        ("packages/execution/**/*", {"SIM103", "SIM110"}),
        ("packages/tools/**/*", {"UP046", "F401", "B904", "B905", "F841"}),
        ("apps/jupyter/**/*", {"F401", "I001", "B904"}),
    ):
        assert kept.get(pattern, set()) == rules, (
            f"{pattern}: expected {sorted(rules)}, found {sorted(kept.get(pattern, set()))}"
        )
    assert "packages/mcp/**/*" not in kept, "the mcp entry was inert in all seven rules (§127)"
