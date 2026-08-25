# Analysis Report — run-cd71ab4f39

**Objective:** What factors predict Titanic survival? Hypothesis: class vs survival (chi2), age vs survival.
**Dataset:** `titanic`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T10:46:15.955872+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Hypothesis test** (`hypothesis_test`): Appropriate hypothesis test with assumptions
- **Model training** (`train_model`): Baseline model with CV
- **Visualization** (`create_chart`): Create evidence chart

## Tool Calls
- ✓ **correlation_analysis** (TC-b2f74290) — 2ms
- ✗ **hypothesis_test** (TC-3fbde794) — 5ms
  - error: Each group needs >=2 observations
- ✓ **create_chart** (TC-85cbf736) — 34ms
  - ![chart](5da9ff0bf6_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/5da9ff0bf6_histogram.png`
- ✓ **profile_dataset** (TC-ffaee4a1) — 2ms
- ✗ **train_model** (TC-30945cf6) — 1ms
  - error: Non-numeric features: could not convert string to float: 'female'
- ✗ **hypothesis_test** (TC-9bd6f5e4) — 0ms
  - error: Each group needs >=2 observations
- ✗ **train_model** (TC-3efb8e2b) — 0ms
  - error: Non-numeric features: could not convert string to float: 'female'

## Evidence
- **E-bc000647** (statistical_test → TC-b2f74290) — Correlation pclass vs age: r=-0.022 — confidence 0.80 — pending
  - result: `{"r": -0.021524787719288025, "p_value": 0.5291644942038389, "method": "pearson"}`
- **E-fea8b80a** (visualization → TC-85cbf736) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/5da9ff0bf6_histogram.png", "chart_type": "histogram"}`
- **E-da2ccf19** (python → TC-ffaee4a1) — Profile: 900 rows, 5 cols — confidence 0.90 — pending
  - result: `{"rows": 900, "columns": 5}`

## Insights
- **I-6e5b8207**: Correlation pclass vs age: r=-0.022
  - limitation: Association does not imply causation.
  - evidence: E-bc000647

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✗ **tool_errors**: 4 tool error(s)
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
