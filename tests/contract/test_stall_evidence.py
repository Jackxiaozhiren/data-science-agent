"""The stall report is an instrument, so it is asserted the way one is: each line must be able to say two things.

A timeout message nobody checks quietly becomes decoration -- the census line in this file once implied more than
`asyncio.all_tasks()` can see (it is loop-local), and nothing failed until the reading was leaned on. Each test
here drives one branch of the report with a fabricated condition and requires the specific words that carry the
discrimination, so a future edit that drops a line, or restores an over-claiming label, is red.
"""

from __future__ import annotations

import asyncio
import gc
import logging
import sys
import weakref
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import conftest  # noqa: E402  (the fixture module is the owner of the report)

LOGGER = "dsa_api.services.run_lifecycle"


async def execute(run_id: str) -> None:  # the shipped coroutine's own name is what the scan matches
    await asyncio.Event().wait()


@pytest.fixture
async def live_lifecycle_task() -> AsyncGenerator[dict[str, Any], None]:
    holder: dict[str, Any] = {}

    task = asyncio.ensure_future(execute("run-instrument"))
    holder["task"] = task
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    yield holder
    if not task.done():
        task.cancel()
        await asyncio.sleep(0)


async def test_the_report_names_every_discriminator_it_prints(
    live_lifecycle_task: dict[str, Any],
) -> None:
    text = conftest._stall_evidence("run-instrument")
    for required in (
        "task registry:",
        "scheduled loop:",
        "how the lifecycle task ended:",
        "task object:",
        "live tasks on THIS loop (all_tasks() cannot see another loop's tasks):",
        "threads still inside the lifecycle or the graph:",
        "engine pool:",
        "lifecycle lines emitted for run-instrument anywhere in this process:",
    ):
        assert required in text, f"the report lost the line that says {required!r}"
    # The frame scan is the part that may legitimately claim the writer is elsewhere; the census may not.
    assert "IS on this loop while the registry says otherwise" in text, text


async def test_an_absent_writer_is_reported_as_absent_not_as_a_census_claim() -> None:
    text = conftest._stall_evidence("run-never-scheduled")
    assert "no task for run-never-scheduled" in text
    # A run nobody scheduled has no loop to name, and the report must not imply one: this is the third state,
    # distinct from "recorded, still open" and "recorded, closed".
    assert "never recorded for run-never-scheduled" in text, text
    assert "IS on this loop" not in text, "the claim fired for a coroutine that does not exist"
    assert "threads still inside the lifecycle or the graph: 0" in text


async def test_the_session_wide_counter_hears_what_per_test_capture_cannot(
    live_lifecycle_task: dict[str, Any],
) -> None:
    """A record emitted during a different test is invisible to caplog there; this counter is process-wide.

    That distinction is the last open question about the CI timeouts, so it is pinned rather than trusted: emit
    one WARNING for the run, require the report to read it back with the run id, and require an unrelated run id
    to read back none -- otherwise an empty counter would look like the same answer as a full one.
    """
    before = len(conftest._LIFECYCLE_RECORDS)
    logging.getLogger(LOGGER).warning("instrument probe line", extra={"run_id": "run-instrument"})
    assert len(conftest._LIFECYCLE_RECORDS) == before + 1, "the counting handler is not attached"

    text = conftest._stall_evidence("run-instrument")
    assert "instrument probe line" in text, text
    assert f"{len(conftest._LIFECYCLE_RECORDS)} WARNING+ line(s) seen session-wide" in text, text
    # The sample must exist and must be able to name runs other than the polled one: a session that spoke about
    # other runs while staying quiet about this one is a different failure from never reaching either branch.
    assert "session-wide lines (first" in text, text
    assert any("run-instrument: instrument probe line" in line for line in text.splitlines()), text
    other = conftest._stall_evidence("run-unrelated")
    assert "run-unrelated anywhere in this process: none" in other, other


