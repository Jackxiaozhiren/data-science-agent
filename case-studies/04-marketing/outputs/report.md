# Analysis Report — run-0c004191b2

**Objective:** Which marketing channel has highest ROI? Correlation between spend and conversions?
**Dataset:** `marketing`  |  **Status:** REPORTING  |  **Generated:** 2026-08-25T10:46:15.807826+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **SQL analysis** (`run_sql`): SQL: SELECT date, COUNT(*) as cnt, AVG(price) as avg_price FROM dataset GROUP BY date
- **Visualization** (`create_chart`): Create evidence chart
- **Time series line** (`create_chart`): Line chart over time for trend

## Tool Calls
- ✓ **correlation_analysis** (TC-6c1a2652) — 2ms
- ✓ **run_sql** (TC-f01733e9) — 175ms
- ✓ **create_chart** (TC-24428f1d) — 33ms
  - ![chart](29ca4dd063_histogram.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/29ca4dd063_histogram.png`
- ✓ **create_chart** (TC-6265388a) — 36ms
  - ![chart](d33647e1ea_line.png)
  - artifact: `/Users/jackson/Data agent/packages/artifacts/charts/d33647e1ea_line.png`
- ✓ **profile_dataset** (TC-e5c0ff7f) — 3ms

## Evidence
- **E-c4ab51fd** (statistical_test → TC-6c1a2652) — Correlation price vs units: r=0.060 — confidence 0.80 — pending
  - result: `{"r": 0.05956807927551924, "p_value": 0.2345620698136366, "method": "pearson"}`
- **E-0c5cbebd** (sql → TC-f01733e9) — SQL returned 84 rows — confidence 0.85 — pending
  - result: `{"columns": ["date", "cnt", "avg_price"], "row_count": 84, "rows": [["2024-01-09", 5, 75.016], ["2024-08-16", 5, 70.224], ["2024-08-28", 5, 59.248000000000005], ["2024-08-12", 4, 78.5575], ["2024-06-22", 4, 58.16]]}`
- **E-f596dae7** (visualization → TC-24428f1d) — Chart histogram created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/29ca4dd063_histogram.png", "chart_type": "histogram"}`
- **E-f408f836** (visualization → TC-6265388a) — Chart line created — confidence 0.70 — pending
  - result: `{"artifact_path": "/Users/jackson/Data agent/packages/artifacts/charts/d33647e1ea_line.png", "chart_type": "line"}`
- **E-86ef2be1** (python → TC-e5c0ff7f) — Profile: 400 rows, 6 cols — confidence 0.90 — pending
  - result: `{"rows": 400, "columns": 6}`

## Insights
- **I-5a412d17**: Correlation price vs units: r=0.060
  - limitation: Association does not imply causation.
  - evidence: E-c4ab51fd

## Validation
- ✓ **evidence_coverage**: Evidence coverage ok
- ✓ **unsupported_claim**: No unsupported causal claims detected
- ✓ **tool_errors**: No tool errors
- ✓ **budget**: Budget ok

## Limitations
- Correlation does not imply causation unless causal evidence is established.
- Reproducibility bundle includes dataset hash, code, and parameters where available.
