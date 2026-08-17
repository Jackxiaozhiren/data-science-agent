# DS-Agent-Benchmark v2 — Documentation & Provenance (§50)

> 30 datasets (20 v1 verbatim + 10 new) · 100 tasks · 11 categories (EDA 11 / SQL 11 / Statistics 13 / Regression 9 / Classification 9 / Time Series 8 / Visualization 8 / Data Quality 8 / Data Profiling 6 / Clustering 7 / Evidence Validation 10) · difficulties easy 35 / medium 43 / hard 14 / expert 8 · `catalog 0.3.0` (audited) · `seed 42` deterministic

Built by `scripts/generate_benchmark_v2.py` (seed 42, deterministic). Each task carries `difficulty`, `gold_method`, `required_tools`, `gold_metrics`, `required_evidence`, `forbidden_claims` + audit fields `source/license/citation/benchmark_version/benchmark_generator/human_reviewer/statistical_reviewer/acceptable_method/acceptable_metrics/acceptable_evidence/acceptable_interpretation/forbidden_interpretation/evaluation_function/evaluator_version` + 6-level evaluation via `packages/evaluation/src/dsa_evaluation/evaluation_framework.py`.

```
benchmarks/v2/
  catalog.json    100 tasks (50 v1 annotated + 50 new) — version 0.3.0, audit sha c493bc69
  datasets/       30 CSVs (mirrors ds-agent-benchmark/datasets + clustering/imbalanced/time_series_long/mixed_types/high_card/high/leakage/missing_heavy/unicode/wide/causal_toy)
```

## Documentation (§50 Required)

- **Dataset Sources / Licenses / Citation**: Synthetic via `generate_benchmark_v2.py` (seed 42) — per-task `source = synthetic generate_benchmark_v2.py`, `license = CC0`, `citation = benchmark 0.3.0`. Real swaps record `THIRD_PARTY_LICENSES.md`. See `docs/v3/BENCHMARK_AUDIT.md` Q1–Q6 + `docs/v3/V2_FINAL_BASELINE.md` §7.
- **Task Generation / Validation / Gold Standards**: Generation §50 above; validation = `BENCHMARK_AUDIT.md` Q1–Q10 (§12) + per-task `acceptable_*` / `forbidden_interpretation` (§16) forbidding single-method gating; metrics in `metrics.py` + `statistical_eval.py` evaluator_v2.
- **Scoring / Limitations / Seed / Hardware / Software**: §50 scoring in `metrics.py` + `statistical_eval.py`; limitations §50 in this report + `research/V3_RESEARCH_REPORT.md`; `seed 42 / Python 3.12 / uv 0.11.7 / Node v24.15.0 / Darwin arm64 / uv.lock 114`.

Run:

```bash
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --out /tmp/v2-bench --limit 50
uv run dsa --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets --out /tmp/dsa-bench-baseline   # frozen baseline
# Reproducibility: uv run dsa --reproduce v2 --out reproduction/v2
```

Categories match V2 §15 (Profiling/EDA/Statistics/Regression/Classification/Clustering/Time Series/Data Quality/Visualization/Evidence Validation).
