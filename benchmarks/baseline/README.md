# Baseline Freeze — V1.8 → V2.0 Regression Contract

> Frozen on `v1.8.0` (`587c4bf`) · live-verified 2026-08-16 · re-measured 2026-10-05 at `9f6ab35` · `docs/v2/Baseline Report.md` is authoritative.

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

Read `DSA_LLM_MODE` before trusting that diff. It is unset in the command above, and the runner
resolves it to `stub`: the heuristic provider, zero model calls (`call_count: 0` in the manifest a
reproduce run writes). Nothing here records which mode produced *these* numbers -- the frozen
`results.json` has no `execution` block and no `run_manifest.json` was ever committed -- so the two
sides of the diff are not known to be the same kind of run.

Measured on 2026-10-05 at `9f6ab35`, four runs of the command above (§113):

- `task_success_rate`, `statistical_accuracy`, `sql_accuracy`, `code_execution_success` and
  `evidence_coverage` reproduce exactly: 50/50 @ 1.0 in all four.
- `unsupported_claim_rate` reads 0.0, against the 0.06 stored here and the 0.08 §86 measured on
  2026-10-03. The direction is a reduction in unsupported claims, so it is not a regression; which
  of §99 (the planner's spurious `causal_check` step) or §107 (its always-chart branch) accounts for
  it is not pinned, and saying "the metric became honest" again would launder an unattributed delta.
- `mean_latency_ms` is not comparable in either direction. The same command on the same commit read
  162.3, 73.04 and 89.56 within minutes of each other, so a latency delta says more about the
  machine than about the code, and the 47.92 ms stored here is a 2026-08-16 reading on a different
  tree. The figure that carries weight is the ceiling in
  `tests/regression/test_regression_matrix.py::test_baseline_contract`, which is checked against
  this stored file and never against a fresh run.

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

- Functional: `pytest -q --cov` against the `fail_under` floor in `pyproject.toml`, with `ruff check`,
  `ruff format --check` and `mypy` as CI steps. No count is quoted on this line on purpose: the
  figures it used to carry were a dated snapshot of a different tree, and this directory sat outside
  every prose guard until §113 brought it inside `scripts/check_public_claims.py`.
- Budget: 50 tasks / 20 datasets (seed 42). Those three are catalog facts with owners, and
  `tests/test_baseline_readme_integrity.py` re-derives each from `benchmarks/ds-agent-benchmark/`
  and `scripts/generate_benchmark_datasets.py` rather than restating them.
- Tolerance: nothing in CI recomputes this snapshot, so a product regression that leaves the stored
  file untouched stays green. `tests/regression/test_regression_matrix.py::test_baseline_contract`
  compares the file against `1.0`; the ADR requirement is a review convention, not a check. Adding a
  workflow step that re-runs the 50 tasks would be the way to make the old sentence true, and is not
  something this document can promise on its own.
