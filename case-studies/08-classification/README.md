# CS08 ML Classification — Machine Learning (W4 §28)

## Problem (§31)

Classification: predict imbalanced label, evaluate accuracy/F1, feature importance.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/imbalanced.csv (synthetic imbalanced) + clustering.csv + credit-like synthetic` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public, CC0/MIT) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` + `DATA_SCIENCE_AGENT_V4_2.md` |
| **Download** | `benchmarks/v2/datasets/<name>.csv` (local, `git clone` includes) |
| **Version / Hash** | `v2 0.3.0` / `sha256:e47fd0fd12cdc56523da6377d4b311a6c40c3b022d587f58299cf319578fe1ef (imbalanced)` |
| **Rows** | See `wc -l` (e.g., 301-901) |

## Question (§31)

> **"Train classification for imbalanced.csv, evaluate holdout, and report feature importance."**

## Analysis Plan (§31)

1. Profile 2. train_model (logistic, random_forest, cv_folds=3) 3. evaluate_model (accuracy, F1, ROC) 4. feature_importance 5. Evidence

## Agent Trajectory (§31)

**Planned:** `Agent().analyze_sync("<dataset>", "<question>")` — will generate `COMPLETED` with evidence (similar to CS01/CS02 live runs).  
**Current status:** 📝 **Planned** — dataset + plan ready, execution queued for Phase D full. Outputs will be in `case-studies/08-classification/outputs/` + `artifacts/reports/<runId>/` (real, not mock).  
**Expected trajectory:** `profile_dataset` → `run_sql`/`forecast`/`train_model` → `create_visualization` → `get_evidence` → `generate_report` (via `dsa_tools` 18).

## Tools (§31)

`profile_dataset, train_model, evaluate_model, feature_importance, create_visualization`

## Statistics / Model (§31)

- **Statistics:** CV mean/std, holdout metrics, importance ranking
- **Model:** Logistic + RandomForest, cross-validation

## Evidence (§31)

Planned: `Insight→Evidence→ToolCall→Dataset` (like CS01: 6 evidence, CS02: 3). Will be `case-studies/08-classification/outputs/evidence.json` (real).

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` + base64 in `report.md`.

## Report (§31)

Will be `outputs/report.md` + `artifacts/reports/<runId>/` (report.md, experiment.json, reproduce.sh, analysis.ipynb, evidence_graph.json) — same as CS01/CS02.

## Limitations (§31)

- Synthetic imbalanced, baseline only, no tuning
- Synthetic data, not real-world distribution.
- Single run, no external validation (Phase E).
- No causal claim without `causal_check` bar.

## Reproduction (§31)

```bash
# Planned execution (same pattern as CS01/CS02)
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/<dataset>.csv', 'Train classification for imbalanced.csv, evaluate holdout, and report feature importance.')
print(r.status, len(r.evidence))
"
# Outputs: case-studies/08-classification/outputs/ + artifacts/reports/<runId>/
```

**Quality Gate (§33):** 📝 **Planned** — will be `✅ Verified` after real run (no mock). Current: dataset ready, plan ready.

*Planned: 2026-08-22 — `b79610d`*
