from __future__ import annotations

import pathlib


def test_mcp_has_13_tools() -> None:
    from dsa_mcp.adapter import MCP_TOOL_MAP, list_mcp_tools

    tools = list_mcp_tools()
    assert len(tools) == 13
    assert len(MCP_TOOL_MAP) == 13
    names = {t.name for t in tools}
    assert "profile_dataset" in names
    assert "run_sql" in names
    assert "run_python" in names
    assert "run_statistical_test" in names
    assert "create_visualization" in names


def test_adapter_is_decoupled_from_core() -> None:
    # Core should not import mcp
    import pathlib

    core_files = []
    for p in pathlib.Path("packages/agent/src").rglob("*.py"):
        core_files.append(p.read_text())
    for p in pathlib.Path("packages/tools/src").rglob("*.py"):
        core_files.append(p.read_text())
    core_text = "\n".join(core_files)
    assert "dsa_mcp" not in core_text
    assert "mcp" not in core_text.lower() or "import dsa_mcp" not in core_text


def test_mcp_tool_schemas_present() -> None:
    from dsa_mcp.adapter import list_mcp_tools

    tools = list_mcp_tools()
    for t in tools:
        assert t.input_schema is not None
        assert isinstance(t.input_schema, dict)


def test_mcp_call_run_sql(tmp_path: pathlib.Path) -> None:
    import asyncio

    p = tmp_path / "t.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    from dsa_mcp.adapter import call_mcp_tool

    async def _run():
        r = await call_mcp_tool("run_sql", {"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p)})
        assert not r.get("isError"), r
        assert r["tool"] == "run_sql"
        assert "output" in r

    asyncio.run(_run())


def test_mcp_call_unknown_tool() -> None:
    import asyncio
    from dsa_mcp.adapter import call_mcp_tool

    async def _run():
        r = await call_mcp_tool("not_a_tool", {})
        assert r.get("isError")
        assert "Unknown" in r.get("error", "")

    asyncio.run(_run())


def test_mcp_query_dataset_alias() -> None:
    import asyncio

    p = pathlib.Path("/tmp") / "mcp_query_test.csv"
    p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    from dsa_mcp.adapter import call_mcp_tool

    async def _run():
        r = await call_mcp_tool("query_dataset", {"sql": "SELECT * FROM dataset LIMIT 1", "dataset_path": str(p)})
        assert not r.get("isError"), r

    asyncio.run(_run())


def test_mcp_http_list_and_call() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    client = TestClient(app)
    # tools/list via JSON-RPC
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert r.status_code == 200
    data = r.json()
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) >= 13
    # initialize
    r2 = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})
    assert r2.status_code == 200
    # tools/call
    r3 = client.post("/mcp", json={"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "run_sql", "arguments": {"sql": "SELECT 1 as a"}}})
    assert r3.status_code == 200
    assert "result" in r3.json()
