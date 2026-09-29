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


def test_check_sees_a_copy_whose_named_source_was_deleted(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, VENDOR / "dsa_reports", {"__init__.py": b"STALE\n"})

    result = _run(root, "--check")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "dsa_reports" in result.stderr
    assert (root / VENDOR / "dsa_reports/__init__.py").read_bytes() == b"STALE\n"


def test_sync_names_only_the_package_that_actually_changed(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"AGENT\n"})
    _make(root, API_SRC, {"__init__.py": b"API\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"STALE\n"})
    _make(root, VENDOR / "dsa_api", {"__init__.py": b"API\n"})

    result = _run(root, "--all")

    assert result.returncode == 0, result.stdout + result.stderr
    out = result.stdout
    assert "dsa_agent/__init__.py" in out, out
    assert "dsa_api" not in out, out
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"AGENT\n"
    assert _run(root, "--check").returncode == 0


# --- repair scoping (D-INFRA-05) -------------------------------------------------------


def test_bare_repair_refuses_instead_of_adopting_every_drifted_package(
    tmp_path: Path,
) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"AGENT\n"})
    _make(root, API_SRC, {"__init__.py": b"API\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"STALE\n"})
    _make(root, VENDOR / "dsa_api", {"__init__.py": b"STALE\n"})

    result = _run(root)

    assert result.returncode != 0, "a bare run repaired two packages unasked"
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"STALE\n"
    assert (root / VENDOR / "dsa_api/__init__.py").read_bytes() == b"STALE\n"
    assert "--package" in result.stdout + result.stderr


def test_package_scope_leaves_another_drifted_package_alone(tmp_path: Path) -> None:
    """The hazard this flag exists for: a foreign edit in a second package must not be copied."""
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"MINE\n"})
    _make(root, API_SRC, {"__init__.py": b"SOMEONE_ELSES_WIP\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"OLD\n"})
    _make(root, VENDOR / "dsa_api", {"__init__.py": b"OLD\n"})

    result = _run(root, "--package", "dsa_agent")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"MINE\n"
    assert (root / VENDOR / "dsa_api/__init__.py").read_bytes() == b"OLD\n", (
        "the scoped repair pulled an unrelated package's source into the mirror"
    )


def test_file_scope_writes_exactly_one_file(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"A\n", "graph.py": b"GRAPH\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"OLD\n", "graph.py": b"OLD\n"})

    result = _run(root, "--file", "packages/agent/src/dsa_agent/graph.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / VENDOR / "dsa_agent/graph.py").read_bytes() == b"GRAPH\n"
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"OLD\n", (
        "--file silently did a whole-package copy"
    )


def test_file_scope_outside_the_known_sources_writes_nothing(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"A\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"OLD\n"})

    result = _run(root, "--file", "packages/agent/src/dsa_agent/nope.py")

    assert result.returncode != 0
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"OLD\n"


def test_all_flag_keeps_the_bulk_repair_available(tmp_path: Path) -> None:
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"A\n"})
    _make(root, API_SRC, {"__init__.py": b"B\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"OLD\n"})
    _make(root, VENDOR / "dsa_api", {"__init__.py": b"OLD\n"})

    result = _run(root, "--all")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / VENDOR / "dsa_agent/__init__.py").read_bytes() == b"A\n"
    assert (root / VENDOR / "dsa_api/__init__.py").read_bytes() == b"B\n"


def test_package_scope_propagates_a_deleted_source_file(tmp_path: Path) -> None:
    """A copy-only repair would keep shipping a module its source no longer has."""
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"A\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"A\n", "removed.py": b"GONE\n"})

    result = _run(root, "--package", "dsa_agent")

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (root / VENDOR / "dsa_agent/removed.py").exists(), (
        "the vendored copy of a deleted module is still shipped"
    )
    assert "removed.py" in result.stdout, "the deletion happened silently"


def test_check_advice_names_a_scoped_command_not_a_bare_one(tmp_path: Path) -> None:
    """The old hint told people to run the tool that adopts someone else's work-in-progress."""
    root = _scratch(tmp_path)
    _make(root, AGENT_SRC, {"__init__.py": b"AGENT\n"})
    _make(root, VENDOR / "dsa_agent", {"__init__.py": b"STALE\n"})

    result = _run(root, "--check")

    assert "--package" in result.stderr, result.stderr
    assert "dsa_agent" in result.stderr
