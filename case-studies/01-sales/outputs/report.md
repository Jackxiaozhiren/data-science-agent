# Analysis Report — run-008a1531cf

**Objective:** Analyze revenue trends by region and category, identify key drivers, correlations between price and revenue, and provide actionable insights.
**Dataset:** `sales`  |  **Status:** REPORTING  |  **Generated:** 2026-08-22T04:21:59.721715+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Forecast** (`forecast`): 30-day baseline forecast with MAE
- **Causal check (stub)** (`causal_check`): Association vs causation guard — requires confounders for causal claim
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✓ **correlation_analysis** (TC-b3554a53) — 14ms
- ✓ **create_chart** (TC-2124c7fc) — 53ms
  - ![chart](adaba1df75_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/adaba1df75_histogram.png`
- ✓ **create_chart** (TC-36c28fe6) — 41ms
  - ![chart](036aadd30c_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/036aadd30c_line.png`
- ✓ **profile_dataset** (TC-f77cca39) — 6ms
- ✓ **forecast** (TC-14efa136) — 5ms
- ✓ **causal_check** (TC-c9713104) — 1ms

## Evidence
- **E-f58fc304** (statistical_test → TC-b3554a53) — Correlation price vs units: r=-0.057 — confidence 0.80 — pending
  - result: `{"r": -0.05678020416868902, "p_value": 0.20498052215583826, "method": "pearson"}`
- **E-7c8d5b5b** (visualization → TC-2124c7fc) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/adaba1df75_histogram.png", "chart_type": "histogram"}`
- **E-6de1fdf2** (visualization → TC-36c28fe6) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/036aadd30c_line.png", "chart_type": "line"}`
- **E-c815413b** (python → TC-f77cca39) — Profile: 500 rows, 6 cols — confidence 0.90 — pending
  - result: `{"rows": 500, "columns": 6}`
- **E-f84be2f0** (model → TC-14efa136) — Forecast linear_trend: next 30 periods, MAE=635.97 — confidence 0.70 — pending
  - result: `{"forecast": [1314.632969816089, 1314.0823904661156, 1313.531811116142, 1312.9812317661685, 1312.4306524161952], "mae": 635.9708248748128, "method": "linear_trend"}`
- **E-1f3d9206** (statistical_test → TC-c9713104) — Causal check (difference_in_means): estimate=0.000, causal_bar=fail — Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association  — confidence 0.50 — pending
  - result: `{"estimate": 0.0, "method": "difference_in_means", "passes_causal_bar": false, "confidence_note": "Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association only."}`

## Insights
- **I-450fa717**: Correlation price vs units: r=-0.057
  - limitation: Association does not imply causation.
  - evidence: E-f58fc304
- **I-4c5bf47e**: Forecast linear_trend: next 30 periods, MAE=635.97
  - limitation: Association does not imply causation.
  - evidence: E-f84be2f0
- **I-ecfee616**: Causal check (difference_in_means): estimate=0.000, causal_bar=fail — Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association 
  - limitation: Association does not imply causation.
  - evidence: E-1f3d9206

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✗ **unsupported_claim**: Causal language detected without causal evidence; rewrite as association.
- ✓ **tool_errors**: No tool errors
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
