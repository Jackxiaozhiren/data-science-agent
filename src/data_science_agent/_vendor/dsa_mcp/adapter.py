from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from dsa_mcp.resources import _discover_datasets, store_analysis

ToolClass = Literal["SAFE_READ", "ANALYSIS", "COMPUTE", "WRITE_ARTIFACT", "DESTRUCTIVE"]


class MCPToolDef(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    idempotency: bool = False
    timeout_ms: int = 30000
    cost_class: str = "low"
    tool_class: ToolClass = "ANALYSIS"
    cache_hint: str | None = None


MCP_TOOL_MAP: dict[str, str] = {
    "profile_dataset": "profile_dataset",
    "inspect_dataset": "profile_dataset",
    "query_dataset": "run_sql",
    "run_sql": "run_sql",
    "run_python": "run_python",
    "run_statistical_test": "hypothesis_test",
    "correlation_analysis": "correlation_analysis",
    "forecast": "forecast",
    "assumption_check": "assumption_check",
    "causal_check": "causal_check",
    "train_model": "train_model",
    "evaluate_model": "evaluate_model",
    "feature_importance": "feature_importance",
    "create_visualization": "create_chart",
    "get_evidence": "create_evidence",
    "generate_report": "generate_report",
    "save_artifact": "save_artifact",
    "export_artifact": "export_artifact",
    "analyze": "analyze",  # §36 full loop Dataset→Question→Analysis→Evidence→Viz→Report
}

MCP_TOOL_CLASS: dict[str, ToolClass] = {
    "profile_dataset": "SAFE_READ",
    "inspect_dataset": "SAFE_READ",
    "query_dataset": "ANALYSIS",
    "run_sql": "ANALYSIS",
    "run_python": "COMPUTE",
    "run_statistical_test": "ANALYSIS",
    "correlation_analysis": "ANALYSIS",
    "forecast": "COMPUTE",
    "assumption_check": "ANALYSIS",
    "causal_check": "ANALYSIS",
    "train_model": "COMPUTE",
    "evaluate_model": "ANALYSIS",
    "feature_importance": "COMPUTE",
    "create_visualization": "WRITE_ARTIFACT",
    "get_evidence": "SAFE_READ",
    "generate_report": "WRITE_ARTIFACT",
    "save_artifact": "WRITE_ARTIFACT",
    "export_artifact": "WRITE_ARTIFACT",
    "analyze": "COMPUTE",
}

MCP_IDEMPOTENT = {
    "profile_dataset",
    "inspect_dataset",
    "query_dataset",
    "run_sql",
    "correlation_analysis",
    "assumption_check",
    "forecast",
}
MCP_WRITE = {"generate_report", "save_artifact", "export_artifact", "create_visualization"}

MCP_DESCRIPTIONS: dict[str, str] = {
    "profile_dataset": "Profile a dataset file (schema, missing, duplicates, cardinality).",
    "inspect_dataset": "Inspect dataset schema / columns (alias of profile_dataset).",
    "query_dataset": "Run a SELECT SQL query against a dataset exposed as 'dataset'.",
    "run_sql": "Execute read-only SQL against a dataset (DuckDB, row-limited).",
    "run_python": "Execute Python in a restricted sandbox with dataset as df (Polars).",
    "run_statistical_test": "Run hypothesis tests (t/welch/mann-whitney/anova/kruskal/chi2).",
    "correlation_analysis": "Correlation (pearson/spearman/kendall) with p-value and CI.",
    "forecast": "Baseline time-series forecast (linear_trend/moving_average/naive_trend) with holdout MAE.",
    "assumption_check": "Check statistical assumptions (Shapiro normality, Levene homogeneity).",
    "causal_check": "Causal stub: association vs causation guard (never returns causal effect without bar).",
    "train_model": "Train a baseline model with cross-validation.",
    "evaluate_model": "Evaluate a model on holdout (accuracy/F1/ROC or MAE/RMSE/R2).",
    "feature_importance": "Feature importance via RandomForest with chart artifact.",
    "create_visualization": "Create a chart (histogram/bar/scatter/line/boxplot/heatmap) as PNG artifact.",
    "get_evidence": "Create or validate an evidence record for a claim.",
    "generate_report": "Generate report.md + experiment.json + reproduce.sh + notebook.",
    "save_artifact": "Save an artifact under artifacts/<run_id>/",
    "export_artifact": "Persist a prior tool result to a file in the run workspace (csv/xlsx/png, byte-identical).",
    "analyze": "Run full analysis (§36 Dataset→Question→Analysis→Evidence→Viz→Report) — stateless with explicit run_id handle.",
}

#: Names this surface publishes for canonical run fields: MCP keeps the SDK's `validation` spelling and
#: adds `analysis_id` as the handle alias of `run_id` (§38).
MCP_RUN_ALIASES = {"validation": "validation_results", "analysis_id": "run_id"}

EVIDENCE_VIA_VALIDATE = {"validate_result"}


def _tool_input_schema(backend: str) -> dict[str, Any]:
    from dsa_tools import get as get_tool

    tool = get_tool(backend)
    try:
        return tool.input_model.model_json_schema()  # type: ignore[no-any-return]
    except Exception:
        return {"type": "object", "properties": {}}


def _tool_output_schema(backend: str) -> dict[str, Any]:
    from dsa_tools import get as get_tool

    tool = get_tool(backend)
    try:
        return tool.output_model.model_json_schema()  # type: ignore[no-any-return]
    except Exception:
        return {"type": "object", "properties": {}}


def _analyze_input_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "dataset": {
                "type": "string",
                "description": "Dataset path or dataset_id (e.g. sales.csv or dataset://sales)",
            },
            "dataset_path": {"type": "string", "description": "Alias for dataset"},
            "task": {"type": "string", "description": "Natural-language question"},
            "question": {"type": "string", "description": "Alias for task"},
            "run_id": {"type": "string", "description": "Optional explicit run_id handle (§38)"},
        },
        "required": ["task"],
    }


