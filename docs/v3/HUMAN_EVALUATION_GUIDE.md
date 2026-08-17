# Human Evaluation Guide — V3 Phase G (W7 §35–38)

> **Human evaluation is not the only evidence — but it is required evidence (§35). Automated metrics need manual grounding.**

---

## 1. Sampling (§35) — 5%–10% of Benchmark

- **Population**: `benchmarks/v2/catalog.json` `100 tasks` (11 categories, seed 42).
- **Sample**: `human-eval/samples.json` — **11 tasks (11%)** via `dsa_evaluation.human_eval.sample_human_eval_tasks(ratio=0.08, seed=42, min_n=5, max_n=20)`:
  - Stratified by category (one per available category; proportional allocation, deterministic via `seed 42`, round-robin to `n_target = clamp(round(n*0.08), 5, 20)`).
  - Stable hash `hash_human_eval_sample(samples) = c3835816…` (sha256 of sorted task_ids).
  - Re-generated deterministically — `seed 42` is the experiment id for this sample.
- **What ground-truth each reviewer needs**: `Task` + `Dataset` (CSV under `benchmarks/v2/datasets/`) + `Gold Criteria` (`gold_method / expected_analysis`) + `Evidence` (run's `insights/evidence`) + `Tool Outputs` (`run_benchmark --limit` trace or `reproduction/`).

Sampled task_ids (seed 42):

```
clf-04 (Classification · hr_promotion.csv)
clus-04 (Clustering · wide_table.csv)
dq-06 (Data Quality)
eda-08 (EDA)
ev-01 (Evidence Validation)
prof-04 (Data Profiling)
reg-08 (Regression)
sql-05 (SQL)
stats-10 (Statistics)
ts-06 (Time Series)
viz-03 (Visualization)
```

---

## 2. Rubric (§36) — 8 dimensions × 5-point scale

Rate **each sampled task's final report/evidence** on:

| # | Dimension | What to judge |
|---|-----------|---------------|
| 1 | **Correctness** | Is the answer correct w.r.t. the dataset and question? Wrong calculation / wrong SQL / hallucinated numbers → low. |
| 2 | **Clarity** | Is the reasoning and report readable, structured, and unambiguous? |
| 3 | **Statistical Validity** | Method choice, assumption checks, test execution, p-value/CI/effect size — aligns with `evaluator_v2` 10 dims (§22). |
| 4 | **Evidence Quality** | Are claims grounded in tool outputs? Any unsupported causal language should be flagged (see `docs/v3/STATISTICAL_EVALUATION.md §24` observational vs causal). |
| 5 | **Interpretation** | Are conclusions faithful to the statistics (no overclaim, no misread of correlation as causation)? |
| 6 | **Uncertainty** | Are CIs / intervals / limitations / sampling uncertainty reported where appropriate (§25)? |
| 7 | **Actionability** | Does the report give usable next steps or decisions, or just descriptive text? |
| 8 | **Report Quality** | Overall professional quality: structure, figures/tables, reproducibility notes. |

**Scale** — `1 = unacceptable · 2 = poor · 3 = acceptable · 4 = strong · 5 = excellent`

Implementation: `dsa_evaluation.human_eval.RUBRIC_DIMENSIONS` (8) and `SCORE_SCALE` (5). `HumanEvalReview(task_id, reviewer, scores: {dimension: 1..5}, comments)`.

Anchors (apply consistently; calibrate with a shared pilot of 2 tasks):

- **5 excellent** — correct, well-evidenced, statistically rigorous, clearly written, uncertainty stated, actionable.
- **3 acceptable** — broadly correct with minor gaps (e.g. missing assumption note, slight causal wording but evidence otherwise sound).
- **1 unacceptable** — wrong answer, fabricated numbers, causal overclaim on correlation only, missing evidence.

---

## 3. What to read before scoring a task (§37)

For each `task_id` in `human-eval/samples.json`:

1. **Task**: `catalog.json` `question` + `expected_analysis` + `required_tools` + `required_evidence` + `forbidden_claims`.
2. **Dataset**: `benchmarks/v2/datasets/<dataset>` — skim schema; reproduce one run if in doubt (`uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 1` or `reproduction/v2/first`).
3. **Gold Criteria**: `gold_method / gold_result / acceptable_method / acceptable_metrics / acceptable_evidence` from the catalog's per-task `acceptable_*` / `evaluation_function`.
4. **Evidence**: The run's `insights` (each with `evidence_ids`) + `evidence` payloads + `tool_calls` trace + `report_markdown`.
5. **Tool Outputs**: Raw tool outputs for the task (SQL result, Python/statistics outputs, chart paths) — judge whether insights trace to a tool, not to free text.

**Scoring tip**: Score `Correctness + Statistical Validity + Evidence Quality` first; if any is `≤2`, `Interpretation / Actionability` cannot exceed `3`.

---

## 4. Agreement (§38) — Inter-Rater Reliability

When **≥2 reviewers** rate the same task(s) on the same dimension:

| Reviewers | Metric | When | Reporting |
|-----------|--------|------|-----------|
| 2 | **Cohen's Kappa** (unweighted, `k=5`) | pairwise | `value ∈ [-1,1]`, `n = paired items` |
| 3+ | **Krippendorff's Alpha** (ordinal, squared distance) | coincident matrix | `value ∈ [-1,1]`, `n = paired items` |

Also report: `Agreement` (Kappa/Alpha), `Sample Size` (`n` paired tasks for that dimension), `Confidence Interval` (bootstrap 95% when `n ≥ 20`; otherwise `null`).

Code:

```python
from dsa_evaluation.human_eval import agreement_summary, HumanEvalReview
reviews: list[HumanEvalReview] = [...]  # from human-eval/reviews/*.json
for dim in RUBRIC_DIMENSIONS:
    rep = agreement_summary(reviews, dim, level="ordinal")
    # rep = AgreementReport(dimension, metric, value, n, ci95, notes)
```

Conventional reading: `≥0.80 strong · 0.60–0.80 moderate · <0.60 weak` (dimension-specific; do not average Kappas across dimensions).

---

## 5. Workflow

```
samples.json (seed 42, 11 tasks)
      ↓
reviews/<reviewer>.json  — one file per reviewer (copy from reviews.template.json)
      ↓
agreement.json  — computed via agreement_summary per dimension
      ↓
human-eval/report.md  — optional downstream summary (means per dimension, distribution, sampled task coverage)
```

No blocking gate: human evaluation is **informational** for V3.0; automated gates (`dsa 100/100`, `evaluator_v2`) remain authoritative. Human review validates them.

---

## 6. Files

- `human-eval/samples.json` — 11 stratified tasks (hash `c3835816e699bb5f`)
- `human-eval/reviews.template.json` — rubric + example review
- `human-eval/agreement.json` — placeholder pending real reviews
- `packages/evaluation/src/dsa_evaluation/human_eval.py` — sampling, rubric, Kappa/Alpha
- `tests/evals/test_human_eval.py` — sampling ratio, rubric, Kappa=1 / Alpha=1, two- and three-rater agreement
