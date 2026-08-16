# DS-Agent-Benchmark

Evidence-grounded benchmark for the Data Science Agent.

## Structure
- `datasets/`  20 synthetic public-domain CSVs (seeded, deterministic)
- `catalog.json`  50 tasks across 8 categories with ground truth + evaluation criteria
- Runner: `packages/evaluation` (Python) + CLI `dsa benchmark`

## Categories
- EDA (8), SQL (7), Statistics (8), Regression (6), Classification (6), Time Series (5), Visualization (5), Data Quality (5) = 50

## Metrics
- Task Success Rate, Statistical Accuracy, Code Execution Success, SQL Accuracy, Evidence Coverage, Unsupported Claim Rate, Hallucination flags, Latency, Reproducibility

## Run
```bash
uv run dsa benchmark --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets --out benchmarks/ds-agent-benchmark/results
# or via package
uv run python -m dsa_evaluation --help
```

Datasets are **synthetic and deterministic** (seed 42) — no external download, no copyrighted data.
