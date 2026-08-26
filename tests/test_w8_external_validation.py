"""Repo integrity checks (fresh-clone invariants)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_fresh_clone_workspace_members_are_tracked() -> None:
    """The workspace must be cloneable — lockfile and members tracked, no local paths."""
    assert (
        "uv.lock" in Path(".gitignore").read_text() is False
        or "uv.lock" not in Path(".gitignore").read_text()
    )
    cp = subprocess.run(["git", "ls-files", "uv.lock"], capture_output=True, text=True)
    assert "uv.lock" in cp.stdout, "uv.lock must be tracked (§46 pinning)"
    cp2 = subprocess.run(
        ["git", "ls-files", "packages/reports/pyproject.toml"], capture_output=True, text=True
    )
    assert "packages/reports/pyproject.toml" in cp2.stdout, (
        "packages/reports must be tracked (fresh clone)"
    )
