from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from dsa_agent.graph import _evidence_for_tool_call, _run_tool, _tool_inputs_for_step
from dsa_agent.state import AnalysisState, AnalysisStatus, Insight


class LGState(TypedDict, total=False):
    dataset_path: str | None
    dataset_id: str
    user_query: str
    run_id: str | None
    plan: list[dict[str, Any]]
    objective: str
    columns: list[str]
    step_index: int
    analysis_state: dict[str, Any]
    messages: Annotated[list[dict[str, Any]], add_messages]
    status: str
    retry_count: int


async def _node_understand(state: LGState) -> dict[str, Any]:
    return {
        "messages": [{"role": "assistant", "content": "Understanding user query"}],
        "step_index": 0,
        "retry_count": 0,
    }


async def _node_plan(state: LGState) -> dict[str, Any]:
    from dsa_agent.planner import heuristics_plan

    cols: list[str] = []
    ds_path = state.get("dataset_path")
    if ds_path:
        try:
            from dsa_datasets.loader import load_dataframe
            from dsa_datasets.validate import detect_format

            pp = Path(ds_path)
            if pp.exists():
                fmt = detect_format(pp.name)
                df = load_dataframe(pp, fmt)
                cols = list(df.columns)
        except Exception:
            cols = []
    plan = heuristics_plan(state.get("user_query", ""), ds_path, cols)
    return {
        "plan": [s.model_dump(mode="json") for s in plan.steps],
        "objective": plan.objective,
        "columns": cols,
        "status": "PLANNING",
        "messages": [
            {
                "role": "assistant",
                "content": f"Planned {len(plan.steps)} steps: {', '.join(s.tool for s in plan.steps)}",
            }
        ],
    }


async def _node_exec_step(state: LGState) -> dict[str, Any]:
    plan = state.get("plan") or []
    idx = int(state.get("step_index") or 0)
    if idx >= len(plan):
        return {"messages": [{"role": "assistant", "content": "No more steps"}]}
    step = plan[idx]
    ds_path = state.get("dataset_path")
    tool = step.get("tool", "")
    inputs = _tool_inputs_for_step(tool, dict(step.get("inputs") or {}), ds_path)
    t0 = time.perf_counter()
    output, ok, err = await _run_tool(tool, inputs)
    dur = int((time.perf_counter() - t0) * 1000)
    call_id = f"TC-{uuid.uuid4().hex[:8]}"
    # Build tool call record as JSON so it can be merged into analysis_state incrementally
    rec = {
        "call_id": call_id,
        "tool": tool,
        "input": inputs,
        "output": output.model_dump(mode="json")
        if hasattr(output, "model_dump")
        else (dict(output) if isinstance(output, dict) else None),
        "status": "ok" if ok else "error",
        "error": err,
        "duration_ms": dur,
    }
    ev = _evidence_for_tool_call(tool, call_id, output) if ok and output is not None else None
    evj = ev.model_dump(mode="json") if ev else None
    insight = None
    if ev and tool in (
        "correlation_analysis",
        "hypothesis_test",
        "regression_analysis",
        "forecast",
        "feature_importance",
        "assumption_check",
        "causal_check",
    ):
        iid = f"I-{uuid.uuid4().hex[:8]}"
        insight = Insight(
            id=iid,
            finding=ev.claim,
            evidence_ids=[ev.id],
            limitation="Association does not imply causation.",
        ).model_dump(mode="json")
    # Incrementally update analysis_state via reducer-style merge in state
    analysis = state.get("analysis_state") or {}
    tcs = list(analysis.get("tool_calls") or [])
    evs = list(analysis.get("evidence") or [])
    iss = list(analysis.get("insights") or [])
    tcs.append(rec)
    if evj:
        evs.append(evj)
    if insight:
        iss.append(insight)
    new_analysis = {**analysis, "tool_calls": tcs, "evidence": evs, "insights": iss}
    return {
        "analysis_state": new_analysis,
        "step_index": idx + 1,
        "messages": [
            {"role": "assistant", "content": f"Step {idx + 1}/{len(plan)} {tool} {rec['status']}"}
        ],
    }


