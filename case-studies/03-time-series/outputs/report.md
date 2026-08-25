# Analysis Report — run-1c70a7896a

**Objective:** Forecast next 30 periods for timeseries_trend, evaluate holdout MAE, and visualize trend.
**Dataset:** `timeseries_trend`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T10:46:15.529090+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Model training** (`train_model`): Baseline model with CV
- **Forecast** (`forecast`): 30-day baseline forecast with MAE
- **Causal check (stub)** (`causal_check`): Association vs causation guard — requires confounders for causal claim
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✗ **correlation_analysis** (TC-0203473c) — 4ms
  - error: DuplicateError: projections contained duplicate output name 'value'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.
- ✓ **create_chart** (TC-e90fec65) — 59ms
  - ![chart](e4d06375ed_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/e4d06375ed_histogram.png`
- ✓ **create_chart** (TC-3f30910b) — 45ms
  - ![chart](a9441add23_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/a9441add23_line.png`
- ✓ **profile_dataset** (TC-b3726c25) — 3ms
- ✗ **train_model** (TC-babce07e) — 4ms
  - error: CV failed: Supported target types are: ('binary', 'multiclass'). Got 'continuous' instead.
- ✓ **forecast** (TC-d762404c) — 1ms
- ✓ **causal_check** (TC-22fdf6dc) — 0ms
- ✗ **correlation_analysis** (TC-b3ea13f9) — 0ms
  - error: DuplicateError: projections contained duplicate output name 'value'. It's possible that multiple expressions are returning the same default column name. If this is the case, try renaming the columns with `.alias("new_name")` to avoid duplicate column names.
- ✗ **train_model** (TC-97327d38) — 0ms
  - error: CV failed: Supported target types are: ('binary', 'multiclass'). Got 'continuous' instead.

## Evidence
- **E-261af4d5** (visualization → TC-e90fec65) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/e4d06375ed_histogram.png", "chart_type": "histogram"}`
- **E-b0e20417** (visualization → TC-3f30910b) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/a9441add23_line.png", "chart_type": "line"}`
- **E-a0d4cae3** (python → TC-b3726c25) — Profile: 300 rows, 2 cols — confidence 0.90 — pending
  - result: `{"rows": 300, "columns": 2}`
- **E-91e7a831** (model → TC-d762404c) — Forecast linear_trend: next 30 periods, MAE=34.83 — confidence 0.70 — pending
  - result: `{"forecast": [181.18857033856582, 181.22910684950713, 181.26964336044847, 181.31017987138978, 181.3507163823311], "mae": 34.82799205598004, "method": "linear_trend"}`
- **E-225c595f** (statistical_test → TC-22fdf6dc) — Causal check (difference_in_means): estimate=0.000, causal_bar=fail — Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association  — confidence 0.50 — pending
  - result: `{"estimate": 0.0, "method": "difference_in_means", "passes_causal_bar": false, "confidence_note": "Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association only."}`

## Insights
- **I-09f3d294**: Forecast linear_trend: next 30 periods, MAE=34.83
  - limitation: Association does not imply causation.
  - evidence: E-91e7a831
- **I-49dc059e**: Causal check (difference_in_means): estimate=0.000, causal_bar=fail — Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association 
  - limitation: Association does not imply causation.
  - evidence: E-225c595f

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✗ **unsupported_claim**: Causal language detected without causal evidence; rewrite as association.
- ✗ **tool_errors**: 4 tool error(s)
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
