# Human Evaluation — V3 Phase G (W7 §35–38)

> **5–10% sampled manual review · 8-dimension rubric 1–5 · Guide + Agreement (Kappa/Alpha)**

## Contents

| File | Purpose |
|------|---------|
| `samples.json` | Deterministic stratified sample (`ratio 0.08, seed 42`): **11 tasks / 100** (5–10% + `[5,20]`, one per category). Source: `dsa_evaluation.human_eval.sample_human_eval_tasks` |
| `reviews.template.json` | Per-reviewer scoring template — copy to `reviews/<reviewer>.json`, fill `scores 1..5` per dimension |
| `agreement.json` | Pending — computed from `reviews/*.json` via `agreement_summary` (`cohens_kappa` for 2 raters, `krippendorff_alpha` ordinal for 3+) |
| `../docs/v3/HUMAN_EVALUATION_GUIDE.md` | Reviewer guide (§37): Task + Dataset + Gold Criteria + Evidence + Tool Outputs, rubric anchors, agreement method, CI |

## How to run

```bash
# 1. Re-generate the sample (deterministic)
uv run python -c "from pathlib import Path; from dsa_evaluation.catalog import Catalog; from dsa_evaluation.human_eval import sample_human_eval_tasks; cat=Catalog.load(Path('benchmarks/v2/catalog.json')); print([s.task_id for s in sample_human_eval_tasks(cat)])"

# 2. Fill reviews per reviewer
cp human-eval/reviews.template.json human-eval/reviews/alice.json
# edit scores 1..5 for each sampled task_id

# 3. Compute agreement per dimension
uv run python -c "
from pathlib import Path; import json
from dsa_evaluation.human_eval import HumanEvalReview, agreement_summary
reviews = []
for p in Path('human-eval/reviews').glob('*.json'):
    data = json.loads(p.read_text())
    for item in data.get('reviews', []):
        reviews.append(HumanEvalReview(**item))
for dim in ['correctness','clarity','statistical_validity','evidence_quality','interpretation','uncertainty','actionability','report_quality']:
    print(agreement_summary(reviews, dim).model_dump())
"
```

## Sample (seed 42, 8% → 11 tasks)

`clf-04, clus-04, dq-06, eda-08, ev-01, prof-04, reg-08, sql-05, stats-10, ts-06, viz-03` — stratified one per category across 11 categories (8 dims × 11 tasks = 88 ratings per reviewer).
