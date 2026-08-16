from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPToolDef(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


MCP_TOOL_MAP: dict[str, str] = {
    # mcp_name -> backend tool name (dsa_tools registry)
    "profile_dataset": "profile_dataset",
    "inspect_dataset": "profile_dataset",
    "query_dataset": "run_sql",
    "run_sql": "run_sql",
    "run_python": "run_python",
    "run_statistical_test": "hypothesis_test",
    "correlation_analysis": "correlation_analysis",
    "train_model": "train_model",
    "evaluate_model": "evaluate_model",
    "create_visualization": "create_chart",
    "get_evidence": "create_evidence",
    "generate_report": "generate_report",
    "save_artifact": "save_artifact",
}

# Human descriptions for MCP discovery
MCP_DESCRIPTIONS: dict[str, str] = {
    "profile_dataset": "Profile a dataset file (schema, missing, duplicates, cardinality).",
    "inspect_dataset": "Inspect dataset schema / columns (alias of profile_dataset).",
    "query_dataset": "Run a SELECT SQL query against a dataset exposed as 'dataset'.",
    "run_sql": "Execute read-only SQL against a dataset (DuckDB, row-limited).",
    "run_python": "Execute Python in a restricted sandbox with dataset as df (Polars).",
    "run_statistical_test": "Run hypothesis tests (t/welch/mann-whitney/anova/kruskal/chi2).",
    "correlation_analysis": "Correlation (pearson/spearman/kendall) with p-value and CI.",
    "train_model": "Train a baseline model with cross-validation.",
    "evaluate_model": "Evaluate a model on holdout (accuracy/F1/ROC or MAE/RMSE/R2).",
    "create_visualization": "Create a chart (histogram/bar/scatter/line/boxplot/heatmap) as PNG artifact.",
    "get_evidence": "Create or validate an evidence record for a claim.",
    "generate_report": "Generate report.md + experiment.json + reproduce.sh + notebook.",
    "save_artifact": "Save an artifact under artifacts/<run_id>/",
}

# Route get_evidence specially: map to validate_result if claim looks like validation, else create_evidence
EVIDENCE_VIA_VALIDATE = {"validate_result"}


def _tool_input_schema(backend: str) -> dict[str, Any]:
    from dsa_tools import get as get_tool

    tool = get_tool(backend)
    try:
        return tool.input_model.model_json_schema()  # type: ignore[no-any-return]
    except Exception:
        return {"type": "object", "properties": {}}


def list_mcp_tools() -> list[MCPToolDef]:
    # Ensure tools bootstrapped
    from dsa_tools import bootstrap, list_tools

    if not list_tools():
        bootstrap()
    out: list[MCPToolDef] = []
    for mcp_name, backend in MCP_TOOL_MAP.items():
        schema = _tool_input_schema(backend if MCP_TOOL_MAP[mcp_name] != "inspect_dataset" else "profile_dataset")
        desc = MCP_DESCRIPTIONS.get(mcp_name, backend)
        out.append(MCPToolDef(name=mcp_name, description=desc, input_schema=schema))
    return out


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Stateless dispatch: validate → call backend BaseTool → return output/error."""
    from dsa_tools import bootstrap, get as get_tool, list_tools

    if not list_tools():
        bootstrap()
    backend = MCP_TOOL_MAP.get(name)
    if backend is None:
        return {"isError": True, "error": f"Unknown MCP tool: {name}", "available": sorted(MCP_TOOL_MAP)}
    # Special cases
    if name == "inspect_dataset":
        # map to profile_dataset but project a slimmer output (still full profile for V0.1)
        backend = "profile_dataset"
    if name == "query_dataset":
        # ensure sql present; wrap as run_sql
        backend = "run_sql"
        if "sql" not in arguments and "query" in arguments:
            arguments = {**arguments, "sql": arguments["query"]}
    if name == "get_evidence":
        # Heuristic: if arguments has 'check_type' or 'validate', route to validate_result
        if "check_type" in arguments or arguments.get("mode") == "validate":
            backend = "validate_result"
        else:
            backend = "create_evidence"

    tool = get_tool(backend)
    result = await tool.run(arguments)
    if result.status == "ok":
        out_val = result.output
        if out_val is not None:
            out = out_val.model_dump(mode="json") if hasattr(out_val, "model_dump") else out_val
            return {"isError": False, "tool": backend, "mcp_tool": name, "call_id": result.call_id, "output": out}
        return {"isError": False, "tool": backend, "mcp_tool": name, "call_id": result.call_id, "output": {}}
    return {"isError": True, "tool": backend, "mcp_tool": name, "call_id": result.call_id, "error": result.error}