def _analyze_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "description": "Explicit handle (§38)"},
            "analysis_id": {
                "type": "string",
                "description": "Alias of run_id, emitted for handle compatibility (§38)",
            },
            "status": {"type": "string"},
            "report_markdown": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "insights": {"type": "array", "items": {"type": "object"}},
            "artifacts": {"type": "array", "items": {"type": "object"}},
            "tool_calls": {"type": "array", "items": {"type": "object"}},
            "validation": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Evidence-critic verdicts; the same checks the SDK and REST publish",
            },
            "error": {"type": ["string", "null"]},
        },
        "required": ["run_id", "status"],
    }


def list_mcp_tools() -> list[MCPToolDef]:
    from dsa_tools import bootstrap, list_tools

    if not list_tools():
        bootstrap()
    out: list[MCPToolDef] = []
    for mcp_name, backend in MCP_TOOL_MAP.items():
        if mcp_name == "analyze":
            schema = _analyze_input_schema()
            out_schema = _analyze_output_schema()
        else:
            schema = _tool_input_schema(
                backend if MCP_TOOL_MAP[mcp_name] != "inspect_dataset" else "profile_dataset"
            )
            out_schema = _tool_output_schema(
                backend if MCP_TOOL_MAP[mcp_name] != "inspect_dataset" else "profile_dataset"
            )
        desc = MCP_DESCRIPTIONS.get(mcp_name, backend)
        klass = MCP_TOOL_CLASS.get(mcp_name, "ANALYSIS")
        is_idem = mcp_name in MCP_IDEMPOTENT
        is_write = mcp_name in MCP_WRITE
        out.append(
            MCPToolDef(
                name=mcp_name,
                description=desc,
                input_schema=schema,
                output_schema=out_schema,
                permissions=["read"]
                if klass in ("SAFE_READ", "ANALYSIS")
                else (["write"] if is_write else ["compute"]),
                idempotency=is_idem,
                timeout_ms=30000 if klass == "COMPUTE" else 10000,
                cost_class="high"
                if klass == "COMPUTE"
                else ("medium" if klass == "ANALYSIS" else "low"),
                tool_class=klass,
                cache_hint="max-age=60" if is_idem else None,
            )
        )
    return out


