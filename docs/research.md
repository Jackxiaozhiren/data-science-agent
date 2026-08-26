# Research

> Report: `research/V3_RESEARCH_REPORT.md` (Abstract→Limitations) — `research/questions/RQs.md` (RQs 1–5) → `research/experiments/` (ablation A–F) → `research/figures/` + `research/tables/` + `research/paper/` (V2 draft preserved as history). Figures/tables are generated from raw results by `research/scripts/` (raw → script → artifact).

## Full report

See `research/V3_RESEARCH_REPORT.md` — Abstract, Introduction, Research Questions, System Architecture (§49 7 diagrams), Evaluation Methodology (§72–77 versioning + §45 traceability), Benchmark (§50 provenance), Experimental Setup (§56 manifests), Results (Ablation A–F + Cross-Model 4 classes + Statistical S01–S10 + Failures F01–F15 + Human 11/100), Reproducibility (§17–21 L0–L5), Limitations, Conclusion, Appendix (gates).

## DS-Agent-Benchmark (v1 + v2)

`benchmarks/ds-agent-benchmark/` — 20 synthetic CSVs (seed 42, 8770 rows) + `catalog.json` (50 tasks over 8 categories: EDA / SQL / Statistics / Regression / Classification / Time Series / Visualization / Data Quality) + `scripts/generate_benchmark_datasets.py`.
`benchmarks/v2/` — 30 CSVs + `catalog.json 0.3.0` (100 tasks over 11 categories) — see `docs/benchmark.md` + `benchmarks/v2/README.md`.

```bash
uv run dsa --help
uv run dsa --limit 50
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100
```

Metrics in `packages/evaluation/src/dsa_evaluation/metrics.py`: `task_success_rate / statistical_accuracy / sql_accuracy / code_execution / evidence_coverage / unsupported_claim_rate / mean_latency / by_category`.
Statistical rigour: S01–S10 (see `docs/evaluation.md`).

## Research packaging (§51–57)

Figures/tables are `research/figures/` + `research/tables/` reproducible from `research/results/` + `benchmarks/v2` (`§54–57`: no hand-edited charts without script, raw→script→table). Every experiment emits `research/results/ablation_*.json` with `experiment_id/git_commit/benchmark_version/dataset_version/model/prompt_version/seed/timestamp` (§56) + `dsa research run/reproduce --experiment <id>` (§57).

