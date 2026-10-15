"""The task that executes a run, and what the row says while it happens (web plan R-03).

Split from ``analysis_service`` on purpose: that module answers questions about a stored run and every
function in it is safe to call from inside a request. This one owns the thing that outlives the request --
the asyncio task, the session it writes through, and the vocabulary for "still going" -- so the request
layer never has to know how execution is scheduled, and the writes a client observes are all in one place.

Why in-process and not a queue: the product has to run with ``docker compose up`` and on a free Render
instance, so a broker would be a new dependency and a new thing to operate for a single-server demo. What
that buys and costs is stated in ``docs/api.md``: progress is real, and a process that dies mid-run leaves
a row that ``sweep_abandoned_runs`` closes out on the next boot rather than a tab that spins forever.
"""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Any

from sqlalchemy import select

from dsa_agent.state import AnalysisState, AnalysisStatus
from dsa_api.core import database
from dsa_api.models.analysis import AnalysisRunORM

log = logging.getLogger(__name__)

#: The run has stopped and its row will not be written again by a task.
TERMINAL_STATUSES = ("COMPLETED", "FAILED")
#: Stopped, but waiting on a person rather than on the machine: not in flight, not finished.
REVIEW_STATUS = "HUMAN_REVIEW"

#: Derived, never listed: a status added to ``AnalysisStatus`` is in flight until someone classifies it,
#: which is the failure mode that matters (an unclassified status stops looking like a frozen page and
#: starts looking like a run nobody is running).
IN_FLIGHT_STATUSES = tuple(
    s.value for s in AnalysisStatus if s.value not in (*TERMINAL_STATUSES, REVIEW_STATUS)
)

_TASKS: dict[str, asyncio.Task[Any]] = {}

#: Serialises find-or-create on the create path. Two clicks are two requests, and the gap between the
#: SELECT that finds nothing and the INSERT that would have found the other one is an await.
CREATE_LOCK = asyncio.Lock()


def is_terminal(status: str) -> bool:
    return str(status or "").strip().upper() in TERMINAL_STATUSES


def failure_message(exc: BaseException) -> str:
    """What a reader may see about a crash: the kind of error, never its message.

    The row is public and the traceback is not. Before this requirement a graph crash produced a 500 with a
    generic detail and no row at all; now it produces a row, so the same non-disclosure rule has to be
    carried over deliberately rather than inherited.
    """
    return f"The analysis stopped unexpectedly ({type(exc).__name__}). Start the run again."


def abandoned_message() -> str:
    return "The API restarted while this run was in flight. Start the run again."


def session_factory() -> Any:
    """Resolved at call time, not import time: a background task must follow the app's current engine."""
    return database.AsyncSessionLocal


async def read_run(run_id: str) -> dict[str, Any] | None:
    async with session_factory()() as session:
        row = await session.get(AnalysisRunORM, run_id)
        return row.to_dict() if row else None


async def _write(
    run_id: str,
    *,
    status: str,
    state_json: str | None = None,
    error: str | None = None,
) -> None:
    async with session_factory()() as session:
        row = await session.get(AnalysisRunORM, run_id)
        if row is None:
            return
        row.status = status
        if state_json is not None:
            row.state_json = state_json
        if error is not None:
            row.error = error
        await session.commit()


async def persist_state(state: AnalysisState) -> None:
    """Store the run as it stands, so a client polling the row sees the stage the graph is in."""
    await _write(state.run_id, status=state.status.value, state_json=state.model_dump_json())