def _route_after_step(state: LGState) -> str:
    plan = state.get("plan") or []
    idx = int(state.get("step_index") or 0)
    if idx < len(plan):
        return "exec_step"
    return "critic"


async def _node_critic(state: LGState) -> dict[str, Any]:
    # Build a lightweight AnalysisState from accumulated analysis_state to validate
    analysis = state.get("analysis_state") or {}
    run_id = state.get("run_id") or f"run-{uuid.uuid4().hex[:10]}"
    try:
        from dsa_agent.critic import critic_validate, should_retry
        from dsa_agent.state import AnalysisState as AS

        # materialize a minimal AS for validation
        tool_calls = analysis.get("tool_calls") or []
        evidence = analysis.get("evidence") or []
        insights = analysis.get("insights") or []
        validation: list[dict[str, Any]] = analysis.get("validation_results") or []
        # fabricate AS
        from dsa_agent.state import Evidence as _Ev
        from dsa_agent.state import Insight as _Ins
        from dsa_agent.state import ToolCallRecord as _TC
        from dsa_agent.state import ValidationResult as _VR

        as_obj = AS(
            run_id=run_id,
            dataset_id=state.get("dataset_id", "ds"),
            dataset_path=state.get("dataset_path"),
            user_query=state.get("user_query", ""),
            objective=state.get("objective", ""),
            plan=[],
            tool_calls=[_TC.model_validate(tc) for tc in tool_calls],
            evidence=[_Ev.model_validate(ev) for ev in evidence],
            insights=[_Ins.model_validate(i) for i in insights],
            validation_results=[_VR.model_validate(v) for v in validation],
            tool_call_count=len(tool_calls),
            retry_count=int(state.get("retry_count") or 0),
        )
        vresults = critic_validate(as_obj)
        analysis2 = {
            **analysis,
            "validation_results": [r.model_dump(mode="json") for r in vresults],
        }
        retry = should_retry(vresults, int(state.get("retry_count") or 0))
        msg = f"Critic {'retry' if retry else 'pass'}: {len([r for r in vresults if not r.passed])} failed"
        new_retry = int(state.get("retry_count") or 0) + (1 if retry else 0)
        return {
            "analysis_state": analysis2,
            "messages": [{"role": "assistant", "content": msg}],
            "retry_count": new_retry,
            "status": "VALIDATION",
        }
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Critic error: {e}"}]}


def _route_after_critic(state: LGState) -> str:
    analysis = state.get("analysis_state") or {}
    vrs = analysis.get("validation_results") or []
    failed = [
        v
        for v in vrs
        if not v.get("passed") and v.get("check") in ("evidence_coverage", "tool_errors")
    ]
    rc = int(state.get("retry_count") or 0)
    if failed and rc < 3:
        # retry failed tool calls via exec_step again? For incremental graph we just record and proceed to report
        # In checkpointed mode, a retry would re-enter exec_step for failed indices — for V0.4 we pass through to report
        return "report"
    return "report"


