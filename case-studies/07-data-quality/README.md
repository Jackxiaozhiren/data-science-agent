# CS07 Data Quality Investigation — Data Quality (W4 §28)

## Problem (§31)

Investigate missing, duplicates, cardinality, outliers, and propose cleaning.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/data_quality.csv + missing_heavy.csv (501) + outliers.csv (251) + mixed_types.csv` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:88bb2b0208a50e6f577d8d36d9370d51db95ce7fd25f7b0254fe4329a558e997 (data_quality)` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"Profile data_quality.csv for missing/duplicates/outliers and recommend cleaning steps."**

## Analysis Plan (§31)

1. Profile (missing, duplicates) 2. run_sql distinct counts 3. create_visualization boxplot/histogram 4. Evidence

## Agent Trajectory (§31)

**Run:** `Agent().analyze_sync("<dataset>", ...)` — **COMPLETED** `run-9c943b40b5` in 0.04s, 3 evidence, 5 tool calls, 2 failed tool calls (2026-08-25 live).
**Trajectory:** `profile_dataset` → `correlation_analysis`/`run_sql`/`train_model` → `create_visualization` → `get_evidence`/`generate_report` (via `dsa_tools` 18). Full trace in `outputs/tool_calls.json`.
**Evidence:** `outputs/evidence.json` (3 items, real Agent output — no mock).

## Tools (§31)

`profile_dataset, run_sql, create_visualization`

## Statistics / Model (§31)

- **Statistics:** Missing ratio, duplicate count, outlier via IQR
- **Model:** No ML

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/07-data-quality/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic quality issues, not real dirty data
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.
- **Observed tool failures (live, honest):** `causal_check` `DuplicateError` (duplicate `a` projection) ×2 — profile/correlation/viz still emitted. Recorded in `outputs/tool_calls.json` (`status: error`).

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'Profile data_quality.csv for missing/duplicates/outliers and recommend cleaning steps.')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/07-data-quality/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** ✅ **Verified** — real run `run-9c943b40b5` `COMPLETED` 0.04s, 3 evidence, 5 tool calls, failed tool calls 2. No mock / no hard-coded result.

*Planned: 2026-08-22 — `b79610d` → **Verified: 2026-08-25 — Phase D execution** (HEAD)*
