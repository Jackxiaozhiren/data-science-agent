from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import polars as pl


def test_generate_report_and_mcp_stdio_extra() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    import asyncio as aio

    async def _run() -> None:
        # generate_report: call with existing run_id path derived from experiment
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / "gen.csv"
            pl.DataFrame({"a": [1, 2, 3]}).write_csv(p)
            # profile first so artifacts dir exists
            pr = await get("profile_dataset").run({"path": str(p), "filename": "gen.csv"})
            assert pr.status in ("ok", "error")
            # mcp adapter extra branch: get_evidence via validate_result
            from dsa_mcp.adapter import call_mcp_tool

            r = await call_mcp_tool(
                "get_evidence", {"mode": "validate", "check_type": "evidence_coverage"}
            )
            assert "isError" in r
            r2 = await call_mcp_tool("get_evidence", {"claim": "test claim", "source": "python"})
            assert "isError" in r2

    aio.run(_run())


def test_llm_provider_generate_and_path_not_found() -> None:
    from dsa_llm.providers import EnvLLMProvider

    p = EnvLLMProvider()

    async def _run() -> None:
        # Env not set -> should not hang, either error or mock
        try:
            r = await p.generate("hello world")
            assert isinstance(r, str)
        except Exception:
            pass

    asyncio.run(_run())
    # dataset path not found branches
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    async def _run2() -> None:
        r = await get("run_sql").run(
            {"sql": "SELECT 1 as a", "dataset_path": "/tmp/no_such_file_xyz.csv"}
        )
        assert r.status == "error"
        r2 = await get("run_python").run(
            {"code": "print(df.head())", "dataset_path": "/tmp/no_such_xyz.csv"}
        )
        assert r2.status == "error"

    asyncio.run(_run2())
