from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_agent.report_export import EXPORT_MODES, export_html, export_markdown
from dsa_agent.run_summary import run_summary
from dsa_api.core.database import get_session
from dsa_api.services.analysis_service import (
    analysis_progress,
    create_pending_run,
    evidence_trace_for_state,
    get_analysis_run,
    list_analysis_runs,
    sse_event_identity,
    sse_events_for_state,
)
from dsa_api.services.run_lifecycle import is_terminal, read_run, schedule_run

#: Names this endpoint publishes for canonical fields, kept explicit at the boundary.
REST_RUN_ALIASES = {"markdown": "report_markdown", "validation": "validation_results"}

#: How often the live stream re-reads the row. The graph writes at stage boundaries, so this only sets how
#: long a written event waits before it reaches a watching client; it is not a polling loop for progress.
_EVENT_POLL_SECONDS = 0.25

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

log = logging.getLogger(__name__)


class CreateAnalysisBody(BaseModel):
    dataset_id: str
    user_query: str = ""


@router.post("/", status_code=202)
async def create_analysis(
    body: CreateAnalysisBody,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Accept a run: the row exists and is executing when this returns, not after it finishes.

    202 for a run this call started, 200 when an identical question is already in flight -- a double click
    is one run, and the second response says so without inventing a field for it.
    """
    if not body.dataset_id or not body.user_query.strip():
        raise HTTPException(status_code=400, detail="dataset_id and user_query required")
    try:
        result, started = await create_pending_run(session, body.dataset_id, body.user_query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception:
        # Never leak internals to clients; the traceback goes to server logs. A crash inside the run
        # itself is no longer reachable here -- it lands on the row, see dsa_api.services.run_lifecycle.
        log.exception("analysis run failed", extra={"dataset_id": body.dataset_id})
        raise HTTPException(
            status_code=500, detail="Analysis failed unexpectedly. Please retry shortly."
        ) from None
    if started:
        schedule_run(str(result["id"]))
    else:
        response.status_code = 200
    response.headers["Location"] = f"/api/v1/analysis/{result['id']}"
    return result


@router.get("/")
async def list_analyses(
    dataset_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    items, total = await list_analysis_runs(
        session, dataset_id=dataset_id, limit=limit, offset=offset
    )
    return {"analyses": items, "total": total}


@router.get("/{run_id}")
async def get_analysis(run_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return row


@router.get("/{run_id}/progress")
async def get_analysis_progress(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_progress(row)


async def analysis_event_frames(
    run_id: str,
    first_row: dict[str, Any],
    *,
    read_row: Callable[[str], Awaitable[dict[str, Any] | None]] = read_run,
    disconnected: Callable[[], Awaitable[bool]] | None = None,
    poll_s: float = _EVENT_POLL_SECONDS,
) -> AsyncGenerator[dict[str, Any], None]:
    """Each event of one run, exactly once, following the row while it is still being written.

    A generator over the stored row rather than a snapshot of it: the events a client watches are produced
    by a task in this same process, so "live" means re-reading the row until it says it has stopped. The
    caller formats these as SSE frames; keeping the two apart is what makes the liveness testable, because
    an HTTP test client buffers a response body to the end and can never observe a stream mid-run.
    """
    emitted: set[str] = set()
    current: dict[str, Any] | None = first_row
    while current is not None:
        for event in sse_events_for_state(current):
            key = sse_event_identity(event)
            if key in emitted:
                continue
            emitted.add(key)
            yield event
        if is_terminal(str(current.get("status") or "")):
            return
        if disconnected is not None and await disconnected():
            return
        await asyncio.sleep(poll_s)
        current = await read_row(run_id)


@router.get("/{run_id}/events")
async def get_analysis_events(
    run_id: str, request: Request, session: AsyncSession = Depends(get_session)
) -> StreamingResponse:
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
        # Initial SSE comment for proxy keepalive
        yield ": analysis events\n\n"
        async for ev in analysis_event_frames(run_id, row, disconnected=request.is_disconnected):
            yield f"event: {ev.get('event', 'message')}\n"
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}/report")
async def get_analysis_report(
    run_id: str,
    format: str = Query(default="json", description="json|markdown|html"),
    mode: str = Query(
        default="audited",
        description=(
            "Which rendering of this run to return: `audited` carries the evidence ids, tool trace and "
            "paths; `findings` is the plain document -- conclusions, numbers and limitations, with no "
            "trace material. Both are produced by the same owner from the same run summary."
        ),
    ),
    session: AsyncSession = Depends(get_session),
) -> Any:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if mode not in EXPORT_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown report mode {mode!r}; expected one of {', '.join(EXPORT_MODES)}",
        )
    state = row.get("state") or {}
    plain = mode == "findings"
    md: str | None = state.get("report_markdown")
    if format == "markdown":
        if plain:
            # Rendered on read rather than stored: the plain document is a view of the run, and keeping a
            # second copy in the row is how the two would start to disagree.
            return PlainTextResponse(
                content=export_markdown(state, "findings"),
                media_type="text/markdown; charset=utf-8",
            )
        if not md:
            raise HTTPException(status_code=404, detail="Report not yet generated")
        return PlainTextResponse(content=md, media_type="text/markdown; charset=utf-8")
    if format == "html":
        if plain:
            raise HTTPException(
                status_code=400,
                detail=(
                    "the self-contained HTML rendering is only produced for the audited mode; "
                    "the plain document is meant to be pasted into a submission, not opened offline"
                ),
            )
        return HTMLResponse(content=export_html(state), media_type="text/html; charset=utf-8")
    summary = run_summary(state)
    return {
        "run_id": run_id,
        "status": row.get("status") or summary["status"],
        "mode": mode,
        "markdown": export_markdown(state, mode)
        if plain
        else summary[REST_RUN_ALIASES["markdown"]],
        "insights": summary["insights"],
        "evidence": summary["evidence"],
        "validation": summary[REST_RUN_ALIASES["validation"]],
    }


@router.get("/{run_id}/artifacts")
async def get_analysis_artifacts(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    state = row.get("state") or {}
    # Enrich with progress
    prog = analysis_progress(row)
    return {
        "artifacts": state.get("artifacts", []),
        "tool_calls": state.get("tool_calls", []),
        "progress": prog,
    }


@router.get("/{run_id}/evidence/{evidence_id}")
async def get_evidence_trace(
    run_id: str, evidence_id: str, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    traced = evidence_trace_for_state(row, evidence_id)
    if traced is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return traced


@router.post("/{run_id}/approve")
async def approve_analysis(
    run_id: str, body: dict[str, Any] | None = None, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    row = await get_analysis_run(session, run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if row.get("status") != "HUMAN_REVIEW":
        raise HTTPException(
            status_code=409, detail=f"Analysis not awaiting approval (status={row.get('status')})"
        )
    # For MVP, approval flips to COMPLETED with note; full re-run is Phase 9+
    from sqlalchemy import select as _select

    from dsa_api.models.analysis import AnalysisRunORM

    result = await session.execute(_select(AnalysisRunORM).where(AnalysisRunORM.id == run_id))
    orm = result.scalars().first()
    if orm is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    note = (body or {}).get("note", "Approved by human")
    # Append to state_json as synthetic validation
    import json as _json

    state = _json.loads(orm.state_json) if orm.state_json else {}
    state.setdefault("validation_results", []).append(
        {"check": "human_approval", "passed": True, "message": note}
    )
    orm.state_json = _json.dumps(state)
    orm.status = "COMPLETED"
    await session.commit()
    await session.refresh(orm)
    return orm.to_dict()
