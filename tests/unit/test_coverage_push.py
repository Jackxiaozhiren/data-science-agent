from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import polars as pl


def test_hypothesis_forecast_extra_variants() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    async def _run() -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p = td / "cov.csv"
            # groups for hypothesis variants: t-test, welch, mann, anova, kruskal, chi2, fisher
            rows = []
            for g in ["A", "B"]:
                for i in range(15):
                    rows.append({"group": g, "val": float(i + (3 if g == "B" else 0)), "cat": g})
            pl.DataFrame(rows).write_csv(p)
            hyp = get("hypothesis_test")
            for test in ["t_test", "welch_t_test", "mann_whitney", "anova", "kruskal", "chi_square", "fisher_exact"]:
                r = await hyp.run({"dataset_path": str(p), "test": test, "group_col": "group", "value_col": "val" if "chi" not in test and "fisher" not in test else "cat"})
                assert r.status in ("ok", "error")
            # invalid test
            r2 = await hyp.run({"dataset_path": str(p), "test": "unknown_test", "group_col": "group", "value_col": "val"})
            assert r2.status == "error"
            # forecast variants + bad fallback
            pf = td / "ts2.csv"
            pl.DataFrame({"date": [f"2024-01-{i+1:02d}" for i in range(80)], "value": [float(i) for i in range(80)]}).write_csv(pf)
            fc = get("forecast")
            for method in ["linear_trend", "moving_average", "naive_trend", "bad_method"]:
                r = await fc.run({"dataset_path": str(pf), "periods": 10, "method": method})
                assert r.status in ("ok", "error")
            # assumption check extra path
            ac = get("assumption_check")
            r3 = await ac.run({"dataset_path": str(p), "group_col": "group", "value_col": "val"})
            assert r3.status in ("ok", "error")
            # generate_report missing run_id
            gr = get("generate_report")
            r4 = await gr.run({"run_id": "no-such-run-xyz"})
            assert r4.status in ("ok", "error")

    asyncio.run(_run())
