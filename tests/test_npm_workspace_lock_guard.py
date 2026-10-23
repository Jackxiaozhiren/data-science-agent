"""Guard the root and committed member npm workspace lockfiles."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_npm_workspace_lock.py"
SPEC = importlib.util.spec_from_file_location("workspace_lock_check_for_tests", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
lock_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lock_check)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path
    _write(
        root / "package.json",
        {
            "workspaces": ["apps/*"],
            "dependencies": {"postcss": "8.5.31"},
        },
    )
    _write(
        root / "package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"dependencies": {"postcss": "8.5.31"}},
                "apps/web": {"dependencies": {"react": "19.2.8"}},
            },
        },
    )
    _write(root / "apps/web/package.json", {"dependencies": {"react": "19.2.8"}})
    _write(
        root / "apps/web/package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"dependencies": {"react": "19.2.8"}},
            },
        },
    )
    monkeypatch.setattr(lock_check, "ROOT", root)
    return root


def test_consistent_root_and_member_locks_pass(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert lock_check.main() == 0
    assert "matches all workspace manifests" in capsys.readouterr().out


def test_member_lock_mismatch_is_rejected_even_if_root_matches(
    workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        workspace / "apps/web/package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"dependencies": {"react": "19.2.7"}},
            },
        },
    )
    assert lock_check.main() == 1
    output = capsys.readouterr().out
    assert "apps/web/package-lock.json dependencies.react" in output
    assert "manifest='19.2.8'" in output
    assert "lock='19.2.7'" in output


def test_member_lock_missing_package_mapping_is_rejected(
    workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(workspace / "apps/web/package-lock.json", {"lockfileVersion": 3})
    assert lock_check.main() == 1
    assert "apps/web/package-lock.json: missing packages mapping" in capsys.readouterr().out


def test_member_lock_without_root_entry_is_rejected(
    workspace: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        workspace / "apps/web/package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "node_modules/react": {"version": "19.2.8"},
            },
        },
    )
    assert lock_check.main() == 1
    assert "apps/web/package-lock.json: missing" in capsys.readouterr().out


def test_workspace_without_member_lock_uses_root_lock(
    workspace: Path,
) -> None:
    (workspace / "apps/web/package-lock.json").unlink()
    assert lock_check.main() == 0
