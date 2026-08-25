# CS05 Financial Time Series — Financial Data (W4 §28)

## Problem (§31)

Analyze financial price series for volatility and forecast; evaluate risk.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **Schema note** | `financial.csv` columns are `date,region,category,price,units,revenue` (same generator schema as `sales.csv`) — **not** OHLC. Volatility/risk framing applies to the `value/revenue` series only; no true OHLC returns. See `outputs/tool_calls.json`. |
| **File** | `benchmarks/v2/datasets/financial.csv (synthetic; schema = sales-like, not OHLC) + paired_series.csv` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:df61636cec6135757f95a5185f675af5fed03ea20b9985cb24a621f4c3c05328 (financial)` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"Analyze financial.csv volatility, forecast 30 periods, and report risk metrics."**

## Analysis Plan (§31)

1. Profile 2. forecast (moving_average) 3. assumption_check (normality) 4. create_visualization line 5. Evidence

## Agent Trajectory (§31)

**Run:** `Agent().analyze_sync("<dataset>", ...)` — **COMPLETED** `run-d1f43414f1` in 0.09s, 5 evidence, 7 tool calls, 2 failed tool calls (2026-08-25 live).
**Trajectory:** `profile_dataset` → `correlation_analysis`/`run_sql`/`train_model` → `create_visualization` → `get_evidence`/`generate_report` (via `dsa_tools` 18). Full trace in `outputs/tool_calls.json`.
**Evidence:** `outputs/evidence.json` (5 items, real Agent output — no mock).

## Tools (§31)

`profile_dataset, forecast, assumption_check, create_visualization`

## Statistics / Model (§31)

- **Statistics:** Forecast MAE, Shapiro normality, volatility via std
- **Model:** Baseline forecast

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/05-financial/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic, no real market; no GARCH
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.
- **Observed tool failures (live, honest):** `train_model` failed (non-numeric regression target) ×2 — recovered; forecast still produced MAE. Recorded in `outputs/tool_calls.json` (`status: error`).

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'Analyze financial.csv volatility, forecast 30 periods, and report risk metrics.')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/05-financial/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** ✅ **Verified** — real run `run-d1f43414f1` `COMPLETED` 0.09s, 5 evidence, 7 tool calls, failed tool calls 2. No mock / no hard-coded result.

*Planned: 2026-08-22 — `b79610d` → **Verified: 2026-08-25 — Phase D execution** (HEAD)*
