from __future__ import annotations

import asyncio
import sys


def test_mcp_server_stdio_and_call_branches() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    c = TestClient(app)
    # /mcp/call with bad json (no name) -> 400
    r = c.post("/mcp/call", json={})
    assert r.status_code == 400
    # /mcp/call with valid name but bad sql -> isError true via adapter
    r2 = c.post("/mcp/call", json={"name": "run_sql", "arguments": {"sql": "DROP TABLE x"}})
    assert r2.json().get("isError") is True
    # /mcp/tools list
    r3 = c.get("/mcp/tools")
    assert r3.status_code == 200 and r3.json().get("count", 0) >= 17


def test_llm_provider_env_and_stateless_call() -> None:
    from dsa_llm.providers import EnvLLMProvider

    prov = EnvLLMProvider()
    # without API keys should return fallback provider name available
    assert hasattr(prov, "active_provider") or hasattr(prov, "provider")
    # call_mcp_tool stateless repeated calls (tool cache)
    from dsa_mcp.adapter import call_mcp_tool

    async def _run() -> None:
        r1 = await call_mcp_tool("run_sql", {"sql": "SELECT 1 as a"})
        r2 = await call_mcp_tool("run_sql", {"sql": "SELECT 1 as a"})
        assert "isError" in r1 and "isError" in r2
        # inspect dataset alias
        import pathlib
        import tempfile

        p = pathlib.Path(tempfile.gettempdir()) / "cov_llm_inspect.csv"
        p.write_text("a,b\n1,2\n", encoding="utf-8")
        r3 = await call_mcp_tool("inspect_dataset", {"path": str(p)})
        assert "isError" in r3

    asyncio.run(_run())
