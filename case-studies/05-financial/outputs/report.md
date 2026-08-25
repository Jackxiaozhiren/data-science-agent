# Analysis Report — run-d1f43414f1

**Objective:** Analyze financial.csv volatility, forecast 30 periods, and report risk metrics.
**Dataset:** `financial`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T10:46:15.897619+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Model training** (`train_model`): Baseline model with CV
- **Forecast** (`forecast`): 30-day baseline forecast with MAE
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✓ **correlation_analysis** (TC-e2f36749) — 1ms
- ✓ **create_chart** (TC-631c76cc) — 29ms
  - ![chart](32201e77d3_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/32201e77d3_histogram.png`
- ✓ **create_chart** (TC-88657d58) — 38ms
  - ![chart](759d5e9c75_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/759d5e9c75_line.png`
- ✓ **profile_dataset** (TC-1bc2a18d) — 2ms
- ✗ **train_model** (TC-906d23d0) — 2ms
  - error: Non-numeric features: float() argument must be a string or a real number, not 'datetime.date'
- ✓ **forecast** (TC-8bfdd0a0) — 2ms
- ✗ **train_model** (TC-ddb6289c) — 0ms
  - error: Non-numeric features: float() argument must be a string or a real number, not 'datetime.date'

## Evidence
- **E-5d0f1634** (statistical_test → TC-e2f36749) — Correlation price vs units: r=-0.005 — confidence 0.80 — pending
  - result: `{"r": -0.005375759068942075, "p_value": 0.9045579020673234, "method": "pearson"}`
- **E-aadb3a32** (visualization → TC-631c76cc) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/32201e77d3_histogram.png", "chart_type": "histogram"}`
- **E-28dbed07** (visualization → TC-88657d58) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/759d5e9c75_line.png", "chart_type": "line"}`
- **E-6f8be548** (python → TC-1bc2a18d) — Profile: 500 rows, 6 cols — confidence 0.90 — pending
  - result: `{"rows": 500, "columns": 6}`
- **E-d1d161d0** (model → TC-8bfdd0a0) — Forecast linear_trend: next 30 periods, MAE=818.03 — confidence 0.70 — pending
  - result: `{"forecast": [1389.956029405756, 1389.6207678264052, 1389.2855062470544, 1388.9502446677036, 1388.6149830883528], "mae": 818.0329896194594, "method": "linear_trend"}`

## Insights
- **I-ff62ab1e**: Correlation price vs units: r=-0.005
  - limitation: Association does not imply causation.
  - evidence: E-5d0f1634
- **I-b43be314**: Forecast linear_trend: next 30 periods, MAE=818.03
  - limitation: Association does not imply causation.
  - evidence: E-d1d161d0

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✗ **tool_errors**: 2 tool error(s)
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
