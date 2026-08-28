# CS03 Time Series Forecasting — Time Series

> **Flagship workflow:** forecast a temporal series, preserve the full tool trajectory, and expose both successful evidence and recovered tool failures.

| Verified status | Runtime | Evidence | Tool calls | Artifacts |
|---|---:|---:|---:|---:|
| `COMPLETED` | 1.284s | 5 | 9 | 5 |

**Question →** What are the next 30 values, how well does the baseline forecast perform on holdout data, and what evidence supports the forecast?  
**Why this case matters →** Forecasting is where silent modeling assumptions are especially risky. This case keeps the real execution trace — including recoverable failures — visible next to the final reproducible output.

## Problem (§31)

Forecast future values from historical time series with trend/seasonality; evaluate holdout MAE and provide trajectory.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/timeseries_trend.csv` (301 rows) + `timeseries_seasonal.csv` (301) + `time_series_long.csv` (601) — synthetic trend `y = 0.5*t + noise`, seasonal `sin(2πt/30)` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:09396b21de8dc6627b6966f02fc9d45a4128abccbb232af66de189352508ea93` (trend) |
| **Rows** | 301 for the verified `timeseries_trend.csv` run |

## Question (§31)

> **"Forecast next 30 periods for timeseries_trend, evaluate holdout MAE, and visualize trend."**

## Analysis Plan (§31)

1. Profile the date/value series.
2. Run the baseline forecast for 30 periods.
3. Evaluate the holdout trajectory and supporting statistics.
4. Create a time-series visualization.
5. Capture evidence and generate the reproducible report bundle.

## Agent Trajectory (§31)

**Run:** `run-1c70a7896a` — **COMPLETED** in 1.284s with **5 evidence items, 9 tool calls, and 5 artifacts** (2026-08-25 live).

The live trajectory included profiling, statistical/SQL/model attempts, visualization, evidence capture, and report generation. Four tool calls failed and were retained in the trace rather than removed from the case-study record.

**Full trajectory:** `outputs/tool_calls.json`  
**Verified run summary:** `outputs/summary.json`  
**Evidence:** `outputs/evidence.json`

## Tools (§31)

`profile_dataset`, `forecast`, `run_sql`, `create_visualization`, `get_evidence`, plus the additional automatically selected tools recorded in the live trajectory.

## Statistics / Model (§31)

- **Statistics:** forecast MAE via holdout data; diagnostics include training size, forecast horizon, and generated forecast values.
- **Model:** baseline time-series forecast (`linear_trend` / moving-average / naive-trend family depending on tool selection).
- **Interpretation guard:** this is a forecasting workflow, not a causal claim.

## Evidence (§31)

The verified run generated **5 real evidence items**. They are stored in `outputs/evidence.json` and remain linked to the corresponding tool calls and dataset provenance.

The evidence chain follows the same project contract used throughout DSA:

`Insight → Evidence → ToolCall → Dataset`

## Visualization (§31)

`create_visualization` produced chart artifacts for the verified run. The generated report bundle preserves the visualization alongside the analytical outputs.

## Report (§31)

The verified run produced `outputs/report.md` plus the reproducibility artifacts recorded by the case-study execution. The case-study audit reports a 4,526-character report and a valid reproduction package.

## Limitations (§31)

- Synthetic trend data is useful for deterministic evaluation but is not a substitute for a real operational forecasting distribution.
- This is a single verified run rather than a rolling-origin or external-validation study.
- The baseline workflow is not intended to replace a tuned domain-specific forecasting stack.
- **Observed tool failures remain visible:** `correlation_analysis` encountered a duplicate-projection error and `train_model` encountered an unsupported-target/CV path. The agent recovered and the forecasting workflow still produced evidence and a report. See `outputs/tool_calls.json`.

## Reproduction (§31)

```bash
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync(
    'benchmarks/v2/datasets/timeseries_trend.csv',
    'Forecast next 30 periods for timeseries_trend, evaluate holdout MAE, and visualize trend.'
)
print(r.status, len(r.evidence))
"
```

Expected reference run: `run-1c70a7896a`, `COMPLETED`, 5 evidence items. Compare a new run with `outputs/summary.json`, `outputs/evidence.json`, and the generated report bundle rather than relying on screenshots.

**Quality Gate (§33):** ✅ **Verified** — real run, real evidence, real tool trace, reproduction artifacts, and recorded failures. No mock / no hard-coded success result.

*Verified: 2026-08-25 — Phase D execution*
