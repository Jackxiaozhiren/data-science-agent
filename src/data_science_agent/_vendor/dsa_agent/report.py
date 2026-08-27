from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dsa_agent.state import AnalysisState


def build_markdown_report(state: AnalysisState) -> str:
    lines: list[str] = []
    lines.append(f"# Analysis Report — {state.run_id}")
    lines.append("")
    lines.append(f"**Objective:** {state.objective or state.user_query}")
    lines.append(
        f"**Dataset:** `{state.dataset_id}`  |  **Status:** {state.status.value}  |  **Generated:** {datetime.now(UTC).isoformat()}"
    )
    lines.append("")
    lines.append("## Plan")
    for s in state.plan:
        lines.append(f"- **{s.name}** (`{s.tool}`): {s.description}")
    lines.append("")
    lines.append("## Tool Calls")
    for tc in state.tool_calls:
        status = "✓" if tc.status == "ok" else "✗"
        lines.append(f"- {status} **{tc.tool}** ({tc.call_id}) — {tc.duration_ms}ms")
        if tc.error:
            lines.append(f"  - error: {tc.error}")
        if tc.tool == "create_chart" and tc.output:
            ap = (
                tc.output.get("artifact_path")
                if isinstance(tc.output, dict)
                else getattr(tc.output, "artifact_path", None)
            )
            if ap:
                rel = Path(str(ap)).name
                # artifact lives under artifacts/reports/<run_id>/ — link relative for markdown readers
                lines.append(f"  - ![chart]({rel})")
                lines.append(f"  - artifact: `{ap}`")
    lines.append("")
    lines.append("## Evidence")
    for ev in state.evidence:
        lines.append(
            f"- **{ev.id}** ({ev.source_type} → {ev.source_id}) — {ev.claim} — confidence {ev.confidence:.2f} — {ev.validation_status}"
        )
        if ev.result:
            snippet = json.dumps(ev.result, ensure_ascii=False, default=str)[:600]
            lines.append(f"  - result: `{snippet}`")
    lines.append("")
    lines.append("## Insights")
    if not state.insights:
        lines.append("_No insights yet — analysis may be incomplete or blocked by validation._")
    for ins in state.insights:
        lines.append(f"- **{ins.id}**: {ins.finding}")
        if ins.magnitude:
            lines.append(f"  - magnitude: {ins.magnitude}")
        if ins.significance:
            lines.append(f"  - significance: {ins.significance}")
        if ins.limitation:
            lines.append(f"  - limitation: {ins.limitation}")
        if ins.evidence_ids:
            lines.append(f"  - evidence: {', '.join(ins.evidence_ids)}")
    lines.append("")
    lines.append("## Validation")
    for vr in state.validation_results:
        mark = "✓" if vr.passed else "✗"
        lines.append(f"- {mark} **{vr.check}**: {vr.message}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("- Correlation does not imply causation unless causal evidence is established.")
    lines.append(
        "- Reproducibility bundle includes dataset hash, code, and parameters where available."
    )
    lines.append("")
    return "\n".join(lines)


def write_report_artifacts(state: AnalysisState, out_dir: Path | None = None) -> dict[str, str]:
    root = out_dir or (Path(__file__).resolve().parents[4] / "artifacts" / "reports" / state.run_id)
    root.mkdir(parents=True, exist_ok=True)
    md = build_markdown_report(state)
    md_path = root / "report.md"
    md_path.write_text(md, encoding="utf-8")
    exp = {
        "run_id": state.run_id,
        "dataset_id": state.dataset_id,
        "user_query": state.user_query,
        "status": state.status.value,
        "created_at": state.created_at.isoformat(),
        "tool_calls": len(state.tool_calls),
        "evidence": len(state.evidence),
    }
    exp_path = root / "experiment.json"
    exp_path.write_text(json.dumps(exp, indent=2), encoding="utf-8")
    return {"markdown": str(md_path), "experiment": str(exp_path)}
