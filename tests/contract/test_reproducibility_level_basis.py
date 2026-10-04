"""§102: the reproducibility score must say *how* each level decided.

`compare_runs` was written for the record `dsa_evidence.repro.build_experiment_json` produces -- that
payload carries `dataset_sha256` and `environment`. Its only shipped caller, `dsa_evaluation.cli`'s
reproduction harness, passes `run_result` dicts, i.e. `AnalysisState.model_dump()`, which has neither
field. Measured on the shipped shapes:

    AnalysisState dump  -> "dataset_sha256" in record: False, "environment" in record: False
    L2_same_data: True  (decided by `dataset_id` equality, not by any hash)
    L3_same_env:  True  (decided by the lenient `else True` branch, no environment was compared)

Two runs over two different byte-contents of the same dataset id therefore report `L2_same_data: True`
-- and `comparison.json`'s own `method` string advertises "L2 data hash, L3 env". The comparator is
fine (fed the experiment-record shape it detects a changed hash and a changed interpreter); the level
results were just untraceable to their basis. These tests pin the basis into `details` so a reader of
the artifact can tell a real check from a lenient pass.
"""

from __future__ import annotations

from typing import Any

from dsa_evidence.reproducibility import compare_runs

#: Field names as they appear in an `AnalysisState.model_dump()` -- what the harness really passes.
STATE_SHAPE = {
    "run_id": "r1",
    "dataset_id": "sales",
    "dataset_path": "benchmarks/v2/datasets/sales.csv",
    "user_query": "what sold",
    "tool_calls": [],
    "insights": [],
    "evidence": [],
}


#: Field names as `build_experiment_json` writes them -- the shape `compare_runs` was designed for.
def experiment_shape(sha: str, python_version: str) -> dict[str, Any]:
    return {
        "user_query": "what sold",
        "dataset_path": "benchmarks/v2/datasets/sales.csv",
        "dataset_sha256": sha,
        "environment": {"python_version": python_version, "platform": "macOS"},
        "tool_calls": [],
        "insights": [],
        "evidence": [],
    }


def test_l2_names_the_equality_that_decided_it() -> None:
    details = compare_runs(dict(STATE_SHAPE), dict(STATE_SHAPE)).details

    assert details["L2_same_data"] is True
    assert details["L2_basis"] == "dataset_id", (
        "no hash was in either record, so a caller must be able to see that id equality decided it"
    )


def test_l3_names_the_branch_that_decided_it() -> None:
    details = compare_runs(dict(STATE_SHAPE), dict(STATE_SHAPE)).details

    assert details["L3_same_env"] is True
    assert details["L3_basis"] == "no_environment_in_either_record", (
        "the lenient branch passed the level without comparing any environment"
    )


def test_l1_admits_that_no_code_identity_was_compared() -> None:
    """L1 has always been a hard pass; the label said 'same code', so the basis says what it is."""
    details = compare_runs(dict(STATE_SHAPE), dict(STATE_SHAPE)).details

    assert details["L1_same_code"] is True
    assert details["L1_basis"] == "lenient_no_code_identity_is_compared"


def test_a_changed_hash_still_fails_l2_and_says_which_hash_side_differed() -> None:
    score = compare_runs(experiment_shape("a" * 64, "3.12"), experiment_shape("b" * 64, "3.12"))

    assert score.details["L2_same_data"] is False
    assert score.details["L2_basis"] == "dataset_sha256"
    assert score.dataset_sha256_match is False


def test_a_matching_hash_pair_is_reported_as_a_real_check() -> None:
    score = compare_runs(experiment_shape("a" * 64, "3.12"), experiment_shape("a" * 64, "3.12"))

    assert score.details["L2_same_data"] is True
    assert score.details["L2_basis"] == "dataset_sha256"
    assert score.dataset_sha256_match is True


def test_a_changed_interpreter_fails_l3_and_says_it_compared() -> None:
    score = compare_runs(experiment_shape("a" * 64, "3.12"), experiment_shape("a" * 64, "4.0"))

    assert score.details["L3_same_env"] is False
    assert score.details["L3_basis"] == "environment.python_version"


