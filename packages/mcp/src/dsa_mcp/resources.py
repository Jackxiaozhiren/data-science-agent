"""The MCP resource surface (§37): URIs, the dataset catalogue behind ``dataset://``, and the
explicit-handle store (§8) the ``evidence:// report:// analysis:// artifact://`` readers serve from.

Split out of ``dsa_mcp.adapter`` at §114 (Phase 4 target 2). The tool side -- schemas,
classification, dispatch -- stayed there, because MCP clients list resources and call tools through
different handlers and ``server.py`` already imported the two groups separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


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
        except Exception as e:
            return {
                "uri": uri,
                "mimeType": "text/plain",
                "text": f"evidence for {run_id} unreadable: {e}",
                "isError": True,
            }
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
        except Exception as e:
            return {
                "uri": uri,
                "mimeType": "text/plain",
                "text": f"report for {run_id} unreadable: {e}",
                "isError": True,
            }
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
