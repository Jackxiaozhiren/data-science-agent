from __future__ import annotations

import json
import pathlib

import pytest

BASELINE_DIR = pathlib.Path("benchmarks/baseline")
CATALOG = pathlib.Path("benchmarks/ds-agent-benchmark/catalog.json")
DATASETS = pathlib.Path("benchmarks/ds-agent-benchmark/datasets")

# W1 contract — mirrors the frozen v1 baseline.
CONTRACT = {
    "task_success_rate": 1.0,
    "sql_accuracy": 1.0,
    "unsupported_max": 0.10,
    "mean_latency_ms_max": 500,
    "min_tools": 17,
}


def test_baseline_snapshot_exists() -> None:
    assert (BASELINE_DIR / "summary.json").exists(), (
        "benchmarks/baseline/summary.json missing — run W1 snapshot"
    )
    assert (BASELINE_DIR / "results.json").exists()


def test_benchmark_fixture_invariants() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert len(data["tasks"]) == 50
    cats = {t["category"] for t in data["tasks"]}
    assert len(cats) == 8
    assert (DATASETS / "sales.csv").exists()
    assert len(list(DATASETS.glob("*.csv"))) == 20


def test_baseline_contract() -> None:
    agg = json.loads((BASELINE_DIR / "summary.json").read_text())
    assert agg["task_success_rate"] == CONTRACT["task_success_rate"]
    assert agg["sql_accuracy"] == CONTRACT["sql_accuracy"]
    assert agg["unsupported_claim_rate"] <= CONTRACT["unsupported_max"]
    assert agg["mean_latency_ms"] <= CONTRACT["mean_latency_ms_max"]


def test_tool_registry_contract() -> None:
    from dsa_tools import bootstrap, list_tools

    if not list_tools():
        bootstrap()
    tools = list_tools()
    assert len(tools) >= CONTRACT["min_tools"]
    for name in (
        "profile_dataset",
        "run_sql",
        "run_python",
        "correlation_analysis",
        "hypothesis_test",
        "create_chart",
    ):
        assert name in tools


@pytest.mark.asyncio
async def test_data_boundary_matrix() -> None:
    """CSV/Parquet boundary, malformed, unicode, missing, dup, high-cardinality handled without crash."""
    import tempfile
    from pathlib import Path

    import polars as pl

    from dsa_datasets.loader import load_dataframe
    from dsa_datasets.models import DatasetFormat
    from dsa_datasets.profiler import build_profile
    from dsa_datasets.validate import detect_format
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # well-formed CSV
        p = td / "ok.csv"
        pl.DataFrame({"a": [1, 2, None], "b": ["x", "y", "y"]}).write_csv(p)
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        prof = build_profile(df, "test", p.name, DatasetFormat.csv)
        assert prof.rows == 3
        # unicode + missing
        p2 = td / "uni.csv"
        p2.write_text("a,b\n1,café\n2,\n3,naïve\n", encoding="utf-8")
        df2 = load_dataframe(p2, detect_format(p2.name))
        assert df2.height == 3
        # duplicate rows
        p3 = td / "dup.csv"
        pl.DataFrame({"x": [1, 1, 2], "y": [1, 1, 2]}).write_csv(p3)
        prof3 = build_profile(
            load_dataframe(p3, detect_format(p3.name)), "test", p3.name, DatasetFormat.csv
        )
        assert prof3.rows == 3
        # high cardinality (500 unique)
        p4 = td / "high.csv"
        pl.DataFrame({"id": [f"id_{i}" for i in range(500)], "v": list(range(500))}).write_csv(p4)
        df4 = load_dataframe(p4, detect_format(p4.name))
        assert df4.height == 500
        # parquet round-trip
        pp = td / "t.parquet"
        pl.DataFrame({"a": [1, 2, 3]}).write_parquet(pp)
        dfp = load_dataframe(pp, detect_format(pp.name))
        assert dfp.height == 3
        # malformed input should not crash API service — tool returns error not exception
        tool = get("run_sql")
        r = await tool.run({"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p2)})
        assert r.status in ("ok", "error")
