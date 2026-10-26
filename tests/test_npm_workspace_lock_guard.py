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


def _resolve_both(root: Path, root_version: str, member_version: str) -> None:
    """Put the same specifier in both locks at two different resolved versions."""
    root_lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    root_lock["packages"]["node_modules/react"] = {"version": root_version}
    _write(root / "package-lock.json", root_lock)
    member_lock = json.loads((root / "apps/web/package-lock.json").read_text(encoding="utf-8"))
    member_lock["packages"]["node_modules/react"] = {"version": member_version}
    _write(root / "apps/web/package-lock.json", member_lock)


def _write_ledger(root: Path, keys: list[tuple[str, str]]) -> None:
    entries = [
        {"member": member, "package": package, "note": "test", "reviewed": "2026-10-26"}
        for member, package in keys
    ]
    _write(root / "docs/audit/npm-lock-divergences.json", {"divergences": entries})


def test_cross_lock_version_divergence_is_rejected_without_a_ledger_entry(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _resolve_both(workspace, root_version="19.2.7", member_version="19.2.8")
    assert lock_check.main() == 1
    output = capsys.readouterr().out
    assert (
        "apps/web:react resolves to 19.2.8 in the member lock but 19.2.7 in the root lock" in output
    )
    assert "(version)" in output
    assert "docs/audit/npm-lock-divergences.json" in output


def test_ledger_entry_admits_a_measured_divergence(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _resolve_both(workspace, root_version="19.2.7", member_version="19.2.8")
    _write_ledger(workspace, [("apps/web", "react")])
    assert lock_check.main() == 0
    assert (
        "1 divergence(s) named in docs/audit/npm-lock-divergences.json" in capsys.readouterr().out
    )


def test_reconciling_a_ledger_divergence_without_pruning_the_entry_is_rejected(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The exemption list cannot decay into a pile of permissions.

    Without this direction the file would keep covering a path long after the divergence it recorded
    was fixed, and the next divergence at that same path would be waved through by an entry nobody
    re-checked. The first half runs in the same test so the assertion cannot be satisfied by a
    comparison that never compared anything: admitted-then-pruned is one arc, and a neutralised
    detector fails the first step.
    """
    _resolve_both(workspace, root_version="19.2.7", member_version="19.2.8")
    _write_ledger(workspace, [("apps/web", "react")])
    assert lock_check.main() == 0, "the recorded divergence must be admitted first"
    capsys.readouterr()  # discard, so the assertion below can only see the reconcile step

    _resolve_both(workspace, root_version="19.2.8", member_version="19.2.8")
    assert lock_check.main() == 1
    assert (
        "lists apps/web:react, which no longer diverges -- prune the entry"
        in capsys.readouterr().out
    )


def test_nested_entries_are_not_compared_by_name(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """npm's layout choice is not a version violation, so the gate does not read it as one."""
    root_lock = json.loads((workspace / "package-lock.json").read_text(encoding="utf-8"))
    root_lock["packages"]["node_modules/next/node_modules/postcss"] = {"version": "8.5.31"}
    _write(workspace / "package-lock.json", root_lock)
    member_lock = json.loads((workspace / "apps/web/package-lock.json").read_text(encoding="utf-8"))
    member_lock["packages"]["node_modules/next/node_modules/postcss"] = {"version": "8.5.23"}
    _write(workspace / "apps/web/package-lock.json", member_lock)
    assert lock_check.main() == 0
    assert "divergence(s)" in capsys.readouterr().out


def test_placement_only_difference_is_reported_and_not_gated(
    workspace: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shape `apps/web:jiti` has on main: member top level, root resolves it nested elsewhere.

    Pinned so a later tightening cannot quietly turn a hoisting difference into a red gate -- the
    reclassification that moved this out of the ledger was measured, not assumed.
    """
    member_lock = json.loads((workspace / "apps/web/package-lock.json").read_text(encoding="utf-8"))
    member_lock["packages"]["node_modules/jiti"] = {"version": "2.7.0"}
    _write(workspace / "apps/web/package-lock.json", member_lock)
    root_lock = json.loads((workspace / "package-lock.json").read_text(encoding="utf-8"))
    root_lock["packages"]["node_modules/@tailwindcss/node/node_modules/jiti"] = {"version": "2.7.0"}
    _write(workspace / "package-lock.json", root_lock)
    assert lock_check.main() == 0
    output = capsys.readouterr().out
    assert "placement-only differences between the locks, deliberately not gated: 1" in output
    assert "apps/web:jiti" in output


def test_the_committed_ledger_names_exactly_the_committed_divergences() -> None:
    """`docs/audit/npm-lock-divergences.json` is re-derived from the lockfiles, not trusted.

    Same discipline as the npm advisory gate: the prose in that file is a claim about the tree, and a
    claim nobody recomputes is how an exemption list starts lying.

    The vacuity guard is deliberately about the corpus, not the result. Asserting a non-empty divergence
    set would freeze today's debt into an invariant and break the day someone reconciles it; asserting
    that many specifiers were compared is what keeps "zero divergences" meaningful, because a detector
    that looked at nothing could not produce that number.
    """
    root_packages = lock_check._load_json(lock_check.ROOT / "package-lock.json")["packages"]
    found: set[str] = set()
    compared = 0
    for member in ("apps/web", "apps/vscode"):
        member_packages = lock_check._load_json(lock_check.ROOT / member / "package-lock.json")[
            "packages"
        ]
        compared += len(lock_check._member_root_specifiers(member_packages))
        found |= {
            f"{item['member']}:{item['package']}"
            for item in lock_check._cross_lock_divergences(root_packages, member, member_packages)
            if item["kind"] != "placement"
        }
    assert found == lock_check._ledger_keys(), sorted(found ^ lock_check._ledger_keys())
    assert compared > 100, f"the comparison looked at only {compared} specifiers"
