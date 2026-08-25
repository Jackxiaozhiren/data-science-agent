# CS04 Marketing Analytics — Marketing (W4 §28)

## Problem (§31)

Analyze marketing spend vs conversions/ROI; identify channel effectiveness and budget allocation.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **Schema note** | `marketing.csv` columns are `date,region,category,price,units,revenue` (identical to `sales.csv` generator schema) — **not** `channel/spend/conversions`. The marketing-ROI question is therefore only approximately answerable: `run_sql`/`correlation` operate on `region/category/price/units/revenue`. See `outputs/tool_calls.json`. |
| **File** | `benchmarks/v2/datasets/marketing.csv (synthetic; schema = sales-like, not channel/spend/conversions) + ads.csv` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:d0c365d9a663c22763b8cea92c5ea93854566d5efeee0a678fdf203a525fa8ed (marketing), ads.csv synthetic` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"Which marketing channel has highest ROI? Correlation between spend and conversions?"**

## Analysis Plan (§31)

1. Profile 2. run_sql ROI by channel 3. correlation_analysis spend vs conversions 4. create_visualization bar 5. Evidence

## Agent Trajectory (§31)

**Run:** `Agent().analyze_sync("<dataset>", ...)` — **COMPLETED** `run-0c004191b2` in 0.26s, 5 evidence, 5 tool calls, 0 failed tool calls (2026-08-25 live).
**Trajectory:** `profile_dataset` → `correlation_analysis`/`run_sql`/`train_model` → `create_visualization` → `get_evidence`/`generate_report` (via `dsa_tools` 18). Full trace in `outputs/tool_calls.json`.
**Evidence:** `outputs/evidence.json` (5 items, real Agent output — no mock).

## Tools (§31)

`profile_dataset, run_sql, correlation_analysis, create_visualization`

## Statistics / Model (§31)

- **Statistics:** Pearson r spend~conversions, SQL ROI aggregates
- **Model:** No ML, EDA focus

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/04-marketing/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic, no real attribution; no causal (guarded)
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.
- **Observed tool failures (live, honest):** none — all tool calls `ok`. Recorded in `outputs/tool_calls.json` (`status: error`).

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'Which marketing channel has highest ROI? Correlation between spend and conversions?')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/04-marketing/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** ✅ **Verified** — real run `run-0c004191b2` `COMPLETED` 0.26s, 5 evidence, 5 tool calls, failed tool calls 0. No mock / no hard-coded result.

*Planned: 2026-08-22 — `b79610d` → **Verified: 2026-08-25 — Phase D execution** (HEAD)*
