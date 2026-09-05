# Contribute a Benchmark Task

This walkthrough adds one small task to the benchmark that the default `dsa` runner and current evaluator can execute locally. It uses an existing synthetic dataset, so there is no download, API key, or dataset-license setup.

## 1. Start from the active benchmark

The default regression suite lives here:

```text
benchmarks/ds-agent-benchmark/
├── catalog.json
└── datasets/
```

`catalog.json` is validated by `dsa_evaluation.catalog.Catalog`. Every task must provide:

- `id` — unique task identifier;
- `category` — one of the categories accepted by `BenchmarkTask`;
- `dataset` — a filename under `datasets/`;
- `question` — the user-facing analysis request;
- `expected_analysis` — a short description of the intended analysis.

`ground_truth`, `criteria`, difficulty, and the richer gold fields are optional in the schema, but a useful benchmark contribution should include scoring criteria that make the intended behavior measurable.

## 2. Add one measurable task

For this example, reuse the existing synthetic `sales.csv` and add a genuinely new SQL question. Append a task like this to the `tasks` array in `benchmarks/ds-agent-benchmark/catalog.json`:

```json
{
  "id": "contrib-sql-avg-revenue-region",
  "category": "SQL",
  "dataset": "sales.csv",
  "question": "Compute average revenue by region.",
  "expected_analysis": "AVG revenue grouped by region",
  "ground_truth": {
    "expected_tool": "run_sql",
    "sql_contains": ["AVG", "GROUP BY"]
  },
  "criteria": {
    "task_success": true,
    "sql_accuracy": true
  },
  "difficulty": "easy"
}
```

Use a unique, stable ID. Do not renumber existing tasks just to insert a new one.

Before proposing a task, search the catalog for an equivalent question. A benchmark grows in value when a new task adds coverage for a distinct capability or regression, not when it restates an existing task.

## 3. Know what the current scorer actually checks

The catalog contains both descriptive metadata and fields that feed the current lightweight evaluator. Do not assume a field changes the score merely because it exists in the schema.

| Field / criterion | Current behavior |
|---|---|
| `task_success` | Passes when the run has at least one successful tool call and a usable run result. |
| `sql_accuracy` + `ground_truth.sql_contains` | Requires successful `run_sql` output whose SQL contains every configured fragment, case-insensitively. |
| `statistical_accuracy` + `expected_value` | Searches supported numeric outputs and compares against `expected_value` using `tolerance` (default relative tolerance 5%). |
| `evidence_coverage` | Checks that insights carry evidence IDs, with a fallback to the presence of evidence. |
| `visualization` | Checks for a successful `create_chart` call; `chart_type` can make chart presence part of task success. |
| `expected_tool` | Useful ground-truth metadata, but it is not currently a standalone scoring assertion. Pair it with measurable criteria such as `sql_accuracy`, or add evaluator coverage if exact tool selection is the behavior you need to score. |
| `expected_analysis` | Human-readable intent; it is not scored by prose similarity. |

The evaluator also runs its statistical-quality audit and records S01–S10-style dimensions in result details. For statistical tasks, read [Evaluation](evaluation.md) before choosing assertions.

### Prefer structural assertions over prose similarity

Good assertions verify an executed behavior or measurable output, for example:

- SQL contains `GROUP BY` and `AVG`;
- a numerical result is within a declared tolerance;
- evidence exists for generated insights;
- a chart tool executed successfully.

Avoid gold answers such as “the response should mention that region A performs well.” The current benchmark is designed around execution and provenance rather than fuzzy text matching.

## 4. Validate the catalog schema

Run this before executing the task:

```bash
uv run python -c "from pathlib import Path; from dsa_evaluation.catalog import Catalog; c=Catalog.load(Path('benchmarks/ds-agent-benchmark/catalog.json')); print(len(c.tasks), 'tasks; catalog valid')"
```

A misspelled category, missing required field, or invalid value should fail here instead of becoming a confusing benchmark failure later.

## 5. Run only the new task

The top-level CLI supports task-ID filtering, so you do not need to run the whole catalog:

```bash
uv run dsa \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets \
  --task contrib-sql-avg-revenue-region \
  --out /tmp/dsa-contrib-task
```

The default local mode is deterministic/offline; no model API key is required for this contributor check.

Inspect the generated files:

```text
/tmp/dsa-contrib-task/
├── results.json
├── summary.json
├── run_manifest.json
└── raw_runs.json
```

For this example, confirm that:

- `n_tasks` is `1`;
- the result has `task_id: contrib-sql-avg-revenue-region`;
- `metrics.task_success` is `true`;
- `metrics.sql_accuracy` is `true`;
- `details.sql_contains` records the fragments being checked.

A task is not ready just because the command exits. Read the per-task result and make sure the criterion is testing the behavior you intended.

## 6. Add a dataset only when needed

Prefer an existing synthetic dataset when it can express the new capability. If a new dataset is necessary:

1. Put it under `benchmarks/ds-agent-benchmark/datasets/`.
2. Prefer a tiny deterministic synthetic dataset that can be regenerated or independently inspected.
3. Never add private, credentialed, confidential, or personally identifying data.
4. For third-party public data, verify redistribution rights and record the source, license, and citation in `THIRD_PARTY_LICENSES.md` before opening the PR.

The datasets currently shipped with the benchmark are documented as synthetic, deterministic (seed 42), and CC0/public-domain data.

## 7. Run the repository gates

At minimum, run the focused benchmark task and the documentation build:

```bash
uv run dsa \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets \
  --task contrib-sql-avg-revenue-region \
  --out /tmp/dsa-contrib-task

uv run python -m mkdocs build --strict
```

Before opening a PR, follow the full gate list in [Contributing](contributing.md).

## Contribution checklist

- [ ] The task ID is unique and stable.
- [ ] The question adds distinct benchmark coverage.
- [ ] The dataset exists and its license/provenance is acceptable.
- [ ] The task validates through `Catalog.load`.
- [ ] The scoring criterion is structural and measurable.
- [ ] The single-task benchmark run passes for the intended reason.
- [ ] No existing benchmark task or result was silently rewritten.
- [ ] Documentation still builds with MkDocs strict mode.

If the behavior you want to measure cannot be expressed by the current evaluator, propose the evaluator change and its tests together with the new task rather than encoding an unscored field and assuming it is enforced.
