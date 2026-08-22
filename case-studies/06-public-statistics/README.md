# CS06 Public Statistics — Public Statistics (W4 §28)

## Problem (§31)

Public-style stats: Titanic survival analysis and health metrics; hypothesis testing.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/titanic.csv (901 rows, synthetic Titanic) + health.csv + house_prices.csv — synthetic but mimics public; real Titanic is public domain (Kaggle CC0)` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:68e76faa3137b685e9038edec3261c78403c29c796ace0ef1faa1ec49432880d (titanic synthetic 901)` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"What factors predict Titanic survival? Hypothesis: class vs survival (chi2), age vs survival."**

## Analysis Plan (§31)

1. Profile 2. run_sql survival by class/sex 3. run_statistical_test (chi2, t_test) 4. create_visualization bar 5. Evidence

## Agent Trajectory (§31)

**Planned:** `Agent().analyze_sync("<dataset>", "<question>")` — will generate `COMPLETED` with evidence (similar to CS01/CS02 live runs).  
**Current status:** 📝 **Planned** — dataset + plan ready, execution queued for Phase D full. Outputs will be in `case-studies/06-public-statistics/outputs/` + `artifacts/reports/<runId>/` (real, not mock).  
**Expected trajectory:** `profile_dataset` → `run_sql`/`forecast`/`train_model` → `create_visualization` → `get_evidence` → `generate_report` (via `dsa_tools` 18).

## Tools (§31)

`profile_dataset, run_sql, run_statistical_test, assumption_check, create_visualization`

## Statistics / Model (§31)

- **Statistics:** Chi2 for class~survival, t_test age by survival, effect size
- **Model:** Optional train_model (logistic survival)

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/06-public-statistics/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic Titanic, not real Kaggle; health.csv synthetic
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'What factors predict Titanic survival? Hypothesis: class vs survival (chi2), age vs survival.')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/06-public-statistics/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** 📝 **Planned** — will be `✅ Verified` after real run (no mock). Current: dataset ready, plan ready.

*Planned: 2026-08-22 — `b79610d`*
