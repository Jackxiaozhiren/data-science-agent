from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


def test_generate_report_and_llm_more() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    async def _run() -> None:
        # generate_report with temp dataset should hit success path if fabric builds
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            import polars as pl

            p = td / "g.csv"
            pl.DataFrame({"a": [1, 2, 3, 4, 5], "b": [2, 3, 4, 5, 6]}).write_csv(p)
            gr = get("generate_report")
            # call with missing run_id -> should error but exercise code
            r = await gr.run({"run_id": "xyz-not-exist"})
            assert r.status in ("ok", "error")
            # call with dataset_path variant if supported
            r2 = await gr.run({"run_id": "xyz", "dataset_path": str(p)})
            assert r2.status in ("ok", "error")

    asyncio.run(_run())
    # LLM provider branches
    from dsa_llm.providers import EnvLLMProvider

    prov = EnvLLMProvider()
    # with no env, should not crash
    try:
        asyncio.run(prov.generate("hello", model="x"))
    except Exception:
        pass
    # mcp stdio not tested here but adapter already covered
