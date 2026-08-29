# Benchmark

DSA keeps its benchmark runner, task catalog, datasets, and evaluation artifacts in the repository so a result can be inspected against the exact task definition that produced it.

## Active regression suite

The default CLI and CI smoke run use:

```text
benchmarks/ds-agent-benchmark/
├── README.md
├── catalog.json
└── datasets/
```

The suite currently contains 50 tasks over synthetic, deterministic datasets. `catalog.json` is loaded through `dsa_evaluation.catalog.Catalog`, and scoring is implemented in `packages/evaluation/src/dsa_evaluation/`.

The repository also contains larger/versioned research benchmark material under `benchmarks/v2/`. Keep the benchmark path and evaluator version attached to any reported result; do not compare outputs from different suites as if they were the same frozen evaluation.

## Run the active suite

Run a small deterministic smoke:

```bash
uv run dsa \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets \
  --limit 5 \
  --out /tmp/dsa-bench
```

Run one task by ID:

```bash
uv run dsa \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets \
  --task sql-03 \
  --out /tmp/dsa-sql-03
```

Run the whole active catalog by omitting `--limit` and `--task`.

## What gets written

A benchmark run produces:

- `results.json` — per-task metrics plus aggregate metrics and execution metadata;
- `summary.json` — lightweight aggregate summary;
- `run_manifest.json` — catalog/dataset paths and execution provenance;
- `raw_runs.json` — raw per-task execution results for debugging and audit.

Real-model runs add provider/model call provenance through the same runner. See [Real-model Evaluation](real-model-evaluation.md) before treating a result as model-performance evidence.

## How tasks are evaluated

The lightweight evaluator records task success, code execution success, optional SQL/statistical accuracy, evidence coverage, unsupported-claim checks, and latency. A second statistical audit attaches evaluator-v2 quality dimensions to result details.

The benchmark intentionally favors structural evidence from executed work over fuzzy prose matching. For example, SQL tasks can require SQL fragments; statistical tasks can compare supported numeric outputs against a value with tolerance; evidence tasks can require evidence coverage.

See [Evaluation](evaluation.md) for interpretation rules and versioning requirements.

## Contribute one task

New contributors can add and run a single task without executing the entire suite. Follow [Contribute a Benchmark Task](benchmark-task-contribution.md) for the schema, a complete example, task-ID filtering, scoring behavior, and dataset licensing rules.

## Dataset provenance

The datasets currently shipped under `benchmarks/ds-agent-benchmark/datasets/` are synthetic, deterministic (seed 42), and documented as CC0/public domain. Third-party data must have verified redistribution rights and be recorded in `THIRD_PARTY_LICENSES.md` before it is added.
