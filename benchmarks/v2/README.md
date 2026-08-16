# DS-Agent-Benchmark v2

> 30 datasets (20 v1 verbatim + 10 new) · 100 tasks · 11 categories (EDA 11 / SQL 11 / Statistics 13 / Regression 9 / Classification 9 / Time Series 8 / Visualization 8 / Data Quality 8 / Data Profiling 6 / Clustering 7 / Evidence Validation 10) · difficulties easy 35 / medium 43 / hard 14 / expert 8

Built by `scripts/generate_benchmark_v2.py` (seed 42, deterministic). Each task carries `difficulty`, `gold_method`, `required_tools`, `gold_metrics`, `required_evidence`, `forbidden_claims` + 6-level evaluation via `packages/evaluation/src/dsa_evaluation/evaluation_framework.py`.

```
benchmarks/v2/
  catalog.json    100 tasks (50 v1 tasks annotated + 50 new)
  datasets/       30 CSVs (mirrors ds-agent-benchmark/datasets + clustering/imbalanced/time_series_long/mixed_types/high_card/high/leakage/missing_heavy/unicode/wide/causal_toy)
```

Run:

```bash
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --out /tmp/v2-bench --limit 50
uv run dsa --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets --out /tmp/dsa-bench-baseline   # frozen baseline
```

Categories match V2 §15 (Profiling/EDA/Statistics/Regression/Classification/Clustering/Time Series/Data Quality/Visualization/Evidence Validation).
