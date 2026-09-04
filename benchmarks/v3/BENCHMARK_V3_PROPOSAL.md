# Benchmark V3 Proposal (V4.3 W6 §62)

> **Spec:** `DATA_SCIENCE_AGENT_V4_3.md` §58-62 — mine real failures, inventory
> benchmark gaps, propose Benchmark V3. **Status: PLAN ONLY — the frozen
> `benchmark v2 0.3.0` is NOT modified by this document** (Architecture Freeze §8;
> any schema/benchmark change requires a V4 ADR per §10).
> **Date:** 2026-09-04 (consolidation of evidence recorded 2026-08-22 → 2026-08-31).
> **Primary sources (all committed):**
> - `research/v4_2/benchmark_vs_real_world.md` — gap inventory + v3 candidate table (§50)
> - `case-studies/01..08/outputs/tool_calls.json` — 18 real tool-call failures (§17)
> - `docs/v4_3/V4_2_1_RECONCILIATION.md` §5 — per-case failure ledger
> - `research/v4_3/datascibench/failures/FAILURE_TYPES.md` — external failure classes
>   (DataSciBench full run, 45/45 executed, no GT → nothing scored)

---

## 1. Evidence Basis (§58)

- **18 real tool-call failures** preserved across CS01-08 (counted from committed
  `outputs/tool_calls.json`, `status: error`; never sanitized — §17).
- **14 gap classifications**: 1 `Benchmark-Covered` / 7 `Benchmark-Underrepresented`
  / 6 `Benchmark-Missing` (§61; full inventory in `research/v4_2/benchmark_vs_real_world.md`).
- **1 new external failure class** discovered by the DataSciBench full run:
  empty-input tasks (`UnsupportedFormatError`, 44 steps) — internal benchmarks
  always ship a data file, so this class is `Benchmark-Missing` internally.
- **Evidence bar met (2026-08-25):** 8/8 case studies executed with the real Agent;
  this satisfies the §50 bar to PLAN `benchmark v3 0.4.0` — implementation belongs
  to a future version (§62: "Benchmark V3 实现原则上应属于未来版本").

## 2. Failure Clusters (§59)

| Cluster (§59) | Real evidence (committed) |
|---|---|
| Incorrect tool routing | `train_model` triggered for forecast-style requests (CS03, CS05, CS06) |
| Duplicate-column assumptions | `causal_check` / `correlation_analysis` `DuplicateError` (CS03, CS07, CS08) |
| Insufficient group detection | `hypothesis_test` group < 2 (CS06) |
| Domain / schema mismatch | CS04/CS05 `sales-like` schema vs marketing/financial questions (§18 honesty note) |
| Forecast / model confusion | `train_model` non-numeric / CV errors on time-series (CS03, CS05) |
| Causal / statistical misuse | `causal_check` `DuplicateError` family (CS02 ×2, CS07 ×2, CS08 ×2) |

External cluster (W6 input from DataSciBench run): empty-input / missing-data
handling — `UnsupportedFormatError` ×44 steps, honest `failed` before evidence.

## 3. Candidates (§62 required fields per candidate)

### C1. Long-tail dataset tasks ×4 (`missing_heavy`, `mixed_types`, `high_cardinality`, `unicode`)

- **Gap:** `Benchmark-Underrepresented` — 6 long-tail datasets ship in v2 with 0 tasks.
- **Real-world evidence:** CS07 data-quality run exercises missing/mixed types; live
  `profile_dataset` behavior is the proposed oracle.
- **Proposed task:** 1 task per dataset (4 total), `profile` → targeted cleaning/assertions.
- **Why V2 missed it:** v2 0.3.0 task catalog covers only canonical schema datasets.
- **Evaluation design:** exact-match on profile facts (missing %, dtype set, cardinality)
  + tool-trajectory assertion that `profile_dataset` runs before mutation.
- **Leakage risk:** LOW — datasets already committed in v2; no held-out answers online.

### C2. Open-ended business tasks ×4 (rubric-scored)

- **Gap:** `Benchmark-Missing` — benchmark is closed-form (`SELECT ...`); no open
  question with a rubric.
- **Real-world evidence:** CS01 "Analyze revenue trends…" (open, `COMPLETED`) vs
  benchmark closed tasks — correlation between the two is 0 until a rubric exists
  (`research/v4_2/benchmark_vs_real_world.md` §6).
- **Proposed task:** 4 Business-Analytics open tasks (ROI, retention, allocation, churn)
  scored on a multi-dimension rubric (completeness, correctness, evidence, clarity).
