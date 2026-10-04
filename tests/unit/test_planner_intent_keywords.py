"""§99 D-L3-12: `"ate"` is an acronym in a list of stems, so it matched inside words.

`heuristics_plan` reads intent from keyword lists, and substring matching is the deliberate
convention there -- `classif`, `correlat`, `visual`, `predict` are stems, chosen so
"classification"/"classifier" and "correlated"/"correlation" all land. One entry is not a stem:
`wants_causal` carries `"ate"`, meaning ATE, average treatment effect. Tested with the same
`k in q`, it matches *create*, *validate*, *duplicates*, *regenerate*, *estimate*, *calculate*,
*state* -- measured across the shipped catalogs, 35 of 150 queries contain `ate` only inside a
longer word, and 33 of them were being handed a `causal_check` step their question never asked for.

A causal claim in the report is the most consequential wrong step this agent can take (the critic
lane treats causal overclaim as an S09 error), so an acronym matching as a substring is not a
cosmetic keyword bug.
"""

from __future__ import annotations

import pytest

from dsa_agent.planner import heuristics_plan

COLS = ["region", "revenue", "campaign", "value", "label", "group"]


def _tools(query: str) -> list[str]:
    return [step.tool for step in heuristics_plan(query, None, COLS).steps]


@pytest.mark.parametrize(
    "query",
    [
        "correlate label with group",
        "create a histogram of revenue",
        "validate that no revenue values are negative",
        "regenerate the report chart",
        "estimate the total revenue by region",
        "calculate the average value",
    ],
)
def test_a_word_containing_ate_is_not_a_causal_request(query: str) -> None:
    tools = _tools(query)
    assert "causal_check" not in tools, f"{query!r} was planned as causal: {tools}"


def test_a_real_causal_request_still_is_causal() -> None:
    tools = _tools("what is the average treatment effect of campaign on revenue")
    assert "causal_check" in tools, tools


def test_the_acronym_still_works_when_written_as_a_word() -> None:
    """Word-bounded, not deleted: someone asking for the ATE must still get the step."""
    tools = _tools("what is the ATE of campaign on revenue")
    assert "causal_check" in tools, tools


def test_stem_matching_is_still_the_convention_elsewhere() -> None:
    """The fix must not "correct" the stems -- that matching is deliberate and load-bearing."""
    assert "train_model" in _tools("classify label and report accuracy")
    assert "correlation_analysis" in _tools("are value and revenue correlated?")
    assert "create_chart" in _tools("visualise the distribution of revenue")
