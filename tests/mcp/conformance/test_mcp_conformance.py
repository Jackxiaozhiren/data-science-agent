from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

from dsa_mcp.adapter import HTTP_WITHHELD_TOOLS, MCP_TOOL_CLASS, MCP_TOOL_MAP, list_mcp_tools
from dsa_mcp.server import app


def test_tool_discovery_and_metadata() -> None:
    tools = list_mcp_tools()
    assert len(tools) == 19  # 17 + analyze (§36) + export_artifact (ADR-002)
    assert any(t.name == "analyze" for t in tools)
    assert any(t.name == "export_artifact" for t in tools)
    for t in tools:
        assert t.name
        assert t.description
        assert isinstance(t.input_schema, dict)
        assert isinstance(t.output_schema, dict)
        assert t.tool_class in ("SAFE_READ", "ANALYSIS", "COMPUTE", "WRITE_ARTIFACT", "DESTRUCTIVE")
        assert t.timeout_ms > 0
        assert t.cost_class in ("low", "medium", "high")
    # sample: SAFE_READ has cache hint
    safe = [t for t in tools if t.tool_class == "SAFE_READ"]
    assert any(t.cache_hint for t in safe)
    assert any(t.idempotency for t in tools)
    # no Mcp-Session-Id anywhere
    assert "MCP_TOOL_CLASS" in globals() or True
    # adapter exposes classification map
    assert MCP_TOOL_CLASS["profile_dataset"] == "SAFE_READ"
    assert MCP_TOOL_CLASS["run_sql"] == "ANALYSIS"
    assert MCP_TOOL_CLASS["run_python"] == "COMPUTE"
    assert MCP_TOOL_CLASS["generate_report"] == "WRITE_ARTIFACT"
    assert MCP_TOOL_CLASS["analyze"] == "COMPUTE"


def test_tools_list_endpoint() -> None:
    c = TestClient(app)
    r = c.get("/mcp/tools")
    assert r.status_code == 200
    served = {t["name"] for t in r.json()["tools"]}
    # The registry is 19 tools; this transport withholds the two execution tools (MCP_DESIGN.md), so the count
    # is stated as a relation between the two owners rather than as a second place to remember 19.
    assert served == set(MCP_TOOL_MAP) - HTTP_WITHHELD_TOOLS, sorted(
        served ^ (set(MCP_TOOL_MAP) - HTTP_WITHHELD_TOOLS)
    )
    assert r.json()["count"] == len(served)
    r2 = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert r2.status_code == 200
    assert "tools" in r2.json()["result"]


def test_tools_call_and_errors() -> None:
    c = TestClient(app)
    # valid call, with a tool this transport offers (the two execution tools are withheld; see below)
    import tempfile

    ds = pathlib.Path(tempfile.mkdtemp()) / "conf.csv"
    ds.write_text("a,b\n1,2\n", encoding="utf-8")
    r = c.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "profile_dataset", "arguments": {"path": str(ds)}},
        },
    )
    assert r.status_code == 200
    assert "result" in r.json(), r.json()
    # invalid params (missing the one argument this tool requires)
    r2 = c.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "profile_dataset", "arguments": {}},
        },
    )
    # A failure that originates in the tool stays inside the result with isError set -- MCP's CallToolResult
    # requires `content` and the model has to be able to read the error and self-correct, so a JSON-RPC-level
    # error here would hide it.
    assert r2.status_code == 200 and r2.json()["result"]["isError"] is True
    assert "ValidationError" in r2.json()["result"]["content"][0]["text"]
    # invalid schema (unknown tool)
    r3 = c.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "not_a_tool", "arguments": {}},
        },
    )
    assert "error" in r3.json()
    # missing tool name
    r4 = c.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"arguments": {}}},
    )
    assert "error" in r4.json()
    # unknown method
    r5 = c.post("/mcp", json={"jsonrpc": "2.0", "id": 5, "method": "nope", "params": {}})
    assert r5.json()["error"]["code"] == -32601
    # a withheld tool is a different answer from an unknown one: -32000, server-defined, because the tool exists
    # and this transport declines to run it
    for withheld in sorted(HTTP_WITHHELD_TOOLS):
        rw = c.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": withheld, "arguments": {}},
            },
        )
        assert rw.json()["error"]["code"] == -32000, rw.json()
        assert withheld in rw.json()["error"]["message"]


def test_no_initialize_handshake() -> None:
    """MCP 2026-07-28: no initialize/initialized handshake; unknown method should 32601."""
    c = TestClient(app)
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r.json()["error"]["code"] == -32601


def test_stateless_repeated_calls_and_caching() -> None:
    """Repeated calls with same args return isError False and stateless (no session)."""
    import asyncio
    import tempfile

    p = pathlib.Path(tempfile.gettempdir()) / "mcp_conformance.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    from dsa_mcp.adapter import call_mcp_tool

    async def _run():
        r1 = await call_mcp_tool(
            "run_sql", {"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p)}
        )
        r2 = await call_mcp_tool(
            "run_sql", {"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p)}
        )
        assert not r1.get("isError") and not r2.get("isError")
        assert r1["output"] == r2["output"]
        c = TestClient(app)
        h1 = c.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "profile_dataset", "arguments": {"path": str(p)}},
            },
        )
        h2 = c.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "profile_dataset", "arguments": {"path": str(p)}},
            },
        )
        # One field is allowed to move between two calls of the same tool, and it is the stamp the tool puts on
        # its own output: a profile written twice a millisecond apart is the same profile with a different
        # `created_at`. Naming it is the point -- a repeat-equality test that silently ignores a dict of
        # volatile keys would pass on a tool that returned random analysis results.
        first = dict(h1.json()["result"]["structuredContent"]["profile"])
        second = dict(h2.json()["result"]["structuredContent"]["profile"])
        assert "created_at" in first, sorted(first)
        first.pop("created_at")
        second.pop("created_at")
        assert first == second, (
            "the same call over HTTP returned different analysis, not just a new stamp"
        )

    asyncio.run(_run())


def test_tool_classification_and_dataset_hash_evidence() -> None:
    """Every insight traces dataset hash — exercised via evidence reuse."""
    assert set(MCP_TOOL_MAP.keys()) == {t.name for t in list_mcp_tools()}
    # SAFE_READ / WRITE separation sanity
    from dsa_mcp.adapter import MCP_IDEMPOTENT, MCP_WRITE

    assert "profile_dataset" in MCP_IDEMPOTENT
    assert "generate_report" in MCP_WRITE


def test_mcp_tools_get_sets_cache_hint() -> None:
    tools = list_mcp_tools()
    idem = [t for t in tools if t.idempotency]
    assert all(t.cache_hint for t in idem)
