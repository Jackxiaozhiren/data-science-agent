"""`sync_vendor --check` audits `_vendor` without repairing it, and reports honestly.

Every case builds a scratch tree whose `scripts/sync_vendor.py` copy resolves
`ROOT` to that tree, so nothing here can touch the real vendored modules.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REAL_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_vendor.py"

# Two of the real SOURCES entries, enough to exercise per-package reporting.
AGENT_SRC = Path("packages/agent/src/dsa_agent")
API_SRC = Path("apps/api/src/dsa_api")
VENDOR = Path("src/data_science_agent/_vendor")


def _scratch(tmp_path: Path) -> Path:
    script = tmp_path / "scripts" / "sync_vendor.py"
    script.parent.mkdir(parents=True)
    shutil.copy(REAL_SCRIPT, script)
    return tmp_path


def _make(root: Path, base: Path, files: dict[str, bytes]) -> None:
    for name, body in files.items():
        target = root / base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts/sync_vendor.py"), *args],
        capture_output=True,
        text=True,
    )


def test_check_reports_drift_without_rewriting_the_copy_it_audits(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"SOURCE\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"DRIFTED\n"})

    result = _run(root, "--check")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "dsa_agent" in result.stderr
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"DRIFTED\n"


def test_check_accepts_a_faithful_copy_and_ignores_bytecode(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"X\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"X\n"})
    _make(root, VENDOR / "dsa_agent/__pycache__", {"x.cpython-312.pyc": b"junk\n"})

    result = _run(root, "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_check_sees_a_vendored_copy_no_workspace_source_backs(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, VENDOR / "dsa_gone", {"__init__.py": b"STALE\n"})

    result = _run(root, "--check")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "dsa_gone" in result.stderr


def test_sync_names_only_the_package_that_actually_changed(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"AGENT\n"})
    _make(root, API_SRC, {"__init__.py": b"API\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"STALE\n"})
    _make(root, VENDOR / "dsa_api", {"__init__.py": b"API\n"})

    result = _run(root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "Synced: dsa_agent"
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"AGENT\n"
    assert _run(root, "--check").returncode == 0
