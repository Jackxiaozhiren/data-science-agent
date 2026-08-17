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
    sub.add_parser("demo", help="One-command demo (§40): demo dataset → analysis → evidence → report")
    sub.add_parser("external-validation", help="Installation + demo metrics (§42)")
    p_verify = sub.add_parser("verify-release", help="Release verification (§63): dsa verify-release v3.0.0")
    p_verify.add_argument("version", nargs="?", default="v3.0.0", help="Release version")
    p_verify.add_argument("--json", action="store_true", help="Output JSON")
    p_research = sub.add_parser("research", help="Research run/reproduce (§57): dsa research run|reproduce --experiment <id>")
    p_research.add_argument("action", nargs="?", choices=["run", "reproduce"], help="run or reproduce")
    p_research.add_argument("--experiment", type=str, default=None, help="Experiment id")
    sub.add_parser("doctor", help="One-command setup check (§34 W5): dsa doctor")
    p_init = sub.add_parser("init", help="One-command project (§36 W5): dsa init my-project")
    p_init.add_argument("project", nargs="?", default="my-project", help="Project name")
    sub.add_parser("analyze", help="Analyze dataset (§37): dsa analyze <dataset> --task ... [--json]")
    sub.add_parser("profile", help="Profile dataset (§37): dsa profile <dataset> [--json]")
    sub.add_parser("benchmark", help="Run benchmark (§37): dsa benchmark [--limit N] [--catalog ...]")
    sub.add_parser("reproduce", help="Reproduce (§37): dsa reproduce [--benchmark v2]")
    sub.add_parser("plugin", help="Plugin registry (§28): dsa plugin list")
    sub.add_parser("mcp", help="MCP (§32): dsa mcp tools")

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

    if args.cmd == "demo":
        from dsa_evaluation.external_validation import run_demo

        out = Path("demo/runs/demo")
        res = run_demo(out=out)
        print(json.dumps(res.model_dump(mode="json"), indent=2, ensure_ascii=False))
        if not res.task_success:
            print(f"demo failed: {res.error}", file=sys.stderr)
            sys.exit(1)
        return
    if args.cmd == "external-validation":
        from dsa_evaluation.external_validation import collect_installation_metrics

        m = collect_installation_metrics()
        print(json.dumps(m.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return
    if args.cmd == "verify-release":
        from dsa_evaluation.verify_release import verify_release

        ver = getattr(args, "version", "v3.0.0") or "v3.0.0"
        use_json = bool(getattr(args, "json", False))
        rep = verify_release(ver)
        if use_json:
            print(json.dumps(rep, indent=2, ensure_ascii=False))
        else:
            print(f"=== Release Verification Report {rep['version']} ===")
            for k, v in rep["gates"].items():
                print(f"  {k}: {v}")
            print(f"Summary: {rep['summary']}")
            if rep["details"]:
                print("\nDetails (failures):")
                for k, v in rep["details"].items():
                    print(f"  {k}: {v[:400]}")
        if any(v == "FAIL" for v in rep["gates"].values()):
            sys.exit(1)
        return
    if args.cmd == "research":
        # dsa research run|reproduce --experiment <id> (§57) — via argparse subcommand
        action = getattr(args, "action", None)
        exp = getattr(args, "experiment", None)
        if action in ("run", "reproduce") and exp:
            from dsa_evaluation.research_manifest import build_manifest

            root = Path.cwd() if (Path.cwd() / "pyproject.toml").exists() else Path(__file__).parents[3]
            man = build_manifest(exp, root=root, configuration={"action": action})
            print(json.dumps(man.model_dump(mode="json"), indent=2, ensure_ascii=False))
            return
            print(json.dumps({"error": "Usage: dsa research run|reproduce --experiment <id> (§57)"}, ensure_ascii=False))
        sys.exit(2)
    if args.cmd == "doctor":
        from dsa_evaluation.doctor import run_doctor

        rep = run_doctor()
        as_json = "--json" in sys.argv
        if as_json:
            print(json.dumps(rep, indent=2, ensure_ascii=False))
        else:
            print(f"=== dsa doctor ({rep['status']}) ===")
            for c in rep["checks"]:
                print(f"  {c['name']}: {c['status']}" + (f" — {c['message']}" if c.get("message") else ""))
            print(f"Status: {rep['status']}")
        sys.exit(0 if rep["status"] in ("ok", "warn") else 1)
    if args.cmd == "init":
        proj = getattr(args, "project", "my-project") or "my-project"
        if "--json" in sys.argv:
            import tempfile

            # JSON mode for tests: create in temp
            td = Path(tempfile.mkdtemp(prefix="dsa-init-"))
            from dsa_evaluation.project_init import init_project

            p = init_project(td / proj)
            print(json.dumps({"project": str(p), "status": "ok"}, ensure_ascii=False))
        else:
            from dsa_evaluation.project_init import init_project

            p = init_project(Path(proj))
            print(f"Created {p}")
        return
    if args.cmd == "analyze":
        # Usage: dsa analyze <dataset> --task "..." [--json]  -> parse remaining argv
        import argparse as _ap2

        ap2 = _ap2.ArgumentParser(prog="dsa analyze")
        ap2.add_argument("dataset")
        ap2.add_argument("--task", required=True)
        ap2.add_argument("--json", action="store_true")
        a2 = ap2.parse_args(sys.argv[2:])
        from data_science_agent import Agent

        agent = Agent()
        r = agent.analyze_sync(a2.dataset, a2.task)
        if a2.json:
            print(json.dumps({"run_id": r.run_id, "status": r.status, "report": r.report_markdown[:500] if r.report_markdown else None, "evidence": len(r.evidence), "error": r.error}, ensure_ascii=False))
        else:
            print(f"status={r.status} evidence={len(r.evidence)}")
            if r.report_markdown:
                print(r.report_markdown[:2000])
        return
    if args.cmd == "profile":
        import argparse as _ap3

        ap3 = _ap3.ArgumentParser(prog="dsa profile")
        ap3.add_argument("dataset")
        ap3.add_argument("--json", action="store_true")
        a3 = ap3.parse_args(sys.argv[2:])
        from data_science_agent import Agent

        prof = Agent().profile(a3.dataset)
        print(json.dumps(prof, ensure_ascii=False) if a3.json else str(prof))
        return
    if args.cmd == "benchmark":
        import argparse as _ap4

        ap4 = _ap4.ArgumentParser(prog="dsa benchmark")
        ap4.add_argument("--limit", type=int, default=None)
        ap4.add_argument("--catalog", type=Path, default=None)
        ap4.add_argument("--datasets", type=Path, default=None)
        ap4.add_argument("--json", action="store_true")
        a4 = ap4.parse_args(sys.argv[2:])
        cat = a4.catalog or Path("benchmarks/ds-agent-benchmark/catalog.json")
        ds = a4.datasets or Path("benchmarks/ds-agent-benchmark/datasets")
        payload = run_benchmark(cat, ds, Path("benchmarks/ds-agent-benchmark/results"), limit=a4.limit)
        print(json.dumps({"n_tasks": payload.get("n_tasks"), "aggregate": payload.get("aggregate")}, ensure_ascii=False) if a4.json else f"Tasks: {payload.get('n_tasks')} success={payload.get('aggregate', {}).get('task_success_rate')}")
        return
    if args.cmd == "plugin":
        from dsa_plugins.registry import list_plugins

        pls = list_plugins()
        print(json.dumps([p.model_dump(mode="json") if hasattr(p, "model_dump") else dict(p) for p in pls], ensure_ascii=False))
        return
    if args.cmd == "mcp":
        from dsa_mcp.adapter import list_tools as mcp_list

        tools = mcp_list()
        print(json.dumps([t if isinstance(t, dict) else t for t in tools], ensure_ascii=False))
        return

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
