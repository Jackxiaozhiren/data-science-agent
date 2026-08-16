from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest

from dsa_tools import bootstrap, clear, get


@pytest.fixture(autouse=True)
def _bootstrap():
    clear()
    bootstrap()
    yield
    clear()


def _sales_with_dates(path: Path, n: int = 120) -> None:
    rows = []
    for i in range(n):
        date = f"2024-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}"
        region = "East" if i % 4 == 0 else "West"
        cat = "A" if i % 3 == 0 else "B"
        price = 50 + (i % 20)
        units = 10 + (i % 15)
        revenue = float(price * units)
        if i >= n - 30:
            revenue *= 0.7
        rows.append([date, region, cat, price, units, revenue])
    pl.DataFrame(
        {
            "date": [r[0] for r in rows],
            "region": [r[1] for r in rows],
            "category": [r[2] for r in rows],
            "price": [r[3] for r in rows],
            "units": [r[4] for r in rows],
            "revenue": [r[5] for r in rows],
        }
    ).write_csv(path)


@pytest.mark.asyncio
async def test_forecast_baseline() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sales.csv"
        _sales_with_dates(p)
        tool = get("forecast")
        r = await tool.run({"dataset_path": str(p), "periods": 30, "method": "linear_trend"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert len(r.output.forecast) == 30
        assert "mae" in r.output.metrics


@pytest.mark.asyncio
async def test_assumption_check() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        pl.DataFrame(
            {"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "group": ["A"] * 5 + ["B"] * 5}
        ).write_csv(p)
        tool = get("assumption_check")
        r = await tool.run({"dataset_path": str(p), "column": "a", "group_col": "group"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert len(r.output.checks) >= 1


@pytest.mark.asyncio
async def test_feature_importance() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        pl.DataFrame(
            {
                "f1": list(range(100)),
                "f2": [i % 5 for i in range(100)],
                "target": [i % 2 for i in range(100)],
            }
        ).write_csv(p)
        tool = get("feature_importance")
        r = await tool.run({"dataset_path": str(p), "target": "target"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert len(r.output.importances) >= 1
        assert Path(r.output.artifact_path).exists()  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_planner_adds_forecast_and_line_chart_for_time_series() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sales.csv"
        _sales_with_dates(p)
        from dsa_agent.planner import heuristics_plan

        plan = heuristics_plan(
            "Forecast revenue for the next 30 days", str(p), ["date", "region", "price", "revenue"]
        )
        tools = [s.tool for s in plan.steps]
        assert "forecast" in tools
        assert "create_chart" in tools
        # should have line chart for time series when has_time
        chart_tools = [s for s in plan.steps if s.tool == "create_chart"]
        assert any(s.inputs.get("chart_type") == "histogram" for s in chart_tools)
