# Paper Outline — Evidence-Grounded Autonomous Data Science (V2 Research Package)

Abstract / Introduction / Related Work / System Architecture / Methodology / Benchmark (v2 30 datasets / 100 tasks / 11 categories) / Experimental Setup / Results / Ablation (A–F) / Failure Analysis (F01–F15) / Limitations (LLM stochasticity, model dependence, leakage, bias, cost) / Conclusion.

All sections to be generated from `research/results/*.json` (experiment_id, git_commit, dataset_version, prompt_version, model, config, seed, timestamp, metrics) — no fabricated numbers. Figures/tables under `research/figures` / `research/tables`.

V2 final arch: Frontend → API → LangGraph (Planner/Scientist/Critic) → Tool Layer (DuckDB/Python/Stats/ML/Viz) → Evidence Graph → Validation → Report → Reproduce/Benchmark → Research (Observability/Security/MCP/Evaluation/Telemetry sidecars).
