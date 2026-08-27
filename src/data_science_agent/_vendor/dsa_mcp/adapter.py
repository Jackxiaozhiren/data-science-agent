from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

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
MCP_WRITE = {"generate_report", "save_artifact", "create_visualization"}

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
    "analyze": "Run full analysis (§36 Dataset→Question→Analysis→Evidence→Viz→Report) — stateless with explicit run_id handle.",
}

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
            "status": {"type": "string"},
            "report_markdown": {"type": "string"},
            "evidence": {"type": "array", "items": {"type": "object"}},
            "insights": {"type": "array", "items": {"type": "object"}},
            "artifacts": {"type": "array", "items": {"type": "object"}},
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


def _discover_datasets() -> list[dict[str, str]]:
    """Discover local datasets for resources (§37 dataset://)."""
    from pathlib import Path

    candidates: list[dict[str, str]] = []
    roots = [
        Path("benchmarks/v2/datasets"),
        Path("benchmarks/ds-agent-benchmark/datasets"),
        Path("examples/datasets"),
        Path("data"),
    ]
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.glob("*.csv"):
            did = p.stem
            if did in seen:
                continue
            seen.add(did)
            candidates.append({"id": did, "path": str(p), "name": did})
        for p in root.glob("*.parquet"):
            did = p.stem
            if did in seen:
                continue
            seen.add(did)
            candidates.append({"id": did, "path": str(p), "name": did})
    return candidates[:50]


# §38 Explicit state store (analysis_id/run_id handles, not session)
_ANALYSIS_STORE: dict[str, dict[str, Any]] = {}


def store_analysis(run_id: str, payload: dict[str, Any]) -> None:
    _ANALYSIS_STORE[run_id] = payload


def list_resources() -> list[dict[str, Any]]:
    """§37 Resource Model — dataset://, evidence://, report://, artifact://, analysis://"""
    resources: list[dict[str, Any]] = []
    # dataset:// — concrete
    for ds in _discover_datasets():
        resources.append(
            {
                "uri": f"dataset://{ds['id']}",
                "name": f"Dataset: {ds['id']}",
                "description": f"Dataset {ds['id']} at {ds['path']}",
                "mimeType": "text/csv",
                "cacheHint": "max-age=60",
            }
        )
    # evidence://, report://, analysis:// — for stored runs (explicit handles §38)
    for run_id, payload in _ANALYSIS_STORE.items():
        resources.append(
            {
                "uri": f"evidence://{run_id}",
                "name": f"Evidence: {run_id}",
                "description": "Evidence graph Insight→Evidence→ToolCall→Dataset",
                "mimeType": "application/json",
            }
        )
        resources.append(
            {
                "uri": f"report://{run_id}",
                "name": f"Report: {run_id}",
                "description": "Report markdown + artifacts",
                "mimeType": "text/markdown",
            }
        )
        resources.append(
            {
                "uri": f"analysis://{run_id}",
                "name": f"Analysis: {run_id}",
                "description": "Full Analysis state (status, insights, evidence, artifacts)",
                "mimeType": "application/json",
            }
        )
        for art in payload.get("artifacts", [])[:5]:
            aid = art.get("id", "artifact")
            resources.append(
                {
                    "uri": f"artifact://{run_id}/{aid}",
                    "name": f"Artifact: {aid}",
                    "description": f"Artifact {art.get('type', '')} at {art.get('path', '')}",
                    "mimeType": "application/octet-stream",
                }
            )
    # Ensure templates for all 5 schemes are discoverable even when no stored analysis (§37)
    schemes_present = {r["uri"].split("://")[0] for r in resources}
    if "evidence" not in schemes_present:
        resources.append(
            {
                "uri": "evidence://{run_id}",
                "name": "Evidence",
                "description": "Evidence graph for a run",
                "mimeType": "application/json",
            }
        )
    if "report" not in schemes_present:
        resources.append(
            {
                "uri": "report://{run_id}",
                "name": "Report",
                "description": "Report markdown + artifacts",
                "mimeType": "text/markdown",
            }
        )
    if "artifact" not in schemes_present:
        resources.append(
            {
                "uri": "artifact://{run_id}/{artifact_id}",
                "name": "Artifact",
                "description": "Artifact file",
                "mimeType": "application/octet-stream",
            }
        )
    if "analysis" not in schemes_present:
        resources.append(
            {
                "uri": "analysis://{run_id}",
                "name": "Analysis",
                "description": "Full Analysis state",
                "mimeType": "application/json",
            }
        )
    # dataset template is covered by concrete datasets above; if none, add
    if "dataset" not in schemes_present:
        resources.append(
            {
                "uri": "dataset://{dataset_id}",
                "name": "Dataset",
                "description": "Dataset resource (CSV/Parquet)",
                "mimeType": "text/csv",
            }
        )
    return resources


