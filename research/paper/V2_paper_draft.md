# Evidence-Grounded Autonomous Data Science Agent — V2 Draft

> Status: skeleton wired to live benchmark (`research/results/ablation_*.json`, `benchmarks/v2/catalog.json` 100 tasks, `benchmarks/baseline/summary.json` frozen). No fabricated numbers — all tables derive from `research/results/` and `benchmarks/v2` live runs (seed 42).

## Abstract

V2 upgrades V1.8 (50/50 @1.0) to a research-grade agent system: baseline freeze with regression contract, evaluation framework (EvaluationResultV2 10-dim + 6-level), scientific benchmark v2 (30 datasets / 100 tasks / 11 categories, 8 difficulties), reliability / reproducibility L0–L5, failure taxonomy F01–F15, observability (Trace/Span), MCP 2026-07-28 stateless, adversarial security, and a runnable research package (ablation A–F, bootstrap CI, McNemar).

## 1 Introduction / 2 Related Work

See `ARCHITECTURE_FREEZE_V0.1.md` §1–12, `docs/v2/Baseline Report.md`, `docs/MCP_DESIGN.md`.

## 3 System Architecture

Frontend (Next.js 15, 13 routes) → API (FastAPI) → LangGraph (Planner/Scientist/Critic, MemorySaver) → Tool Layer (17 tools: profile_dataset, run_sql, run_python, correlation, hypothesis, regression, train/evaluate, feature_importance, forecast, create_chart, evidence, report) → DuckDB+Polars / Python sandbox / Stats-ML / Viz → Evidence Graph → Validation → Reproducibility bundle (`experiment.json` + `reproduce.sh` + `analysis.ipynb`) — see `docs/v2/baseline/ARCHITECTURE.md`.

## 4 Benchmark

- v1 frozen: `benchmarks/baseline/` 20 datasets / 50 tasks / 8 cats — live 50/50 @1.0 (mean 47.92ms, unsupported 0.06), see `docs/v2/Baseline Report.md`
- v2: `benchmarks/v2/catalog.json` 30 datasets / 100 tasks / 11 cats (EDA/SQL/Statistics/Regression/Classification/Time Series/Visualization/Data Quality + Data Profiling/Clustering/Evidence Validation), with `difficulty/gold_method/required_tools/gold_metrics/required_evidence/forbidden_claims` — see `benchmarks/v2/README.md`

Run:

```bash
uv run python research/experiments/run_ablation.py --limit 20 --out research/results
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 --out /tmp/v2-100
```

## 5 Experimental Setup / 6 Results

Provenance per run: `experiment_id, git_commit, catalog, datasets, limit, configs A–F, summary, ci_bootstrap_task_success` — see `research/results/ablation_*.json`, `research/experiments/run_ablation.py`, `packages/evaluation/src/dsa_evaluation/significance.py` (bootstrap_ci, paired_bootstrap_diff, mcnemar). RQs: see `research/questions/RQs.md` (RQs 1–5, ablation A–F, tool-efficiency, retry quality, critic effectiveness). Full 100-task smoke: 100/100 @1.0 (mean 31–40ms), sql_accuracy 0.69 on v2 (new Unicode/wide tasks).

## 7 Failure Analysis / 8 Limitations

Taxonomy F01–F15, `packages/evidence/src/dsa_evidence/failure_taxonomy.py`, frontend `/failures` (top categories, failure/recovery rate, agent/tool hotspots). Limitations: LLM stochasticity, model dependence, leakage, dataset/eval/selection bias, cost, see `research/questions/RQs.md` and V2 spec §62/108.

## 9 Conclusion

Reviewer can clone, `uv sync --dev && uv run pytest` (116 passed), `mypy` clean (87), `npm run build` (13 routes), `docker compose config` valid, `uv run dsa --limit 50` and `--catalog benchmarks/v2/... --limit 100` reproducible, inspect a run via `/runs/[id]` → trace to `evidence_graph.json`, replay via LangGraph checkpoints.
