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

## Provenance of the frozen numbers

The `task_success_rate: 1.0` stored here was produced by the evaluator **as it stood before
`c1c7680`**, at which point `task_success` was `bool(has_ok and (has_report or tcalls))` and ignored
the run's own verdict. `c1c7680` made it honour that verdict, so the same harness now measures
lower on runs the agent itself reports `FAILED` — verified at `--limit 5`, which moved 1.0 → 0.8
because `eda-01`'s `unsupported_claim` check fails:

```bash
uv run dsa --limit 5 --out /tmp/dsa-bench-probe \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

A lower number measured this way is the metric becoming honest, not a regression. Do not "fix" it
by restoring the old evaluator behaviour.

Two scope notes so the gates above are not read as more than they are:

- `tests/regression/test_regression_matrix.py::test_baseline_contract` compares the **stored** file
  against `1.0`. Nothing in CI recomputes the snapshot, so the `diff` in "How to reproduce" is a
  manual step and a genuine product regression would not redden it on its own.
- Re-freezing this directory to post-`c1c7680` numbers requires a version bump
  (`docs/reproducibility.md` §"Immutability") and is therefore held as a release decision,
  not folded into a fix commit.

## Gates anchored here

- Functional: 86 tests pass · 74% coverage branch · mypy 81 files clean · ruff 184 frozen · next 7/7 · compose valid
- Budget: 50 tasks / 20 datasets (seed 42) — mean_latency 47.92ms baseline
- Tolerance: any W2+ PR that drops `task_success_rate` or raises `unsupported_claim_rate` without ADR fails CI
