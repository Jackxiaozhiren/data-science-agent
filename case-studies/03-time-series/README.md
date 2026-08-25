# CS03 Time Series Forecasting — Time Series (W4 §28)

## Problem (§31)

Forecast future values from historical time series with trend/seasonality; evaluate holdout MAE and provide trajectory.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/timeseries_trend.csv (301 rows) + timeseries_seasonal.csv (301) + time_series_long.csv (601) — synthetic trend `y = 0.5*t + noise`, seasonal `sin(2πt/30)`` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:09396b21de8dc6627b6966f02fc9d45a4128abccbb232af66de189352508ea93 (trend), time_series_long: synthetic 601` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"Forecast next 30 periods for timeseries_trend, evaluate holdout MAE, and visualize trend."**

## Analysis Plan (§31)

1. Profile (date, value) 2. forecast (linear_trend, periods=30) 3. run_sql holdout 4. create_visualization line 5. Evidence/Report

## Agent Trajectory (§31)

**Run:** `Agent().analyze_sync("<dataset>", ...)` — **COMPLETED** `run-1c70a7896a` in 1.28s, 5 evidence, 9 tool calls, 4 failed tool calls (2026-08-25 live).
**Trajectory:** `profile_dataset` → `correlation_analysis`/`run_sql`/`train_model` → `create_visualization` → `get_evidence`/`generate_report` (via `dsa_tools` 18). Full trace in `outputs/tool_calls.json`.
**Evidence:** `outputs/evidence.json` (5 items, real Agent output — no mock).

## Tools (§31)

`profile_dataset, forecast, run_sql, create_visualization, get_evidence`

## Statistics / Model (§31)

- **Statistics:** forecast MAE via holdout 20%; diagnostics: n_train, periods, forecast array
- **Model:** Baseline forecast (linear_trend / moving_average / naive_trend) — no dsa-time-series plugin for this pilot, but plugin would be used in full

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/03-time-series/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic trend, no real seasonality/cross-validation; plugin not yet wired for Agent auto-selection
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.
- **Observed tool failures (live, honest):** `correlation_analysis` `DuplicateError` (duplicate `value` projection) and `train_model` `CV failed` (unsupported target type) — recovered; forecast still produced MAE. Recorded in `outputs/tool_calls.json` (`status: error`).

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'Forecast next 30 periods for timeseries_trend, evaluate holdout MAE, and visualize trend.')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/03-time-series/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** ✅ **Verified** — real run `run-1c70a7896a` `COMPLETED` 1.28s, 5 evidence, 9 tool calls, failed tool calls 4. No mock / no hard-coded result.

*Planned: 2026-08-22 — `b79610d` → **Verified: 2026-08-25 — Phase D execution** (HEAD)*
