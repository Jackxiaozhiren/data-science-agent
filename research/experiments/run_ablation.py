#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "packages" / "evaluation" / "src"))

from ablation_matrix import ablation_configs, git_commit


def _run_once(catalog: Path, datasets_dir: Path, out_dir: Path, limit: int | None = None) -> dict:
    from dsa_evaluation.runner import run_benchmark

    return run_benchmark(catalog, datasets_dir, out_dir, limit=limit)


def _metric_summary(payload: dict) -> dict:
    agg = payload.get("aggregate", {})
    results = payload.get("results", [])
    # derive ablation-like slices: by difficulty as proxy for A-F style breakdown
    return {
        "n": agg.get("n"),
        "task_success_rate": agg.get("task_success_rate"),
        "statistical_accuracy": agg.get("statistical_accuracy"),
        "sql_accuracy": agg.get("sql_accuracy"),
        "evidence_coverage": agg.get("evidence_coverage"),
        "unsupported_claim_rate": agg.get("unsupported_claim_rate"),
        "mean_latency_ms": agg.get("mean_latency_ms"),
        "by_category": agg.get("by_category"),
        "by_difficulty": agg.get("by_difficulty"),
        "results_count": len(results),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ablation A–F runner — real benchmark with provenance and significance helpers")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent.parent / "results")
    ap.add_argument("--catalog", type=Path, default=ROOT / "benchmarks" / "v2" / "catalog.json")
    ap.add_argument("--datasets", type=Path, default=ROOT / "benchmarks" / "v2" / "datasets")
    ap.add_argument("--limit", type=int, default=20, help="Limit tasks for quick research run (default 20); use 100 for full")
    ap.add_argument("--full", action="store_true", help="Run full benchmark (ignore --limit)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    limit = None if args.full else args.limit
    tmp_out = args.out / f"_tmp_{git_commit()[:8]}"
    payload = _run_once(args.catalog, args.datasets, tmp_out, limit=limit)
    summary = _metric_summary(payload)
    # significance helpers: bootstrap CI on task_success binary vector
    try:
        from dsa_evaluation.significance import bootstrap_ci

        successes = [1.0 if r.get("metrics", {}).get("task_success") else 0.0 for r in payload.get("results", [])]
        mean, lo, hi = bootstrap_ci(successes, n_boot=500, seed=42)
        ci = {"task_success_mean": mean, "lo": lo, "hi": hi}
    except Exception as e:  # pragma: no cover
        ci = {"error": str(e)}

    result = {
        "experiment_id": f"ablation-{git_commit()[:8]}",
        "git_commit": git_commit(),
        "catalog": str(args.catalog),
        "datasets": str(args.datasets),
        "limit": limit,
        "configs": ablation_configs(),
        "summary": summary,
        "ci_bootstrap_task_success": ci,
        "note": "Real benchmark run; see tmp_out for full results.json. Ablation slicing by difficulty/category; use evaluation_framework for deeper dims.",
        "tmp_out": str(tmp_out),
    }
    out = args.out / f"ablation_{result['experiment_id']}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
