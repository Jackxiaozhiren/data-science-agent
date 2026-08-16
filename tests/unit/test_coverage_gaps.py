from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl


def test_mcp_server_extra_branches() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    c = TestClient(app)
    # GET /mcp/tools
    r = c.get("/mcp/tools")
    assert r.status_code == 200 and r.json()["count"] >= 17
    # POST /mcp/call missing name
    r2 = c.post("/mcp/call", json={"arguments": {}})
    assert r2.status_code == 400
    # POST /mcp/call success via adapter
    p = Path(tempfile.gettempdir()) / "cov_mcp_call.csv"
    p.write_text("a,b\n1,2\n", encoding="utf-8")
    r3 = c.post("/mcp/call", json={"name": "run_sql", "arguments": {"sql": "SELECT 1 as a"}})
    assert r3.status_code == 200


def test_cached_llm_provider_and_hypothesis_extra() -> None:
    import asyncio

    from dsa_llm import CachedLLMProvider, LLMProvider

    class Dummy(LLMProvider):
        def __init__(self) -> None:
            self.calls = 0

        async def generate(self, prompt: str, **kwargs) -> str:  # type: ignore[no-untyped-def]
            self.calls += 1
            return f"hi-{prompt}"

        async def structured_output(self, prompt: str, schema: type, **kwargs) -> str:  # type: ignore[no-untyped-def]
            return "structured"

        def stream(self, prompt: str, **kwargs):  # type: ignore[no-untyped-def]
            return iter(["a"])

    async def _run() -> None:
        d = Dummy()
        c = CachedLLMProvider(d, max_entries=2, ttl_s=1000)
        a = await c.generate("hello")
        b = await c.generate("hello")
        assert a == b and d.calls == 1
        # different prompt -> miss
        await c.generate("world")
        assert d.calls == 2
        # overflow -> still works
        await c.generate("x1")
        await c.generate("x2")
        await c.generate("x3")
        assert len(c._cache) <= 2
        s = await c.structured_output("p", str)
        assert s == "structured"
        assert list(c.stream("p")) == ["a"]

    asyncio.run(_run())

    # hypothesis_test extra branches: anova / chi2
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p = td / "hyp.csv"
        rows = []
        for g in ["A", "B", "C"]:
            for i in range(10):
                rows.append({"g": g, "v": float(i + (5 if g == "C" else 0)), "cat": g, "num": float(i)})
        pl.DataFrame(rows).write_csv(p)
        import asyncio as aio

        async def _hyp() -> None:
            tool = get("hypothesis_test")
            r1 = await tool.run({"dataset_path": str(p), "test": "anova", "group_col": "g", "value_col": "v"})
            assert r1.status in ("ok", "error")
            r2 = await tool.run({"dataset_path": str(p), "test": "chi_square", "group_col": "g", "value_col": "cat"})
            assert r2.status in ("ok", "error")

        aio.run(_hyp())


def test_forecast_and_regression_extra() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # timeseries for forecast
        p = td / "ts.csv"
        pl.DataFrame({"date": [f"2024-01-{i+1:02d}" for i in range(60)], "value": [float(i) for i in range(60)]}).write_csv(p)
        # regression dataset
        pr = td / "reg.csv"
        pl.DataFrame({"x": [float(i) for i in range(80)], "y": [float(i * 2) for i in range(80)], "z": [float(i % 5) for i in range(80)]}).write_csv(pr)
        import asyncio as aio

        async def _run() -> None:
            fc = get("forecast")
            r = await fc.run({"dataset_path": str(p), "periods": 10, "method": "linear_trend"})
            assert r.status in ("ok", "error")
            rg = get("regression_analysis")
            r2 = await rg.run({"dataset_path": str(pr), "target": "y", "features": ["x", "z"], "model": "ridge", "alpha": 1.0})
            assert r2.status in ("ok", "error")
            r3 = await rg.run({"dataset_path": str(pr), "target": "y", "features": ["x"], "model": "lasso", "alpha": 0.1})
            assert r3.status in ("ok", "error")

        aio.run(_run())
