# Research & Benchmark

## DS-Agent-Benchmark
`benchmarks/ds-agent-benchmark/` — 20 synthetic CSVs (seed 42, 8770 rows) + `catalog.json` (50 tasks over 8 categories: EDA / SQL / Statistics / Regression / Classification / Time Series / Visualization / Data Quality) + `scripts/generate_benchmark_datasets.py`.

```bash
uv run dsa --help
uv run dsa --limit 50
```

Metrics in `packages/evaluation/src/dsa_evaluation/metrics.py`: `task_success_rate / statistical_accuracy / sql_accuracy / code_execution / evidence_coverage / unsupported_claim_rate / mean_latency / by_category`.

## Research Report Stub
When publishing, replace `reports/` with experiment logs and cite `ARCHITECTURE_FREEZE_V0.1.md` §50-52 for metric definitions. Synthetic datasets are CC0; when swapping in real ones (e.g. Titanic), record source/license/citation in `THIRD_PARTY_LICENSES.md`.
