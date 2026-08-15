from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.services.analysis_service import create_analysis_run, get_analysis_run, list_analysis_runs, sse_events_for_state

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


@router.get("/{run_id}/events")
async def get_analysis_events(run_id: str, session: AsyncSession = Depends(get_session)) -> StreamingResponse:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    async def _gen() -> AsyncGenerator[str, None]:
        events = sse_events_for_state(row)
        for ev in events:
            yield f"data: {json.dumps(ev)}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/{run_id}/report")
async def get_analysis_report(run_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    state = row.get("state") or {}
    return {
        "run_id": run_id,
        "status": row.get("status"),
        "markdown": state.get("report_markdown"),
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
    return {"artifacts": state.get("artifacts", []), "tool_calls": state.get("tool_calls", [])}
