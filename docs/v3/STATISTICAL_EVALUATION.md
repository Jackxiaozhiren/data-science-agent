# Statistical Evaluation Upgrade — V3 Phase D (W4 §22–25)

> **Phase D · W4 Statistical Evaluation Upgrade** · Date: 2026-08-16 · `evaluator_v2` · §22–25 faithful

---

## 1. Dimensions (§22)

Independent per-task scoring for 9 requested dims (our result has 10 — adds `causal_language` as mandated by §24, plus `uncertainty_communication` per §25):

| # | Dimension | What it checks | Source |
|---|-----------|----------------|--------|
| 1 | `method_selection` | Did a statistical tool run when `statistical_accuracy` required? | `tool_names ∩ {correlation,hypothesis,regression,causal,assumption}` |
| 2 | `assumption_validation` | Was assumption evidence emitted? | `assumption_check` or `output.assumptions` or task not-statistical |
| 3 | `test_execution` | At least one `ok` tool call | `tool_calls[].status` |
| 4 | `parameter_estimation` | Numeric params present (`r/statistic/coef/...`) | `output` keys |
| 5 | `p_value_correctness` | `p_value ∈ [0,1]` when present | output `p_value` |
| 6 | `ci_correctness` | `ci_low ≤ ci_high` and finite | `ci_low/ci_high` |
| 7 | `effect_size` | Effect present (`effect_size/r/r2/...`) | output keys |
| 8 | `interpretation` | No unsupported causal overclaim | `dsa_agent.critic.check_unsupported_claims` → `S08` |
| 9 | `causal_language` | Causal words (`causes/leads to/...`) only with `causal_check` | §24 `S09` |
| 10 | `uncertainty_communication` | CI/forecast interval/limitation/uncertainty phrasing, or tool `limitations` | §25 `S10` |

Each dim is `{passed: bool|None, score: 1|0|None, reason, error_codes[]}`; `None` means *not applicable* (excluded from `overall`).

`overall` = mean of applicable dimensions (rounded to 4dp).

---

## 2. Error Taxonomy (§23 S01–S10)

| Code | Label | When emitted |
|------|-------|--------------|
| S01 | Wrong Test | No stat tool when required |
| S02 | Missing Assumption Check | No `assumption_check` nor `assumptions` |
| S03 | Incorrect Statistic / Param | No numeric params / not ok |
| S04 | Incorrect P-value | `p_value` out of `[0,1]` |
| S05 | Incorrect CI | `ci_low > ci_high` / non-finite |
| S06 | Incorrect Effect Size | No effect size on statistical task |
| S07 | Multiple Testing Error | Q mentions `multiple testing/Bonferroni/FDR` without correction token in outputs |
| S08 | Misinterpretation | Critic `unsupported_claim` fail |
| S09 | Causal Overclaim | Causal words without `causal_check` tool |
| S10 | Uncertainty Omission | No uncertainty phrasing nor CI nor `limitations` |

All codes are deduped per task into `error_codes` (sorted, set).

---

## 3. Causal Language Audit (§24)

Pattern (case-insensitive):

```
causes? | caused by | leads to | impacts?ed? | effects? | drives? | results in | due to
```

If causal language is found in `insights.finding` or `report_markdown` **without** `causal_check` having run, `causal_language` fails and `S09` is emitted. Example from spec:

- ❌ `Price causes revenue to increase.` → flagged `S09`
- ✅ `Price is positively associated with revenue.` → pass

---

## 4. Uncertainty Evaluation (§25)

Passes if any of these holds:

- Text contains `confidence interval | forecast interval | uncertainty | limitation | sampling ... | model uncertainty`
- Tool output had `ci_low/ci_high`
- Tool output had `limitations`

Otherwise on statistical tasks → `S10`.

---

## 5. Wiring (evaluator versioning §73)

- **Module:** `packages/evaluation/src/dsa_evaluation/statistical_eval.py` — pure function `evaluate_statistical(task, run_result) -> StatisticalEvaluation`.
- **Hook:** `packages/evaluation/src/dsa_evaluation/runner.py` now runs `evaluate_statistical` for **every** task after `evaluate_task` and attaches via `metrics.attach_statistical_eval`:
  - `result.details["statistical_eval"] = {dimensions, error_codes, overall, causal_flag, uncertainty_flag, ...}`
  - `result.details["evaluator_version"] = "evaluator_v2"`
  - `result.details["statistical_overall"] / "statistical_error_codes"` as flat proxies
- **No regression:** `aggregate_metrics` is unchanged; `evaluator_v1` aggregates still apply. `evaluator_v2` is **additive** under `details`. Comparison across versions must check `evaluator_version`.

Benchmark results after this change contain evaluator v2 fields:

```json
{
  "details": {
    "statistical_eval": { "dimensions": { "causal_language": {...} }, "error_codes": ["S08"], "overall": 0.8889, ... },
    "evaluator_version": "evaluator_v2"
  }
}
```

---

## 6. Tests

`tests/evals/test_statistical_eval.py`:

- `test_dimensions_present` — 10 dims emitted, `overall` defined
- `test_causal_flag_s09` — `"x causes y"` without `causal_check` → `S09`, `causal_flag True`
- `test_s10_uncertainty_omission` — no uncertainty → `S10` or `uncertainty_communication False`
- `test_attach_via_metrics` — `evaluator_version == "evaluator_v2"` after `attach_statistical_eval`
- `test_error_labels_cover_s01_s10` — `S01..S10` labeled

All 5 pass; full suite `142 passed` (was 137).

---

## 7. Live Verification

```
uv run pytest -q → 142 passed
uv run mypy packages apps/api --ignore-missing-imports → 88 source files Success
uv run ruff check packages apps/api tests → All checks passed
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 → 100/100 @1.00 (every result now carries evaluator_v2)
docker compose config → valid, npm 13/13 → valid
```
