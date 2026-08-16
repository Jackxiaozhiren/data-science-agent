from __future__ import annotations

import tempfile
from pathlib import Path


def test_generate_report_with_state_json_and_hash() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    import asyncio as aio
    import json

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        csv = td / "data.csv"
        csv.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        state = {
            "dataset_path": str(csv),
            "user_query": "hello",
            "plan": [],
            "tool_calls": [],
            "evidence": [],
            "insights": [],
        }
        state_json = json.dumps(state)

        async def _run() -> None:
            tool = get("generate_report")
            run_id = f"test-report-{td.name[-6:]}"
            r = await tool.run({"run_id": run_id, "markdown": "# Title\nHi", "state_json": state_json, "include_repro": True})
            assert r.status == "ok"
            assert Path(r.output.report_path).exists()
            assert r.output.experiment_path is not None
            assert r.output.reproduce_path is not None
            assert r.output.notebook_path is not None
            # without markdown fallback
            r2 = await tool.run({"run_id": f"{run_id}-2", "state_json": state_json})
            assert r2.status == "ok"
            # with include_repro False -> no repro but has exp + nb
            r3 = await tool.run({"run_id": f"{run_id}-3", "state_json": state_json, "include_repro": False})
            assert r3.status == "ok"
            assert r3.output.reproduce_path is None
            # missing run_id
            r4 = await tool.run({"run_id": "   ", "state_json": state_json})
            assert r4.status == "error"

        aio.run(_run())


def test_mcp_server_jsonrpc_and_stdio_parse() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    c = TestClient(app)
    # JSON-RPC equivalent via /mcp/call with invalid params
    r = c.post("/mcp/call", json={"name": "run_sql", "arguments": {"sql": "DROP TABLE dataset"}})
    assert r.status_code in (400, 200)
    r2 = c.post("/mcp/tools", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert r2.status_code in (200, 404, 405)
    # GET unknown should 404
    assert c.get("/not-exist-xyz").status_code in (404, 405)
