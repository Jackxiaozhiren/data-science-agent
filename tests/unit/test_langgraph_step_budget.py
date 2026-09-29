"""The LangGraph variant must honour the same step budget as the shipped engine.

``LGState`` carried no ``budget`` key at all and ``_route_after_step`` looped purely on
``idx < len(plan)``, so wiring ``max_steps`` into ``graph.py`` alone would have left the claim
"tool budgets enforced" true for one engine and false for the other -- the exact half-truth
this lane keeps uncovering. The router is a pure dict-in/string-out function, so this is
behaviour, not text, under test.
"""

from __future__ import annotations

from dsa_agent.langgraph_graph import _route_after_step
from dsa_agent.state import Budget


def _plan(n: int) -> list[dict[str, object]]:
    return [{"id": f"S-{i}", "tool": "correlation_analysis"} for i in range(n)]


def test_router_stops_at_the_step_budget_not_the_plan_length() -> None:
    state = {"plan": _plan(25), "step_index": 20}
    assert _route_after_step(state) == "critic", (
        "a plan longer than the step budget still routed back into exec_step"
    )


def test_router_continues_below_the_step_budget() -> None:
    assert _route_after_step({"plan": _plan(25), "step_index": 3}) == "exec_step"


def test_router_finishes_normally_when_the_plan_is_exhausted() -> None:
    assert _route_after_step({"plan": _plan(5), "step_index": 5}) == "critic"


def test_router_reads_the_budget_knob_not_a_hardcoded_twenty() -> None:
    """Proves the limit comes from state.budget, which is what makes the knob a knob."""
    state = {"plan": _plan(25), "step_index": 2, "budget": Budget(max_steps=2)}
    assert _route_after_step(state) == "critic", "an explicit smaller budget was ignored"
