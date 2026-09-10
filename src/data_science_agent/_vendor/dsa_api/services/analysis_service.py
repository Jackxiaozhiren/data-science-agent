from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.models.analysis import AnalysisRunORM
from dsa_api.models.dataset import DatasetORM


async def _ensure_tables(session: AsyncSession) -> None:
    from dsa_api.core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_analysis_run(
    session: AsyncSession,
    dataset_id: str,
    user_query: str,
) -> dict[str, Any]:
    await _ensure_tables(session)
    result = await session.execute(select(DatasetORM).where(DatasetORM.id == dataset_id))
    ds = result.scalars().first()
    if ds is None:
        raise ValueError(f"Dataset not found: {dataset_id}")

    dataset_path = Path(ds.path)
    if not dataset_path.is_file():
        raise ValueError(
            "Dataset file is no longer available on this demo instance. "
            "The hosted demo uses ephemeral storage; please re-upload the dataset and run the analysis again."
        )

    run_id = f"run-{uuid.uuid4().hex[:10]}"

    # run the agent graph synchronously (for MVP)
    from dsa_agent.graph import run_analysis

    state = await run_analysis(
        dataset_path=str(dataset_path),
        dataset_id=dataset_id,
        user_query=user_query,
        run_id=run_id,
    )

    orm = AnalysisRunORM(
        id=run_id,
        dataset_id=dataset_id,
        dataset_path=str(dataset_path),
        user_query=user_query,
        status=state.status.value,
        state_json=state.model_dump_json(),
        error=state.error,
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)
    return orm.to_dict()


async def get_analysis_run(session: AsyncSession, run_id: str) -> dict[str, Any] | None:
    await _ensure_tables(session)
    result = await session.execute(select(AnalysisRunORM).where(AnalysisRunORM.id == run_id))
    row = result.scalars().first()
    return row.to_dict() if row else None


async def list_analysis_runs(
    session: AsyncSession, dataset_id: str | None = None
) -> list[dict[str, Any]]:
    await _ensure_tables(session)
    q = select(AnalysisRunORM).order_by(AnalysisRunORM.created_at.desc())
    if dataset_id:
        q = q.where(AnalysisRunORM.dataset_id == dataset_id)
    result = await session.execute(q)
    rows = result.scalars().all()
    return [r.to_dict() for r in rows]


def sse_events_for_state(state_dict: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    state = state_dict.get("state") or {}
    for msg in state.get("agent_messages", []):
        events.append(
            {"event": "agent_completed", "agent": msg.get("agent"), "content": msg.get("content")}
        )
    for tc in state.get("tool_calls", []):
        events.append(
            {
                "event": "tool_completed",
                "tool": tc.get("tool"),
                "status": tc.get("status"),
                "duration_ms": tc.get("duration_ms"),
                "call_id": tc.get("call_id"),
            }
        )
    for vr in state.get("validation_results", []):
        events.append(
            {
                "event": "validation_completed",
                "check": vr.get("check"),
                "passed": vr.get("passed"),
                "message": vr.get("message"),
            }
        )
    if state.get("report_markdown"):
        events.append({"event": "report_generated", "run_id": state_dict.get("id")})
    status = state_dict.get("status", "")
    events.append({"event": "analysis_completed", "status": status, "run_id": state_dict.get("id")})
    return events


def evidence_trace_for_state(state_dict: dict[str, Any], evidence_id: str) -> dict[str, Any] | None:
    state = state_dict.get("state") or {}
    evs = {e.get("id"): e for e in state.get("evidence", [])}
    ev = evs.get(evidence_id)
    if ev is None:
        return None
    tcs = {c.get("call_id"): c for c in state.get("tool_calls", [])}
    tc = tcs.get(ev.get("source_id"))
    dataset = {
        "dataset_id": state_dict.get("dataset_id"),
        "dataset_path": state_dict.get("dataset_path"),
    }
    insights = [
        i for i in state.get("insights", []) if evidence_id in (i.get("evidence_ids") or [])
    ]
    return {"evidence": ev, "tool_call": tc, "insights": insights, "dataset": dataset}


def analysis_progress(state_dict: dict[str, Any]) -> dict[str, Any]:
    state = state_dict.get("state") or {}
    plan_len = len(state.get("plan", []))
    done = len(state.get("tool_calls", []))
    pct = int(
        (done / plan_len * 100)
        if plan_len
        else (100 if state_dict.get("status") == "COMPLETED" else 0)
    )
    return {
        "run_id": state_dict.get("id"),
        "status": state_dict.get("status"),
        "progress_pct": min(100, max(0, pct)),
        "steps_total": plan_len,
        "steps_done": done,
        "evidence": len(state.get("evidence", [])),
        "insights": len(state.get("insights", [])),
    }
