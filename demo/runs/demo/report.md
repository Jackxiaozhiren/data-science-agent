# Analysis Report — run-6376a4d014

**Objective:** Analyze correlation between price and revenue
**Dataset:** `sales`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T11:27:17.307495+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✓ **correlation_analysis** (TC-1020b1e3) — 2ms
- ✓ **create_chart** (TC-c915a2c0) — 44ms
  - ![chart](ef5ff61f8a_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/ef5ff61f8a_histogram.png`
- ✓ **create_chart** (TC-c86c0eab) — 38ms
  - ![chart](36c5e4fbca_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/36c5e4fbca_line.png`
- ✓ **profile_dataset** (TC-c8ceee17) — 2ms

## Evidence
- **E-9ba294cf** (statistical_test → TC-1020b1e3) — Correlation price vs units: r=-0.057 — confidence 0.80 — pending
  - result: `{"r": -0.05678020416868902, "p_value": 0.20498052215583826, "method": "pearson"}`
- **E-471af836** (visualization → TC-c915a2c0) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/ef5ff61f8a_histogram.png", "chart_type": "histogram"}`
- **E-82f13b81** (visualization → TC-c86c0eab) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/36c5e4fbca_line.png", "chart_type": "line"}`
- **E-b57cccb3** (python → TC-c8ceee17) — Profile: 500 rows, 6 cols — confidence 0.90 — pending
  - result: `{"rows": 500, "columns": 6}`

## Insights
- **I-5b935c3b**: Correlation price vs units: r=-0.057
  - limitation: Association does not imply causation.
  - evidence: E-9ba294cf

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✓ **tool_errors**: No tool errors
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
