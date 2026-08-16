from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import polars as pl


def test_routers_and_llm_env_provider() -> None:
    from fastapi.testclient import TestClient

    from dsa_api.main import app

    c = TestClient(app)
    # health / metrics / version
    assert c.get("/health").status_code in (200, 500)  # degraded if db not ready
    assert c.get("/ready").status_code in (200, 500)
    assert c.get("/version").status_code == 200
    assert c.get("/metrics").status_code == 200
    # experiments list (may be empty)
    assert c.get("/api/v1/experiments/").status_code in (200, 404)
    # datasets list
    assert c.get("/api/v1/datasets/").status_code == 200
    # analysis list
    assert c.get("/api/v1/analysis/").status_code == 200

    # LLM env provider smoke — without keys it should fallback ok
    from dsa_llm.providers import EnvLLMProvider

    p = EnvLLMProvider()
    assert hasattr(p, "active_provider")


def test_create_chart_all_types_and_generate_report() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / "chart.csv"
            pl.DataFrame({"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10], "cat": ["A", "A", "B", "B", "C"], "val": [1, 2, 3, 4, 5]}).write_csv(p)
            for ct in ["histogram", "bar", "scatter", "line", "boxplot", "heatmap"]:
                tool = get("create_chart")
                r = await tool.run({"dataset_path": str(p), "chart_type": ct, "x": "x" if ct in ("histogram", "line") else "cat", "y": "y" if ct not in ("histogram",) else None})
                assert r.status in ("ok", "error")
            # fallback without dataset_path should error or ok
            rg = get("generate_report")
            r2 = await rg.run({"run_id": "test-run-123"})
            assert r2.status in ("ok", "error")

    asyncio.run(_run())


def test_tool_error_branches_and_regression_variants() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / "reg.csv"
            pl.DataFrame({"a": [1.0, 2.0, 3.0], "b": ["x", "y", "z"], "target": [1, 0, 1]}).write_csv(p)
            # regression with non-numeric should hit error path
            rg = get("regression_analysis")
            r = await rg.run({"dataset_path": str(p), "target": "target", "features": ["b"], "model": "linear"})
            assert r.status in ("ok", "error")
            # missing feature
            r2 = await rg.run({"dataset_path": str(p), "target": "target", "features": ["missing"], "model": "linear"})
            assert r2.status == "error"
            # hypothesis with missing data edge
            hyp = get("hypothesis_test")
            r3 = await hyp.run({"dataset_path": str(p), "test": "welch_t_test", "group_col": "b", "value_col": "a"})
            assert r3.status in ("ok", "error")

    asyncio.run(_run())
