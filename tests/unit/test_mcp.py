from __future__ import annotations

import pathlib
from typing import Any

import anyio
from httpx import ASGITransport, AsyncClient


def test_mcp_has_13_tools() -> None:
    from dsa_mcp.adapter import MCP_TOOL_MAP, list_mcp_tools

    tools = list_mcp_tools()
    assert len(tools) == 19  # 17 + analyze (§36) + export_artifact (ADR-002)
    assert len(MCP_TOOL_MAP) == 19
    names = {t.name for t in tools}
    assert "profile_dataset" in names
    assert "run_sql" in names
    assert "run_python" in names
    assert "run_statistical_test" in names
    assert "create_visualization" in names
    assert "forecast" in names
    assert "assumption_check" in names
    assert "feature_importance" in names
    assert "causal_check" in names


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
        r = await call_mcp_tool(
            "run_sql", {"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p)}
        )
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
        r = await call_mcp_tool(
            "query_dataset", {"sql": "SELECT * FROM dataset LIMIT 1", "dataset_path": str(p)}
        )
        assert not r.get("isError"), r

    asyncio.run(_run())


def test_mcp_http_list_and_call() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    client = TestClient(app)
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    assert r.status_code == 200
    data = r.json()
    assert "result" in data
    assert "tools" in data["result"]
    assert len(data["result"]["tools"]) >= 17
    # initialize is no longer supported on 2026-07-28 stateless core
    r2 = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})
    assert r2.json()["error"]["code"] == -32601
    # tools/call -- with a tool this transport offers. run_sql and run_python are withheld from HTTP
    # (MCP_DESIGN.md, tests/security/test_mcp_http_surface.py), so a success probe cannot name them.
    import tempfile

    probe = pathlib.Path(tempfile.mkdtemp()) / "mcp_http_call.csv"
    probe.write_text("a,b\n1,2\n", encoding="utf-8")
    r3 = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "profile_dataset", "arguments": {"path": str(probe)}},
        },
    )
    assert r3.status_code == 200
    assert "result" in r3.json(), r3.json()


def _r14_state() -> Any:
    """One completed run in the shape the graph persists -- the thing the app's report view must render."""
    from datetime import UTC, datetime

    from dsa_agent.state import AnalysisState, AnalysisStatus, Evidence, Insight, ToolCallRecord

    return AnalysisState(
        run_id="run-r14mcp000",
        dataset_id="9bdfe7ad-mcp00",
        dataset_path="/var/lib/dsa/output/datasets/9bdfe7ad_sales.csv",
        user_query="Which regions drove revenue?",
        objective="Attribute revenue to region.",
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC),
        plan=[],
        tool_calls=[
            ToolCallRecord(
                call_id="TC-r14mcp00",
                tool="profile_dataset",
                input={"path": "x.csv"},
                output={
                    "rows": 10,
                    "sha256": "05e300aca0537fcc850cbd06c0649e3c869163a180daec4e7a20e002d1ad6044",
                },
                status="ok",
                duration_ms=5,
            )
        ],
        evidence=[
            Evidence(
                id="E-r14mcp00",
                source_type="statistical_test",
                source_id="TC-r14mcp00",
                claim="Revenue concentrates in region A.",
                result={"r": 0.5},
                confidence=0.7,
                validation_status="verified",
            )
        ],
        insights=[
            Insight(
                id="I-r14mcp00",
                finding="Revenue concentrates in region A.",
                evidence_ids=["E-r14mcp00"],
                limitation="Association does not imply causation.",
            )
        ],
        validation_results=[],
    )


def test_the_mcp_report_view_is_the_single_renderer_byte_for_byte() -> None:
    """R-14: the app's report view must BE the product's one renderer, not a sibling of it.

    Byte equality is the strongest form of that claim -- any assembly of this app's own would diverge the
    first time the renderer grew a section.
    """
    import json as _json

    from dsa_agent.report_export import export_html
    from dsa_mcp.app import app as mcp_app
    from dsa_mcp.resources import store_state

    state = _r14_state()
    store_state(state.run_id, state)
    try:
        transport = ASGITransport(app=mcp_app)
        import anyio

        async def _fetch() -> tuple[int, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"/report/{state.run_id}")
                return r.status_code, r.text

        status, body = anyio.run(_fetch)
        assert status == 200
        assert body == export_html(state), (
            "the MCP app's report view diverged from the one renderer"
        )
    finally:
        from dsa_mcp import resources as _res

        _res._STATE_STORE.pop(state.run_id, None)


def test_the_mcp_report_view_names_the_unknown_handle() -> None:
    from dsa_mcp.app import app as mcp_app

    async def _fetch() -> int:
        async with AsyncClient(
            transport=ASGITransport(app=mcp_app), base_url="http://test"
        ) as client:
            r = await client.get("/report/run-unknown000")
            return r.status_code

    assert anyio.run(_fetch) == 404


def test_the_app_page_embeds_the_renderer_instead_of_truncating_the_markdown() -> None:
    """The old page put `report_markdown.slice(0, 3000)` in a <pre> -- a second, amputated rendering."""
    from dsa_mcp import app as mcp_module

    source = pathlib.Path(mcp_module.__file__).read_text(encoding="utf-8")
    assert "format=html" not in source, "the page reached around the renderer via the API route"
    assert "/mcp-app/report/" in source, "the report card no longer points at the render endpoint"
    assert "slice(0,3000)" not in source and "report_markdown||''" not in source, (
        "the page still renders the markdown itself, truncated"
    )
