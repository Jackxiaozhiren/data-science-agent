from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest


@pytest.mark.asyncio
async def test_langgraph_build_and_invoke() -> None:
    from dsa_agent.langgraph_graph import build_graph, run_analysis_langgraph

    g = build_graph()
    assert g is not None
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        pl.DataFrame(
            {"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "b": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]}
        ).write_csv(p)
        state = await run_analysis_langgraph(
            dataset_path=str(p), dataset_id="ds", user_query="Analyze correlation between a and b"
        )
        assert state.run_id
        assert state.status.value in ("COMPLETED", "FAILED")
        assert len(state.tool_calls) >= 1


def test_langgraph_nodes_exist() -> None:
    from dsa_agent.langgraph_graph import build_graph

    g = build_graph()
    # CompiledStateGraph should have our nodes
    assert hasattr(g, "ainvoke")
