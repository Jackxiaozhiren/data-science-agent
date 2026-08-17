# Failure Case Study — V3 §67 (10 Representative Failures)

> **Format per failure**: `Task / Initial Agent Behavior / Failure / Failure Category (F01–F15) / Why It Happened / Critic Detection / Recovery / Final Outcome / Lesson`

These are **representative failure patterns** observed or anticipated; all are grounded in the taxonomy `packages/evidence/src/dsa_evidence/failure_taxonomy.py` (`F01 Missing Tool → F15 Hallucinated Insight`). Evidence-graph traces are available via `reproduction/v2/comparison.json` and `demo/evidence/state.json`.

| # | Task | Initial Behavior | Failure | Category | Why | Critic | Recovery | Outcome | Lesson |
|---|------|------------------|---------|----------|-----|--------|----------|---------|--------|
| 1 | `sql-03` wide_table `SELECT *` | `run_sql` without column filter | Hit row limit / wide payload | F07 Resource Exhaustion | Planner missed `wide_table` heuristic | Flagged `tool_errors` | Retry with `SELECT col1,col2 LIMIT` | `1.00` after retry budget | Add wide-table column pruning |
| 2 | `stats-09` unicode `café` | `run_python` encoding miss | `UnicodeDecodeError` | F02 Tool Error | Missing `encoding=utf-8` | `unsupported_claim` not | Retry with `polars read_csv` | Recovered | Encode guard |
| 3 | `viz-05` sparse histogram | `create_chart` on sparse series | Empty chart / `matplotlib` no data | F09 Validation Failure | Empty `evidence_result` | Evidence coverage fail | Fallback `profile_dataset` + retry viz | Recovered | Validate non-empty evidence |
| 4 | `dq-04` missing_heavy | `describe` over imputed | Imputed mean flagged as insight without evidence | F12 Unsupported Claim | Causal language "causes missing" | Critic `S09` | Reword to association | Pass | Causal guard (§24) |
| 5 | `ts-02` leakage | `time_series_long` with future leak | `train_model` leaked target | F11 Data Leakage | Temporal split missing | Not detected (heuristic gap) | Manual block in `leakage` dataset | Pass | Add temporal split tool |
| 6 | `eda-03` outliers | `outliers.csv` with 0 rows after filter | `profile_dataset` empty → no evidence | F10 Data Quality | Planner assumed non-empty | Coverage fail | Retry with no-filter profile | Pass | Assume non-empty guard |
| 7 | `reg-05` high cardinality | `high_card.csv` one-hot blowup | Memory spike in `train_model` | F07 Resource | `high_card` wide | `over_analysis` flag | Sample + feature_importance | Pass | Cap cardinality |
| 8 | `ev-07` evidence validation | `evidence_validation` without evidence | `validator` `insight_evidence` fail | F08 Evidence Gap | Missing `evidence_ids` | Critic flag | Re-run with evidence trace | Pass | Always carry evidence_ids |
| 9 | `causal_toy` observational | correlation `r=0.8` → "causes" | Causal overclaim | F12 + S09 | Heuristic `causes` without `causal_check` | S09 | Reword `associated` | Pass | Causal phrase audit |
| 10 | `demo` concurrent `dsa --limit 50` | 4 parallel runs | `report.md` race (same artifacts dir) | F05 Concurrency | Global `ARTIFACTS_DIR` | Not flagged | Scope per-run `out` | Pass | Per-run `out` (§18 `reproduction/`) |

All categories map to `F01–F15`; recovery paths are via retry budgets (`max_retries 3`) or `Critic` re-analysis. Frontend `/failures` aggregates `F01–F15` (see `research/V3_RESEARCH_REPORT.md` Failure Analysis).
