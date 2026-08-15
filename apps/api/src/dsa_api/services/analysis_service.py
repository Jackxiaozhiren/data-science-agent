from __future__ import annotations

import json
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
    # resolve dataset_path
    result = await session.execute(select(DatasetORM).where(DatasetORM.id == dataset_id))
    ds = result.scalars().first()
    if ds is None:
        raise ValueError(f"Dataset not found: {dataset_id}")
    run_id = f"run-{uuid.uuid4().hex[:10]}"

    # run the agent graph synchronously (for MVP)
    from dsa_agent.graph import run_analysis

    state = await run_analysis(
        dataset_path=ds.path,
        dataset_id=dataset_id,
        user_query=user_query,
        run_id=run_id,
    )

    orm = AnalysisRunORM(
        id=run_id,
        dataset_id=dataset_id,
        dataset_path=ds.path,
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


async def list_analysis_runs(session: AsyncSession, dataset_id: str | None = None) -> list[dict[str, Any]]:
    await _ensure_tables(session)
    q = select(AnalysisRunORM).order_by(AnalysisRunORM.created_at.desc())
    if dataset_id:
        q = q.where(AnalysisRunORM.dataset_id == dataset_id)
    result = await session.execute(q)
    rows = result.scalars().all()
    return [r.to_dict() for r in rows]


def sse_events_for_state(state_dict: dict[str, Any]) -> list[dict[str, Any]]:
    # synthesize SSE events from stored state for polling fallback demo
    events: list[dict[str, Any]] = []
    state = state_dict.get("state") or {}
    for tc in state.get("tool_calls", []):
        events.append({"event": "tool_completed", "tool": tc.get("tool"), "status": tc.get("status"), "duration_ms": tc.get("duration_ms")})
    status = state_dict.get("status", "")
    events.append({"event": "analysis_completed", "status": status})
    return events
