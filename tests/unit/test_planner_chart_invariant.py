"""§107: the planner's "always produce an evidence chart" rule is an invariant, not a tautology.

`planner.py` computed `wants_viz` from keywords and then wrote ``if wants_viz or True:`` -- a condition
that cannot be false, so the signal was decorative and the rule invisible. Measured against the shipped
v2 catalog: 100 tasks, 13 queries naming a visualization, 0 plans without a chart, and honouring the
keyword would remove the chart from **87 of 100** plans. So the unconditional chart is the product rule
(every analysis carries at least one evidence chart); what was missing is a check that says so.

These tests make the rule explicit twice: the dead keyword must not come back, and the invariant must
hold across the whole catalog. The invariant itself passes before and after the cleanup -- it is labelled
green-on-arrival -- and the pin that drives the change is the AST check for the unused signal.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from dsa_agent.graph import _get_columns
from dsa_agent.planner import heuristics_plan

ROOT = Path(__file__).resolve().parents[2]
PLANNER = ROOT / "packages/agent/src/dsa_agent/planner.py"
CATALOG = ROOT / "benchmarks/v2/catalog.json"

#: Keywords the planner once matched on. Kept here so the dead signal stays dead on purpose.
VIZ_KEYWORDS = ("chart", "plot", "visual", "histogram", "scatter", "heatmap")


def _catalog_tasks() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    tasks = data["tasks"] if isinstance(data, dict) and "tasks" in data else data
    assert tasks, "the v2 catalog must have tasks for this invariant to mean anything"
    return tasks


def test_the_planner_has_no_unused_visualization_signal() -> None:
    """The red-first pin: `wants_viz` existed but could not influence the plan."""
    tree = ast.parse(PLANNER.read_text(encoding="utf-8"))
    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    loaded = {
        n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
    }

    assert "wants_viz" not in assigned, (
        "either the keyword signal must decide something, or the always-chart rule must be stated as "
        "the invariant it is -- a computed value feeding `or True` is neither"
    )
    assert "wants_viz" not in loaded


def test_no_condition_in_the_planner_can_only_be_true() -> None:
    """`X or True` / `X and False` hide a rule behind a tautology; none may survive here."""
    tree = ast.parse(PLANNER.read_text(encoding="utf-8"))
    offenders: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp):
            continue
        constants = [v.value for v in node.values if isinstance(v, ast.Constant)]
        if (isinstance(node.op, ast.Or) and True in constants) or (
            isinstance(node.op, ast.And) and False in constants
        ):
            offenders.append(node.lineno)

    assert not offenders, f"tautological conditions at lines {offenders}"


def test_every_plan_carries_an_evidence_chart() -> None:
    """Green-on-arrival: the rule the `or True` was secretly protecting, now asserted."""
    for task in _catalog_tasks():
        plan = heuristics_plan(
            task.get("question", ""),
            f"benchmarks/v2/datasets/{task.get('dataset')}",
            _get_columns(f"benchmarks/v2/datasets/{task.get('dataset')}"),
        )
        tools = [step.tool for step in plan.steps]
        assert "create_chart" in tools, task.get("id")


def test_a_query_that_never_mentions_a_chart_still_gets_one() -> None:
    """The case the dead keyword would have dropped: 87 of 100 catalog tasks look like this."""
    plain = "compare average revenue between regions"
    assert not any(k in plain for k in VIZ_KEYWORDS)

    plan = heuristics_plan(plain, None, ["region", "revenue"])

    assert "create_chart" in [step.tool for step in plan.steps]
