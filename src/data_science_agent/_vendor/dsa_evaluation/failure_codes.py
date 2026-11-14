"""The closed vocabulary a non-passing run may name its location with.

ADR-004 D2: a failure carries a location, never a diagnosis. The distinction is enforced here rather
than in prose — every member names a place in this tree that decided the outcome, and a value outside
these two enumerations is refused by :func:`assert_known` before it can enter a record.

Why closed at all: an open string field collects whatever a later author finds convenient ("oom",
"bad data", "model was weak"), and those are diagnoses. A closed set makes the honest answer for an
unrecorded location — ``unrecorded`` — cheaper to write than an invention.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

__all__ = [
    "CODED_STAGES",
    "TERMINAL_STAGES",
    "FailureCode",
    "FailureStage",
    "assert_known",
    "last_execution_stage",
]


class FailureStage(str, Enum):
    """Where a run stopped being able to produce a passing result.

    The first eight mirror :class:`dsa_agent.state.AnalysisStatus`; ``evaluation`` and ``adapter``
    are the two stages that exist only outside the agent, and ``unrecorded`` is the honest value for
    a run whose own record carries no interval.
    """

    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    DATA_PROFILING = "data_profiling"
    ANALYSIS = "analysis"
    MODELING = "modeling"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"
    REPORTING = "reporting"
    EVALUATION = "evaluation"
    ADAPTER = "adapter"
    UNRECORDED = "unrecorded"


class FailureCode(str, Enum):
    """One code per place in this tree that can decide a run did not pass.

    The docstring of each member quotes the line of code the code points at. A member without such
    a place does not belong here: that is what separates a location from a guess.
    """

    #: ``run_analysis`` reached a terminal status other than COMPLETED.
    RUN_NOT_COMPLETED = "run_not_completed"
    #: the ``max_tool_calls`` guard in ``run_analysis`` set FAILED.
    TOOL_BUDGET_EXCEEDED = "tool_budget_exceeded"
    #: the ``max_steps`` guard in ``run_analysis`` set FAILED.
    STEP_BUDGET_EXCEEDED = "step_budget_exceeded"
    #: ``write_report_artifacts`` raised, so the run had nothing to deliver.
    REPORT_NOT_PERSISTED = "report_not_persisted"
    #: the critic recorded a failure on one of ``HARD_FAIL_CHECKS``.
    VALIDATION_HARD_FAIL = "validation_hard_fail"
    #: ``DataSciBenchAdapter.run_task`` reported the task outside this adapter's scope.
    SKIPPED_UNSUPPORTED = "skipped_unsupported"
    #: ``DataSciBenchAdapter.run_task`` caught an exception from the runner.
    ADAPTER_EXECUTION_ERROR = "adapter_execution_error"
    #: the run completed but produced no report text.
    EMPTY_REPORT = "empty_report"
    #: the run completed but recorded no tool call.
    NO_TOOL_CALLS = "no_tool_calls"
    #: the run completed but recorded no evidence.
    NO_EVIDENCE = "no_evidence"
    #: the evaluator returned a score below the adapter's own threshold.
    SCORE_BELOW_THRESHOLD = "score_below_threshold"
    #: the evaluator returned no score at all, so nothing here may call it a near miss.
    EVALUATOR_RETURNED_NO_SCORE = "evaluator_returned_no_score"
    #: the run did not complete and its record carries no interval to place it.
    STAGE_UNRECORDED = "stage_unrecorded"


#: The stages a run can occupy; every member is a location.
CODED_STAGES = frozenset(stage.value for stage in FailureStage)

#: Statuses that say the run ended rather than where it was. ``last_execution_stage`` skips them.
TERMINAL_STAGES = frozenset({"completed", "failed", "human_review"})


def assert_known(stage: str, code: str) -> None:
    """Refuse a stage or code outside the closed set.

    Called by the adapter that writes the fields and by the test that enumerates them, so a value
    added in one place and not the other fails loudly instead of entering a record.
    """
    if stage not in CODED_STAGES:
        raise ValueError(f"failure_stage {stage!r} is not in the closed vocabulary")
    if code not in {member.value for member in FailureCode}:
        raise ValueError(f"failure_code {code!r} is not in the closed vocabulary")


def last_execution_stage(stage_timings: Any) -> str:
    """The last interval a run occupied that names a place, or ``unrecorded``.

    ``stage_timings`` is the run record's own list of ``{stage, ...}`` mappings. A run that never
    entered a stage, or whose last intervals are terminal markers, gets the honest value instead of
    a plausible one: placing an unrecorded failure at ``analysis`` would be a diagnosis dressed as a
    location.
    """
    if not isinstance(stage_timings, list):
        return FailureStage.UNRECORDED.value
    for entry in reversed(stage_timings):
        name = entry.get("stage") if isinstance(entry, dict) else getattr(entry, "stage", None)
        if isinstance(name, str) and name in CODED_STAGES and name not in TERMINAL_STAGES:
            return name
    return FailureStage.UNRECORDED.value