async def _node_report(state: LGState) -> dict[str, Any]:
    analysis = state.get("analysis_state") or {}
    run_id = state.get("run_id") or f"run-{uuid.uuid4().hex[:10]}"
    dataset_id = state.get("dataset_id", "ds")
    dataset_path = state.get("dataset_path")
    user_query = state.get("user_query", "")
    try:
        from dsa_agent.report import build_markdown_report, write_report_artifacts
        from dsa_agent.state import AnalysisState as AS
        from dsa_agent.state import Evidence, Insight, ToolCallRecord, ValidationResult

        def _load_list(key: str, model: Any) -> list[Any]:
            return [model.model_validate(x) for x in (analysis.get(key) or [])]

        as_obj = AS(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_path=dataset_path,
            user_query=user_query,
            objective=state.get("objective", user_query[:500]),
            plan=[],
            tool_calls=_load_list("tool_calls", ToolCallRecord),
            evidence=_load_list("evidence", Evidence),
            insights=_load_list("insights", Insight),
            validation_results=_load_list("validation_results", ValidationResult),
            status=AnalysisStatus.REPORTING,
        )
        md = build_markdown_report(as_obj)
        analysis2 = {
            **analysis,
            "report_markdown": md,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "dataset_path": dataset_path,
            "user_query": user_query,
            "objective": state.get("objective", ""),
            "status": "COMPLETED",
        }
        # persist artifacts (best-effort)
        try:
            tmp_state = AS(
                run_id=run_id,
                dataset_id=dataset_id,
                dataset_path=dataset_path,
                user_query=user_query,
                objective=state.get("objective", ""),
                tool_calls=_load_list("tool_calls", ToolCallRecord),
                evidence=_load_list("evidence", Evidence),
                insights=_load_list("insights", Insight),
                validation_results=_load_list("validation_results", ValidationResult),
                report_markdown=md,
                status=AnalysisStatus.REPORTING,
            )
            paths = write_report_artifacts(tmp_state)
            arts = list(analysis2.get("artifacts") or [])
            arts.append(
                {
                    "id": f"A-{uuid.uuid4().hex[:8]}",
                    "type": "report",
                    "path": paths["markdown"],
                    "metadata": {"kind": "markdown"},
                }
            )
            arts.append(
                {
                    "id": f"A-{uuid.uuid4().hex[:8]}",
                    "type": "report",
                    "path": paths["experiment"],
                    "metadata": {"kind": "experiment"},
                }
            )
            analysis2["artifacts"] = arts
            # evidence bundle
            try:
                from dsa_agent.state import Evidence as Ev
                from dsa_agent.state import Insight as Ins
                from dsa_agent.state import ToolCallRecord as TC
                from dsa_agent.state import ValidationResult as VR
                from dsa_evidence.graph import build_evidence_graph
                from dsa_evidence.repro import (
                    build_experiment_json,
                    build_notebook,
                    build_reproduce_sh,
                )
                from dsa_evidence.validator import validate_evidence_graph

                evs = [Ev.model_validate(x) for x in (analysis2.get("evidence") or [])]
                iss = [Ins.model_validate(x) for x in (analysis2.get("insights") or [])]
                tcs = [TC.model_validate(x) for x in (analysis2.get("tool_calls") or [])]
                g = build_evidence_graph(run_id, dataset_id, dataset_path, evs, iss, tcs)
                v = validate_evidence_graph(g)
                vjs = [
                    VR(
                        check=item["check"], passed=bool(item["passed"]), message=item["message"]
                    ).model_dump(mode="json")
                    for item in v
                ]
                existing_v = list(analysis2.get("validation_results") or [])
                analysis2["validation_results"] = existing_v + vjs
                from pathlib import Path as _P

                report_dir = _P(paths["markdown"]).parent
                (report_dir / "evidence_graph.json").write_text(
                    g.model_dump_json(indent=2), encoding="utf-8"
                )
                arts2 = list(analysis2.get("artifacts") or [])
                arts2.append(
                    {
                        "id": f"A-{uuid.uuid4().hex[:8]}",
                        "type": "evidence",
                        "path": str(report_dir / "evidence_graph.json"),
                        "metadata": {"kind": "evidence_graph"},
                    }
                )
                sha = g.dataset_sha256
                # plan for notebook cells comes from outer plan (if any) — best-effort
                outer_plan = state.get("plan") or []
                exp_path = build_experiment_json(
                    run_id,
                    dataset_path,
                    sha,
                    user_query,
                    outer_plan,
                    [c.model_dump(mode="json") for c in tcs],
                    [e.model_dump(mode="json") for e in evs],
                    [i.model_dump(mode="json") for i in iss],
                    report_dir,
                )
                repro_path = build_reproduce_sh(run_id, dataset_path, user_query, report_dir)
                nb_path = build_notebook(
                    run_id,
                    dataset_path,
                    user_query,
                    outer_plan,
                    [c.model_dump(mode="json") for c in tcs],
                    report_dir,
                )
                existing = {a.get("path") for a in arts2}
                for pth, kind in [
                    (exp_path, "experiment"),
                    (repro_path, "reproduce"),
                    (nb_path, "notebook"),
                ]:
                    sp = str(pth)
                    if sp not in existing:
                        arts2.append(
                            {
                                "id": f"A-{uuid.uuid4().hex[:8]}",
                                "type": "report" if kind == "experiment" else kind,
                                "path": sp,
                                "metadata": {"kind": kind},
                            }
                        )
                analysis2["artifacts"] = arts2
            except Exception:
                pass
        except Exception:
            pass
        return {
            "analysis_state": analysis2,
            "status": "COMPLETED",
            "messages": [{"role": "assistant", "content": "Report generated"}],
        }
    except Exception as e:
        return {
            "messages": [{"role": "assistant", "content": f"Report error: {e}"}],
            "status": "FAILED",
        }


