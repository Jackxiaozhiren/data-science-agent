"""Evidence construction for a completed tool call (audit §105, Phase 4 target 2).

Split out of ``dsa_agent.graph``, which held two jobs in one module: orchestrating a run and
deciding what a tool's output *proves*. The mapping below is pure -- tool name plus output object in,
an ``Evidence`` record or ``None`` out -- so it can be tested without an agent, and both orchestration
engines (``graph.run_analysis`` and ``langgraph_graph``) consume the same definition instead of one
importing the other's private helper.

Behaviour is a verbatim move: ``tests/unit/test_tool_evidence_seam.py`` compares every branch's
output against the pre-split function, including the branches that answer ``None``.
"""

from __future__ import annotations

import uuid
from typing import Any

from dsa_agent.state import Evidence


def build_tool_evidence(tool: str, call_id: str, output: Any) -> Evidence | None:
    """The evidence record this tool result supports, or ``None`` when it supports none.

    Unknown tools, an absent output, and a result that will not format all answer ``None``;
    the caller records no evidence rather than a fabricated one.
    """
    eid = f"E-{uuid.uuid4().hex[:8]}"
    claim = ""
    source_type: Any = "python"
    confidence = 0.7
    result: dict[str, Any] = {}
    try:
        if tool == "run_sql" and output is not None:
            source_type = "sql"
            result = {
                "columns": getattr(output, "columns", []),
                "row_count": getattr(output, "row_count", 0),
                "rows": getattr(output, "rows", [])[:5],
            }
            claim = f"SQL returned {result.get('row_count', 0)} rows"
            confidence = 0.85
        elif tool == "correlation_analysis" and output is not None:
            source_type = "statistical_test"
            result = {
                "r": getattr(output, "r", None),
                "p_value": getattr(output, "p_value", None),
                "method": getattr(output, "method", ""),
            }
            claim = f"Correlation {getattr(output, 'x', '')} vs {getattr(output, 'y', '')}: r={getattr(output, 'r', 0):.3f}"
            confidence = 0.8
        elif tool == "hypothesis_test" and output is not None:
            source_type = "statistical_test"
            result = {
                "statistic": getattr(output, "statistic", None),
                "p_value": getattr(output, "p_value", None),
                "test": getattr(output, "test", ""),
            }
            claim = f"Hypothesis test {getattr(output, 'test', '')}: p={getattr(output, 'p_value', 0):.4g}"
            confidence = 0.8
        elif tool == "regression_analysis" and output is not None:
            source_type = "model"
            result = {
                "metrics": getattr(output, "metrics", {}),
                "model": getattr(output, "model", ""),
            }
            claim = f"Regression {getattr(output, 'model', '')} metrics {getattr(output, 'metrics', {})}"
            confidence = 0.75
        elif tool in ("train_model", "evaluate_model") and output is not None:
            source_type = "model"
            result = {
                "metrics": getattr(output, "metrics", getattr(output, "cv_scores", {})),
                "model": getattr(output, "model", ""),
            }
            claim = f"Model {getattr(output, 'model', '')} evaluated"
            confidence = 0.75
        elif tool == "forecast" and output is not None:
            source_type = "model"
            result = {
                "forecast": getattr(output, "forecast", [])[:5],
                "mae": getattr(output, "metrics", {}).get("mae"),
                "method": getattr(output, "method", ""),
            }
            claim = f"Forecast {getattr(output, 'method', '')}: next {len(getattr(output, 'forecast', []))} periods, MAE={getattr(output, 'metrics', {}).get('mae', 0):.2f}"
            confidence = 0.7
        elif tool == "feature_importance" and output is not None:
            source_type = "model"
            imps = getattr(output, "importances", [])[:3]
            result = {"top_features": imps}
            claim = f"Top features for {getattr(output, 'target', '')}: {', '.join(i.get('feature', '') for i in imps)}"
            confidence = 0.7
        elif tool == "assumption_check" and output is not None:
            source_type = "statistical_test"
            result = {
                "checks": getattr(output, "checks", []),
                "passed": getattr(output, "passed", True),
            }
            claim = f"Assumption check: {getattr(output, 'recommendation', '')[:120]}"
            confidence = 0.75
        elif tool == "causal_check" and output is not None:
            source_type = "statistical_test"
            result = {
                "estimate": getattr(output, "estimate", 0),
                "method": getattr(output, "method", ""),
                "passes_causal_bar": getattr(output, "passes_causal_bar", False),
                "confidence_note": getattr(output, "confidence_note", ""),
            }
            claim = f"Causal check ({getattr(output, 'method', '')}): estimate={getattr(output, 'estimate', 0):.3f}, causal_bar={'pass' if getattr(output, 'passes_causal_bar', False) else 'fail'} — {getattr(output, 'confidence_note', '')[:100]}"
            confidence = 0.5
        elif tool == "create_chart" and output is not None:
            source_type = "visualization"
            result = {
                "artifact_path": getattr(output, "artifact_path", ""),
                "chart_type": getattr(output, "chart_type", ""),
            }
            claim = f"Chart {getattr(output, 'chart_type', '')} created"
            confidence = 0.7
        elif tool == "profile_dataset" and output is not None:
            source_type = "python"
            prof = getattr(output, "profile", {}) or {}
            result = {"rows": prof.get("rows"), "columns": prof.get("columns")}
            claim = f"Profile: {result.get('rows')} rows, {result.get('columns')} cols"
            confidence = 0.9
        elif tool == "run_python" and output is not None:
            source_type = "python"
            result = {
                "stdout": getattr(output, "stdout", "")[:500],
                "error": getattr(output, "error", None),
            }
            claim = "Python execution completed"
            confidence = 0.6
        else:
            return None
    except Exception:
        return None
    return Evidence(
        id=eid,
        claim=claim,
        source_type=source_type,
        source_id=call_id,
        result=result,
        confidence=confidence,
        validation_status="pending",
    )
