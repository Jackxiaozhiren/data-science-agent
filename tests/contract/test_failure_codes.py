"""ADR-004 D2 — the failure vocabulary is closed, and the runtime writes only members of it.

The ADR allows a failure to carry a location and forbids it carrying a diagnosis. That distinction
is only real if two things hold, and this file checks both:

* every value the runtime writes is a member of the enumeration, found by reading ``graph.py``
  rather than by trusting the import (the agent package deliberately does not import the evaluator's
  enum, so a mismatch cannot surface as an ImportError);
* a value outside the set is refused by ``assert_known``, so the adapter that fills the record can
  fail loudly instead of writing a plausible string.

The negative control below is the point: a field that exists with a null or an unlisted value is not
a placed failure, and the reading must not count it as one.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from dsa_agent.state import AnalysisState, AnalysisStatus
from dsa_evaluation.failure_codes import (
    CODED_STAGES,
    TERMINAL_STAGES,
    FailureCode,
    FailureStage,
    assert_known,
    last_execution_stage,
)
from scripts import measure_attribution as attribution

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "packages/agent/src/dsa_agent/graph.py"
ADAPTER = ROOT / "benchmarks/external/datascibench/adapter.py"


def _codes() -> set[str]:
    return {member.value for member in FailureCode}


def test_the_vocabulary_has_no_duplicate_and_no_terminal_stage() -> None:
    assert len(_codes()) == len(list(FailureCode))
    assert len(CODED_STAGES) == len(list(FailureStage))
    # A terminal status says the run ended, not where it was; allowing one into the vocabulary would
    # let "failed" be reported as a location.
    assert not (CODED_STAGES & TERMINAL_STAGES)


def test_every_code_written_by_the_runtime_is_in_the_vocabulary() -> None:
    tree = ast.parse(GRAPH.read_text(encoding="utf-8"))
    written: set[str] = set()
    stages: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue  # the delivered branch clears both fields with None
        for target in node.targets:
            if not isinstance(target, ast.Attribute):
                continue
            if target.attr == "failure_code":
                written.add(str(node.value.value))
            elif target.attr == "failure_stage":
                stages.add(str(node.value.value))
    assert written, "run_analysis writes no failure_code at all"
    assert stages, "run_analysis writes no failure_stage at all"
    assert not written - _codes(), f"codes outside the vocabulary: {sorted(written - _codes())}"
    assert not stages - CODED_STAGES, (
        f"stages outside the vocabulary: {sorted(stages - CODED_STAGES)}"
    )


def test_the_adapter_names_only_vocabulary_members() -> None:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    written: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "value":
            owner = node.value
            if isinstance(owner, ast.Attribute) and isinstance(owner.value, ast.Name):
                if owner.value.id == "FailureCode":
                    written.add(owner.attr.lower())
    # Attribute names are upper case; the values are the strings the record receives.
    assert written, "the adapter never assigns a FailureCode"
    assert all(name.upper() in {member.name for member in FailureCode} for name in written), written


@pytest.mark.parametrize(
    ("stage", "code"),
    [
        ("analysis", "run_not_completed"),
        ("evaluation", "score_below_threshold"),
        ("unrecorded", "stage_unrecorded"),
    ],
)
def test_a_member_of_each_set_is_accepted(stage: str, code: str) -> None:
    assert_known(stage, code)


@pytest.mark.parametrize(
    ("stage", "code"),
    [("analysis", "oom"), ("wherever", "run_not_completed"), ("completed", "run_not_completed")],
)
def test_a_value_outside_the_set_is_refused(stage: str, code: str) -> None:
    with pytest.raises(ValueError):
        assert_known(stage, code)


def test_last_execution_stage_skips_terminal_markers_and_unrecorded_runs() -> None:
    assert last_execution_stage([]) == FailureStage.UNRECORDED.value
    assert last_execution_stage(None) == FailureStage.UNRECORDED.value
    assert (
        last_execution_stage([{"stage": "planning"}, {"stage": "reporting"}, {"stage": "failed"}])
        == "reporting"
    )
    # An interval whose name nobody enumerated is not a location either.
    assert last_execution_stage([{"stage": "warmup"}]) == FailureStage.UNRECORDED.value


def test_enter_stage_closes_the_interval_it_leaves() -> None:
    state = AnalysisState(run_id="run-probe", dataset_id="ds", user_query="q")
    assert state.stage_timings == []
    state.enter_stage(AnalysisStatus.UNDERSTANDING)
    state.enter_stage(AnalysisStatus.PLANNING)
    assert [entry.stage for entry in state.stage_timings] == ["understanding", "planning"]
    assert state.stage_timings[0].left_at is not None
    assert state.stage_timings[1].left_at is None
    state.close_stage()
    assert all(entry.duration_ms is not None for entry in state.stage_timings)
    assert state.status is AnalysisStatus.PLANNING


def test_a_blank_or_unlisted_code_does_not_count_as_a_location() -> None:
    """The negative control: the reading counts vocabulary members, not the presence of a key."""
    vocabulary = {
        "stages": sorted(CODED_STAGES),
        "codes": sorted(member.value for member in FailureCode),
    }
    good = {"failure_stage": "evaluation", "failure_code": "score_below_threshold"}
    assert len(attribution._codes_present(good, vocabulary)) == 2
    # D2's wording is "a stage *or* a cause code", so one valid member is a placed failure.
    assert attribution._codes_present({"failure_stage": "evaluation"}, vocabulary)
    assert attribution._codes_present({"failure_code": "score_below_threshold"}, vocabulary)
    # What does not count is a key that exists with nothing the vocabulary owns behind it.
    for spoiled in (
        {"failure_stage": None, "failure_code": None},
        {"failure_stage": "", "failure_code": ""},
        {"failure_stage": "somewhere", "failure_code": "because_it_was_wrong"},
        {},
    ):
        assert attribution._codes_present(spoiled, vocabulary) == [], spoiled


def test_an_empty_stage_list_is_not_a_boundary() -> None:
    assert attribution._stages_recorded({"stage_timings": []}) == []
    assert attribution._stages_recorded({"stage_timings": [{"stage": "analysis"}]}) == [
        "stage_timings"
    ]
