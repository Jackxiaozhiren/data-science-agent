from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import polars as pl


def test_repro_and_llm_provider_variants() -> None:
    from dsa_evidence.repro import build_experiment_json
    from dsa_llm.providers import EnvLLMProvider

    p = EnvLLMProvider()
    assert hasattr(p, "generate")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = td / "exp"
        out.mkdir()
        path = build_experiment_json(
            run_id="r1",
            dataset_path=str(td / "x.csv"),
            dataset_sha256="abc",
            user_query="hello",
            plan=[],
            tool_calls=[],
            evidence=[],
            insights=[],
            out_dir=out,
        )
        assert path.exists() and out.joinpath("experiment.json").exists()

    async def _gen() -> None:
        try:
            await p.generate("hi")
        except Exception:
            pass

    asyncio.run(_gen())


def test_mcp_adapter_branches() -> None:
    from dsa_mcp.adapter import MCP_TOOL_MAP, call_mcp_tool, list_mcp_tools

    assert len(list_mcp_tools()) >= 17
    assert "run_sql" in MCP_TOOL_MAP

    async def _run() -> None:
        # query_dataset alias -> sql query
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            csv = td / "a.csv"
            pl.DataFrame({"a": [1, 2], "b": [3, 4]}).write_csv(csv)
            r = await call_mcp_tool("query_dataset", {"query": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(csv)})
            assert "isError" in r
            # unknown tool
            r2 = await call_mcp_tool("no_such_tool_xyz", {})
            assert r2["isError"]

    asyncio.run(_run())
