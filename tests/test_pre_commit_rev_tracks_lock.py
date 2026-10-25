"""`.pre-commit-config.yaml` must not enforce a different ruff than CI does.

The file shipped `rev: v0.4.9` while `uv.lock` resolves ruff 0.17.1 and `pyproject.toml` asks for `ruff>=0.4`, and
nothing installs the hook -- no `pre-commit` dependency, no `.git/hooks/pre-commit`, no contributing page telling a
reader to run `pre-commit install`. So it was a declared control with no wiring *and* a stale pin: someone who did
opt in would have `ruff --fix` rewriting their files in the shape of a thirteen-month-old formatter, and CI's
`ruff format --check` would then refuse the result. The gap between "my hooks passed" and "the gate is green" is
exactly the thing this repository keeps having to measure rather than assume.

Two properties, checked in both directions: the rev equals the version the lock resolves, and the config's own
header says plainly that the enforced copies are the CI steps -- because the comment is the only part of this file
a reader can act on without installing anything.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".pre-commit-config.yaml"
LOCK = ROOT / "uv.lock"
PYPROJECT = ROOT / "pyproject.toml"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _locked_ruff_version() -> str:
    block = re.search(
        r'\[\[package\]\]\nname = "ruff"\nversion = "([^"]+)"', LOCK.read_text(encoding="utf-8")
    )
    assert block, (
        "ruff is not a resolved package in uv.lock, so this guard has nothing to compare against"
    )
    return block.group(1)


def _config_rev() -> str:
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*rev:\s*v([0-9][0-9a-z.\-]*)\s*$", text)
    assert match, "the config carries no parsable `rev:` line"
    return match.group(1)


def test_the_pinned_ruff_is_the_version_the_lock_resolves() -> None:
    assert _config_rev() == _locked_ruff_version(), (
        f".pre-commit-config.yaml pins ruff v{_config_rev()} while CI runs the locked {_locked_ruff_version()}"
    )


def test_the_config_says_the_gate_lives_in_ci_not_in_this_file() -> None:
    """A reader who cannot tell whether these hooks run is a reader who will trust them."""
    text = CONFIG.read_text(encoding="utf-8")
    assert "pre-commit install" in text, (
        "the file must name the step nobody took, so the gap is visible"
    )
    assert ".github/workflows/ci.yml" in text, (
        "the file must point at the copies that actually gate a change"
    )


def test_ci_still_runs_both_gates_the_config_claims_to_mirror() -> None:
    ci = CI.read_text(encoding="utf-8")
    for step in ("ruff check", "ruff format --check"):
        assert step in ci, f"the config mirrors a CI gate that no longer exists: {step}"
    declared = set(
        re.findall(r"^\s*- id:\s*(\S+)\s*$", CONFIG.read_text(encoding="utf-8"), re.MULTILINE)
    )
    assert declared == {"ruff", "ruff-format"}, declared
    # `ruff>=0.4` in pyproject is a floor, not a pin: the lock is what CI resolves, so the floor may not exceed it.
    floor = re.search(r'"ruff>=([0-9.]+)"', PYPROJECT.read_text(encoding="utf-8"))
    assert floor and tuple(int(n) for n in floor.group(1).split(".")) <= tuple(
        int(n) for n in _locked_ruff_version().split(".")
    ), "pyproject's ruff floor is above the locked version"
