"""L8: after LangGraph crossed to major 1 (langgraph 1.2.x, langgraph-checkpoint 4.2.x),
does any guard prove the new shape — or only that the call returned?

``tests/unit/test_langgraph.py`` asserted ``status in ("COMPLETED", "FAILED")`` and
``len(tool_calls) >= 1``. Both hold when LangGraph is not the engine that answered:
``run_analysis_langgraph`` catches *any* exception from ``graph.ainvoke`` and re-runs the
non-LangGraph engine, appending a ``langgraph_fallback`` validation result. With the tool
registry empty the existing assertions still passed, which is the vacuous-guard signature
this lane exists to catch — a green test that cannot tell the two engines apart.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest


def _dataset(tmp: Path) -> Path:
    p = tmp / "t.csv"
    pl.DataFrame({"a": [1, 2, 3, 4, 5, 6], "b": [2, 4, 6, 8, 10, 12]}).write_csv(p)
    return p


@pytest.mark.asyncio
async def test_langgraph_engine_actually_serves_the_run() -> None:
    """The LangGraph path must answer, not hand off to the legacy engine."""
    from dsa_agent.langgraph_graph import run_analysis_langgraph
    from dsa_tools import bootstrap

    bootstrap()
    with tempfile.TemporaryDirectory() as td:
        state = await run_analysis_langgraph(
            dataset_path=str(_dataset(Path(td))),
            dataset_id="ds",
            user_query="Analyze correlation between a and b",
        )
    silent = [r for r in state.validation_results if r.check == "langgraph_fallback"]
    assert not silent, (
        "LangGraph did not serve this run — the legacy engine answered instead: "
        f"{[r.message for r in silent]}"
    )
    assert state.status.value == "COMPLETED", state.status.value
    assert len(state.tool_calls) >= 1


@pytest.mark.asyncio
async def test_checkpointer_shape_still_persists_thread_state() -> None:
    """langgraph-checkpoint 4.x must still return readable state for a thread_id.

    The docs sell MemorySaver checkpoints as enabling pause/resume/replay/fork. This
    guards the half of that claim that is real: state is written and readable through
    ``get_state`` on the graph that produced it.
    """
    from dsa_agent.langgraph_graph import build_graph
    from dsa_tools import bootstrap

    bootstrap()
    with tempfile.TemporaryDirectory() as td:
        cfg = {"configurable": {"thread_id": "guard-thread"}}
        graph = build_graph(checkpoint=True)
        await graph.ainvoke(
            {
                "dataset_path": str(_dataset(Path(td))),
                "dataset_id": "ds",
                "user_query": "Analyze correlation between a and b",
                "run_id": "guard-thread",
                "analysis_state": {},
                "step_index": 0,
                "retry_count": 0,
            },
            config=cfg,
        )
        snapshot = graph.get_state(cfg)
        assert snapshot.values, "the checkpointer kept nothing for the thread it just ran"
        assert "step_index" in snapshot.values, (
            f"state shape changed under the checkpoint major: {sorted(snapshot.values)}"
        )
