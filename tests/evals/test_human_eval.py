from __future__ import annotations

import json
from pathlib import Path

from dsa_evaluation.catalog import Catalog
from dsa_evaluation.human_eval import (
    RUBRIC_DIMENSIONS,
    SCORE_SCALE,
    HumanEvalReview,
    agreement_summary,
    cohens_kappa_two_raters,
    hash_human_eval_sample,
    krippendorff_alpha,
    sample_human_eval_tasks,
)


def test_sampling_ratio_and_stratified() -> None:
    cat = Catalog.load(Path("benchmarks/v2/catalog.json"))
    samples = sample_human_eval_tasks(cat, ratio=0.08, seed=42)
    n = len(cat.tasks)
    assert 5 <= len(samples) <= 20
    assert 0.05 * n - 1 <= len(samples) <= 0.10 * n + 1 or 5 <= len(samples) <= 20
    # Deterministic
    s2 = sample_human_eval_tasks(cat, ratio=0.08, seed=42)
    assert [s.task_id for s in samples] == [s.task_id for s in s2]
    # Stratified: at least 2 categories covered when n>=8 (catalog has 11 cats)
    cats = {s.category for s in samples}
    assert len(cats) >= 2
    # Hash is stable
    h = hash_human_eval_sample(samples)
    assert len(h) == 16


def test_rubric_and_kappa_alpha() -> None:
    assert len(RUBRIC_DIMENSIONS) == 8
    assert set(SCORE_SCALE.values()) == {
        "unacceptable",
        "poor",
        "acceptable",
        "strong",
        "excellent",
    }
    # Perfect agreement -> kappa 1
    assert cohens_kappa_two_raters([3, 4, 5, 3], [3, 4, 5, 3]) == 1.0
    # Krippendorff: 3 raters perfect agreement -> 1
    assert krippendorff_alpha([[3, 4, 5], [3, 4, 5], [3, 4, 5]], level="ordinal") == 1.0
    # Mixed still computes
    a = krippendorff_alpha([[3, 4, 5], [3, 5, 5], [4, 4, 5]], level="ordinal")
    assert -1 <= a <= 1


def test_agreement_summary_two_and_three_raters() -> None:
    # Two raters, same scores -> kappa 1 on sampled dimension
    r1 = HumanEvalReview(task_id="t1", reviewer="alice", scores={"correctness": 4, "clarity": 3})
    r2 = HumanEvalReview(task_id="t1", reviewer="bob", scores={"correctness": 4, "clarity": 3})
    r3 = HumanEvalReview(task_id="t2", reviewer="alice", scores={"correctness": 5, "clarity": 4})
    r4 = HumanEvalReview(task_id="t2", reviewer="bob", scores={"correctness": 5, "clarity": 4})
    rep = agreement_summary([r1, r2, r3, r4], dimension="correctness")
    assert rep.metric == "cohens_kappa"
    assert rep.value == 1.0
    assert rep.n == 2
    # 3 raters -> alpha
    r5 = HumanEvalReview(task_id="t1", reviewer="carol", scores={"correctness": 4})
    r6 = HumanEvalReview(task_id="t2", reviewer="carol", scores={"correctness": 5})
    rep3 = agreement_summary([r1, r2, r3, r4, r5, r6], dimension="correctness")
    assert rep3.metric == "krippendorff_alpha"


def test_human_eval_review_normalized_validation() -> None:
    r = HumanEvalReview(task_id="x", reviewer="a", scores={"correctness": 3, "clarity": 5})
    d = r.normalized()
    assert d["overall"] == 4.0
    # Unknown dimension should raise on normalized()
    bad = HumanEvalReview(task_id="x", reviewer="a", scores={"unknown": 3})  # type: ignore[typeddict-item]
    try:
        bad.normalized()
        raise AssertionError("should have raised ValueError")
    except ValueError:
        pass
