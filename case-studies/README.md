# Real-World Data Science Case Studies — V4.2 W4 (§28-33)

> **V4.2 最重要的工作 (§28): 真实数据科学工作流中，它到底有没有用？**  
> **Date:** 2026-08-22  
> **Commit:** `b79610d` (v4.1.1) + `857a92d` (Phase C) — live  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` §28-33

## 1. Objective (§28)

建立真实、可复现的数据科学案例，覆盖 (§28):

- Business Analytics (CS01)
- Time Series (CS03, CS05)
- Customer Analytics (CS02)
- Marketing (CS04)
- Financial Data (CS05)
- Public Statistics (CS06)
- Data Quality (CS07)
- Machine Learning (CS08)

每个数据集必须具有 (§29): `Public Source / Clear License / Citation / Download Instructions / Version / Hash` — 禁止提交许可证不明确的版权数据.

## 2. Case Study Structure (§31)

每个案例包含: `Problem / Dataset / Question / Analysis Plan / Agent Trajectory / Tools / Statistics / Model / Evidence / Visualization / Report / Limitations / Reproduction` (§31)

## 3. Repository (§32)

```
case-studies/
├── 01-sales/               # CS01 Sales Analysis — ✅ Verified (COMPLETED, 1.3s, 6 evidence)
├── 02-churn/               # CS02 Customer Churn — ✅ Verified (COMPLETED, 0.1s, 3 evidence)
├── 03-time-series/         # CS03 Time Series Forecasting — 📝 Planned (dataset ready, synthetic)
├── 04-marketing/           # CS04 Marketing Analytics — 📝 Planned
├── 05-financial/           # CS05 Financial Time Series — 📝 Planned
├── 06-public-statistics/   # CS06 Public Statistics — 📝 Planned (titanic.csv, health)
├── 07-data-quality/        # CS07 Data Quality Investigation — 📝 Planned
└── 08-classification/      # CS08 ML Classification — 📝 Planned
```

## 4. Quality Gate (§33)

每个 Case Study 必须: `run from clean environment / generate real output / generate evidence / generate report / generate reproduction package` — 不得使用 `mock output / fake metrics / hard-coded result`.

**Current:**

| Case | Status | Run | Evidence | Report | Repro | Notes |
|------|--------|-----|----------|--------|-------|-------|
| CS01 Sales | ✅ Verified | `COMPLETED` 1.3s | 6 | ✅ 3890 chars | ✅ `reproduce.sh` via `artifacts/reports/<runId>/` | Real Agent, no mock |
| CS02 Churn | ✅ Verified | `COMPLETED` 0.1s | 3 | ✅ 2983 chars | ✅ | Real Agent, no mock |
| CS03-08 | 📝 Planned | — | — | — | — | Dataset + Plan ready, execution queued for Phase D full |

## 5. Recommended Case Studies (§30)

At least 8: `CS01 Sales / CS02 Churn / CS03 Time Series / CS04 Marketing / CS05 Financial / CS06 Public Stats / CS07 Data Quality / CS08 Classification` (§30) — all 8 defined, 2 verified.

## 6. Dataset Rules (§29)

All datasets are **synthetic** generated via `scripts/generate_benchmark_v2.py` seed 42 (CC0, MIT) — no copyrighted data. Each has `Source: synthetic / License: MIT/CC0 / Citation: DATA_SCIENCE_AGENT_V4_2 + benchmarks/v2` + `Download: benchmarks/v2/datasets/<name>.csv` + `Version: v2 0.3.0` + `Hash: sha256` (see each case).

## 7. How to Reproduce

```bash
# Sales (CS01)
uv run python -c "from data_science_agent import Agent; r=Agent().analyze_sync('benchmarks/v2/datasets/sales.csv', 'Analyze revenue trends by region and category...'); print(r.status, len(r.evidence))"

# Churn (CS02)
uv run python -c "from data_science_agent import Agent; r=Agent().analyze_sync('benchmarks/v2/datasets/customer_churn.csv', 'Analyze churn...'); print(r.status)"

# Or via CLI
uv run dsa analyze benchmarks/v2/datasets/sales.csv --task "Analyze revenue" --json
```

Outputs in `case-studies/<id>/outputs/` (real, not mock) + `artifacts/reports/<runId>/` (report.md, evidence_graph.json, reproduce.sh, analysis.ipynb).

## 8. Next

- Phase D full: Execute CS03-08 with same gate (real Agent, not mock) and generate `research/v4_2/benchmark_vs_real_world.md` (§48)
- Phase E: External Reproduction (§34-39) — 3 envs (Linux/macOS/Container)

*Generated: 2026-08-22 live — `b79610d` → `857a92d`*
