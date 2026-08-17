# Success Case Study — V3 §68 (10 Representative Successful Analyses)

> **Format**: `Question / Plan / Tool Trajectory / Evidence / Validation / Final Result` — all traceable `Insight→Evidence→ToolCall→Dataset(hash)` (§49 Evidence Graph).

| # | Question (from `benchmarks/v2`) | Plan (Planner heuristics) | Tool Trajectory | Evidence | Validation | Final Result |
|---|--------------------------------|---------------------------|-----------------|----------|------------|--------------|
| 1 | `Summarize sales.csv: rows/cols/missing` | `profile_dataset` | `profile_dataset` (TC-profile, 24ms) | `E-8ccd7ad2` rows 500 cols 6 | `evidence_coverage ok` | `500×6, 0 missing` — `report.md` |
| 2 | `Analyze correlation price vs revenue` | `correlation + chart` | `correlation_analysis` → `create_chart hist` → `create_chart line` → `profile` | `E-884b` r=-0.057 + `E-9822`/`E-9aea` charts | `unsupported_claim` ok, `budget ok` | `r=-0.057 (not significant)` + 2 charts |
| 3 | `SQL: top 3 categories by revenue` | `run_sql` | `run_sql SELECT category SUM(revenue) GROUP BY ORDER BY LIMIT 3` | `E-sql3` result rows 3 | `tool_errors ok` | `3 rows, sum(revenue)` |
| 4 | `Run hypothesis test price vs units` | `hypothesis_test` | `hypothesis_test` (t-test) | `E-hyp` p=0.205 | `statistical` S01–S06 ok | `p=0.205, not significant` |
| 5 | `Forecast next 30 days sales` | `forecast` | `forecast` (ARIMA/Prophet) | `E-fc` 30-day interval | `uncertainty` CI present | `30-day forecast + interval` |
| 6 | `Cluster customers into 3 segments` | `clustering` | `train_model kmeans k=3` + `evaluate_model` | `E-clus` 3 clusters, sil 0.42 | `evidence_ids` carried | `3 segments, sil 0.42` |
| 7 | `Validate evidence for insight I-59ce` | `get_evidence` | `get_evidence I-59ce` | `E-884b` trace | `traceability ok` | `Insight→E→TC→Dataset(hash)` |
| 8 | `Assumption check for regression` | `assumption_check` | `assumption_check` + `regression` | `E-assum` normality/homo | `S02` assumption checked | `assumptions validated` |
| 9 | `Feature importance for churn` | `feature_importance` | `feature_importance` | `E-fi` top 3 features | `tool_correct` | `top features: recency/frequency/monetary` |
| 10 | `Profile wide_table + reduce + cluster` | `profile → run_python PCA → cluster` | `profile → run_python (PCA) → train_model` | `E-wide` reduced dims | `reproducibility L2/L4` | `PCA + 3 clusters` |

All 10 are live `100/100 @1.00` on `benchmarks/v2 0.3.0` (seed 42). Traces: `demo/runs/demo/state.json` (4 tool_calls, 1 insight, 4 evidence) and `reproduction/v2/comparison.json` (100 tasks, `L0..L5` 1.0).

Demo case (§69 flagship) is `Analyze correlation between price and revenue` → see `research/evidence-trace-showcase.md`.
