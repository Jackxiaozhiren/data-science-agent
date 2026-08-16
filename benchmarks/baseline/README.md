# Baseline Freeze — V1.8 → V2.0 Regression Contract

> Frozen on `v1.8.0` (`587c4bf`) · live-verified 2026-08-16 · `docs/v2/Baseline Report.md` is authoritative.

This directory is the **regression anchor** for V2.0. Every V2 workstream must not regress these without an ADR.

```
benchmarks/baseline/
├── summary.json   # aggregate 50/50 @ 1.0 (task_success 1.0, sql 1.0, statistical 1.0, code 1.0, evidence 1.0, unsupported 0.06, mean_latency 47.92ms)
├── results.json   # per-task EvaluationResult + by_category (8 cats @ 1.0)
└── raw_runs.json  # full run_result dump (state + tool_calls + evidence) for trajectory debugging
```

## How to reproduce

```bash
uv run dsa --limit 50 --out /tmp/dsa-bench-baseline
cat /tmp/dsa-bench-baseline/summary.json
diff /tmp/dsa-bench-baseline/summary.json benchmarks/baseline/summary.json
```

## Gates anchored here

- Functional: 86 tests pass · 74% coverage branch · mypy 81 files clean · ruff 184 frozen · next 7/7 · compose valid
- Budget: 50 tasks / 20 datasets (seed 42) — mean_latency 47.92ms baseline
- Tolerance: any W2+ PR that drops `task_success_rate` or raises `unsupported_claim_rate` without ADR fails CI