def build_graph(checkpoint: bool = True) -> Any:
    g = StateGraph(LGState)
    g.add_node("understand", _node_understand)
    g.add_node("plan", _node_plan)
    g.add_node("exec_step", _node_exec_step)
    g.add_node("critic", _node_critic)
    g.add_node("report", _node_report)
    g.set_entry_point("understand")
    g.add_edge("understand", "plan")
    g.add_edge("plan", "exec_step")
    g.add_conditional_edges(
        "exec_step", _route_after_step, {"exec_step": "exec_step", "critic": "critic"}
    )
    g.add_conditional_edges("critic", _route_after_critic, {"report": "report"})
    g.add_edge("report", END)
    if checkpoint:
        return g.compile(checkpointer=MemorySaver())
    return g.compile()


async def run_analysis_langgraph(
    dataset_path: str | None,
    dataset_id: str,
    user_query: str,
    run_id: str | None = None,
) -> AnalysisState:
    try:
        graph = build_graph(checkpoint=True)
        cfg = {"configurable": {"thread_id": run_id or f"run-{uuid.uuid4().hex[:10]}"}}
        out = await graph.ainvoke(
            {
                "dataset_path": dataset_path,
                "dataset_id": dataset_id,
                "user_query": user_query,
                "run_id": run_id,
                "analysis_state": {},
                "step_index": 0,
                "retry_count": 0,
            },
            config=cfg,
        )
        state_dict = out.get("analysis_state") or {}
        # Map LG analysis_state dict to AnalysisState
        if state_dict:
            # ensure required fields present
            state_dict.setdefault(
                "run_id",
                out.get("run_id")
                or run_id
                or state_dict.get("run_id")
                or f"run-{uuid.uuid4().hex[:10]}",
            )
            state_dict.setdefault("dataset_id", dataset_id)
            state_dict.setdefault("user_query", user_query)
            state_dict.setdefault("dataset_path", dataset_path)
            state_dict.setdefault("status", out.get("status") or "COMPLETED")
            try:
                return AnalysisState.model_validate(state_dict)
            except Exception:
                pass
            from dsa_agent.state import AnalysisState as AS
            from dsa_agent.state import Evidence as _Ev2
            from dsa_agent.state import Insight as _Ins2
            from dsa_agent.state import ToolCallRecord as _TC2
            from dsa_agent.state import ValidationResult as _VR2

            try:
                return AS(
                    run_id=state_dict.get("run_id", run_id or "run-1"),
                    dataset_id=dataset_id,
                    dataset_path=dataset_path,
                    user_query=user_query,
                    objective=state_dict.get("objective", user_query[:500]),
                    tool_calls=[
                        _TC2.model_validate(x) for x in (state_dict.get("tool_calls") or [])
                    ],
                    evidence=[_Ev2.model_validate(x) for x in (state_dict.get("evidence") or [])],
                    insights=[_Ins2.model_validate(x) for x in (state_dict.get("insights") or [])],
                    validation_results=[
                        _VR2.model_validate(x) for x in (state_dict.get("validation_results") or [])
                    ],
                    report_markdown=state_dict.get("report_markdown"),
                    status=AnalysisStatus(state_dict.get("status", "COMPLETED")),
                )
            except Exception:
                pass
    except Exception:
        pass
    from dsa_agent.graph import run_analysis as _run_analysis

    return await _run_analysis(
        dataset_path=dataset_path, dataset_id=dataset_id, user_query=user_query, run_id=run_id
    )
