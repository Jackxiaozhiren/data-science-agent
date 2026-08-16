from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from dsa_evaluation.catalog import BenchmarkTask, Catalog
from dsa_evaluation.metrics import EvaluationResult, aggregate_metrics, evaluate_task


async def _run_one(task: BenchmarkTask, datasets_dir: Path) -> tuple[dict[str, Any] | None, int, str | None]:
    dataset_path = datasets_dir / task.dataset
    if not dataset_path.exists():
        return None, 0, f"Dataset not found: {task.dataset}"
    t0 = time.perf_counter()
    try:
        # Lazily import to avoid heavy deps at import time
        from dsa_agent.graph import run_analysis
        from dsa_tools import bootstrap, list_tools

        if not list_tools():
            bootstrap()
        # Derive a dataset_id from filename
        dataset_id = task.dataset.replace(".csv", "").replace("/", "_")
        state = await run_analysis(dataset_path=str(dataset_path), dataset_id=dataset_id, user_query=task.question)
        elapsed = int((time.perf_counter() - t0) * 1000)
        return state.model_dump(mode="json"), elapsed, None
    except Exception as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return None, elapsed, f"{type(e).__name__}: {e}"


def run_benchmark(
    catalog_path: Path,
    datasets_dir: Path,
    out_dir: Path,
    limit: int | None = None,
    task_ids: list[str] | None = None,
) -> dict[str, Any]:
    catalog = Catalog.load(catalog_path)
    tasks = catalog.tasks
    if task_ids:
        tasks = [t for t in tasks if t.id in task_ids]
    if limit:
        tasks = tasks[:limit]
    out_dir.mkdir(parents=True, exist_ok=True)

    results: list[EvaluationResult] = []
    raw_runs: list[dict[str, Any]] = []

    async def _run_all() -> None:
        for task in tasks:
            run_result, elapsed, err = await _run_one(task, datasets_dir)
            if err and run_result is None:
                ev = evaluate_task(task, None, elapsed_ms=elapsed)
                ev.error = err
            else:
                ev = evaluate_task(task, run_result, elapsed_ms=elapsed)
                if err:
                    ev.error = err
            results.append(ev)
            raw_runs.append({"task_id": task.id, "elapsed_ms": elapsed, "run_result": run_result, "error": err})

    asyncio.run(_run_all())

    agg = aggregate_metrics(results)
    payload = {
        "catalog": str(catalog_path),
        "datasets_dir": str(datasets_dir),
        "n_tasks": len(tasks),
        "aggregate": agg,
        "results": [r.model_dump(mode="json") for r in results],
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    # also write lightweight summary
    summary = json.dumps(agg, indent=2)
    (out_dir / "summary.json").write_text(summary, encoding="utf-8")
    # raw for debugging
    (out_dir / "raw_runs.json").write_text(json.dumps(raw_runs, indent=2, ensure_ascii=False)[:10_000_000], encoding="utf-8")
    return payload
