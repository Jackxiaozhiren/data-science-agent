# Tools (Phase 3 / 5 / 6)

All tools derive `BaseTool[Input, Output]` (`dsa_tools.base`) — Pydantic `Input` + `Output`, `bootstrap()` registry via `dsa_tools.__init__`.

| Tool | Purpose | Notes |
|---|---|---|
| profile_dataset | schema/profile | Polars · kind heuristic |
| run_sql | SQL (DuckDB Arrow) | read-only guard + row limit |
| run_python | Python (sandbox) | `df` bound, allowlist |
| correlation_analysis | Pearson/Spearman/Kendall + CI | evidence insight |
| hypothesis_test | t/welch/mann/anova/kruskal/chi2 | Cohen d + assumptions |
| regression_analysis | linear/ridge/lasso/elastic/logistic | metrics |
| train_model | with CV | StratifiedKFold/R² |
| evaluate_model | metrics + confusion | charts downstream |
| create_chart | histogram/bar/scatter/line/boxplot/heatmap | PNG + base64 |
| forecast | linear_trend/moving_average | holdout MAE |
| assumption_check | Shapiro/Levene | recommendation |
| feature_importance | RF + chart | artifact |
| causal_check | difference/adjusted stub | never passes bar |
| save_artifact | run_id-scoped write | traversal block |
| create_evidence | claim↔source link | ledger |
| validate_result | coverage/causal/completeness | 4 checks |

See `packages/tools/src/dsa_tools/tools/` for Typed I/O and tests `tests/unit/test_tools.py`.
