"""The opt-in formatter hooks must agree with CI in version, in commands, and in where they are documented.

The file shipped `rev: v0.4.9` while `uv.lock` resolves ruff 0.17.1 and CI runs `ruff check` / `ruff format --check`
with it, and nothing wired it: no `pre-commit` dependency, no installed `.git/hooks/pre-commit`, and no contributing
page mentioning `pre-commit install`. A declared control with no wiring and a stale pin is the worst combination --
a reader assumes enforcement that never happens, and the one person who does opt in gets `ruff --fix` rewriting
files in the shape of a superseded formatter that CI then refuses.

It is now a real opt-in: `pre-commit` is a dev dependency, both contributing guides document
`uv run pre-commit install`, and the config says plainly that the enforced copies are the CI steps and that a shared
worktree should not install the hook (`.git/hooks` is one directory for every session in the checkout). Four
properties, each able to fail:

* the config's rev equals the version `uv.lock` resolves;
* the two hook ids still correspond to the two CI commands they copy;
* the header names both the install step and the workflow that enforces;
* the guides that promise the step still mention it, and `pyproject.toml` still provides the tool.

A "green" here means the copy and the gate agree, not that either ran.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".pre-commit-config.yaml"
LOCK = ROOT / "uv.lock"
PYPROJECT = ROOT / "pyproject.toml"
CI = ROOT / ".github" / "workflows" / "ci.yml"
GUIDES = (ROOT / "CONTRIBUTING.md", ROOT / "docs" / "contributing.md")


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


def test_the_install_step_is_documented_and_the_tool_is_provided() -> None:
    """The config offers `pre-commit install`; that offer is only honest if both halves behind it exist."""
    for guide in GUIDES:
        text = guide.read_text(encoding="utf-8")
        assert "pre-commit install" in text, (
            f"{guide.relative_to(ROOT)} no longer documents the opt-in it advertises"
        )
        assert "shared worktree" in text or "more than one session" in text, (
            f"{guide.relative_to(ROOT)} must still warn against installing the hook where .git/hooks is shared"
        )
    text = PYPROJECT.read_text(encoding="utf-8")
    group = text[text.index("[dependency-groups]") :]
    boundary = group.index("\n[", 1)
    specs = re.findall(r'"([^"]+)"', group[:boundary])
    # Match the requirement's name, not the substring: a comment in the same list mentioning
    # `.pre-commit-config.yaml` would otherwise satisfy a bare `"pre-commit" in group` check, and the guard would
    # keep passing on a tree where `uv sync --dev` no longer provides the tool the guides tell you to run.
    names = {re.split(r"[<>=!\[]", s, maxsplit=1)[0].strip().lower() for s in specs}
    assert "pre-commit" in names, (
        "pre-commit is documented as installable but is not in the dev group, so `uv sync --dev` would not "
        f"provide it -- the group declares {sorted(names)}"
    )
