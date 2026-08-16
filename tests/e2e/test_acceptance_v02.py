from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest


def _make_sales_decline(path: Path, n: int = 200) -> None:
    rows = []
    for i in range(n):
        date = f"2024-{(i // 28) % 12 + 1:02d}-{i % 28 + 1:02d}"
        region = ["East", "West", "North", "South"][i % 4]
        price = 40 + (i % 30)
        units = 20 + (i % 20)
        revenue = float(price * units)
        if i >= n - 40:
            revenue *= 0.75
        rows.append([date, region, price, units, revenue])
    pl.DataFrame(
        {
            "date": [r[0] for r in rows],
            "region": [r[1] for r in rows],
            "price": [r[2] for r in rows],
            "units": [r[3] for r in rows],
            "revenue": [r[4] for r in rows],
        }
    ).write_csv(path)


@pytest.mark.asyncio
async def test_e2e_sales_decline_and_forecast() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sales.csv"
        _make_sales_decline(p)
        from dsa_agent.graph import run_analysis

        state = await run_analysis(
            dataset_path=str(p),
            dataset_id="sales",
            user_query="Analyze why revenue declined and forecast revenue for the next 30 days",
        )
        assert state.status.value in ("COMPLETED", "FAILED")
        # Must have at least profile + forecast + chart
        tools = [tc.tool for tc in state.tool_calls]
        assert "profile_dataset" in tools
        assert "forecast" in tools
        fc = [tc for tc in state.tool_calls if tc.tool == "forecast"]
        assert fc and fc[0].status == "ok"
        # Evidence for forecast
        assert any("Forecast" in e.claim for e in state.evidence)
        # Report exists
        assert state.report_markdown is not None
        assert "Forecast" in state.report_markdown or "forecast" in state.report_markdown.lower()
        # Validation includes evidence traceability
        checks = {v.check for v in state.validation_results}
        assert "evidence_traceability" in checks or "evidence_coverage" in checks
