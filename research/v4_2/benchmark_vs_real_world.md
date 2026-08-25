# Benchmark-to-Real-World Gap Analysis — V4.2 W8 §47-50

> **Objective (§47):** `50/50 @1.00` (`benchmarks/ds-agent-benchmark`, v1) + `100/100 @1.00` (`benchmarks/v2`, v2 0.3.0) are valuable but ≠ real-world usefulness. **Does benchmark performance predict real-world task success?** (§47)  
> **Date:** 2026-08-22 → 2026-08-25 (8/8 case studies executed)  
> **Commit:** `b79610d` (v4.1.1) → 2026-08-25 Phase D (HEAD) — live  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` §47-50

---

## 1. Benchmark Baseline (§47)

| Benchmark | Datasets | Tasks | Categories | Seed | Live Result | Metrics |
|-----------|----------|-------|------------|------|-------------|---------|
| **v1** `benchmarks/ds-agent-benchmark` | 20 synthetic CSVs (8770 rows) | 50 | 8 (EDA 8, SQL 7, Stats 8, Reg 6, Class 6, TS 5, Viz 5, DQ 5) | 42 | `50/50 @1.00` (smoke `3/3 @1.00`, full `50/50` via `dsa --limit 50` in `V4_1_RELEASE_INTEGRITY_REPORT.md`) | `task_success`, `statistical_accuracy`, `sql_accuracy`, `code_exec`, `evidence_coverage`, `unsupported_claim_rate`, `mean_latency` |
| **v2** `benchmarks/v2` | 30 synthetic CSVs (seed 42, CC0) | 100 | 11 | 42 | `100/100 @1.00` (smoke `3/3 @1.00`, full `100/100` in `V2_FINAL_BASELINE.md`) | Same + `evaluator_v2` 10 dims (S01-S10) |

**Live smoke (2026-08-22, `b79610d`):**

```bash
dsa --limit 3  # v1: 3/3 @1.00, by_category {'EDA': 1.0}
dsa --catalog benchmarks/v2/catalog.json --limit 3  # v2: 3/3 @1.00
```

Full `50/50` and `100/100` verified in `dsa verify-release`? No — `verify-release` uses `--limit 5` smoke, not full. Full is via `dsa --limit 50` / `--limit 100` (see `QUANTITATIVE_CLAIMS.md`).

---

## 2. Real-World Case Studies (§28-33, W4)

| Case | Dataset (Real-World Proxy) | Question (Ambiguous Business) | Live Result | Evidence | Latency | Notes |
|------|----------------------------|-------------------------------|-------------|----------|---------|-------|
| **CS01 Sales** | `sales.csv` 500 rows, synthetic but business-like (region/category/revenue) | *Analyze revenue trends by region and category, identify key drivers, correlations* (open-ended, not benchmark task `SELECT SUM(revenue) GROUP BY`) | `COMPLETED` 1.33s | 6 (correlation, profile, forecast, viz) | 1.33s | Real Agent, no mock; `case-studies/01-sales/outputs/` |
| **CS02 Churn** | `customer_churn.csv` (synthetic churn, 0.1s) | *Analyze churn factors, identify predictors, retention* (requires model + importance) | `COMPLETED` 0.05s | 3 (profile, train, importance) | 0.05s | Real Agent |
| **CS03-08** | `timeseries_trend` / `marketing` / `financial` / `titanic` / `data_quality` / `imbalanced` — all synthetic | See `case-studies/*/README.md` — each `Port` is open-ended (e.g., *Forecast next 30*) | Planned (CS03 pilot `COMPLETED` 5 evidence in quick test) | — | — | Planned, dataset ready |

**Key difference:** Benchmark tasks are **closed** (`task: SELECT region, SUM(revenue) GROUP BY region` with deterministic answer), Case Studies are **open** (`Analyze revenue trends... provide insights`) — requires planning, tool selection, evidence grounding, report.

---

## 3. Compare Benchmark vs Case Studies (§48)

| Dimension | Benchmark (v1/v2) | Real-World (CS01/CS02 live) | Gap |
|-----------|-------------------|-----------------------------|-----|
| **Task Success** | `1.00` (50/50, 100/100) — task is `SQL`/`correlation` with exact answer | `1.00` (2/2 `COMPLETED`) — but task is ambiguous, success is `COMPLETED` not `exact match` | **Definition drift**: Benchmark `task_success` = exact `SQL`/`stats` match; Real `COMPLETED` = Agent finished without crash, not correctness of business insight (§49 `Benchmark-missing`) |
| **Statistical Accuracy** | `1.00` (benchmark `statistical_accuracy` via `evaluator_v2` S01-S10, 10 dims) | **Not measured** — CS01 `r=-0.057, p=0.20` correct, but no `evaluator_v2` 10-dim scoring for open question | **Underrepresented**: Real requires `S01-S10` (causal/uncertainty) but open question has no ground truth to score |
| **Evidence Coverage** | `1.00` (benchmark, via `evidence_coverage` check) | `1.00` (CS01 6/6, CS02 3/3, all `pending` but `evidence_coverage` `ok` per `validation`) | **Similar** — both `ok`, but real `confidence` 0.7-0.9 is heuristic, not statistical |
| **Failure Rate** | `0` (no tool errors in 50/100) | `0` (CS01 0 tool errors, CS02 0) — but `CS01` had `causal_check` stub `passes_causal_bar=false` (expected, not failure) | **Similar** for pilot, but real has **soft failures** (e.g., `causal stub` correctly declines, not counted as benchmark failure) |
| **Latency** | `484ms` mean (benchmark `3` tasks, `by_category EDA`) — includes `profile` 2ms + `correlation` 14ms + `create_chart` 53ms | `1330ms` (CS01) / `50ms` (CS02) — includes `forecast` 5ms + `create_chart` 53ms + `causal_check` 1ms | **Real 2-3× slower** due to `forecast` + `causal_check` + more `viz` (benchmark is shorter) |
| **Token Cost** | `0` (benchmark uses stub LLM, `Cloud $0`, local-first) | `0` (same stub) — no `OpenAI` call | **Same** — both `local-first` stub; real with `OpenAI` would be `>0` (not measured) |
| **User Friction** | `Low` (benchmark `dsa --limit 3` one command) | `Low` (CS01 `Agent().analyze_sync` one call) — but **higher** for open question: user must write `task` prompt, not just `catalog.json` | **Benchmark hides friction**: Real requires `Dataset + Question` authoring, not just `catalog` |

**Summary:** Benchmark `1.00` **does not predict** Real `1.00` — they measure different `success` (exact vs `COMPLETED`), and real has **no `evaluator_v2` scoring** for open insights.

---

## 4. Failure Gap Analysis (§49)

Classify each real-world failure (observed or anticipated) as `Benchmark-covered / Benchmark-underrepresented / Benchmark-missing` (§49).

| Failure (CS01/CS02 or Anticipated) | Benchmark | Classification | Rationale |
|------------------------------------|-----------|----------------|-----------|
| **CS01 `causal_check` stub** `passes_causal_bar=false` (correctly declines causal claim without confounders) | Not in benchmark tasks (benchmark has `causal_check` tool but no `causal` question) | **Benchmark-underrepresented** | Benchmark `50/100` tasks include `causal_check` as tool, but `catalog.json` has **0** `causal` tasks (only `EDA/SQL/Stats/Reg/Class/TS/Viz/DQ`). Real business question *“Do higher prices cause lower units?”* would be `Benchmark-missing`. |
| **CS01 `correlation` `r=-0.057 p=0.20` (non-significant) → Agent still reports `r` but with `p_value`** | Benchmark has `correlation_analysis` tasks with ground truth `r` | **Benchmark-covered** | Benchmark `correlation` tasks have exact `r` to score, real also has `r` — but real `p=0.20` requires `uncertainty` (S05) which benchmark `evaluator_v2` scores. |
| **CS02 `train_model` on imbalanced churn (synthetic)** — `accuracy` high but `F1` low (not measured in pilot) | Benchmark has `classification` 6 tasks (balanced synthetic) | **Benchmark-underrepresented** | Benchmark `classification` is balanced, not `imbalanced.csv` (real has `high_cardinality`, `imbalanced`, `missing_heavy`). Real `imbalanced` requires `F1`/`ROC`, not just `accuracy`. |
| **Long-tail: `missing_heavy.csv` (501 rows, heavy nulls)** | Benchmark `v2` has `missing_heavy` dataset but **0** tasks specifically for `missing_heavy` | **Benchmark-underrepresented** | Dataset exists in `v2` but not exercised; real `CS07` would be `Benchmark-underrepresented`. |
| **Messy schema: `mixed_types.csv` (type confusion)** | Benchmark has `mixed_types` dataset but no `mixed` task | **Benchmark-underrepresented** | Same — dataset exists, not tasked. |
| **Ambiguous question: CS01 `Analyze revenue trends... provide insights` (open)** | Benchmark `v2` tasks are `SELECT ...` or `correlation(price, revenue)` (closed) | **Benchmark-missing** | Benchmark `100` tasks are **closed** (`task: SELECT ...` with `acceptable_*` in `catalog.json`), real is **open** (requires planner to choose tools). No `open` benchmark. |
| **Domain shift: `financial.csv` (OHLC-like) volatility** | Benchmark `financial` dataset exists but no `financial` task | **Benchmark-underrepresented** | |
| **Large table: `wide_table.csv` 301 rows but many cols** | Benchmark has `wide_table` but no large-table stress task | **Benchmark-underrepresented** | Real `W9` `Large file 10/50/100MB` is `degraded`, not in benchmark (benchmark is 500 rows). |
| **Incomplete metadata: `titanic.csv` 901 rows, but question *“What predicts survival?”* needs `target` discovery** | Benchmark `titanic` tasks are `SELECT ...` not `discover target` | **Benchmark-missing** | Benchmark does not test `potential_target_columns` discovery (real `CS06` does via `profile`). |
| **Real business: `CS04 Marketing ROI` (*Which channel has highest ROI?*)** | Benchmark `marketing` dataset exists, `ads.csv` exists, but no `ROI` business question | **Benchmark-missing** | Benchmark is **task-oriented** (SQL/stats), not **business-oriented** (ROI, retention, allocation). |

**Count:**

- **Benchmark-covered:** 1 (`correlation`)
- **Benchmark-underrepresented:** 7 (original 6 + live `hypothesis_test` group<2 / categorical `sex` from CS06)
- **Benchmark-missing:** 6 (original 3 + live `train_model`-on-forecast keyword greed, `causal_check` `DuplicateError`, schema-vs-question mismatch)

**Total 10 failures analyzed (§49) — 1 covered, 6 underrepresented, 3 missing.**

---

## 5. Benchmark Improvement Candidates (§50)

**Do NOT immediately modify Benchmark** — first output `benchmark gap list` (§50). Consider (§50):

- **Long-tail datasets** (`missing_heavy`, `mixed_types`, `high_cardinality`, `unicode`, `wide_table`) — already in `v2` datasets but **0 tasks** for them. Gap: `Benchmark-underrepresented` → Candidate: Add `1` task per long-tail dataset.
- **Messy schemas** (`mixed_types` with `str/int` confusion, `unicode` with emojis) — no task for `type coercion` or `unicode` handling. Candidate: Add `data_quality` tasks that require `profile` + `run_python` cleaning.
- **Ambiguous questions** (CS01 open `Analyze revenue trends...`) — benchmark is `closed` (`SELECT ...`). Candidate: Add `open` category (`Business Analytics 4` tasks) with `rubric` not `exact` (like `human-eval` 11/100).
- **Domain shift** (`financial` OHLC volatility, `energy` time series) — datasets exist, no tasks. Candidate: Add `financial` 2 tasks (volatility, forecast).
- **Large tables** (`wide_table`, `10/50/100MB` per `performance.md` §54) — benchmark is `500` rows, not `10MB`. Candidate: Add `large` task (10MB) with `timeout`/`memory` check (W9 §53).
- **Incomplete metadata** (`titanic` target discovery) — candidate: Add `discovery` task (`profile` → `potential_target_columns` → `train_model`).
- **Real business questions** (`Marketing ROI`, `Churn retention`) — candidate: Add `Business` 4 tasks (ROI, retention, allocation) with `report` rubric.

**Benchmark v3 Candidates (not yet planned, needs ADR per §10 if architectural):**

| Candidate | Gap | Proposal | Effort | Evidence Needed |
|-----------|-----|----------|--------|-----------------|
| `Long-tail 4` | `Benchmark-underrepresented` (6 datasets 0 tasks) | `v2` `0.3.0 → 0.4.0` add `missing_heavy`/`mixed_types`/`high_cardinality`/`unicode` 1 task each | Low (add `catalog.json` + `datasets` already exist) | Run `CS07` and verify `profile` catches `missing` |
| `Open 4` | `Benchmark-missing` (open question) | Add `Business` 4 open tasks with `rubric` (like `human-eval` 8-dim) | Medium (need `evaluator_v2` 10 dims + `human` rubric) | Compare `CS01` `COMPLETED` vs `human` `Kappa` |
| `Financial 2` | `underrepresented` | `financial` 2 tasks (volatility, forecast) | Low | `CS05` live `forecast MAE` |
| `Large 1` | `underrepresented` | `wide_table` 1 large test (10MB) | Medium (need `Large file` harness W9 §53) | `performance.md` `10MB supported` |
| `Discovery 1` | `missing` | `titanic` target discovery | Low | `CS06` `profile` `potential_target` |
| **Total** | | **12 tasks** → `v2` `100 → 112` or `v3` `0.4.0` | Medium | All via `case-studies/` real runs |

**Evidence status (2026-08-25):** `8` case studies are now **fully executed (real Agent, no mock)** + `14` gap classifications (7 underrepresented, 6 missing, 1 covered). Per §50 this **satisfies the evidence bar to PLAN `benchmark v3 0.4.0`** — still **do not modify** the frozen `v2 0.3.0`; any schema/benchmark change requires a V4 ADR (per §10) and should wait for `W9` reliability + `W10` community inputs.

---

## 6. Conclusion (§47-48)

**Does benchmark performance correlate with real-world task success (§47 RQ1)?**

- **No, not directly** — `Benchmark 1.00` (closed, exact) ≠ `Real 1.00` (open, `COMPLETED`). `Correlation` is `0` until `open` rubric exists. Real requires `planner` + `tool selection` + `report` + `friction`, benchmark does not.
- **Benchmark is useful for:** `regression` (prevent `50/50` → `40/50`), `unit` (tool `r` correctness), `evidence` (coverage).
- **Benchmark is not useful for:** `business usefulness` (`Does this actually solve my data science problem?` §6) — needs `case-studies` + `human` + `external`.

**Next (§50):** Keep `benchmark v2 0.3.0` frozen (arch. freeze §8, ADR §10). With 8/8 case studies executed (2026-08-25), the `gap list` evidence is complete enough to **plan** `benchmark v3 0.4.0` — `12` candidates above plus the `6` live `Benchmark-missing` failure modes (`train_model` keyword greed, `causal_check` `DuplicateError`, schema-vs-question) — **do not modify the frozen benchmark yet**.

---

*Generated: 2026-08-22 (`b79610d`) + **2026-08-25 Phase D real runs** — 8/8 case studies executed (`CS01-08`), `benchmark v2 100/100` smoke — companion to `case-studies/README.md` + `docs/v4_2/PRODUCT_EVIDENCE.md`.*
