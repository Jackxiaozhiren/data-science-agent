"""Rich display for Analysis in Jupyter (§29-30)."""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

try:
    from IPython.display import HTML, Image, Markdown, display  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    HTML = Image = Markdown = display = None  # type: ignore[assignment]

from dsa_jupyter.metadata import collect_notebook_metadata


def _h(s: str) -> str:
    return html.escape(s)


def format_analysis_html(analysis: Any, dataset: str | None = None, task: str | None = None) -> str:
    """Return HTML for Analysis (§29-30)."""
    # analysis is data_science_agent.sdk.Analysis
    run_id = getattr(analysis, "run_id", "unknown")
    status = getattr(analysis, "status", "unknown")
    report = getattr(analysis, "report_markdown", "") or ""
    evidence = getattr(analysis, "evidence", []) or []
    insights = getattr(analysis, "insights", []) or []
    artifacts = getattr(analysis, "artifacts", []) or []
    tool_calls = getattr(analysis, "tool_calls", []) or []
    meta = collect_notebook_metadata(dataset, task, run_id)

    # header
    hdr = f"""
    <div style="border:1px solid #ddd; padding:12px; border-radius:8px; margin:8px 0;">
      <h3 style="margin:0;">🔬 Analysis { _h(run_id) } <span style="color:{'#0a0' if status=='COMPLETED' else '#a00'};">{ _h(status) }</span></h3>
      <small>Dataset: { _h(str(dataset) if dataset else '—')} | Task: { _h(task[:80] if task else '—')} | sdk:{ _h(meta['sdk_version'])} agent:{ _h(meta['agent_version'])} exp:{ _h(meta['experiment_id'])}</small><br/>
      <small style="color:#666;">dataset_hash:{ _h(str(meta['dataset_hash']))} prompt:{ _h(str(meta['prompt_version']))} tool:{ _h(str(meta['tool_version']))}</small>
    </div>
    """

    # report (first 2000 chars)
    report_html = ""
    if report:
        # Use markdown-like simple rendering (escape and preserve)
        snippet = report[:2000]
        report_html = f"<div style='background:#fafafa; padding:12px; border:1px solid #eee; border-radius:6px; margin:8px 0;'><h4>📄 Report</h4><pre style='white-space:pre-wrap;'>{ _h(snippet)}</pre></div>"

    # progress — tool calls summary
    progress_html = f"<div style='margin:8px 0;'><h4>⚙️ Progress — {len(tool_calls)} tool calls</h4><ul>"
    for tc in tool_calls[:10]:
        name = tc.get("name") or tc.get("tool") or "tool"
        st = tc.get("status", "ok")
        progress_html += f"<li>{ _h(str(name))} — { _h(str(st))}</li>"
    if len(tool_calls) > 10:
        progress_html += f"<li>… +{len(tool_calls)-10} more</li>"
    progress_html += "</ul></div>"

    # evidence table
    ev_html = f"<div><h4>🔗 Evidence — {len(evidence)} records</h4>"
    if evidence:
        ev_html += "<table style='border-collapse:collapse; width:100%; font-size:90%;'><tr><th style='border:1px solid #ddd; padding:4px;'>id</th><th style='border:1px solid #ddd; padding:4px;'>claim</th><th style='border:1px solid #ddd; padding:4px;'>source</th><th style='border:1px solid #ddd; padding:4px;'>confidence</th></tr>"
        for ev in evidence[:10]:
            ev_id = getattr(ev, "id", ev.get("id", "")) if isinstance(ev, dict) else getattr(ev, "id", "")
            claim = getattr(ev, "claim", ev.get("claim", "")) if isinstance(ev, dict) else getattr(ev, "claim", "")
            src = getattr(ev, "source_type", ev.get("source_type", "")) if isinstance(ev, dict) else getattr(ev, "source_type", "")
            conf = getattr(ev, "confidence", ev.get("confidence", "")) if isinstance(ev, dict) else getattr(ev, "confidence", "")
            ev_html += f"<tr><td style='border:1px solid #ddd; padding:4px;'>{ _h(str(ev_id))}</td><td style='border:1px solid #ddd; padding:4px;'>{ _h(str(claim)[:120])}</td><td style='border:1px solid #ddd; padding:4px;'>{ _h(str(src))}</td><td style='border:1px solid #ddd; padding:4px;'>{ _h(str(conf))}</td></tr>"
        if len(evidence) > 10:
            ev_html += f"<tr><td colspan=4>… +{len(evidence)-10} more</td></tr>"
        ev_html += "</table></div>"
    else:
        ev_html += "<p><em>No evidence</em></p></div>"

    # insights
    ins_html = f"<div><h4>💡 Insights — {len(insights)} </h4><ul>"
    for ins in insights[:5]:
        finding = getattr(ins, "finding", ins.get("finding", "")) if isinstance(ins, dict) else getattr(ins, "finding", "")
        ins_html += f"<li>{ _h(str(finding)[:200])}</li>"
    ins_html += "</ul></div>"

    # artifacts — charts as images if exists
    art_html = f"<div><h4>📦 Artifacts — {len(artifacts)} </h4><ul>"
    for art in artifacts[:5]:
        art_type = getattr(art, "type", art.get("type", "")) if isinstance(art, dict) else getattr(art, "type", "")
        art_path = getattr(art, "path", art.get("path", "")) if isinstance(art, dict) else getattr(art, "path", "")
        art_html += f"<li>{ _h(str(art_type))}: { _h(str(art_path))}</li>"
    art_html += "</ul></div>"

    # full HTML
    return hdr + report_html + progress_html + ev_html + ins_html + art_html


