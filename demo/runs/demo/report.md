# Analysis Report — run-9d1ad065c0

**Objective:** Analyze correlation between price and revenue
**Dataset:** `sales`  |  **Status:** REPORTING  |  **Generated:** 2026-08-17T04:52:05.488854+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✓ **correlation_analysis** (TC-3a2a6722) — 8ms
- ✓ **create_chart** (TC-185f3b08) — 125ms
  - ![chart](11ea7234e9_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/11ea7234e9_histogram.png`
- ✓ **create_chart** (TC-fe55abb5) — 105ms
  - ![chart](dd3c4529ff_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/dd3c4529ff_line.png`
- ✓ **profile_dataset** (TC-532906a5) — 6ms

## Evidence
- **E-8e024f84** (statistical_test → TC-3a2a6722) — Correlation price vs units: r=-0.057 — confidence 0.80 — pending
  - result: `{"r": -0.05678020416868902, "p_value": 0.20498052215583826, "method": "pearson"}`
- **E-d467541b** (visualization → TC-185f3b08) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/11ea7234e9_histogram.png", "chart_type": "histogram"}`
- **E-f19abf52** (visualization → TC-fe55abb5) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/dd3c4529ff_line.png", "chart_type": "line"}`
- **E-ff22cd82** (python → TC-532906a5) — Profile: 500 rows, 6 cols — confidence 0.90 — pending
  - result: `{"rows": 500, "columns": 6}`

## Insights
- **I-5065cbb4**: Correlation price vs units: r=-0.057
  - limitation: Association does not imply causation.
  - evidence: E-8e024f84

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✓ **tool_errors**: No tool errors
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