async def test_the_loop_is_recorded_through_the_name_the_route_calls() -> None:
    """The wrapper has to sit on the binding the route actually resolves, not only on the definition.

    `dsa_api.routers.analysis` did `from ... import schedule_run`, so patching only
    `dsa_api.services.run_lifecycle` would leave the runs this report exists to explain unrecorded -- the same
    call-time-resolution trap that let a database swap reach a live run. This calls the router's own name and
    requires the record, so an install that quietly covers one binding and not the other is red.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from dsa_api.core import database
    from dsa_api.core.database import Base
    from dsa_api.routers import analysis as analysis_router

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # No row for this id: `execute` reads it, finds nothing, logs and returns. The write-free exit is what keeps
    # this probe off any database another test may still be holding.
    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    try:
        task = analysis_router.schedule_run("run-wiring")
        await task
        # A done callback is queued with `call_soon`, not run inline with the await that observed the result.
        await asyncio.sleep(0)
    finally:
        database.AsyncSessionLocal = previous
        await engine.dispose()

    recorded = conftest._SCHEDULED_ON.get("run-wiring")
    assert recorded is asyncio.get_running_loop(), (
        f"the router's binding recorded {recorded!r}, not the loop that ran it"
    )
    text = conftest._stall_evidence("run-wiring")
    assert "same as polling loop=True; that loop closed=False" in text, text
    # The same wrapper's second hook, proven on the shipped path rather than on a fabricated task: `execute`
    # returned after naming the unknown run, so the recorder has to read it as a normal return.
    assert "how the lifecycle task ended: returned (-)" in text, text
    # The lifetime clause, on a task the shipped `schedule_run` really made and really finished.
    assert "task object: done=True" in text, text


async def test_the_line_tells_an_orphan_on_a_closed_loop_from_the_polling_loop() -> None:
    """Both directions of the one claim the CI samples hinge on, driven from fabricated loops.

    The reading has been "the run coroutine is parked on a loop that already closed" -- consistent with CI's
    `RuntimeError: Event loop is closed` from an aiosqlite worker, and with a report that said no task, no live
    coroutine, no thread frame, no log line. That is exactly the shape an instrument must be able to fail to
    produce, so a closed foreign loop and the open polling loop are both fed in and required to read differently.
    """
    orphan = asyncio.new_event_loop()
    orphan.close()
    conftest._SCHEDULED_ON["run-orphan"] = orphan
    conftest._SCHEDULED_ON["run-here"] = asyncio.get_running_loop()
    try:
        orphan_text = conftest._stall_evidence("run-orphan")
        assert "same as polling loop=False" in orphan_text, orphan_text
        assert "that loop closed=True" in orphan_text, orphan_text
        here_text = conftest._stall_evidence("run-here")
        assert "same as polling loop=True" in here_text, here_text
        assert "that loop closed=False" in here_text, here_text
    finally:
        del conftest._SCHEDULED_ON["run-orphan"]
        del conftest._SCHEDULED_ON["run-here"]


async def test_the_outcome_is_read_off_the_task_for_all_three_endings() -> None:
    """`returned`, `raised`, `cancelled` and `not recorded` have to read four different ways.

    The shipped `execute` has no exit that both leaves a row in flight and stays silent, so for three sections
    the argument has run through "no lifecycle line was emitted for this run". That is an absence read out of a
    log, and a log line can be missing for reasons that have nothing to do with the coroutine. Asking the task
    object is the second, independent reading -- so this drives each ending through the real recorder and
    requires the report to distinguish them, including the fourth: a task whose callbacks never ran.
    """
    done_ok: asyncio.Task = asyncio.ensure_future(_returns())
    done_raised: asyncio.Task = asyncio.ensure_future(_raises())
    done_cancelled: asyncio.Task = asyncio.ensure_future(_parks())
    await asyncio.wait({done_ok, done_raised})
    done_cancelled.cancel()
    await asyncio.wait({done_cancelled})
    conftest._record_outcome("run-returned", done_ok)
    conftest._record_outcome("run-raised", done_raised)
    conftest._record_outcome("run-cancelled", done_cancelled)

    for run_id, expected in (
        ("run-returned", "how the lifecycle task ended: returned (-)"),
        ("run-raised", "how the lifecycle task ended: raised (ValueError)"),
        ("run-cancelled", "how the lifecycle task ended: cancelled (-)"),
    ):
        text = conftest._stall_evidence(run_id)
        assert expected in text, f"{run_id} read {text!r}"
    never = conftest._stall_evidence("run-callbacks-never-ran")
    assert "how the lifecycle task ended: not recorded (no done callback ran)" in never, never
    assert "task object: never scheduled here" in never, never

    # An outcome can be recorded while the object is already gone, and the report has to say both: this is the
    # reading that separates "it ended and nothing kept it" from "it is still in flight".
    parked: asyncio.Task = asyncio.ensure_future(_parks())
    conftest._SCHEDULED_TASK["run-in-flight"] = weakref.ref(parked)
    in_flight = conftest._stall_evidence("run-in-flight")
    assert "task object: done=False" in in_flight, in_flight
    parked.cancel()
    await asyncio.wait({parked})
    del parked
    gc.collect()
    gone = conftest._stall_evidence("run-in-flight")
    assert "task object: garbage-collected" in gone, gone


async def _returns() -> None:
    return None


async def _raises() -> None:
    raise ValueError("instrument")


async def _parks() -> None:
    await asyncio.Event().wait()


class _HangsOnEnter:
    """A session whose acquisition never returns -- the shape that would hang the report itself."""

    async def __aenter__(self) -> _HangsOnEnter:
        await asyncio.Event().wait()
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None


class _HangingFactory:
    def __call__(self) -> _HangsOnEnter:
        return _HangsOnEnter()


async def test_the_writer_side_read_names_what_the_lifecycle_database_actually_holds() -> None:
    """Three states, because the whole remaining question is whether the write landed somewhere else.

    `execute` returns normally only after a terminal write, CI shows no line for the run, and the client still
    reads it in flight. Those three can only hold together if the writer and the client are not looking at one
    database -- so the report asks the writer's own session, and this pins that the answer is readable in every
    case: the row as that database has it, a row that database does not have, and a database that never answers
    (the bounded case, which must return rather than replace the timeout with a second hang).
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from dsa_api.core import database
    from dsa_api.core.database import Base
    from dsa_api.models.analysis import AnalysisRunORM

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            AnalysisRunORM(
                id="run-written",
                dataset_id="ds",
                dataset_path="/tmp/does-not-matter.csv",
                user_query="q",
                status="COMPLETED",
            )
        )
        await session.commit()

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = factory
    try:
        landed = await conftest._writer_side_row("run-written")
        assert "status=COMPLETED" in landed, landed
        assert "factory bind is that engine=False" in landed, landed
        absent = await conftest._writer_side_row("run-not-in-this-database")
        assert "row absent" in absent, absent
    finally:
        database.AsyncSessionLocal = previous
        await engine.dispose()

    database.AsyncSessionLocal = _HangingFactory()
    try:
        slow = await conftest._writer_side_row("run-hanging")
        assert "no answer within 3s" in slow, slow
    finally:
        database.AsyncSessionLocal = previous


