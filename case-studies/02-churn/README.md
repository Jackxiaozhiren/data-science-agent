# CS02 Customer Churn — Customer Analytics (W4 §28)

## Problem

Business question: *What drives churn? Which segments have highest churn? What retention actions?*  
Stakeholder: Customer Success / Marketing.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/customer_churn.csv` |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 |
| **License** | MIT / CC0 (synthetic) |
| **Citation** | `benchmarks/v2/catalog.json` `0.3.0` |
| **Download** | `benchmarks/v2/datasets/customer_churn.csv` |
| **Version / Hash** | `v2 0.3.0` / `sha256:6e7c2cf73e9c68d17be58fb9ef6dc1bb90357fba2b5afafb6ee33575aca7e456` |
| **Rows / Cols** | Check via `wc -l` / `head` — churn dataset (titanic-style synthetic) |

## Question

> **"Analyze customer churn factors, identify key predictors, churn rate by segment, and provide retention recommendations."**

## Analysis Plan

1. Profile (missing, class balance)
2. Correlation / hypothesis (churn vs tenure/charges)
3. SQL (churn rate by contract, payment)
4. Train/evaluate model (`train_model` logistic, `evaluate_model` accuracy/F1)
5. Feature importance (`feature_importance`)
6. Evidence + Report

## Agent Trajectory (Live)

**Run:** `run-44043c60a0` — **COMPLETED** in 0.05s (2026-08-22, `b79610d`)

- `profile_dataset` → ok
- `train_model` / `evaluate_model` → accuracy via `evidence.json`
- `feature_importance` → chart
- `get_evidence` / `generate_report` → report

Full: `case-studies/02-churn/outputs/tool_calls.json` (7 calls)

## Tools

`profile_dataset`, `train_model`, `evaluate_model`, `feature_importance`, `run_sql`, `get_evidence`, `generate_report`

## Statistics / Model

- **Train:** `train_model(dataset, target=churn, task=classification, model=logistic, cv_folds=3)` → `cv_mean` via `evidence.json`
- **Evaluate:** `evaluate_model` → `metrics` `accuracy/F1` + `confusion_matrix`
- **Feature importance:** via `RandomForest` + chart PNG

## Evidence

Generated `3` evidence items — see `outputs/evidence.json`. Example:

```json
{'id': 'E-6772f2b1', 'claim': 'Correlation tenure vs monthly_charges: r=-0.011', 'source_type': 'statistical_test', 'source_id': 'TC-5f5596bf', 'result': {'r': -0.01061954586103093, 'p_value': 0.7951803902661485, 'method': 'pearson'}, 'confidence': 0.8, 'validation_status': 'pending'}
```

## Visualization

Bar/histogram + feature importance PNG in `artifacts/charts/`.

## Report

`outputs/report.md` (800 chars preview):

```markdown
# Analysis Report — run-44043c60a0

**Objective:** Analyze customer churn factors, identify key predictors, churn rate by segment, and provide retention recommendations.
**Dataset:** `customer_churn`  |  **Status:** REPORTING  |  **Generated:** 2026-08-22T04:21:59.789157+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Model training** (`train_model`): Baseline model with CV
- **Causal check (stub)** (`causal_check`): Association vs causati
```

## Limitations

- Synthetic churn, not real telco data; moderate class imbalance.
- Model is baseline logistic, not tuned; no hyperparam search.
- No external validation.

## Reproduction

```bash
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/customer_churn.csv', 'Analyze churn factors...')
print(r.status, len(r.evidence))
"
```

**Quality Gate:** ✅ Real output (0.1s), 3 evidence, report 2983 chars, no mock.

*Generated: 2026-08-22 live*
