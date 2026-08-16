from __future__ import annotations

import argparse
from pathlib import Path

from dsa_evaluation.runner import run_benchmark


def main() -> None:
    ap = argparse.ArgumentParser(description="DS-Agent-Benchmark runner")
    ap.add_argument(
        "--catalog", type=Path, default=Path("benchmarks/ds-agent-benchmark/catalog.json")
    )
    ap.add_argument("--datasets", type=Path, default=Path("benchmarks/ds-agent-benchmark/datasets"))
    ap.add_argument("--out", type=Path, default=Path("benchmarks/ds-agent-benchmark/results"))
    ap.add_argument("--limit", type=int, default=None, help="Limit number of tasks for quick run")
    ap.add_argument(
        "--task", action="append", dest="tasks", default=None, help="Filter to task id(s)"
    )
    args = ap.parse_args()
    payload = run_benchmark(
        args.catalog, args.datasets, args.out, limit=args.limit, task_ids=args.tasks
    )
    agg = payload.get("aggregate", {})
    print("=== DS-Agent-Benchmark ===")
    print(f"Tasks: {payload.get('n_tasks')}")
    print(f"Task success rate: {agg.get('task_success_rate')}")
    print(f"By category: {agg.get('by_category')}")
    print(f"Results written to: {args.out}")


if __name__ == "__main__":
    main()
