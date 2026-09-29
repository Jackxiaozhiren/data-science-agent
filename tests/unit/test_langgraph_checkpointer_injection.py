"""A retained checkpointer must be injectable, or "pause/resume/replay/fork" is prose.

Measured before this: `build_graph()` constructs ``MemorySaver()`` inside itself and never
returns or stores it, so after a run ``get_state`` on *the same* graph returned 12 state keys
while a *second* ``build_graph()`` on the identical ``thread_id`` returned 0. Seven documents
describe MemorySaver checkpoints as enabling pause/resume/replay/fork; with no way to retain the
saver, no caller could perform any of them.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from dsa_agent.langgraph_graph import build_graph


def _csv(tmp_path: Path) -> Path:
    p = tmp_path / "t.csv"
    pl.DataFrame({"a": [1, 2, 3, 4, 5, 6], "b": [2, 4, 6, 8, 10, 12]}).write_csv(p)
    return p


def _payload(path: Path, run_id: str) -> dict[str, object]:
    return {
        "dataset_path": str(path),
        "dataset_id": "ds",
        "user_query": "Analyze correlation between a and b",
        "run_id": run_id,
        "analysis_state": {},
        "step_index": 0,
        "retry_count": 0,
    }


def test_build_graph_accepts_an_injected_checkpointer() -> None:
    """The seam itself: a caller must be able to hand in the saver it keeps."""
    from langgraph.checkpoint.memory import MemorySaver
    from dsa_tools import bootstrap

    bootstrap()
    saver = MemorySaver()
    graph = build_graph(checkpoint=True, checkpointer=saver)
    assert graph is not None
    assert "ainvoke" in dir(graph)


@pytest.mark.asyncio
async def test_state_written_by_one_graph_is_visible_to_the_next_with_a_shared_saver(
    tmp_path: Path,
) -> None:
    """The 12-vs-0 measurement made permanent: a retained saver carries state across graphs."""
    from langgraph.checkpoint.memory import MemorySaver
    from dsa_tools import bootstrap

    bootstrap()
    path = _csv(tmp_path)
    cfg = {"configurable": {"thread_id": "shared-saver-thread"}}
    saver = MemorySaver()

    first = build_graph(checkpoint=True, checkpointer=saver)
    await first.ainvoke(_payload(path, "shared-saver-thread"), config=cfg)
    assert first.get_state(cfg).values, "the first run persisted nothing"

    second = build_graph(checkpoint=True, checkpointer=saver)
    restored = second.get_state(cfg).values
    assert restored, (
        "a second graph sharing the saver sees no state -- the defect this seam exists to fix"
    )
    assert "step_index" in restored, sorted(restored)


@pytest.mark.asyncio
async def test_entry_point_persists_into_the_callers_saver(tmp_path: Path) -> None:
    """``run_analysis_langgraph`` must honour the injected saver, not build its own.

    Without this the seam would exist only on ``build_graph`` and the documented entry point
    would still discard state -- which is the exact defect the seven claims describe away.
    """
    from langgraph.checkpoint.memory import MemorySaver
    from dsa_tools import bootstrap

    from dsa_agent.langgraph_graph import run_analysis_langgraph

    bootstrap()
    path = _csv(tmp_path)
    saver = MemorySaver()
    state = await run_analysis_langgraph(
        dataset_path=str(path),
        dataset_id="ds",
        user_query="Analyze correlation between a and b",
        run_id="entrypoint-saver",
        checkpointer=saver,
    )
    assert state.run_id == "entrypoint-saver", state.run_id

    reader = build_graph(checkpoint=True, checkpointer=saver)
    values = reader.get_state({"configurable": {"thread_id": "entrypoint-saver"}}).values
    assert values, "the entry point ran against a different saver, so nothing is retainable"
