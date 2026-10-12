"""Report artifacts for a finished run: the stored markdown, and the run's experiment record.

The rendering itself moved to :mod:`dsa_agent.report_export` under web plan R-06, which needs two
serialisations of one assembly (``findings`` and ``audited``) rather than one document with a second
renderer bolted beside it. This module keeps the names the graph, the reporting seam and the SDK call, and
its body is a delegation so a divergence between the stored report and the exported one is structurally
impossible -- ``test_report_export_pair`` pins exactly that.
"""

from __future__ import annotations

import json
from pathlib import Path

from dsa_agent.report_export import export_markdown, final_report_status
from dsa_agent.state import AnalysisState
from dsa_datasets.artifact_paths import artifact_root


def build_markdown_report(state: AnalysisState) -> str:
    """The audited report for one run -- one call to the export owner, no rendering of its own."""
    return export_markdown(state, "audited")


def write_report_artifacts(state: AnalysisState, out_dir: Path | None = None) -> dict[str, str]:
    root = out_dir or artifact_root("reports", state.run_id)
    root.mkdir(parents=True, exist_ok=True)
    md = build_markdown_report(state)
    md_path = root / "report.md"
    md_path.write_text(md, encoding="utf-8")
    exp = {
        "run_id": state.run_id,
        "dataset_id": state.dataset_id,
        "user_query": state.user_query,
        "status": final_report_status(state.status.value),
        "created_at": state.created_at.isoformat(),
        "tool_calls": len(state.tool_calls),
        "evidence": len(state.evidence),
    }
    exp_path = root / "experiment.json"
    exp_path.write_text(json.dumps(exp, indent=2), encoding="utf-8")
    return {"markdown": str(md_path), "experiment": str(exp_path)}
