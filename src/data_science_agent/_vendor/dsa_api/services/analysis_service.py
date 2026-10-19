from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.ownership import visible_to
from dsa_api.models.analysis import AnalysisRunORM
from dsa_api.models.dataset import DatasetORM
from dsa_api.services.run_lifecycle import CREATE_LOCK, find_in_flight, is_terminal


async def create_pending_run(
    session: AsyncSession,
    dataset_id: str,
    user_query: str,
    *,
    owner: str,
) -> tuple[dict[str, Any], bool]:
    """Insert the row a run will execute into, and report whether this call is the one that started it.

    The second value is the double-submit answer: ``False`` means an identical question is already
    executing and the caller must not schedule a second task. Before this change the row was written after
    the graph finished, so there was nothing to deduplicate against and no state to observe.

    R-08 scopes all of it. The dedupe only ever matches *the requester's own* in-flight run: two visitors who
    both ask a published sample question about the published sample dataset get two runs, because telling B
    that A's identical question is already executing is the leak this requirement is about. The dedupe was a
    courtesy and the isolation is the promise.
    """
    async with CREATE_LOCK:
        existing = await find_in_flight(session, dataset_id, user_query)
        if existing is not None and existing.owner == owner:
            return existing.to_dict(), False

        result = await session.execute(
            select(DatasetORM).where(
                DatasetORM.id == dataset_id, DatasetORM.owner.in_(visible_to(owner))
            )
        )
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
        orm = AnalysisRunORM(
            id=run_id,
            dataset_id=dataset_id,
            dataset_path=str(dataset_path),
            user_query=user_query,
            status="UNDERSTANDING",
            owner=owner,
        )
        session.add(orm)
        await session.commit()
        await session.refresh(orm)
        return orm.to_dict(), True


async def get_analysis_run(
    session: AsyncSession, run_id: str, *, owner: str
) -> dict[str, Any] | None:
    """The row, or nothing when it belongs to someone else and is not published.

    `owner` is required so that a route which forgets to scope fails with a TypeError on the first request
    instead of answering with another visitor's data.
    """
    result = await session.execute(
        select(AnalysisRunORM).where(
            AnalysisRunORM.id == run_id, AnalysisRunORM.owner.in_(visible_to(owner))
        )
    )
    row = result.scalars().first()
    return row.to_dict() if row else None


async def list_analysis_runs(
    session: AsyncSession,
    dataset_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    *,
    owner: str,
) -> tuple[list[dict[str, Any]], int]:
    from sqlalchemy import func as _func

    base = select(AnalysisRunORM).where(AnalysisRunORM.owner.in_(visible_to(owner)))
    count_q = (
        select(_func.count())
        .select_from(AnalysisRunORM)
        .where(AnalysisRunORM.owner.in_(visible_to(owner)))
    )
    if dataset_id:
        base = base.where(AnalysisRunORM.dataset_id == dataset_id)
        count_q = count_q.where(AnalysisRunORM.dataset_id == dataset_id)
    total = (await session.execute(count_q)).scalar_one()
    q = base.order_by(AnalysisRunORM.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(q)
    rows = result.scalars().all()
    return [r.to_dict() for r in rows], total


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
    if is_terminal(status):
        # Only a stopped run may be announced as completed: this list is now built from a row that is
        # still growing, and an `analysis_completed` frame for a run in ANALYSIS would be a lie on the wire.
        events.append(
            {"event": "analysis_completed", "status": status, "run_id": state_dict.get("id")}
        )
    return events


def sse_event_identity(event: dict[str, Any]) -> str:
    """What makes one event the same event across two snapshots of a growing row.

    The live stream rebuilds its frames from the stored state on every tick, so "new" has to be a property
    of the payload rather than of its index -- a tool call appended while a client watches must not resend
    the ones it already saw, and a validation result that changes on retry must not be swallowed as a
    duplicate of the old one.
    """
    return json.dumps(event, sort_keys=True, ensure_ascii=False, default=str)


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
