from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from dsa_agent.graph import run_analysis as _run_analysis
from dsa_agent.state import AnalysisState


class LGState(TypedDict, total=False):
    dataset_path: str | None
    dataset_id: str
    user_query: str
    run_id: str | None
    analysis_state: dict[str, Any]
    messages: Annotated[list[dict[str, Any]], add_messages]
    status: str


async def _node_understand(state: LGState) -> dict[str, Any]:
    # UNDERSTANDING -> PLANNING is handled inside run_analysis; this node just tags
    return {"messages": [{"role": "assistant", "content": "Understanding user query"}]}


async def _node_plan(state: LGState) -> dict[str, Any]:
    from dsa_agent.planner import heuristics_plan

    cols: list[str] = []
    try:
        from pathlib import Path

        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format

        p = state.get("dataset_path")
        if p:
            pp = Path(p)
            if pp.exists():
                fmt = detect_format(pp.name)
                df = load_dataframe(pp, fmt)
                cols = list(df.columns)
    except Exception:
        cols = []
    plan = heuristics_plan(state.get("user_query", ""), state.get("dataset_path"), cols)
    return {"messages": [{"role": "assistant", "content": f"Planned {len(plan.steps)} steps: {', '.join(s.tool for s in plan.steps)}"}]}


async def _node_execute(state: LGState) -> dict[str, Any]:
    ds_path = state.get("dataset_path")
    ds_id = state.get("dataset_id", "ds")
    query = state.get("user_query", "")
    run_id = state.get("run_id")
    analysis = await _run_analysis(dataset_path=ds_path, dataset_id=ds_id, user_query=query, run_id=run_id)
    return {"analysis_state": analysis.model_dump(mode="json"), "status": analysis.status.value, "messages": [{"role": "assistant", "content": f"Execution {analysis.status.value}: {len(analysis.tool_calls)} tool calls"}]}


def build_graph() -> Any:
    g = StateGraph(LGState)
    g.add_node("understand", _node_understand)
    g.add_node("plan", _node_plan)
    g.add_node("execute", _node_execute)
    g.set_entry_point("understand")
    g.add_edge("understand", "plan")
    g.add_edge("plan", "execute")
    g.add_edge("execute", END)
    return g.compile()


# Backwards-compatible wrapper: prefer graph but fall back to direct run_analysis
async def run_analysis_langgraph(
    dataset_path: str | None,
    dataset_id: str,
    user_query: str,
    run_id: str | None = None,
) -> AnalysisState:
    try:
        graph = build_graph()
        out = await graph.ainvoke({"dataset_path": dataset_path, "dataset_id": dataset_id, "user_query": user_query, "run_id": run_id})
        state_dict = out.get("analysis_state")
        if state_dict:
            from dsa_agent.state import AnalysisState as AS

            return AS.model_validate(state_dict)
    except Exception:
        pass
    # fallback
    return await _run_analysis(dataset_path=dataset_path, dataset_id=dataset_id, user_query=user_query, run_id=run_id)