def display_analysis(analysis: Any, dataset: str | None = None, task: str | None = None) -> None:
    """Display Analysis rich in notebook (§29-30). Falls back to print."""
    if display is None:
        print(f"Analysis {getattr(analysis,'run_id','?')} status={getattr(analysis,'status','?')}")
        return
    html_str = format_analysis_html(analysis, dataset, task)
    display(HTML(html_str))
    # Display report as Markdown for nice rendering
    report = getattr(analysis, "report_markdown", None)
    if report and Markdown is not None:
        display(Markdown(report[:3000]))
    # Display chart artifacts inline (last one)
    artifacts = getattr(analysis, "artifacts", []) or []
    for art in artifacts:
        art_type = getattr(art, "type", art.get("type", "")) if isinstance(art, dict) else getattr(art, "type", "")
        art_path = getattr(art, "path", art.get("path", "")) if isinstance(art, dict) else getattr(art, "path", "")
        if art_type == "chart" and art_path and Path(art_path).exists() and Image is not None:
            try:
                display(Image(filename=str(art_path)))
            except Exception:
                pass
            break
    # Also handle base64 in tool outputs? For ForecastTool viz, not yet — artifact is file.
    # If analysis has tool_calls with base64_png, show it
    tool_calls = getattr(analysis, "tool_calls", []) or []
    for tc in tool_calls:
        result = tc.get("result") if isinstance(tc, dict) else {}
        if isinstance(result, dict) and result.get("base64_png"):
            try:
                png = base64.b64decode(result["base64_png"])
                display(Image(data=png))
            except Exception:
                pass
            break


def register_formatter(ipython: Any) -> None:
    """Register Analysis formatter for auto-display (so `result` shows rich)."""
    try:
        from data_science_agent.sdk import Analysis

        def _fmt(analysis: Any) -> str:
            return format_analysis_html(analysis)

        # HTML formatter
        html_formatter = ipython.display_formatter.formatters["text/html"]
        html_formatter.for_type(Analysis, lambda obj, p, cycle: format_analysis_html(obj))  # type: ignore[attr-defined]
        # Also plain
        plain = ipython.display_formatter.formatters["text/plain"]
        plain.for_type(Analysis, lambda obj, p, cycle: f"Analysis({obj.run_id}, {obj.status}, {len(obj.evidence)} evidence)")
    except Exception:
        pass
