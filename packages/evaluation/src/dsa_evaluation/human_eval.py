from __future__ import annotations

import hashlib
import random
from typing import Any

from pydantic import BaseModel, Field

RUBRIC_DIMENSIONS: list[str] = [
    "correctness",
    "clarity",
    "statistical_validity",
    "evidence_quality",
    "interpretation",
    "uncertainty",
    "actionability",
    "report_quality",
]

SCORE_SCALE: dict[int, str] = {
    1: "unacceptable",
    2: "poor",
    3: "acceptable",
    4: "strong",
    5: "excellent",
}


class HumanEvalSample(BaseModel):
    task_id: str
    category: str
    dataset: str
    question: str
    gold_criteria: str
    sampled_at_seed: int | None = None


class HumanEvalReview(BaseModel):
    task_id: str
    reviewer: str
    scores: dict[str, int] = Field(default_factory=dict)  # dimension -> 1..5
    comments: dict[str, str] = Field(default_factory=dict)
    overall: float | None = None  # mean of scores

    def normalized(self) -> dict[str, Any]:
        # Validates 1..5
        for k, v in self.scores.items():
            if k not in RUBRIC_DIMENSIONS:
                raise ValueError(f"Unknown dimension {k}")
            if v not in SCORE_SCALE:
                raise ValueError(f"Score {v} out of 1..5")
        if self.scores:
            self.overall = round(sum(self.scores.values()) / len(self.scores), 3)
        return {"task_id": self.task_id, "overall": self.overall, "scores": self.scores}


class AgreementReport(BaseModel):
    dimension: str
    metric: str  # "cohens_kappa" | "krippendorff_alpha" | "agreement"
    value: float
    n: int
    ci95: tuple[float, float] | None = None
    notes: str = ""


def sample_human_eval_tasks(
    catalog: Any,  # Catalog or dict
    ratio: float = 0.08,
    seed: int = 42,
    min_n: int = 5,
    max_n: int = 20,
) -> list[HumanEvalSample]:
    """Stratified 5–10% sampling per spec §35.

    - Stratified by category (proportional).
    - Deterministic via seed.
    - Clamped to [min_n, max_n] and 5–10% of total.
    """
    tasks = catalog.tasks if hasattr(catalog, "tasks") else catalog.get("tasks", [])
    n_total = len(tasks)
    # Clamp ratio 0.05..0.10 as per §35
    ratio = max(0.05, min(0.10, ratio))
    n_target = max(min_n, min(max_n, round(n_total * ratio)))
    # Stratified: group by category, round-robin
    by_cat: dict[str, list[Any]] = {}
    for t in tasks:
        cat = t.category if hasattr(t, "category") else t.get("category", "Unknown")
        by_cat.setdefault(cat, []).append(t)
    rng = random.Random(seed)  # noqa: S311 — deterministic sampling seed
    for cat in by_cat:
        rng.shuffle(by_cat[cat])
    # Allocate proportional counts
    cats = sorted(by_cat)
    alloc: dict[str, int] = {}
    for cat in cats:
        alloc[cat] = max(1, round(n_target * len(by_cat[cat]) / n_total)) if n_target else 0
    # Adjust to n_target
    total_alloc = sum(alloc.values())
    while total_alloc < n_target:
        cat = rng.choice(cats)
        if len(by_cat[cat]) > alloc[cat]:
            alloc[cat] += 1
            total_alloc += 1
        else:
            break
    while total_alloc > n_target:
        cat = max(cats, key=lambda c: alloc[c])
        if alloc[cat] > 1:
            alloc[cat] -= 1
            total_alloc -= 1
        else:
            break
    out: list[HumanEvalSample] = []
    for cat in cats:
        for t in by_cat[cat][: alloc[cat]]:
            tid = t.id if hasattr(t, "id") else t.get("id", "")
            question = t.question if hasattr(t, "question") else t.get("question", "")
            ds = t.dataset if hasattr(t, "dataset") else t.get("dataset", "")
            gold = (
                t.gold_method or t.expected_analysis
                if hasattr(t, "gold_method")
                else (t.get("gold_method") or t.get("expected_analysis", ""))
            )
            out.append(
                HumanEvalSample(
                    task_id=tid,
                    category=cat,
                    dataset=ds,
                    question=question,
                    gold_criteria=str(gold or "")[:400],
                    sampled_at_seed=seed,
                )
            )
    # Stable order by task_id
    out.sort(key=lambda s: s.task_id)
    return out


def cohens_kappa_two_raters(scores_a: list[int], scores_b: list[int], k: int = 5) -> float:
    """Unweighted Cohen's Kappa for two raters on k=5 scale (1..k)."""
    if len(scores_a) != len(scores_b) or not scores_a:
        return float("nan")
    n = len(scores_a)
    # Observed agreement
    po = sum(1 for a, b in zip(scores_a, scores_b) if a == b) / n
    # Expected agreement from marginals
    from collections import Counter

    ca = Counter(scores_a)
    cb = Counter(scores_b)
    pe = sum((ca.get(v, 0) / n) * (cb.get(v, 0) / n) for v in range(1, k + 1))
    denom = 1 - pe
    if abs(denom) < 1e-12:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / denom