async def execute(run_id: str) -> None:
    """Run one stored row to a terminal state, and write the outcome before this coroutine ends.

    The graph runs inside a task that is *awaited* rather than called, because the outcome has to be read as
    a value: an ``except`` here would add a counted handler to the shipped tree for a decision that belongs
    in one place, and letting the exception escape would push the write into a detached callback that no one
    awaits -- which showed up in the suite as ``Exception ignored in: <coroutine object mark_failed>`` when
    the loop closed under a still-pending write. Awaiting the task keeps the row and the task in step: when
    ``execute`` returns, the row is terminal.
    """
    from dsa_agent.graph import run_analysis

    async with session_factory()() as session:
        row = await session.get(AnalysisRunORM, run_id)
        if row is None:
            log.warning("analysis task started for an unknown run", extra={"run_id": run_id})
            return
        dataset_id, dataset_path, user_query = row.dataset_id, row.dataset_path, row.user_query

    attempt = asyncio.create_task(
        run_analysis(
            dataset_path=dataset_path,
            dataset_id=dataset_id,
            user_query=user_query,
            run_id=run_id,
            on_update=persist_state,
        )
    )
    await asyncio.wait({attempt})
    failure: BaseException | None = None if attempt.cancelled() else attempt.exception()
    if failure is not None:
        log.error("analysis task failed", extra={"run_id": run_id}, exc_info=failure)
        await mark_failed(run_id, failure_message(failure))
        return
    # The terminal write goes through `gather(return_exceptions=)` rather than a plain await so a failure here
    # is still handled inside this coroutine: an `except` would add a counted handler to the shipped tree, and
    # letting it escape reaches the done callback below, where writing would mean spawning a detached
    # coroutine -- the `Exception ignored in: <coroutine object mark_failed>` shape §174 already recorded.
    written = await asyncio.gather(persist_state(attempt.result()), return_exceptions=True)
    error = written[0]
    if isinstance(error, BaseException):
        log.error("the terminal write failed", extra={"run_id": run_id}, exc_info=error)
        await mark_failed(run_id, failure_message(error))


def _finish(run_id: str, finished: asyncio.Task[Any]) -> None:
    """Drop the registry entry and look at how the task ended.

    A callback that only pops leaves the exception inside a task that nobody awaits, so the row stays
    non-terminal and the log says nothing about which of the two happened. CI showed exactly that shape: every
    tool call recorded as ok, a report already in the state, and `status: VALIDATION` forever.
    """
    _TASKS.pop(run_id, None)
    if finished.cancelled():
        return
    error = finished.exception()
    if error is not None:
        log.error(
            "run lifecycle ended without a terminal row", extra={"run_id": run_id}, exc_info=error
        )


async def mark_failed(run_id: str, error: str) -> None:
    await _write(run_id, status=AnalysisStatus.FAILED.value, error=error)


def schedule_run(run_id: str) -> asyncio.Task[Any]:
    """Start the run in this process and keep a reference to it.

    Without the registry, CPython is free to garbage-collect an unreferenced task mid-flight, which would
    look exactly like the failure this module exists to prevent: a row frozen in ``ANALYSIS``.
    """
    task = asyncio.create_task(execute(run_id))
    _TASKS[run_id] = task
    task.add_done_callback(partial(_finish, run_id))
    return task


async def find_in_flight(session: Any, dataset_id: str, user_query: str) -> AnalysisRunORM | None:
    """The run this submit is asking for, if one is already executing."""
    result = await session.execute(
        select(AnalysisRunORM)
        .where(AnalysisRunORM.dataset_id == dataset_id)
        .where(AnalysisRunORM.user_query == user_query)
        .where(AnalysisRunORM.status.in_(IN_FLIGHT_STATUSES))
        .order_by(AnalysisRunORM.created_at.desc())
        .limit(1)
    )
    found: AnalysisRunORM | None = result.scalars().first()
    return found


async def sweep_abandoned_runs() -> int:
    """Close out rows whose task died with an earlier process. Called from the app's startup."""
    async with session_factory()() as session:
        result = await session.execute(
            select(AnalysisRunORM).where(AnalysisRunORM.status.in_(IN_FLIGHT_STATUSES))
        )
        rows = list(result.scalars().all())
        for row in rows:
            row.status = AnalysisStatus.FAILED.value
            row.error = abandoned_message()
        if rows:
            await session.commit()
    return len(rows)
