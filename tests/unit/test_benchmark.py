from __future__ import annotations

from pathlib import Path

from dsa_evaluation.catalog import Catalog
from dsa_evaluation.cli import _resolve_datasets_dir
from dsa_evaluation.metrics import evaluate_task
from dsa_evaluation.runner import run_benchmark

CATALOG = Path("benchmarks/ds-agent-benchmark/catalog.json")
DATASETS = Path("benchmarks/ds-agent-benchmark/datasets")


def test_resolve_datasets_dir_prefers_catalog_sibling(tmp_path: Path) -> None:
    """Catalog-only invocation must not silently use the v1 datasets dir.

    Regression test for the 2026-09-08 finding: `dsa --catalog <v2>` without
    `--datasets` scored v2 at 0.57 ('Dataset not found' on v2-only files)
    instead of 1.00.
    """
    custom = tmp_path / "custom"
    (custom / "datasets").mkdir(parents=True)
    cat = custom / "catalog.json"
    cat.write_text("{}", encoding="utf-8")
    # default catalog -> v1 default (unchanged behavior)
    assert _resolve_datasets_dir(Path("benchmarks/ds-agent-benchmark/catalog.json"), None) == Path(
        "benchmarks/ds-agent-benchmark/datasets"
    )
    # NOTE: argparse pre-fills --datasets with the v1 default, so an explicitly
    # passed v1 path is indistinguishable from omission; sibling-wins is the
    # documented behavior in that case (matches the catalog-only v2 invocation).
    assert _resolve_datasets_dir(cat, Path("benchmarks/ds-agent-benchmark/datasets")) == (
        custom / "datasets"
    )
    # overridden catalog + sibling datasets dir -> sibling
    assert _resolve_datasets_dir(cat, None) == custom / "datasets"
    # overridden catalog without sibling -> v1 default (legacy fallback)
    lonely = tmp_path / "lonely" / "catalog.json"
    lonely.parent.mkdir(parents=True)
    assert _resolve_datasets_dir(lonely, None) == Path("benchmarks/ds-agent-benchmark/datasets")


def test_catalog_has_50_tasks_and_categories() -> None:
    cat = Catalog.load(CATALOG)
    assert len(cat.tasks) == 50
    cats = cat.categories()
    assert set(cats) == {
        "EDA",
        "SQL",
        "Statistics",
        "Regression",
        "Classification",
        "Time Series",
        "Visualization",
        "Data Quality",
    }
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
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, "-m", "dsa_evaluation.cli", "--help"], capture_output=True, text=True
    )
    assert r.returncode == 0
    assert "DS-Agent-Benchmark" in r.stdout or "catalog" in r.stdout.lower()
