# Evaluation — V3 W10 §48

> Canonical: `docs/v2/evaluation.md` + `docs/v3/STATISTICAL_EVALUATION.md` + `packages/evaluation/src/dsa_evaluation/`

## Framework

`EvaluationResultV2` — 10 dims (`task_success / statistical / tool / evidence / unsupported / code / sql / reproducibility / safety / latency`) × 6 levels (`Tool → Numerical → Statistical → Interpretation → Evidence → Report`), plus `by_category / by_difficulty` and significance helpers (`bootstrap_ci / mcnemar / wilcoxon`, see `significance.py`).

Evaluator versioning (§73): `evaluator_v1` (pre-audit, keyword) vs `evaluator_v2` (10 dims + `S01–S10`, causal `S09`, uncertainty `S10`). Results must carry `evaluator_version` and not be compared across versions without annot.

## Statistical Rigour (W4)

See `docs/v3/STATISTICAL_EVALUATION.md` — 10 dims + `S01–S10` taxonomy (`Wrong Test … Uncertainty Omission`).

## Reliability & Cross-Model

- Reliability (§27–30, 4 configs `single/planner/planner+critic/full`): `docs/v3/RELIABILITY.md` + `research/V3_RESEARCH_REPORT.md` (Ablation A–F).
- Cross-model (§31–34, 4 classes + 3 Pareto frontiers, no fabrication): `docs/v3/CROSS_MODEL.md`.
- Human eval (§35–38, 11/100 stratified, 8 dims 1–5, Kappa/Alpha): `human-eval/` + `docs/v3/HUMAN_EVALUATION_GUIDE.md`.

## Reproducibility of evaluation

```bash
uv run dsa --limit 50                              # v1, 50/50 @1.00 (8 cats)
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100  # v2, 100/100 @1.00 (11 cats)
uv run dsa --reproduce v2 --out reproduction/v2    # fresh twice + ReproductionScore 6-dim + L0..L5
```

Scores are versioned (§72–74) and immutable under `release/` (see `research/V3_RESEARCH_REPORT.md` Appendix).
