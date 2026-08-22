from __future__ import annotations

import json
from pathlib import Path

from dsa_evaluation.external_validation import (
    DEMO_QUESTION,
    collect_installation_metrics,
    fresh_machine_checklist,
    run_demo,
)


def test_demo_runs_locally() -> None:
    # Local-first: no cloud key, uses stub + DuckDB/Polars
    res = run_demo(question=DEMO_QUESTION)
    assert res.task_success is True, res.error
    assert res.n_tool_calls >= 2
    assert res.has_report is True
    assert res.error is None
    # Workdir contains artifacts
    assert (Path(res.workdir) / "report.md").exists()
    assert (Path(res.workdir) / "state.json").exists()


def test_installation_metrics_captured() -> None:
    # Do not run demo twice in this fast test — reuse run_demo gate above
    m = collect_installation_metrics(include_demo=False)
    assert m.python_version.startswith("3.")
    assert m.install_present is True
    # first_launch is import+bootstrap time
    assert m.first_launch_time_ms is not None
    assert m.benchmark_setup_time_ms is not None
    assert "cold_install_time_ms_note" in m.details.get(
        "cold_install_time_ms_note", ""
    ) or "cold_install" in json.dumps(m.details)


def test_fresh_machine_checklist_no_fabrication() -> None:
    c = fresh_machine_checklist()
    assert c["linux"]["tested_local"] is True
    assert c["macos"]["tested_local"] is True
    assert c["windows"]["tested_local"] is False  # do not claim Windows tested
    assert c["local_first"]["cloud_cost"] == "$0"
