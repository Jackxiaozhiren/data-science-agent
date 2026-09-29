"""Budget.max_steps must actually stop execution.

The field existed with one reference in the whole tree -- its own declaration at
``state.py:95`` -- while SECURITY.md, docs/architecture.md, docs/agent-system.md,
docs/portfolio/PROJECT_SUMMARY.md, research/paper/paper.md and the frozen run payloads all
stated it was enforced. ``max_tool_calls`` and ``max_retries`` were read in graph.py; nothing
ever read ``max_steps``, so a 200-step plan simply executed 200 steps.

Enforcement has to hold on **both** execution paths, or the claim is only half true: the
sequential loop and the leading-independent-batch ``gather`` (which fires whenever more than
one step is in ``_PARALLEL_TOOLS`` and the whole batch fits the tool-call budget).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from dsa_agent import graph
from dsa_agent.state import AnalysisPlan, AnalysisState, AnalysisStatus, AnalysisStep


def _csv(tmp_path: Path) -> Path:
    p = tmp_path / "s.csv"
    pl.DataFrame(
        {
            "a": [1, 2, 3, 4, 5, 6, 7, 8],
            "b": [2, 4, 6, 8, 10, 12, 14, 16],
            "g": ["x", "x", "y", "y", "x", "y", "x", "y"],
        }
    ).write_csv(p)
    return p


def _steps(tool: str, n: int, inputs: dict) -> list[AnalysisStep]:
    return [
        AnalysisStep(
            id=f"S-{i}",
            name=f"{tool} {i}",
            description=f"{tool} #{i}",
            tool=tool,
            inputs=dict(inputs),
        )
        for i in range(n)
    ]


def _patch_plan(monkeypatch: pytest.MonkeyPatch, steps: list[AnalysisStep]) -> None:
    async def _fake_plan(_query: str, _path: str | None, _cols: list[str]) -> AnalysisPlan:
        return AnalysisPlan(objective="bounded run", steps=steps)

    monkeypatch.setattr(graph, "plan_analysis", _fake_plan)


@pytest.mark.asyncio
async def test_sequential_path_stops_at_max_steps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """21 sequential steps, max_steps 20, tool budget 40 -> only the step limit can bind."""
    from dsa_tools import bootstrap

    bootstrap()
    path = _csv(tmp_path)
    _patch_plan(monkeypatch, _steps("profile_dataset", 21, {"path": str(path)}))

    state = await graph.run_analysis(str(path), "ds", "profile it")

    assert state.budget.max_steps == 20
    assert len(state.tool_calls) == 20, (
        f"expected exactly max_steps executions, saw {len(state.tool_calls)}"
    )
    assert state.status == AnalysisStatus.FAILED
    assert state.error and "step" in state.error.lower(), state.error


@pytest.mark.asyncio
async def test_parallel_batch_path_stops_at_max_steps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The gather branch must not execute a whole over-budget batch at once."""
    from dsa_tools import bootstrap

    bootstrap()
    path = _csv(tmp_path)
    _patch_plan(
        monkeypatch, _steps("correlation_analysis", 21, {"x": "a", "y": "b", "path": str(path)})
    )

    state = await graph.run_analysis(str(path), "ds", "correlate a and b")

    assert len(state.tool_calls) <= state.budget.max_steps, (
        f"parallel batch blew past the step budget: {len(state.tool_calls)}"
    )
    assert state.status == AnalysisStatus.FAILED
    assert state.error and "step" in state.error.lower(), state.error


@pytest.mark.asyncio
async def test_plan_within_step_budget_is_not_truncated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Guard against over-triggering: 5 steps under a limit of 20 must all run."""
    from dsa_tools import bootstrap

    bootstrap()
    path = _csv(tmp_path)
    _patch_plan(monkeypatch, _steps("profile_dataset", 5, {"path": str(path)}))

    state = await graph.run_analysis(str(path), "ds", "profile it")

    assert len(state.tool_calls) == 5, len(state.tool_calls)
    assert state.error != "Step budget exceeded"
    assert state.status != AnalysisStatus.FAILED or (
        state.error and "step" not in state.error.lower()
    ), "a within-budget run must not be failed by the step guard"


def test_negative_control_the_knob_is_actually_read() -> None:
    """D-L7-01's premise was zero readers. If that returns, tests above are theatre.

    Counted through the AST so a comment, a string or a doc mentioning ``max_steps`` cannot
    satisfy it -- the original defect was precisely a field that appeared in prose everywhere
    and in code nowhere.
    """
    import ast

    tree = ast.parse(Path("packages/agent/src/dsa_agent/graph.py").read_text(encoding="utf-8"))
    reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "max_steps"
    ]
    assert reads, "nothing in the engine reads budget.max_steps again -- enforcement is gone"