- **Why V2 missed it:** v2 evaluator supports exact match only; no rubric pathway.
- **Evaluation design:** rubric evaluation (8-dimension, human or LLM-judge with
  spot-checked agreement), compared against CS01/CS02 real-run reports as calibration.
- **Leakage risk:** MEDIUM — rubric text lives in the repo; mitigate with blind review
  (V4.3 §77: reviewers see expected answers only after rating) and judge rotation.

### C3. Financial tasks ×2 (volatility, forecast)

- **Gap:** `Benchmark-Underrepresented` — `financial` dataset exists, no tasks.
- **Real-world evidence:** CS05 (`run-d1f43414f1`) — 2 real `train_model` failures on
  non-numeric columns; forecast intent vs tool routing mismatch.
- **Proposed task:** realized-volatility computation + 1-step forecast with MAE scoring.
- **Why V2 missed it:** no task targets the financial dataset's time dimension.
- **Evaluation design:** numeric tolerance windows (MAE ≤ threshold, vol in ±10% band).
- **Leakage risk:** LOW — deterministic dataset, tolerance published with the task.

### C4. Large-table task ×1 (10 MB `wide_table`)

- **Gap:** `Benchmark-Underrepresented` — v2 tasks run on ~500 rows; performance.md
  claims 10/50/100 MB support, untested by any task.
- **Real-world evidence:** `performance.md` §54 claims vs zero benchmark coverage;
  W9 large-file harness dependency.
- **Proposed task:** 10 MB wide-table aggregation with wall-time + memory ceiling.
- **Why V2 missed it:** small fixtures keep CI fast; no size-tier task existed.
- **Evaluation design:** correctness (aggregate values) + resource gates (timeout/mem).
- **Leakage risk:** NONE known — synthetic generator, seeded.

### C5. Target-discovery task ×1 (`titanic`)

- **Gap:** `Benchmark-Missing` — no discovery-style task (find plausible targets).
- **Real-world evidence:** CS06 profile flow demonstrates `potential_target_columns`
  behavior; no benchmark task asserts it.
- **Proposed task:** profile `titanic` → enumerate plausible target columns with rationale.
- **Why V2 missed it:** v2 tasks presuppose the target column.
- **Evaluation design:** set-membership scoring (`Survived` in top-k) + rationale quality check.
- **Leakage risk:** LOW — well-known dataset; scoring is set-based, not string-match.

### C6. Failure-mode regression tasks ×6 (from the 18 live failures)

- **Gap:** `Benchmark-Missing` — the 6 live failure clusters (§2) have no benchmark tasks.
- **Real-world evidence:** the 18 preserved tool-call failures (CS01-08) + 84 tool-error
  steps / 44 empty-input steps from the DataSciBench run (`FAILURE_TYPES.md`).
- **Proposed task:** per cluster, 1 regression task with the honest expected outcome:
  duplicate-column input → clean `DuplicateError`-style failure + recovery, NOT a silent pass;
  forecast request → correct tool routing; group<2 → graceful guard; empty-input dir →
  explicit `UnsupportedFormatError` surfaced to the user.
- **Why V2 missed it:** v2 tasks all start from well-formed inputs and never assert
  failure behavior.
- **Evaluation design:** assert on trajectory + user-visible failure reporting
  (exit status, limitation note), not on analytical output.
- **Leakage risk:** LOW — failure modes come from recorded runs, not from evaluator internals.

**Candidate total: 18 tasks** (12 from the §50 table + 6 failure-mode regressions)
→ `v2 0.3.0 → 0.4.0` or `v3 0.4.0` decision deferred to the ADR.

## 4. Decision Rules (§34, §62, §8, §10)

1. **No modification to frozen `benchmark v2 0.3.0`** — results comparability and
   release immutability (§25) outrank expansion.
2. **No prompt-tuning on held-out tasks; no hard-coded answers; no retry-until-pass**
   (§34 integrity rules apply to any future V3 run).
3. Implementation requires a **V4 ADR** (Problem / Evidence / Impact / Alternatives /
   Recommendation / Migration / Rollback) — benchmark change is architecture-adjacent (§8).
4. Sequencing: after W7 reliability statistics and W10 community inputs
   (`research/v4_2/benchmark_vs_real_world.md` §5 evidence-status note, 2026-08-25).

---

*Generated: 2026-09-04 — consolidation only; every claim above cites a committed
source. No benchmark file was modified.*
