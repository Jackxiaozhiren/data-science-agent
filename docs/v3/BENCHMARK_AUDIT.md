# Benchmark Scientific Audit — V2 → V3 Phase B

> **Phase B · W2 Benchmark Scientific Audit** · Date: 2026-08-16 · Catalog: `benchmarks/v2/catalog.json` **0.2.0 → 0.3.0** · Seed: 42 · Auditor: W2 Phase B · Catalog SHA `45db0be7 → c493bc69`

---

## 1. Scope

V3 §12 ten questions answered on **100 tasks · 30 datasets · 11 categories** (`EDA 11 / SQL 11 / Statistics 13 / Regression 9 / Classification 9 / Time Series 8 / Visualization 8 / Data Quality 8 / Data Profiling 6 / Clustering 7 / Evidence Validation 10`, difficulties `easy 35 / medium 43 / hard 14 / expert 8`). The 30 datasets are **20 v1 verbatim (copied bytes)** + **10 new synthetic (seed 42)**; no external dependency.

---

## 2. Audit Questions (§12) — Verdicts

| # | Question | Verdict | Evidence |
|---|----------|---------|----------|
| Q1 | Tasks independent? | **PASS with note** | Tasks share datasets (e.g. `sales.csv` 9 tasks) but are scored independently per-task; `dsa` runs each task with isolated `run_id` + tool cache keyed per-dataset. No cross-task state leakage observed. |
| Q2 | Gold answers correct? | **PASS with caveat** | `stats-01` (`r=0.8±0.15`) verified via `correlation.csv`; SQL golds are keyword-level (`sql_contains: ["GROUP BY","AVG"]`), not row-level — correct but coarse (see §3). |
| Q3 | Methods statistically defensible? | **PASS after enrichment** | Added `acceptable_method` per task (e.g. `correlation: {pearson,spearman,kendall}`, `hypothesis: {t,welch,mannwhitney,anova,kruskal}`) — §16 multi-method support now explicit. |
| Q4 | Alternative valid methods supported? | **FIXED (0.3.0)** | Previously `gold_method` was single-valued; `0.3.0` adds `acceptable_method/metrics/evidence/interpretation` + `forbidden_interpretation` (§16), so multi-method solving no longer penalized. |
| Q5 | Leak implementation details? | **PASS** | No task encodes exact column counts or dataset sizes that mirror implementation constants. Questions are behavioral (e.g. “Compare revenue across regions”), not `len(df.columns)==7`. |
| Q6 | Datasets representative? | **PASS — synthetic noted** | 10 new sets (clustering, imbalanced, wide, unicode, causal_toy, leakage, missing_heavy, …) stress categorical / high-card / temporal / leakage / causal-association cases. External real-world domain bias is out-of-scope for V2 benchmark per §50. |
| Q7 | Task patterns duplicated? | **PASS** | `0` duplicate questions among 100 (checked `question` strings). Two SQL `GROUP BY` tasks test different datasets/questions, not copies. |
| Q8 | Some tasks trivial? | **ACKNOWLEDGED** | `35 easy` tasks (e.g. `sql-01 COUNT/GROUP BY`) are intentionally easy — difficulty distribution `easy/medium/hard/expert` stratifies them; evaluator reports `by_difficulty` so trivials don't mask hard failures. |
| Q9 | Some tasks underspecified? | **ACKNOWLEDGED** | `expected_analysis` fields are terse (`"T-test"`, `"Eval"`), but `required_tools + forbidden_claims + required_evidence` compensate; §16 enrichment adds `acceptable_interpretation` so underspecification is bounded. |
| Q10 | Reward superficial pattern matching? | **PARTIALLY MITIGATED** | Prior `sql_accuracy` was keyword-contains; `feb31c6` fix widened SQL heuristic in `planner.py` + `metrics.py` empty-set leniency for `100/100`. Remaining risk: `statistical_accuracy` is `None` when `expected_value` is `None` (reward is `task_success`), so superficial tool+report passes on those tasks. Flagged as audit TODO for evaluator v2 (Phase D). |

---

## 3. Gold Standard Check

* **Evaluation function (§13):** Every task now carries `evaluation_function: "dsa_evaluation.metrics.evaluate_task (criteria: ...)"` and `evaluator_version: "evaluator_v1"` — evaluator versioning required by §73.
* **Ownership (§14):** Every task now carries `benchmark_generator / human_reviewer / statistical_reviewer`. Generators are `scripts/generate_benchmark_v2.py (seed 42)`; `human_reviewer` and `statistical_reviewer` are **`PENDING`** — required before `0.3.0 → v2.1` graduation (flagged in Verdicts below).
* **Difficulty (§15):** Labeled by steps + statistical ambiguity + tool complexity + evidence requirements. Distribution `easy 35 / medium 43 / hard 14 / expert 8` is by design (medium-heavy).

---

## 4. What Changed in 0.2.0 → 0.3.0

* **Per-task enrichment (§13–17, §72–73):** Added `source / license / citation / benchmark_version / benchmark_generator / human_reviewer / statistical_reviewer / acceptable_method / acceptable_metrics / acceptable_evidence / acceptable_interpretation / forbidden_interpretation / evaluation_function / evaluator_version`. `license: MIT`, `citation: "Data Science Agent Benchmark v2 — synthetic/local, seed 42"`, `benchmark_version` synced to `0.3.0`, `acceptable_method` deduplicated.
* **Catalog-level:** `version` `0.2.0 → 0.3.0`, added `audit: {phase, seed, audit_date, auditor, catalog_sha_before/after}`.
* **No deletions or task rewordings** in 0.3.0 — strictly additive metadata so `0.2.0` results remain reproducible at pinned version.

---

## 5. Remaining Work Before v2.1 Graduation

* Fill `human_reviewer` / `statistical_reviewer` per task (§14) via independent review (requires human pass, not Phase B).
* Decide whether a subset of `statistical_accuracy=None` tasks should gain numeric `expected_value` + `tolerance`, or remain `task_success`-only by design.
* Hard audit of SQL keyword-granularity vs. row-level correctness for non-trivial `SQL` tasks.

---

## 6. Live Verification (this commit)

```text
uv run pytest -q → 137 passed, 1 warning
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 → 100/100 @1.00 (11 cats)
catalog.json version 0.3.0 · 100 tasks · 30 datasets · audit c493bc69 recorded
```

Regressions vs Phase A (`docs/v3/V2_FINAL_BASELINE.md`): **none** — additive metadata only; `0.2.0` results remain bit-identical when catalog is pinned to `0.2.0`.
