# DS-Agent-Benchmark

Evidence-grounded regression benchmark for Data Science Agent.

## Structure

- `datasets/` — 20 synthetic public-domain CSVs (seeded, deterministic)
- `catalog.json` — 50 tasks across 8 categories with ground truth and evaluation criteria
- runner — `packages/evaluation` plus the `dsa` CLI

## Categories

EDA (8), SQL (7), Statistics (8), Regression (6), Classification (6), Time Series (5), Visualization (5), Data Quality (5) = 50 tasks.

## Metrics

The current runner records task success, statistical accuracy where configured, code execution success, SQL accuracy, evidence coverage, unsupported-claim checks, latency, and evaluator-v2 statistical-quality details.

## Run

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

## Contribute a task

See [`docs/benchmark-task-contribution.md`](../../docs/benchmark-task-contribution.md) for the validated task schema, a complete example, current scoring semantics, single-task execution, and dataset licensing rules.

The datasets in this directory are **synthetic and deterministic** (seed 42) and documented as CC0/public domain. Do not add private or unlicensed data; third-party public datasets must have source/license/citation recorded in `THIRD_PARTY_LICENSES.md`.
