# Real-World Data Science Case Studies — V4.2 W4 (§28-33)

> **V4.2 最重要的工作 (§28): 真实数据科学工作流中，它到底有没有用？**  
> **Date:** 2026-08-22 (planned) → 2026-08-25 (8/8 verified)  
> **Commit:** `b79610d` (v4.1.1) + `857a92d` (Phase C) + 2026-08-25 Phase D execution (HEAD) — live  
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
├── 03-time-series/         # CS03 Time Series Forecasting — ✅ Verified (COMPLETED 1.28s, 5 evidence)
├── 04-marketing/           # CS04 Marketing Analytics — ✅ Verified (COMPLETED 0.26s, 5 evidence)
├── 05-financial/           # CS05 Financial Time Series — ✅ Verified (COMPLETED 0.09s, 5 evidence)
├── 06-public-statistics/   # CS06 Public Statistics — ✅ Verified (COMPLETED 0.06s, 3 evidence)
├── 07-data-quality/        # CS07 Data Quality Investigation — ✅ Verified (COMPLETED 0.04s, 3 evidence)
└── 08-classification/      # CS08 ML Classification — ✅ Verified (COMPLETED 0.11s, 5 evidence)
```

## 4. Quality Gate (§33)

每个 Case Study 必须: `run from clean environment / generate real output / generate evidence / generate report / generate reproduction package` — 不得使用 `mock output / fake metrics / hard-coded result`.

**Current:**

| Case | Status | Run | Evidence | Report | Repro | Notes |
|------|--------|-----|----------|--------|-------|-------|
| CS01 Sales | ✅ Verified | `COMPLETED` 1.3s | 6 | ✅ 3890 chars | ✅ `reproduce.sh` via `artifacts/reports/<runId>/` | Real Agent, no mock |
| CS02 Churn | ✅ Verified | `COMPLETED` 0.1s | 3 | ✅ 2983 chars | ✅ | Real Agent; 4 tool failures (train_model/causal_check) |
| CS03 Time Series | ✅ Verified | `COMPLETED` 1.28s | 5 | ✅ 4526 chars | ✅ `reproduce.sh` via `artifacts/reports/run-1c70a7896a/` | Real Agent; 4 tool failures (correlation/train_model) |
| CS04 Marketing | ✅ Verified | `COMPLETED` 0.26s | 5 | ✅ 2896 chars | ✅ | Real Agent; 0 tool failures; schema = sales-like (documented) |
| CS05 Financial | ✅ Verified | `COMPLETED` 0.09s | 5 | ✅ 3330 chars | ✅ | Real Agent; 2 tool failures (train_model non-numeric); schema = sales-like |
| CS06 Public Stats | ✅ Verified | `COMPLETED` 0.06s | 3 | ✅ 2525 chars | ✅ | Real Agent; 4 failures (hypothesis_test/train_model), fell back to correlation |
| CS07 Data Quality | ✅ Verified | `COMPLETED` 0.04s | 3 | ✅ 2669 chars | ✅ | Real Agent; 2 failures (causal_check DuplicateError) |
| CS08 Classification | ✅ Verified | `COMPLETED` 0.11s | 5 | ✅ 3470 chars | ✅ | Real Agent; 2 failures (causal_check); classification succeeded |

## 5. Recommended Case Studies (§30)

At least 8: `CS01 Sales / CS02 Churn / CS03 Time Series / CS04 Marketing / CS05 Financial / CS06 Public Stats / CS07 Data Quality / CS08 Classification` (§30) — **all 8 defined AND 8 verified (real Agent, no mock)** as of 2026-08-25.

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

## 8. Status (2026-08-25)

- **8/8 case studies executed** (CS03-08 added live 2026-08-25 — real Agent, `COMPLETED`, evidence + report + reproduction package in each `outputs/` + `artifacts/reports/<runId>/`).
- Tool-call failures are real and recorded per case (`outputs/tool_calls.json` `status:error`) — e.g., `train_model` on forecast questions, `causal_check`/`correlation` `DuplicateError` on single-column datasets, `hypothesis_test` group-size. These feed the W8 gap analysis (benchmark-underrepresented failure modes).
- External Reproduction (§34-39) — 3 execution contexts (macOS/Linux-sim/Container-sim), see `reproduction/external/`.

*Generated: 2026-08-22 live — `b79610d` → `857a92d`*