@pytest.fixture
async def completed_somewhere_else(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[str, None]:
    """A database that says COMPLETED while a client keeps reading the row as in flight.

    This is the shape CI reports: `execute` returned normally, no line named the run, and the client polls
    forever. The fixture makes that state real rather than asserted, so the report can be tested against it.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from dsa_api.core import database
    from dsa_api.core.database import Base
    from dsa_api.models.analysis import AnalysisRunORM

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            AnalysisRunORM(
                id="run-completed-here",
                dataset_id="ds",
                dataset_path="/tmp/does-not-matter.csv",
                user_query="q",
                status="COMPLETED",
            )
        )
        await session.commit()
    monkeypatch.setattr(database, "AsyncSessionLocal", factory)
    try:
        yield "run-completed-here"
    finally:
        await engine.dispose()


class _StillInFlight:
    """The client's view: a 200 whose status never stops being a wait condition."""

    status_code = 200

    async def get(self, url: str) -> _StillInFlight:
        return self

    def json(self) -> dict[str, Any]:
        return {"id": "run-completed-here", "status": "VALIDATION"}


async def test_a_wait_that_expires_prints_what_the_writer_database_holds(
    await_terminal_run: Callable[..., Any], completed_somewhere_else: str
) -> None:
    """The report's last claim has to be the one that distinguishes the two remaining readings.

    Only the raise path carries it, so this drives the real fixture with a client that is stuck in flight while
    the writer's own database already says COMPLETED. If the writer-side read were dropped from the message, or
    ran against a different factory, the line would not name that status -- and the CI reading would stay
    ambiguous, which is the whole reason the line exists.
    """
    with pytest.raises(AssertionError) as raised:
        await await_terminal_run(_StillInFlight(), completed_somewhere_else, timeout_s=0.1)
    message = str(raised.value)
    assert f"writer-side row for {completed_somewhere_else} (same session factory" in message, (
        message
    )
    assert "status=COMPLETED" in message, message
    assert "last seen: {'id': 'run-completed-here', 'status': 'VALIDATION'}" in message, message
    assert "scheduled loop:" in message and "how the lifecycle task ended:" in message, message
