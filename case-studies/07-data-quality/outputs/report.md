# Analysis Report — run-9c943b40b5

**Objective:** Profile data_quality.csv for missing/duplicates/outliers and recommend cleaning steps.
**Dataset:** `data_quality`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T10:46:15.992855+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Causal check (stub)** (`causal_check`): Association vs causation guard — requires confounders for causal claim
- **Visualization** (`create_chart`): Create evidence chart

## Tool Calls
- ✓ **correlation_analysis** (TC-9a3f8e0d) — 0ms
- ✓ **create_chart** (TC-ddc3cbe0) — 28ms
  - ![chart](5aa5d9ef58_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/5aa5d9ef58_histogram.png`
- ✓ **profile_dataset** (TC-edc61e3b) — 0ms
- ✗ **causal_check** (TC-ce5bbc6d) — 0ms
  - error: DuplicateError: projections contained duplicate output name 'a'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.
- ✗ **causal_check** (TC-e858bf65) — 0ms
  - error: DuplicateError: projections contained duplicate output name 'a'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.

## Evidence
- **E-e711ead4** (statistical_test → TC-9a3f8e0d) — Correlation a vs b: r=-0.075 — confidence 0.80 — pending
  - result: `{"r": -0.07515111582688787, "p_value": 0.22010047692738197, "method": "pearson"}`
- **E-65253ee1** (visualization → TC-ddc3cbe0) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/5aa5d9ef58_histogram.png", "chart_type": "histogram"}`
- **E-839abe0c** (python → TC-edc61e3b) — Profile: 300 rows, 3 cols — confidence 0.90 — pending
  - result: `{"rows": 300, "columns": 3}`

## Insights
- **I-2d2ead57**: Correlation a vs b: r=-0.075
  - limitation: Association does not imply causation.
  - evidence: E-e711ead4

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✗ **tool_errors**: 2 tool error(s)
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