def list_tools() -> list[dict[str, Any]]:
    return [t.model_dump(mode="json") for t in list_mcp_tools()]


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Stateless dispatch: validate → call backend BaseTool → return output/error. §38 explicit handles."""
    # §36 analyze — full loop with explicit handles (stateless)
    if name == "analyze":
        # Resolve dataset: support dataset://, dataset_path, dataset
        raw_ds = (
            arguments.get("dataset")
            or arguments.get("dataset_path")
            or arguments.get("dataset_id")
            or ""
        )
        task = arguments.get("task") or arguments.get("question") or ""
        run_id = arguments.get("run_id") or arguments.get("analysis_id")
        if not raw_ds:
            # try discover default
            raw_ds = "benchmarks/v2/datasets/sales.csv"
        if not task:
            return {
                "isError": True,
                "error": "task/question required for analyze (§36)",
                "mcp_tool": name,
            }
        # Resolve dataset:// URI
        if isinstance(raw_ds, str) and raw_ds.startswith("dataset://"):
            ds_id = raw_ds[len("dataset://") :]
            for ds in _discover_datasets():
                if ds["id"] == ds_id:
                    raw_ds = ds["path"]
                    break
        # Execute via Agent (stateless, explicit run_id §38)
        try:
            import json as _json

            from data_science_agent import Agent

            agent = Agent()
            analysis_res = await agent.analyze(raw_ds, task, run_id=run_id)
            from dsa_agent.run_summary import normalize_records, run_summary

            summary = run_summary(analysis_res.raw_state) if analysis_res.raw_state else {}
            payload_raw = {
                "run_id": analysis_res.run_id,
                "analysis_id": analysis_res.run_id,
                "status": analysis_res.status,
                "report_markdown": summary.get("report_markdown", analysis_res.report_markdown),
                "evidence": summary.get("evidence") or normalize_records(analysis_res.evidence),
                "insights": summary.get("insights") or normalize_records(analysis_res.insights),
                "artifacts": summary.get("artifacts") or normalize_records(analysis_res.artifacts),
                "tool_calls": summary.get("tool_calls")
                or normalize_records(analysis_res.tool_calls),
                # §108: the critic's verdicts and the run's error are part of the same contract the
                # SDK and REST publish. An MCP client that cannot see them cannot tell a verified
                # analysis from an unvalidated one.
                "validation": (
                    summary.get("validation_results") or normalize_records(analysis_res.validation)
                ),
                "error": summary.get("error", analysis_res.error),
            }
            # Ensure JSON serializable (§38, MCP spec)
            payload = _json.loads(_json.dumps(payload_raw, default=str, ensure_ascii=False))
            # Store for explicit resource handles (§38)
            store_analysis(analysis_res.run_id, payload)
            return {
                "isError": False,
                "mcp_tool": name,
                "tool": "analyze",
                "output": payload,
                "call_id": analysis_res.run_id,
            }
        except Exception as e:
            return {"isError": True, "mcp_tool": name, "error": str(e)}

    from dsa_tools import bootstrap, list_tools
    from dsa_tools import get as get_tool

    if not list_tools():
        bootstrap()
    backend = MCP_TOOL_MAP.get(name)
    if backend is None:
        return {
            "isError": True,
            "error": f"Unknown MCP tool: {name}",
            "available": sorted(MCP_TOOL_MAP),
        }
    if name == "inspect_dataset":
        backend = "profile_dataset"
    if name == "query_dataset":
        backend = "run_sql"
        if "sql" not in arguments and "query" in arguments:
            arguments = {**arguments, "sql": arguments["query"]}
    if name == "get_evidence":
        if "check_type" in arguments or arguments.get("mode") == "validate":
            backend = "validate_result"
        else:
            backend = "create_evidence"

    tool = get_tool(backend)
    tool_result = await tool.run(arguments)
    if tool_result.status == "ok":
        out_val = tool_result.output
        if out_val is not None:
            out = out_val.model_dump(mode="json") if hasattr(out_val, "model_dump") else out_val
            return {
                "isError": False,
                "tool": backend,
                "mcp_tool": name,
                "call_id": tool_result.call_id,
                "output": out,
            }
        return {
            "isError": False,
            "tool": backend,
            "mcp_tool": name,
            "call_id": tool_result.call_id,
            "output": {},
        }
    return {
        "isError": True,
        "tool": backend,
        "mcp_tool": name,
        "call_id": tool_result.call_id,
        "error": tool_result.error,
    }
