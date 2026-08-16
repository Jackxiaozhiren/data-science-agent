from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.services.analysis_service import (
    analysis_progress,
    create_analysis_run,
    evidence_trace_for_state,
    get_analysis_run,
    list_analysis_runs,
    sse_events_for_state,
)

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


class CreateAnalysisBody(BaseModel):
    dataset_id: str
    user_query: str = ""


@router.post("/")
async def create_analysis(body: CreateAnalysisBody, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    if not body.dataset_id or not body.user_query.strip():
        raise HTTPException(status_code=400, detail="dataset_id and user_query required")
    try:
        result = await create_analysis_run(session, body.dataset_id, body.user_query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e
    return result


@router.get("/")
async def list_analyses(dataset_id: str | None = None, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    items = await list_analysis_runs(session, dataset_id=dataset_id)
    return {"analyses": items}


@router.get("/{run_id}")
async def get_analysis(run_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return row


@router.get("/{run_id}/progress")
async def get_analysis_progress(run_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_progress(row)


@router.get("/{run_id}/events")
async def get_analysis_events(run_id: str, request: Request, session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    accept = request.headers.get("accept", "")
    # JSON fallback for clients that don't accept SSE
    wants_json = "application/json" in accept and "text/event-stream" not in accept

    if wants_json:
        payload = json.dumps({"events": sse_events_for_state(row)})
        return StreamingResponse(iter([payload]), media_type="application/json")

    async def _gen() -> AsyncGenerator[str, None]:
        events = sse_events_for_state(row)
        # Initial SSE comment for proxy keepalive
        yield ": analysis events\n\n"
        for ev in events:
            yield f"event: {ev.get('event', 'message')}\n"
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/{run_id}/report")
async def get_analysis_report(run_id: str, format: str = Query(default="json", description="json|markdown"), session: AsyncSession = Depends(get_session)) -> Any:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    state = row.get("state") or {}
    md: str | None = state.get("report_markdown")
    if format == "markdown":
        if not md:
            raise HTTPException(status_code=404, detail="Report not yet generated")
        return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
    return {
        "run_id": run_id,
        "status": row.get("status"),
        "markdown": md,
        "insights": state.get("insights", []),
        "evidence": state.get("evidence", []),
        "validation": state.get("validation_results", []),
    }


@router.get("/{run_id}/artifacts")
async def get_analysis_artifacts(run_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    state = row.get("state") or {}
    # Enrich with progress
    prog = analysis_progress(row)
    return {"artifacts": state.get("artifacts", []), "tool_calls": state.get("tool_calls", []), "progress": prog}


@router.get("/{run_id}/evidence/{evidence_id}")
async def get_evidence_trace(run_id: str, evidence_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    traced = evidence_trace_for_state(row, evidence_id)
    if traced is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return traced


@router.post("/{run_id}/approve")
async def approve_analysis(run_id: str, body: dict[str, Any] | None = None, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if row.get("status") != "HUMAN_REVIEW":
        raise HTTPException(status_code=409, detail=f"Analysis not awaiting approval (status={row.get('status')})")
    # For MVP, approval flips to COMPLETED with note; full re-run is Phase 9+
    from dsa_api.models.analysis import AnalysisRunORM
    from sqlalchemy import select as _select

    result = await session.execute(_select(AnalysisRunORM).where(AnalysisRunORM.id == run_id))
    orm = result.scalars().first()
    if orm is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    note = (body or {}).get("note", "Approved by human")
    # Append to state_json as synthetic validation
    import json as _json

    state = _json.loads(orm.state_json) if orm.state_json else {}
    state.setdefault("validation_results", []).append({"check": "human_approval", "passed": True, "message": note})
    orm.state_json = _json.dumps(state)
    orm.status = "COMPLETED"
    await session.commit()
    await session.refresh(orm)
    return orm.to_dict()
