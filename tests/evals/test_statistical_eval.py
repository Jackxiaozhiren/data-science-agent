from __future__ import annotations

from dsa_evaluation.catalog import BenchmarkTask, EvaluationCriteria, GroundTruth
from dsa_evaluation.statistical_eval import ERROR_LABELS, evaluate_statistical


def _task(**overrides) -> BenchmarkTask:
    base = dict(
        id="t1",
        category="Statistics",
        dataset="a.csv",
        question="Is x correlated with y?",
        expected_analysis="corr",
        ground_truth=GroundTruth(expected_tool="correlation_analysis"),
        criteria=EvaluationCriteria(task_success=True, statistical_accuracy=True),
        difficulty="medium",
    )
    base.update(overrides)
    return BenchmarkTask(**base)  # type: ignore[arg-type]


def test_dimensions_present() -> None:
    t = _task()
    res = evaluate_statistical(
        t,
        {
            "tool_calls": [
                {
                    "tool": "correlation_analysis",
                    "status": "ok",
                    "output": {
                        "r": 0.5,
                        "p_value": 0.01,
                        "ci_low": 0.1,
                        "ci_high": 0.7,
                        "effect_size": 0.5,
                    },
                }
            ]
        },
    )
    for dim in (
        "method_selection",
        "assumption_validation",
        "test_execution",
        "parameter_estimation",
        "p_value_correctness",
        "ci_correctness",
        "effect_size",
        "interpretation",
        "causal_language",
        "uncertainty_communication",
    ):
        assert dim in res.dimensions
    assert "method_selection" in res.dimensions
    assert res.error_codes == [] or isinstance(res.error_codes, list)
    assert res.overall is not None


def test_causal_flag_s09() -> None:
    t = _task()
    res = evaluate_statistical(
        t,
        {
            "tool_calls": [{"tool": "correlation_analysis", "status": "ok", "output": {"r": 0.3}}],
            "insights": [{"finding": "x causes y"}],
            "report_markdown": "x causes y",
        },
    )
    assert res.causal_flag is True
    assert "S09" in res.error_codes
    assert res.dimensions["causal_language"].passed is False


def test_s10_uncertainty_omission() -> None:
    t = _task()
    res = evaluate_statistical(
        t,
        {
            "tool_calls": [{"tool": "correlation_analysis", "status": "ok", "output": {"r": 0.2}}],
            "insights": [],
        },
    )
    # No uncertainty language and no CI -> S10 on statistical task
    assert "S10" in res.error_codes or res.dimensions["uncertainty_communication"].passed is False


def test_attach_via_metrics() -> None:
    from dsa_evaluation.metrics import attach_statistical_eval, evaluate_task

    t = _task()
    ev = evaluate_task(
        t,
        {
            "tool_calls": [
                {
                    "tool": "correlation_analysis",
                    "status": "ok",
                    "output": {"r": 0.4, "p_value": 0.02},
                }
            ],
            "report_markdown": "ok",
        },
    )
    from dsa_evaluation.statistical_eval import evaluate_statistical as eval2

    stat = eval2(
        t,
        {
            "tool_calls": [
                {
                    "tool": "correlation_analysis",
                    "status": "ok",
                    "output": {"r": 0.4, "p_value": 0.02},
                }
            ]
        },
    )
    out = attach_statistical_eval(ev, stat)
    assert out.details.get("evaluator_version") == "evaluator_v2"
    assert "statistical_eval" in out.details


def test_error_labels_cover_s01_s10() -> None:
    assert set(ERROR_LABELS) == {f"S0{i}" for i in range(1, 10)} | {"S10"}
    assert ERROR_LABELS["S09"] == "Causal Overclaim"


def _ci_call(*pairs: object) -> dict:
    return {
        "tool_calls": [
            {
                "tool": "correlation_analysis",
                "status": "ok",
                "output": {"ci_low": lo, "ci_high": hi},
            }
            for lo, hi in pairs
        ]
    }


def test_a_malformed_ci_is_not_reported_as_no_ci_emitted() -> None:
    """§95: the dimension used to say "no CI emitted" about a CI that was emitted and bad.

    `except Exception: pass` around the float() pair dropped the malformed reading from
    `ci_pairs`, and an empty list then scored as absence -- which is not a missing
    diagnostic but a false statement about what the agent produced.
    """
    res = evaluate_statistical(_task(), _ci_call(("not-a-number", "also-not")))

    dim = res.dimensions["ci_correctness"]
    assert dim.passed is False, dim.reason
    assert dim.reason == "ci invalid", dim.reason
    assert "S05" in dim.error_codes


def test_one_malformed_ci_cannot_hide_behind_a_valid_one() -> None:
    """The sharper case: with a good pair present the old code reported *pass*."""
    res = evaluate_statistical(_task(), _ci_call((0.1, 0.7), ("nan-text", 0.9)))

    dim = res.dimensions["ci_correctness"]
    assert dim.passed is False, f"a garbage CI was averaged away: {dim.reason}"


def test_a_well_formed_ci_still_passes() -> None:
    """Guard against over-correcting: this is the behaviour the fix must not disturb."""
    res = evaluate_statistical(_task(), _ci_call((0.1, 0.7)))

    dim = res.dimensions["ci_correctness"]
    assert dim.passed is True, dim.reason
    assert dim.reason == "ci valid"


def test_absent_ci_still_reads_as_absent() -> None:
    """The distinction the fix is built on: absence and malformed are different answers."""
    res = evaluate_statistical(
        _task(),
        {"tool_calls": [{"tool": "correlation_analysis", "status": "ok", "output": {"r": 0.4}}]},
    )

    dim = res.dimensions["ci_correctness"]
    assert dim.passed is None
    assert dim.reason == "no CI emitted"
