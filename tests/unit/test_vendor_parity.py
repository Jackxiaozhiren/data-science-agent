"""`_vendor` parity as a second consumer of the test suite.

The mirror is not a detail: importing the published façade inserts ``_vendor`` at
``sys.path[0]``, so on the installed path — the wheel, the ``dsa`` console script, the
containers — every ``dsa_*`` module resolves there, not to ``packages/*/src``. A fix to a
workspace package is therefore inert in production until the mirror is regenerated, while the
test suite keeps passing against live source.

That is not hypothetical. Audit §57 changed ``dsa_evaluation/metrics.py``, watched the unit
tests go green, and the CLI still reported the old number — until the mirror caught up.
``sync_vendor --check`` was already a CI step; this makes the same invariant fail a local
``pytest`` too, so a stale mirror cannot survive a commit that only ran the suite.

Scope is deliberately per-file, and it is a scope limit rather than a dodge: a source path
carrying uncommitted edits — e.g. another session working in the same tree — is the only thing
excused, because byte parity against content that is not committed is not the claim being made.
On a CI checkout nothing is modified, so the assertion runs over every file.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _tool() -> object:
    """Load scripts/sync_vendor.py, reusing its own mapping and file reader."""
    spec = importlib.util.spec_from_file_location(
        "sync_vendor", ROOT / "scripts" / "sync_vendor.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync_vendor"] = module
    spec.loader.exec_module(module)
    return module


def _modified_paths() -> set[str]:
    """Worktree paths with uncommitted changes, relative to the repository root."""
    cp = subprocess.run(
        ["git", "status", "--porcelain", "-uall", "--"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    paths: set[str] = set()
    for line in cp.stdout.splitlines():
        if len(line) < 4:
            continue
        payload = line[3:].strip()
        for part in payload.split(" -> "):
            paths.add(part.strip().strip('"'))
    return paths


@pytest.mark.parametrize("name", sorted(_tool().SOURCES))  # type: ignore[attr-defined]
def test_vendored_copy_matches_committed_source(name: str) -> None:
    tool = _tool()
    src: Path = tool.SOURCES[name]
    dst: Path = tool.VENDOR / name
    modified = _modified_paths()
    src_root = src.relative_to(ROOT).as_posix()

    src_files: dict[str, bytes] = tool._package_files(src)
    dst_files: dict[str, bytes] = tool._package_files(dst)
    checked = 0
    stale: list[str] = []
    for rel in sorted(set(src_files) | set(dst_files)):
        if f"{src_root}/{rel}" in modified:
            continue
        checked += 1
        if src_files.get(rel) != dst_files.get(rel):
            stale.append(f"{name}/{rel}")

    assert checked > 0, f"{name}: every file was skipped, so this case asserted nothing"
    assert not stale, f"_vendor is stale for {len(stale)} committed file(s): {stale[:6]}"
