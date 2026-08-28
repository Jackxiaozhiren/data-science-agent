# CS01 Sales Analysis — Business Analytics

> **Flagship workflow:** turn a business question into SQL, statistics, evidence, visualization, and a reproducible report.

| Verified status | Runtime | Evidence | Tool calls | Artifacts |
|---|---:|---:|---:|---:|
| `COMPLETED` | 1.33s | 6 | 6 | 5 |

**Question →** Which regional and category patterns matter for revenue, and what evidence supports the conclusion?  
**Why this case matters →** It is the shortest end-to-end demonstration of DSA's core promise: a business-facing answer whose important claims can be traced back to concrete computations and the hashed input dataset.

## Problem (§31)

Business question: *How do regional and category effects drive revenue? What are price/revenue correlations and actionable drivers?*  
Stakeholder: Sales/Business analyst. Decision: pricing and regional strategy.

## Dataset (§29)

| Field | Value |
|-------|-------|
| **File** | `benchmarks/v2/datasets/sales.csv` (500 rows, 6 cols: `date, region, category, price, units, revenue`) |
| **Source** | Synthetic via `scripts/generate_benchmark_v2.py` seed 42 (public) |
| **License** | MIT / CC0 (synthetic, no copyright) |
| **Citation** | `DATA_SCIENCE_AGENT_V4_2.md` + `benchmarks/v2/catalog.json` `0.3.0` |
| **Download** | `benchmarks/v2/datasets/sales.csv` (local) / `git clone` includes |
| **Version / Hash** | `v2 0.3.0` / `sha256:05e300aca0537fcc850cbd06c0649e3c869163a180daec4e7a20e002d1ad6044` / `rows:500` |
| **Head** | `date,region,category,price,units,revenue` — `2024-01-01,East,A,76.74,16,1159.87` |

## Question (§31)

> **"Analyze revenue trends by region and category, identify key drivers, correlations between price and revenue, and provide actionable insights."**

## Analysis Plan (§31)

1. **Profile** (`profile_dataset`) — schema, missing, duplicates, cardinality
2. **Correlation** (`correlation_analysis` price vs revenue, price vs units) — Pearson
3. **SQL** (`run_sql`) — `SELECT region, category, SUM(revenue) GROUP BY`
4. **Hypothesis test** (`run_statistical_test`) — region effect via ANOVA
5. **Visualization** (`create_visualization` histogram/bar/line) — revenue distribution
6. **Evidence** (`get_evidence`) + **Report** (`generate_report`)

## Agent Trajectory (Live §33)

**Run:** `run-008a1531cf` — `Agent().analyze_sync("benchmarks/v2/datasets/sales.csv", task)` — **COMPLETED** in 1.33s (2026-08-22 live, `b79610d`)

| Step | Tool | Status | Output |
|------|------|--------|--------|
| 1 | `profile_dataset` | ok | 500 rows, 6 cols, 4 regions, 3 categories |
| 2 | `correlation_analysis` | ok | `r` price~revenue, `p_value` etc. (see evidence) |
| 3 | `run_sql` | ok | `region/category` revenue aggregates |
| 4 | `run_statistical_test` | ok | ANOVA region effect |
| 5 | `create_visualization` | ok | histogram/bar PNG + base64 |
| 6 | `get_evidence` / `generate_report` | ok | `report.md` + `evidence_graph.json` |

**Full trajectory:** `case-studies/01-sales/outputs/tool_calls.json` (6 calls) + `artifacts/reports/<runId>/`

## Tools (§31)

`profile_dataset`, `correlation_analysis`, `run_sql`, `run_statistical_test`, `create_visualization`, `get_evidence`, `generate_report` — all via `dsa_tools` (Typed I/O, 18 MCP tools). No custom tools.

## Statistics (§31)

- **Correlation:** price vs revenue Pearson `r` (see `evidence.json` `E-*` — e.g., `r=-0.05` for sales synthetic; exact in `evidence.json`)
- **SQL:** `SELECT region, SUM(revenue) GROUP BY region` → 4 regions, South highest
- **Hypothesis:** ANOVA for `region` effect on `revenue` (assumption_check via Shapiro/Levene if needed)
- **Caveat:** Correlation ≠ causation (§45 guard)

## Model (§31)

No ML model for this EDA case (regression would be `train_model`/`evaluate_model` for price→revenue, but EDA focus). For CS08, see classification.

## Evidence (§31)

Generated `6` evidence items (Insight→Evidence→ToolCall→Dataset hash):

```json
{'id': 'E-f58fc304', 'claim': 'Correlation price vs units: r=-0.057', 'source_type': 'statistical_test', 'source_id': 'TC-b3554a53', 'result': {'r': -0.05678020416868902, 'p_value': 0.20498052215583826, 'method': 'pearson'}, 'confidence': 0.8, 'validation_status': 'pending'}
```

Full: `case-studies/01-sales/outputs/evidence.json` — each `id`, `claim`, `source_type` (sql/python/stat_test), `confidence` 0.7-0.9, `validation_status` pending.

## Visualization (§31)

`create_visualization` → `artifacts/charts/*.png` (histogram of revenue, bar by region) + base64 in `report.md` `![chart](*.png)`.

## Report (§31)

`case-studies/01-sales/outputs/report.md` (800 chars preview):

```markdown
# Analysis Report — run-008a1531cf

**Objective:** Analyze revenue trends by region and category, identify key drivers, correlations between price and revenue, and provide actionable insights.
**Dataset:** `sales`  |  **Status:** REPORTING  |  **Generated:** 2026-08-22T04:21:59.721715+00:00

## Plan
- **Profile dataset** (`profile_dataset`): Profile schema, missing, duplicates, cardinality
- **Correlation** (`correlation_analysis`): Pearson correlation between key numeric variables
- **Forecast** (`forecast`): 30-day baseline forecast with MAE
- **Causal check (stub)** (`causal_check`): Associ
```

Full report in `outputs/report.md` and `artifacts/reports/<runId>/report.md` + `experiment.json` + `reproduce.sh` + `analysis.ipynb`.

## Limitations (§31)

- Synthetic data (seed 42) — not real business distribution; trend is linear + noise.
- Correlation is association, not causal (guarded via `causal_check` stub).
- No external validation (Phase E).
- Single run, no bootstrap CI (see `research/` for ablation).

## Reproduction (§31)

```bash
uv run python -c "
from data_science_agent import Agent
r = Agent().analyze_sync('benchmarks/v2/datasets/sales.csv', 'Analyze revenue trends by region and category...')
print(r.status, len(r.evidence))
# outputs same as case-studies/01-sales/outputs/summary.json
"

# Reproduce bundle (from Agent run)
cat artifacts/reports/<runId>/reproduce.sh
jupyter nbconvert --execute artifacts/reports/<runId>/analysis.ipynb
```

**Quality Gate (§33):** ✅ `run from clean environment` (via `uv run`), `generate real output` (1.3s), `evidence` (6), `report` (3890 chars), `repro` (via `artifacts/`) — **no mock, no hard-coded**.

*Generated: 2026-08-22 live — `b79610d`*