def test_one_record_without_a_hash_is_not_reported_as_a_hash_mismatch() -> None:
    mixed = dict(STATE_SHAPE)
    scored = compare_runs(mixed, experiment_shape("a" * 64, "3.12"))

    assert scored.details["L2_same_data"] is False
    assert scored.details["L2_basis"] == "one_record_carries_no_hash"
    assert scored.dataset_sha256_match is None, (
        "the field names a sha comparison; nothing was compared, so it must not claim either answer"
    )


def test_the_harness_shape_cannot_detect_changed_bytes_and_records_that() -> None:
    """The defect, pinned: same `dataset_id` over different bytes passes L2 -- visibly now."""
    left = dict(STATE_SHAPE)
    right = dict(STATE_SHAPE)  # same id and path, but the file behind it changed between the runs

    score = compare_runs(left, right)

    assert score.details["L2_same_data"] is True
    assert score.details["L2_basis"] == "dataset_id", (
        "L2 passing here is id equality, not evidence that the bytes matched"
    )
    assert score.dataset_sha256_match is None, (
        "no sha was available on either side, so a sha match cannot be claimed"
    )


def test_l5_says_whether_any_conclusion_content_was_compared() -> None:
    empty = compare_runs(dict(STATE_SHAPE), dict(STATE_SHAPE))
    assert empty.details["L5_same_conclusion"] is True
    assert empty.details["L5_basis"] == "no_insights_or_evidence_in_either_record"

    filled = dict(STATE_SHAPE, insights=[{"finding": "x"}], evidence=[{"claim": "y"}])
    both = compare_runs(filled, dict(filled))
    assert both.details["L5_basis"] == "insight_and_evidence_counts"


def _old_l2(original: dict[str, Any], fresh: dict[str, Any]) -> bool:
    """`same_data` exactly as it was computed before §102."""
    o_sha = original.get("dataset_sha256") or (
        original.get("evidence_graph", {}).get("dataset_sha256")
        if isinstance(original.get("evidence_graph"), dict)
        else None
    )
    f_sha = fresh.get("dataset_sha256") or (
        fresh.get("evidence_graph", {}).get("dataset_sha256")
        if isinstance(fresh.get("evidence_graph"), dict)
        else None
    )
    same_data = bool(o_sha and f_sha and o_sha == f_sha)
    if o_sha is None and f_sha is None:
        same_data = original.get("dataset_id") == fresh.get("dataset_id")
    return same_data


def _old_l3(original: dict[str, Any], fresh: dict[str, Any]) -> bool:
    """`same_env` exactly as it was computed before §102."""
    o_env = original.get("environment") or {}
    f_env = fresh.get("environment") or {}
    return (
        o_env.get("python_version", "")[:20] == f_env.get("python_version", "")[:20]
        if o_env or f_env
        else True
    )


def test_naming_the_basis_did_not_move_any_level_value() -> None:
    """The regression pin: for every shape pair, the booleans are what the old formulas produced."""
    cases = [
        (dict(STATE_SHAPE), dict(STATE_SHAPE)),
        (dict(STATE_SHAPE), experiment_shape("a" * 64, "3.12")),
        (experiment_shape("a" * 64, "3.12"), dict(STATE_SHAPE)),
        (experiment_shape("a" * 64, "3.12"), experiment_shape("a" * 64, "3.12")),
        (experiment_shape("a" * 64, "3.12"), experiment_shape("b" * 64, "3.12")),
        (experiment_shape("a" * 64, "3.12"), experiment_shape("a" * 64, "4.0")),
        ({"evidence_graph": {"dataset_sha256": "a"}}, {"evidence_graph": {"dataset_sha256": "b"}}),
        ({"evidence_graph": {"dataset_sha256": "a"}}, {"evidence_graph": {"dataset_sha256": "a"}}),
    ]

    for original, fresh in cases:
        details = compare_runs(original, fresh).details
        assert details["L2_same_data"] == _old_l2(original, fresh), (original, fresh)
        assert details["L3_same_env"] == _old_l3(original, fresh), (original, fresh)
