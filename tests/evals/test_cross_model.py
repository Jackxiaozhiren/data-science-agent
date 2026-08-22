from __future__ import annotations

import os

from dsa_evaluation.cross_model import build_cross_model_matrix


def test_matrix_no_fabrication() -> None:
    m = build_cross_model_matrix()
    by = {r.model_class: r for r in m.records}
    assert "local_small" in by and "frontier" in by
    # No fabrication: open/frontier without keys are NOT RUN / available False
    assert (
        by["open_api"].available is False
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    assert (
        by["frontier"].available is False
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
    # Local is available
    assert by["local_small"].available is True
    assert "NOT RUN" in by["local_small"].reason or by["local_small"].task_success is not None


def test_matrix_with_real_agg_and_frontier() -> None:
    agg = {
        "task_success_rate": 1.0,
        "statistical_accuracy": 1.0,
        "evidence_coverage": 1.0,
        "mean_latency_ms": 42,
        "n": 10,
    }
    m = build_cross_model_matrix(
        {"local_small": agg, "local_medium": agg},
        token_estimates={"local_small": (100, 100), "local_medium": (120, 120)},
    )
    by = {r.model_class: r for r in m.records}
    assert by["local_small"].task_success == 1.0
    assert by["local_medium"].cost_usd is not None
    # frontier exists when at least two points have cost
    assert isinstance(m.frontier_quality_cost, list)
    assert m.cost_model.startswith("stub heuristic")


def test_local_first_is_stub_runnable() -> None:
    m = build_cross_model_matrix()
    local = [r for r in m.records if r.model_class in ("local_small", "local_medium")]
    assert all(r.available for r in local)
    assert "stub" in local[0].provider
