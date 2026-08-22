# Analysis Report — run-44043c60a0

**Objective:** Analyze customer churn factors, identify key predictors, churn rate by segment, and provide retention recommendations.
**Dataset:** `customer_churn`  |  **Status:** REPORTING  |  **Generated:** 2026-08-22T04:21:59.789157+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Model training** (`train_model`): Baseline model with CV
- **Causal check (stub)** (`causal_check`): Association vs causation guard — requires confounders for causal claim
- **Visualization** (`create_chart`): Create evidence chart

## Tool Calls
- ✓ **correlation_analysis** (TC-5f5596bf) — 1ms
- ✓ **create_chart** (TC-5260863a) — 33ms
  - ![chart](63c2abde19_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/63c2abde19_histogram.png`
- ✓ **profile_dataset** (TC-e68bd3d0) — 2ms
- ✗ **train_model** (TC-2f18bddd) — 2ms
  - error: Non-numeric features: could not convert string to float: 'Yes'
- ✗ **causal_check** (TC-51f66360) — 1ms
  - error: DuplicateError: projections contained duplicate output name 'tenure'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.
- ✗ **train_model** (TC-35285ede) — 0ms
  - error: Non-numeric features: could not convert string to float: 'Yes'
- ✗ **causal_check** (TC-6da57b72) — 0ms
  - error: DuplicateError: projections contained duplicate output name 'tenure'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.

## Evidence
- **E-6772f2b1** (statistical_test → TC-5f5596bf) — Correlation tenure vs monthly_charges: r=-0.011 — confidence 0.80 — pending
  - result: `{"r": -0.01061954586103093, "p_value": 0.7951803902661485, "method": "pearson"}`
- **E-311f24e8** (visualization → TC-5260863a) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/63c2abde19_histogram.png", "chart_type": "histogram"}`
- **E-dfed9b5c** (python → TC-e68bd3d0) — Profile: 600 rows, 5 cols — confidence 0.90 — pending
  - result: `{"rows": 600, "columns": 5}`

## Insights
- **I-5fe6ff03**: Correlation tenure vs monthly_charges: r=-0.011
  - limitation: Association does not imply causation.
  - evidence: E-6772f2b1

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✗ **tool_errors**: 4 tool error(s)
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
