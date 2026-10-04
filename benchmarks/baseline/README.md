# Baseline Freeze — V1.8 → V2.0 Regression Contract

> Frozen on `v1.8.0` (`587c4bf`) · live-verified 2026-08-16 · `docs/v2/Baseline Report.md` is authoritative.

This directory is the **regression anchor** for V2.0. Every V2 workstream must not regress these without an ADR.

```
benchmarks/baseline/
├── summary.json   # aggregate 50/50 @ 1.0 (task_success 1.0, sql 1.0, statistical 1.0, code 1.0, evidence 1.0, unsupported 0.06, mean_latency 47.92ms)
├── results.json   # per-task EvaluationResult + by_category (8 cats @ 1.0)
└── raw_runs.json  # NOT committed. Produced by a reproduce run into its own out-dir;
                   # a full run_result dump (state + tool_calls + evidence) for trajectory debugging.
```

The tree above is pinned by
`tests/test_baseline_readme_integrity.py::test_every_file_named_in_the_tree_block_is_present_or_annotated`,
which is what the second line's absence taught: a directory listing that names a file nobody commits is
a claim about the repository, not about the benchmark, and it was false since the freeze.

## How to reproduce

```bash
uv run dsa --limit 50 --out /tmp/dsa-bench-baseline
cat /tmp/dsa-bench-baseline/summary.json
diff /tmp/dsa-bench-baseline/summary.json benchmarks/baseline/summary.json
```

## Provenance of the frozen numbers

The `task_success_rate: 1.0` stored here was produced by the evaluator **as it stood before
`c1c7680`**, at which point `task_success` was `bool(has_ok and (has_report or tcalls))` and ignored
the run's own verdict. `c1c7680` made it honour that verdict, so the same harness measures
lower on runs the agent itself reports `FAILED` — observed on 2026-09-28 at `--limit 5` as
1.0 → 0.8, attributed at the time to `eda-01`'s `unsupported_claim` check failing:

```bash
uv run dsa --limit 5 --out /tmp/dsa-bench-probe \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

A lower number measured this way is the metric becoming honest, not a regression. Do not "fix" it
by restoring the old evaluator behaviour. The converse also holds, and is the part this section
had wrong: a number that climbs back has to be explained too. On 2026-10-04 `4d0766a` (audit §99)
removed a planner keyword bug -- the acronym `ate` was matched as a substring, so *cre**ate***,
*duplic**ate**s*, *evalu**ate***, *correl**ate**d* all registered as causal requests, the extra
`causal_check` step produced causal phrasing, the critic raised `S08`, and four tasks read `FAILED`.
With that fixed, both probes measure the frozen value again: `dsa --limit 5` →
`Task success rate: 1.0` (`EDA n=5, task_success 1.0`) and the 50-task run →
`task_success_rate: 1.0`. So the 2026-09-28 attribution ("`eda-01`'s `unsupported_claim` check
fails", and by extension the D-L7-01/D-L7-02 work as the cause of the deficit) was wrong about both
direction and cause; the deficit was a spurious plan step, not the evaluator becoming honest. What
`c1c7680` changed remains true -- `task_success` now honours the run's verdict -- it simply was not
costing anything on this catalog.

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
