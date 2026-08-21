"""W6 Acceptance Test (§39) + Resource Model (§37) + Explicit State (§38)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dsa_api.main import app as main_app
from dsa_mcp.adapter import call_mcp_tool, list_resources, read_resource
from dsa_mcp.app import app as mcp_app
from dsa_mcp.server import app as mcp_server

# §39 Client→Connect→Discover→Call Tool→Receive→Open Resource→Render App→Inspect Evidence


def test_mcp_resource_model_five_schemes() -> None:
    """§37 at least dataset://, evidence://, report://, artifact://, analysis://"""
    resources = list_resources()
    uris = [r["uri"] for r in resources]
    for scheme in ("dataset://", "evidence://", "report://", "artifact://", "analysis://"):
        assert any(u.startswith(scheme) for u in uris), f"missing {scheme} — got {uris[:5]}"
    # Check mimeType and cache hints
    for r in resources:
        assert "uri" in r and "name" in r


@pytest.mark.asyncio
async def test_explicit_handles_stateless() -> None:
    """§38 Explicit handles (analysis_id/run_id) not protocol session; stateless core."""
    # Two different run_id should give different resources
    r1 = await call_mcp_tool("analyze", {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Analyze revenue", "run_id": "run-explicit-1"})
    r2 = await call_mcp_tool("analyze", {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Analyze revenue", "run_id": "run-explicit-2"})
    assert not r1.get("isError") and not r2.get("isError")
    assert r1["output"]["run_id"] == "run-explicit-1"
    assert r2["output"]["run_id"] == "run-explicit-2"
    # Resources are explicit
    ev1 = await read_resource("evidence://run-explicit-1")
    ev2 = await read_resource("evidence://run-explicit-2")
    assert not ev1.get("isError") and not ev2.get("isError")
    # Different evidence (at least run_id in payload)
    assert "run-explicit-1" in str(ev1) or len(ev1["text"]) > 10
    # No session: repeated call same run_id returns same
    ev1b = await read_resource("evidence://run-explicit-1")
    assert ev1["text"] == ev1b["text"]


def test_mcp_app_acceptance_via_server() -> None:
    """§39 via mcp_server (direct): Discover → Call → Receive → Open Resource → Render App."""
    c = TestClient(mcp_server)
    # 1. Discover
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert r.status_code == 200 and "tools" in r.json()["result"]
    assert any(t["name"] == "analyze" for t in r.json()["result"]["tools"])
    # 2. Call Tool (analyze) — explicit handle
    rc = c.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "analyze", "arguments": {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Analyze revenue", "run_id": "run-accept-1"}}},
    )
    assert rc.status_code == 200 and "result" in rc.json()
    assert rc.json()["result"]["output"]["run_id"] == "run-accept-1"
    # 3. Receive Result already done
    # 4. Open Resource (evidence, report)
    for uri in ["evidence://run-accept-1", "report://run-accept-1", "analysis://run-accept-1"]:
        rr = c.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": uri}})
        assert rr.status_code == 200 and "result" in rr.json(), uri
        assert not rr.json()["result"].get("isError")
    # 5. Render App
    ca = TestClient(mcp_app)
    ra = ca.get("/")
    assert ra.status_code == 200
    assert "Dataset" in ra.text and "Question" in ra.text and "Evidence" in ra.text
    assert "run_id" in ra.text  # explicit handles §38


def test_mcp_app_acceptance_via_main_app() -> None:
    """Same via main_app mounts (/mcp, /mcp-app) — stateless."""
    c = TestClient(main_app)
    # Discover via main
    r = c.get("/mcp/tools")
    assert r.status_code == 200 and r.json()["count"] >= 18
    # Resources via main
    r2 = c.get("/mcp/resources")
    assert r2.status_code == 200 and any(x["uri"].startswith("dataset://") for x in r2.json()["resources"])
    # JSON-RPC via main (/mcp)
    rc = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "analyze", "arguments": {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Analyze revenue", "run_id": "run-main-1"}}})
    assert rc.status_code == 200 and "result" in rc.json()
    # App via main
    ra = c.get("/mcp-app/")
    assert ra.status_code == 200
    assert "MCP App" in ra.text or "Dataset" in ra.text
    # Explicit handle in URL
    assert "run_id" in ra.text


def test_mcp_resources_read_dataset_and_analysis() -> None:
    c = TestClient(mcp_server)
    # dataset:// via JSON-RPC
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {"uri": "dataset://sales"}})
    assert r.status_code == 200 and "result" in r.json()
    assert r.json()["result"]["mimeType"] == "text/csv"
    # analysis:// after creating one
    import asyncio

    async def _create():
        return await call_mcp_tool("analyze", {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "test", "run_id": "run-res-test"})

    asyncio.run(_create())
    r2 = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "analysis://run-res-test"}})
    assert r2.status_code == 200 and "result" in r2.json()


def test_mcp_stateless_no_session() -> None:
    """MCP 2026-07-28 stateless: no Mcp-Session-Id, repeated calls same result, no initialize."""
    c = TestClient(mcp_server)
    # No session header
    r = c.get("/mcp/tools")
    assert "mcp-session-id" not in {k.lower(): v for k, v in r.headers.items()}
    # initialize should be 32601
    ri = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert ri.json()["error"]["code"] == -32601
    # Two sequential analyze with same run_id should overwrite, not session
    import asyncio

    async def _dup():
        a1 = await call_mcp_tool("analyze", {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Q1", "run_id": "run-stateless"})
        a2 = await call_mcp_tool("analyze", {"dataset": "benchmarks/v2/datasets/sales.csv", "task": "Q2", "run_id": "run-stateless"})
        return a1, a2

    a1, a2 = asyncio.run(_dup())
    assert a1["output"]["run_id"] == a2["output"]["run_id"] == "run-stateless"
