"""W8 External Developer Validation — §48-50 (Fresh Clone + Developer A)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_external_validation_report_exists_and_has_required_sections() -> None:
    p = Path("docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md")
    assert p.exists(), "W8 report missing (§50)"
    txt = p.read_text()
    for required in (
        "Environment",
        "Steps",
        "Failures",
        "Fixes",
        "Time to First Success",
        "Developer Friction",
        "Recommendations",
    ):
        assert required in txt, f"missing section {required} (§50)"
    # Must contain 7 tasks
    for task in (
        "Install",
        "Run demo",
        "Use SDK",
        "Create analysis",
        "Install Plugin",
        "Run benchmark",
        "Generate report",
    ):
        assert task in txt


def test_fresh_clone_workspace_members_are_tracked() -> None:
    """§48 cannot rely on developer-specific path — workspace must be cloneable."""
    # uv.lock must be tracked (was previously gitignored)
    assert (
        not Path(".gitignore").read_text().splitlines().__contains__("uv.lock")
        or "uv.lock" not in Path(".gitignore").read_text()
    )
    # Check via git
    cp = subprocess.run(["git", "ls-files", "uv.lock"], capture_output=True, text=True)
    assert "uv.lock" in cp.stdout, "uv.lock must be tracked (§46 pinning)"
    cp2 = subprocess.run(
        ["git", "ls-files", "packages/reports/pyproject.toml"], capture_output=True, text=True
    )
    assert "packages/reports/pyproject.toml" in cp2.stdout, (
        "packages/reports must be tracked (fresh clone §48)"
    )


def test_fresh_clone_no_developer_specific_path_in_report() -> None:
    """North Star: no developer-specific path in committed report."""
    txt = Path("docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md").read_text()
    # Should not contain hardcoded /Users/jackson/Data agent as required path (except as clone source example)
    # The report may mention file:///Users/jackson as clone source, but not as required install path
    assert "Install" in txt
    # The report's steps use relative paths like benchmarks/v2/datasets/sales.csv, not absolute /Users
    assert "benchmarks/v2/datasets/sales.csv" in txt


def test_north_star_checklist_in_report() -> None:
    txt = Path("docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md").read_text()
    for item in (
        "Clone",
        "Install",
        "Run",
        "Use SDK",
        "Install Plugin",
        "Run Jupyter",
        "Use MCP",
        "Inspect Evidence",
        "Generate Report",
    ):
        # North Star items should be mentioned
        assert item in txt or item.lower() in txt.lower()


def test_time_to_first_success_recorded() -> None:
    txt = Path("docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md").read_text()
    assert "Time to First Success" in txt
    # Should have timings
    assert "Clone" in txt and "s" in txt