async def read_resource(uri: str) -> dict[str, Any]:
    """Read resource by URI (§37) — explicit handles, stateless."""
    # dataset://
    if uri.startswith("dataset://"):
        ds_id = uri[len("dataset://") :].split("?")[0].split("/")[0]
        for ds in _discover_datasets():
            if ds["id"] == ds_id:
                p = Path(ds["path"])
                try:
                    # return head (first 5 rows) as text/csv + metadata
                    head = p.read_text(encoding="utf-8")[:5000] if p.exists() else "not found"
                    return {
                        "uri": uri,
                        "mimeType": "text/csv",
                        "text": head,
                        "meta": {"path": str(p), "dataset_id": ds_id},
                    }
                except Exception as e:
                    return {
                        "uri": uri,
                        "mimeType": "text/plain",
                        "text": f"error: {e}",
                        "isError": True,
                    }
        return {
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"dataset {ds_id} not found",
            "isError": True,
        }
    # evidence://
    if uri.startswith("evidence://"):
        run_id = uri[len("evidence://") :].split("?")[0].split("/")[0]
        payload = _ANALYSIS_STORE.get(run_id)
        if payload is not None:
            ev = payload.get("evidence", [])
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": __import__("json").dumps(ev, indent=2, ensure_ascii=False, default=str),
            }
        # Try to load from artifacts/reports/<run_id>/evidence_graph.json if store empty
        try:
            from pathlib import Path as _P

            eg = _P(f"artifacts/reports/{run_id}/evidence_graph.json")
            if eg.exists():
                return {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": eg.read_text(encoding="utf-8"),
                }
        except Exception:
            pass
        return {
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"evidence for {run_id} not found",
            "isError": True,
        }
    # report://
    if uri.startswith("report://"):
        run_id = uri[len("report://") :].split("?")[0].split("/")[0]
        payload = _ANALYSIS_STORE.get(run_id)
        if payload is not None and payload.get("report_markdown"):
            return {
                "uri": uri,
                "mimeType": "text/markdown",
                "text": str(payload["report_markdown"]),
            }
        # try artifacts
        try:
            from pathlib import Path as _P

            rp = _P(f"artifacts/reports/{run_id}/report.md")
            if rp.exists():
                return {
                    "uri": uri,
                    "mimeType": "text/markdown",
                    "text": rp.read_text(encoding="utf-8"),
                }
        except Exception:
            pass
        return {
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"report for {run_id} not found",
            "isError": True,
        }
    # analysis://
    if uri.startswith("analysis://"):
        run_id = uri[len("analysis://") :].split("?")[0].split("/")[0]
        payload = _ANALYSIS_STORE.get(run_id)
        if payload is not None:
            return {
                "uri": uri,
                "mimeType": "application/json",
                "text": __import__("json").dumps(
                    payload, indent=2, ensure_ascii=False, default=str
                ),
            }
        return {
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"analysis {run_id} not found",
            "isError": True,
        }
    # artifact://
    if uri.startswith("artifact://"):
        rest = uri[len("artifact://") :]
        parts = rest.split("/")
        run_id = parts[0] if parts else ""
        aid = parts[1] if len(parts) > 1 else ""
        payload = _ANALYSIS_STORE.get(run_id)
        if payload is not None:
            for art in payload.get("artifacts", []):
                if art.get("id") == aid or art.get("path", "").endswith(aid):
                    pp = Path(art.get("path", ""))
                    if pp.exists():
                        try:
                            # try text, else base64
                            txt = pp.read_text(encoding="utf-8")[:8000]
                            return {"uri": uri, "mimeType": "text/plain", "text": txt}
                        except Exception:
                            import base64

                            b64 = base64.b64encode(pp.read_bytes()[:20000]).decode()
                            return {"uri": uri, "mimeType": "application/octet-stream", "blob": b64}
                    return {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": __import__("json").dumps(
                            art, indent=2, ensure_ascii=False, default=str
                        ),
                    }
        return {
            "uri": uri,
            "mimeType": "text/plain",
            "text": f"artifact {aid} for {run_id} not found",
            "isError": True,
        }
    return {"uri": uri, "mimeType": "text/plain", "text": "unknown scheme", "isError": True}


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
            payload_raw = {
                "run_id": analysis_res.run_id,
                "analysis_id": analysis_res.run_id,
                "status": analysis_res.status,
                "report_markdown": analysis_res.report_markdown,
                "evidence": [e.__dict__ for e in analysis_res.evidence],
                "insights": [i.__dict__ for i in analysis_res.insights],
                "artifacts": [a.__dict__ for a in analysis_res.artifacts],
                "tool_calls": analysis_res.tool_calls,
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
