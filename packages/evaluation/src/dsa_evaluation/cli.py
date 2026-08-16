from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

from dsa_evaluation.runner import run_benchmark


def _reproduce_benchmark(catalog: Path, datasets: Path, out: Path) -> None:
    from dsa_evidence.reproducibility import compare_runs

    src_catalog = Path(catalog)
    src_datasets = Path(datasets)
    first = Path(out) / "first"
    second = Path(out) / "second"
    first.mkdir(parents=True, exist_ok=True)
    second.mkdir(parents=True, exist_ok=True)

    print("=== Reproduction: first run ===", flush=True)
    run_benchmark(src_catalog, src_datasets, first)
    print("=== Reproduction: second run ===", flush=True)
    run_benchmark(src_catalog, src_datasets, second)

    raw1 = json.loads((first / "raw_runs.json").read_text(encoding="utf-8"))
    raw2 = json.loads((second / "raw_runs.json").read_text(encoding="utf-8"))
    summ1 = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    summ2 = json.loads((second / "summary.json").read_text(encoding="utf-8"))

    # Build a unified comparison for reviewer (§19–21)
    N = len(raw1)
    per_task: list[dict[str, object]] = []
    exec_match = 0
    traj_match = 0
    for a, b in zip(raw1, raw2):
        rr1 = a.get("run_result") or {}
        rr2 = b.get("run_result") or {}
        ok1 = bool(any((c.get("status") == "ok") for c in (rr1.get("tool_calls") or []) if isinstance(c, dict)))
        ok2 = bool(any((c.get("status") == "ok") for c in (rr2.get("tool_calls") or []) if isinstance(c, dict)))
        score = compare_runs(rr1 if isinstance(rr1, dict) else {}, rr2 if isinstance(rr2, dict) else {})
        # Derive 6-dim gate values for this task
        same_exec = ok1 == ok2
        same_traj = bool(score.tool_trajectory_match)
        exec_match += 1 if same_exec else 0
        traj_match += 1 if same_traj else 0
        per_task.append(
            {
                "task_id": a.get("task_id"),
                "L_level": score.level,
                "score": score.score,
                "execution_match": same_exec,
                "trajectory_match": same_traj,
                "conclusion_match": bool(score.conclusion_match),
                "details": score.details,
            }
        )

    overall = round(sum(float(t["score"]) for t in per_task) / N, 4) if N else 0.0  # type: ignore[arg-type,misc]
    execution_rate = round(exec_match / N, 4) if N else 0.0
    trajectory_rate = round(traj_match / N, 4) if N else 0.0
    numerical_rate = round(
        sum(1 for t in per_task if float(t.get("score", 0)) >= 0.5) / N, 4  # type: ignore[arg-type,misc]
    ) if N else 0.0

    # ReproductionScore (6-dim) per §21 — mapped onto DSR reproducibility L0..L5
    reproduction_score = {
        "execution": execution_rate,
        "numerical": numerical_rate,
        "statistical": summ1.get("statistical_accuracy"),
        "evidence": summ1.get("evidence_coverage"),
        "semantic": trajectory_rate,
        "overall": overall,
        "method": "compare_runs L0=L1 (code lenient), L2 data hash, L3 env, L4 trajectory, L5 conclusion (insights/evidence ±20%)",
        "by_level": {lvl: round(sum(1 for t in per_task if t["L_level"] == lvl) / N, 4) for lvl in ("L0", "L1", "L2", "L3", "L4", "L5")},
    }

    manifest = {
        "catalog": str(src_catalog),
        "datasets_dir": str(src_datasets),
        "catalog_sha256": hashlib.sha256(src_catalog.read_bytes()).hexdigest()[:12] if src_catalog.exists() else None,
        "datasets_sha256": None,
        "n_tasks": N,
        "seed": 42,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }
    # datasets hash: sha of sorted file names + sizes (stable, cheap)
    try:
        ds_files = sorted(src_datasets.glob("*.csv")) if src_datasets.exists() else []
        h = hashlib.sha256()
        for p in ds_files:
            h.update(p.name.encode())
            h.update(str(p.stat().st_size).encode())
        manifest["datasets_sha256"] = h.hexdigest()[:12]
    except Exception:
        pass

    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "environment.json").write_text(
        json.dumps(
            {"python_version": sys.version, "platform": platform.platform(), "manifest": manifest},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "results.json").write_text(
        json.dumps({"first": summ1, "second": summ2, "reproduction_score": reproduction_score}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out / "comparison.json").write_text(
        json.dumps(
            {"per_task": per_task, "reproduction_score": reproduction_score, "first_summary": summ1, "second_summary": summ2},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "first_summary.json").write_text(json.dumps(summ1, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "logs" / "second_summary.json").write_text(json.dumps(summ2, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=== Reproduction complete ===")
    print(f"Overall: {overall}  execution:{execution_rate}  trajectory:{trajectory_rate}")
    print(f"Results: {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="DS-Agent-Benchmark runner")
    sub = ap.add_subparsers(dest="cmd")

    # Default benchmark run (backward compatible: `dsa --catalog ... --limit 50`)
    ap.add_argument(
        "--catalog", type=Path, default=Path("benchmarks/ds-agent-benchmark/catalog.json")
    )
    ap.add_argument("--datasets", type=Path, default=Path("benchmarks/ds-agent-benchmark/datasets"))
    ap.add_argument("--out", type=Path, default=Path("benchmarks/ds-agent-benchmark/results"))
    ap.add_argument("--limit", type=int, default=None, help="Limit number of tasks for quick run")
    ap.add_argument(
        "--task", action="append", dest="tasks", default=None, help="Filter to task id(s)"
    )
    ap.add_argument("--reproduce", nargs="?", const="benchmark", default=None, help="Run reproduction harness: --reproduce [benchmark]")
    args = ap.parse_args()

    if args.reproduce is not None:
        target = (args.reproduce or "benchmark").lower()
        # Default out is reproduction/, not benchmark results — per §18
        default_out = Path("reproduction/v2") if ("v2" in target or "v2" in str(args.catalog)) else Path("reproduction/benchmark")
        catalog = args.catalog if str(args.catalog) != "benchmarks/ds-agent-benchmark/catalog.json" or "v2" in target else args.catalog
        datasets = args.datasets if str(args.datasets) != "benchmarks/ds-agent-benchmark/datasets" or "v2" in target else args.datasets
        # When user runs `dsa --reproduce --limit 50` without explicit out, use reproduction/ default, not benchmark results path
        out = default_out if args.out == Path("benchmarks/ds-agent-benchmark/results") else args.out
        if target in ("v2", "benchmark-v2", "v2.0"):
            catalog = Path("benchmarks/v2/catalog.json")
            datasets = Path("benchmarks/v2/datasets")
            out = Path("reproduction/v2") if out == default_out else out
        elif "v2" in target:
            catalog = Path("benchmarks/v2/catalog.json")
            datasets = Path("benchmarks/v2/datasets")
        elif target == "benchmark":
            catalog = Path("benchmarks/ds-agent-benchmark/catalog.json")
            datasets = Path("benchmarks/ds-agent-benchmark/datasets")
            out = Path("reproduction/benchmark") if out == default_out else out
        _reproduce_benchmark(catalog, datasets, out)
        return

    # Spelled subcommand `dsa reproduce --benchmark v2`
    if args.cmd == "reproduce":
        rp = argparse.ArgumentParser(description="Reproduce benchmark (fresh twice + compare)")
        rp.add_argument("--benchmark", type=str, default="v2", help="v2 | ds-agent-benchmark")
        rp.add_argument("--catalog", type=Path, default=None)
        rp.add_argument("--datasets", type=Path, default=None)
        rp.add_argument("--out", type=Path, default=None)
        rargs = rp.parse_args(sys.argv[2:])
        bench = (rargs.benchmark or "v2").lower()
        catalog = rargs.catalog or (Path("benchmarks/v2/catalog.json") if "v2" in bench else Path("benchmarks/ds-agent-benchmark/catalog.json"))
        datasets = rargs.datasets or (Path("benchmarks/v2/datasets") if "v2" in bench else Path("benchmarks/ds-agent-benchmark/datasets"))
        out = rargs.out or (Path("reproduction/v2") if "v2" in bench else Path("reproduction/benchmark"))
        _reproduce_benchmark(catalog, datasets, out)
        return

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
