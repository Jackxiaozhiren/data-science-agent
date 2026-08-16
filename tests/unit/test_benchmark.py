from __future__ import annotations

from pathlib import Path

import pytest

from dsa_evaluation.catalog import Catalog
from dsa_evaluation.metrics import aggregate_metrics, evaluate_task
from dsa_evaluation.runner import run_benchmark

CATALOG = Path("benchmarks/ds-agent-benchmark/catalog.json")
DATASETS = Path("benchmarks/ds-agent-benchmark/datasets")


def test_catalog_has_50_tasks_and_categories() -> None:
    cat = Catalog.load(CATALOG)
    assert len(cat.tasks) == 50
    cats = cat.categories()
    assert set(cats) == {"EDA", "SQL", "Statistics", "Regression", "Classification", "Time Series", "Visualization", "Data Quality"}
    assert len(cat.by_category("EDA")) == 8
    assert len(cat.by_category("SQL")) == 7
    from collections import Counter

    c = Counter(t.category for t in cat.tasks)
    assert c["Statistics"] == 8
    assert c["Regression"] == 6
    assert c["Classification"] == 6
    assert c["Time Series"] == 5


def test_datasets_exist() -> None:
    files = list(DATASETS.glob("*.csv"))
    assert len(files) == 20
    for f in files:
        assert f.stat().st_size > 0


def test_metrics_evaluate_task_success_and_coverage() -> None:
    cat = Catalog.load(CATALOG)
    task = next(t for t in cat.tasks if t.id == "eda-01")
    # fake run result with tool success
    run_result = {
        "state": {
            "tool_calls": [{"tool": "profile_dataset", "status": "ok", "input": {}, "output": {}}],
            "evidence": [{"id": "E-001", "result": {}}],
            "insights": [{"id": "I-001", "finding": "hello", "evidence_ids": ["E-001"]}],
            "validation_results": [],
            "report_markdown": "# report",
            "status": "COMPLETED",
        },
        "status": "COMPLETED",
    }
    ev = evaluate_task(task, run_result, elapsed_ms=100)
    assert ev.metrics.task_success is True
    assert ev.metrics.evidence_coverage is True


def test_runner_smoke_limit_2() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        payload = run_benchmark(CATALOG, DATASETS, out, limit=2)
        assert payload["n_tasks"] == 2
        assert (out / "results.json").exists()
        assert (out / "summary.json").exists()
        agg = payload["aggregate"]
        assert "task_success_rate" in agg
        assert agg["n"] == 2


def test_cli_dsa_benchmark_help() -> None:
    # Smoke: CLI exists via entry point
    import subprocess, sys

    r = subprocess.run([sys.executable, "-m", "dsa_evaluation.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "DS-Agent-Benchmark" in r.stdout or "catalog" in r.stdout.lower()
