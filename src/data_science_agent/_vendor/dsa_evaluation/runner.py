from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from dsa_evaluation.catalog import BenchmarkTask, Catalog
from dsa_evaluation.metrics import (
    EvaluationResult,
    aggregate_metrics,
    attach_statistical_eval,
    evaluate_task,
)


def _optional_float_env(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _execution_metadata(llm_calls: list[dict[str, Any]]) -> dict[str, Any]:
    from dsa_agent.critic import evidence_critic_enabled

    mode = os.getenv("DSA_LLM_MODE", "stub").strip().lower()
    provider = (
        os.getenv("DSA_LLM_PROVIDER", "openai").strip().lower()
        if mode in {"real", "openai"}
        else "stub"
    )
    model = (
        os.getenv("DSA_OPENAI_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"
        if provider == "openai"
        else "heuristic"
    )
    critic_enabled = evidence_critic_enabled()

    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    model_latency_ms = 0
    for call in llm_calls:
        usage = call.get("usage")
        if isinstance(usage, dict):
            input_tokens += int(usage.get("input_tokens") or 0)
            output_tokens += int(usage.get("output_tokens") or 0)
            total_tokens += int(usage.get("total_tokens") or 0)
        model_latency_ms += int(call.get("latency_ms") or 0)

    input_rate = _optional_float_env("DSA_INPUT_COST_PER_MILLION")
    output_rate = _optional_float_env("DSA_OUTPUT_COST_PER_MILLION")
    cost_usd: float | None = None
    if input_rate is not None and output_rate is not None:
        cost_usd = round(
            input_tokens * input_rate / 1_000_000 + output_tokens * output_rate / 1_000_000,
            8,
        )

    return {
        "llm_mode": mode,
        "provider": provider,
        "model": model,
        "fallback": os.getenv("DSA_LLM_FALLBACK", "error"),
        "git_commit": os.getenv("DSA_GIT_COMMIT") or os.getenv("GITHUB_SHA"),
        "evaluation_variant": "dsa" if critic_enabled else "dsa-no-critic",
        "evidence_critic_enabled": critic_enabled,
        "evidence_critic_setting": os.getenv("DSA_EVIDENCE_CRITIC", "on"),
        "call_count": len(llm_calls),
        "model_latency_ms": model_latency_ms,
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "pricing": {
            "input_cost_per_million": input_rate,
            "output_cost_per_million": output_rate,
            "source": "explicit environment rates"
            if input_rate is not None and output_rate is not None
            else None,
        },
        "cost_usd": cost_usd,
        "llm_calls": llm_calls,
    }


async def _run_one(
    task: BenchmarkTask, datasets_dir: Path
) -> tuple[dict[str, Any] | None, int, str | None]:
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
        state = await run_analysis(
            dataset_path=str(dataset_path), dataset_id=dataset_id, user_query=task.question
        )
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
    from dsa_llm.providers import get_call_log, reset_call_log

    reset_call_log()
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
            # evaluator_v2 statistical dimensions (§22–25) — non-breaking, stored under details
            try:
                from dsa_evaluation.statistical_eval import evaluate_statistical

                stat = evaluate_statistical(task, run_result, elapsed_ms=elapsed)
                ev = attach_statistical_eval(ev, stat)
            except Exception:
                pass
            results.append(ev)
            raw_runs.append(
                {"task_id": task.id, "elapsed_ms": elapsed, "run_result": run_result, "error": err}
            )

    asyncio.run(_run_all())

    agg = aggregate_metrics(results)
    llm_calls = get_call_log()
    execution = _execution_metadata(llm_calls)
    payload = {
        "catalog": str(catalog_path),
        "datasets_dir": str(datasets_dir),
        "n_tasks": len(tasks),
        "execution": execution,
        "aggregate": agg,
        "results": [r.model_dump(mode="json") for r in results],
    }
    (out_dir / "results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Keep the lightweight aggregate summary backward compatible.
    summary = json.dumps(agg, indent=2)
    (out_dir / "summary.json").write_text(summary, encoding="utf-8")
    (out_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "catalog": str(catalog_path),
                "datasets_dir": str(datasets_dir),
                "n_tasks": len(tasks),
                "execution": execution,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # raw for debugging
    (out_dir / "raw_runs.json").write_text(
        json.dumps(raw_runs, indent=2, ensure_ascii=False)[:10_000_000], encoding="utf-8"
    )
    return payload
