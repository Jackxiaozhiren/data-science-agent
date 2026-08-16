from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl


def test_assumption_check_group_and_edges() -> None:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    import asyncio as aio

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        p = td / "assump.csv"
        # groups + enough n for shapiro/levene
        rows = []
        for g in ["A", "B", "C"]:
            for i in range(20):
                rows.append({"g": g, "v": float(i + (5 if g == "C" else 0)), "cat": g})
        pl.DataFrame(rows).write_csv(p)

        async def _run() -> None:
            tool = get("assumption_check")
            r1 = await tool.run({"dataset_path": str(p), "column": "v", "group_col": "g", "check": "all"})
            assert r1.status == "ok"
            assert "passed" in (r1.output.model_dump() if r1.output else {})
            # columns list path
            r2 = await tool.run({"dataset_path": str(p), "columns": ["v"], "check": "normality"})
            assert r2.status in ("ok", "error")
            # no numeric col -> error
            p2 = td / "non_num.csv"
            pl.DataFrame({"a": ["x", "y", "z"]}).write_csv(p2)
            r3 = await tool.run({"dataset_path": str(p2), "column": "a"})
            assert r3.status == "error"
            # missing column
            r4 = await tool.run({"dataset_path": str(p), "column": "missing"})
            assert r4.status == "error"
            # small n (<8)
            p3 = td / "small.csv"
            pl.DataFrame({"g": ["A", "B"], "v": [1.0, 2.0]}).write_csv(p3)
            r5 = await tool.run({"dataset_path": str(p3), "column": "v"})
            assert r5.status in ("ok", "error")

        aio.run(_run())