def krippendorff_alpha(scores_matrix: list[list[int | None]], level: str = "ordinal") -> float:
    """Krippendorff's alpha (ordinal or nominal) for m raters × n items.

    scores_matrix: rows = raters, cols = items. None = missing.
    level: "ordinal" (squared distance) or "nominal" (0/1).
    Reference: Krippendorff 1980; simplified coincident-matrix form.
    """
    # Build pairable values
    # Observed disagreement Do, Expected De via value distribution
    n_raters = len(scores_matrix)
    if n_raters < 2:
        return float("nan")
    n_items = len(scores_matrix[0]) if scores_matrix else 0
    # Collect all pairable distances
    # Do = mean distance over all within-item rater pairs with both values present
    # De = expected distance under independence (from overall value frequencies)
    from collections import Counter

    # Gather values per item pairs and overall frequencies
    pairable: list[tuple[int, int]] = []
    all_vals: list[int] = []
    for j in range(n_items):
        vals: list[int] = [
            int(scores_matrix[i][j]) for i in range(n_raters) if scores_matrix[i][j] is not None
        ]  # type: ignore[arg-type]
        all_vals.extend(vals)
        for a in range(len(vals)):
            for b in range(a + 1, len(vals)):
                va = vals[a]
                vb = vals[b]
                assert va is not None and vb is not None
                pairable.append((va, vb))
    if not pairable:
        return float("nan")

    def _dist(a: int, b: int) -> float:
        if level == "nominal":
            return 0.0 if a == b else 1.0
        return float((a - b) ** 2)

    do = sum(_dist(a, b) for a, b in pairable) / len(pairable)
    # Expected: all unordered pairs from global distribution
    freq = Counter(all_vals)
    total = len(all_vals)
    if total < 2:
        return float("nan")
    # De as population expectation
    pairs: float = 0
    de_sum = 0.0
    uniq = sorted(freq)
    for i, va in enumerate(uniq):
        for vb in uniq[i:]:
            ca = freq[va]
            cb = freq[vb]
            if va == vb:
                cnt = ca * (ca - 1) / 2
            else:
                cnt = ca * cb
            de_sum += cnt * _dist(va, vb)
            pairs += cnt
    if pairs == 0:
        return float("nan")
    de = de_sum / pairs
    if de == 0:
        return 1.0 if do == 0 else 0.0
    return 1 - do / de


def agreement_summary(
    reviews: list[HumanEvalReview],
    dimension: str,
    level: str = "ordinal",
) -> AgreementReport:
    """Summarize agreement for a single rubric dimension across reviewers.

    Expects reviews covering overlapping task_ids. Computes:
    - 2 raters: Cohen's Kappa
    - 3+ raters: Krippendorff's Alpha (ordinal)
    """
    # Group by task_id
    by_task: dict[str, list[HumanEvalReview]] = {}
    for r in reviews:
        by_task.setdefault(r.task_id, []).append(r)
    # Build matrix: rows=reviewers (unique reviewer names), cols=tasks (sorted task_ids)
    reviewers = sorted({r.reviewer for r in reviews})
    task_ids = sorted(by_task)
    if len(reviewers) < 2 or not task_ids:
        return AgreementReport(
            dimension=dimension,
            metric="agreement",
            value=float("nan"),
            n=0,
            notes="need >=2 reviewers and >=1 task",
        )
    r_index = {name: i for i, name in enumerate(reviewers)}
    matrix: list[list[int | None]] = [[None for _ in task_ids] for _ in reviewers]
    for j, tid in enumerate(task_ids):
        for rev in by_task[tid]:
            i = r_index[rev.reviewer]
            matrix[i][j] = rev.scores.get(dimension)
    n_paired = sum(
        1
        for j in range(len(task_ids))
        if sum(1 for i in range(len(reviewers)) if matrix[i][j] is not None) >= 2
    )
    if len(reviewers) == 2:
        a: list[int] = [
            int(matrix[0][j])
            for j in range(len(task_ids))
            if matrix[0][j] is not None and matrix[1][j] is not None
        ]  # type: ignore[arg-type]
        b: list[int] = [
            int(matrix[1][j])
            for j in range(len(task_ids))
            if matrix[0][j] is not None and matrix[1][j] is not None
        ]  # type: ignore[arg-type]
        k = cohens_kappa_two_raters(a, b)
        return AgreementReport(
            dimension=dimension,
            metric="cohens_kappa",
            value=round(k, 3) if k == k else float("nan"),
            n=n_paired,
            notes="Cohen's Kappa (2 raters, k=5)",
        )
    alpha = krippendorff_alpha(matrix, level=level)
    return AgreementReport(
        dimension=dimension,
        metric="krippendorff_alpha",
        value=round(alpha, 3) if alpha == alpha else float("nan"),
        n=n_paired,
        notes=f"Krippendorff's Alpha ({level}, {len(reviewers)} raters)",
    )


def hash_human_eval_sample(samples: list[HumanEvalSample]) -> str:
    payload = "|".join(s.task_id for s in sorted(samples, key=lambda s: s.task_id))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
