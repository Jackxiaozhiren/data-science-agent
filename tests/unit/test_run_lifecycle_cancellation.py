"""One exit of the run lifecycle wrote no row and said nothing, and three CI runs were read by elimination.

`execute` documents that "when ``execute`` returns, the row is terminal", and every other exit honours it: a
failed graph writes FAILED and logs, a failed terminal write logs and writes again. Cancellation was the hole --
`_finish` returned before either, so the only trace of a cancelled lifecycle was a client polling a status that
nothing would ever change again. This pins that the exit now names itself, and states honestly that the row it
leaves is still in flight: writing a terminal status from inside a cancelled coroutine is the detached-write
shape §174 already rejected, so that half stays the lifecycle owner's decision instead of being smuggled in here.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.core import database
from dsa_api.core.database import Base
from dsa_api.models.analysis import AnalysisRunORM
from dsa_api.services import run_lifecycle

RUN_ID = "run-cancel01"
LOGGER = "dsa_api.services.run_lifecycle"


@pytest.fixture
async def memory_database(monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[Any, None]:
    """A one-row database reached through the same module attribute the lifecycle resolves at call time."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        session.add(
            AnalysisRunORM(
                id=RUN_ID,
                dataset_id="ds",
                dataset_path="/tmp/does-not-matter.csv",
                user_query="q",
                status="VALIDATION",
            )
        )
        await session.commit()

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = factory
    try:
        yield factory
    finally:
        database.AsyncSessionLocal = previous
        await engine.dispose()


@pytest.fixture
def graph_that_never_finishes(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace the analysis call with one that stays in flight, so the only way out is a cancel."""
    import dsa_agent.graph

    seen: dict[str, Any] = {"started": asyncio.Event(), "task": None}

    async def _hang(**kwargs: Any) -> None:
        seen["started"].set()
        seen["task"] = asyncio.current_task()
        await asyncio.Event().wait()

    monkeypatch.setattr(dsa_agent.graph, "run_analysis", _hang)
    return seen


async def test_cancelling_a_lifecycle_names_itself(
    memory_database: Any,
    graph_that_never_finishes: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    started = graph_that_never_finishes["started"]

    with caplog.at_level("ERROR", logger=LOGGER):
        task = run_lifecycle.schedule_run(RUN_ID)
        await asyncio.wait_for(started.wait(), timeout=10)
        task.cancel()
        # A done callback is scheduled on the loop, not run inline with the cancel.
        await asyncio.sleep(0.1)

    messages = [record.getMessage() for record in caplog.records if record.name == LOGGER]
    assert any("cancelled before writing a terminal row" in m for m in messages), messages
    named = [
        record.__dict__.get("run_id")
        for record in caplog.records
        if record.name == LOGGER and "cancelled" in record.getMessage()
    ]
    assert named == [RUN_ID], f"the line has to name the run it is about: {named}"

    inner = graph_that_never_finishes["task"]
    if inner is not None and not inner.done():
        inner.cancel()
        await asyncio.sleep(0)


async def test_a_write_for_a_run_this_database_does_not_have_says_so(
    memory_database: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """The second silent exit, and the one that actually fired on CI.

    `session_factory()` is resolved at call time -- documented as deliberate, so a background task follows the
    app's current engine -- which means a database swap mid-run routes every later write for this row into a
    database that has no such row. The write then returned without a word, and the reader was left with a run
    that looks in progress forever: all four tool calls ok, `status: VALIDATION`, `error: null`, and nothing in
    any log. Returning (rather than raising) still stands, because the remedy for a frozen row is the lifecycle
    owner's decision; what is no longer optional is saying that it happened, and where.
    """
    with caplog.at_level("ERROR", logger=LOGGER):
        await run_lifecycle._write("run-nowhere", status="COMPLETED")

    messages = [record.getMessage() for record in caplog.records if record.name == LOGGER]
    assert any("discarded" in m and "run-nowhere" in m for m in messages), messages
    named = [
        record.__dict__.get("run_id")
        for record in caplog.records
        if record.name == LOGGER and "discarded" in record.getMessage()
    ]
    assert named == ["run-nowhere"], named
    assert any(str(database.engine.url) in m for m in messages), (
        "the line has to name the database it wrote to"
    )


async def test_a_cancelled_lifecycle_leaves_the_row_in_flight_and_the_registry_empty(
    memory_database: Any, graph_that_never_finishes: dict[str, Any]
) -> None:
    """What the cancellation actually leaves behind, recorded rather than hoped for.

    Asserted as current behaviour on purpose: the registry no longer knows about the run while the row is still
    in flight, which is the state a client reads as "still working" forever. Closing that gap means writing a
    terminal status from a cancelled coroutine, and §174 already recorded why the detached task that requires is
    not the answer.
    """
    started = graph_that_never_finishes["started"]

    task = run_lifecycle.schedule_run(RUN_ID)
    await asyncio.wait_for(started.wait(), timeout=10)
    task.cancel()
    await asyncio.sleep(0.1)

    assert RUN_ID not in run_lifecycle._TASKS, (
        "the done callback pops the entry whatever the outcome"
    )
    async with memory_database() as session:
        row = await session.get(AnalysisRunORM, RUN_ID)
    assert row is not None
    assert row.status in run_lifecycle.IN_FLIGHT_STATUSES, (
        f"the row was left on {row.status!r}, which this module's own vocabulary calls in flight"
    )

    inner = graph_that_never_finishes["task"]
    if inner is not None and not inner.done():
        inner.cancel()
        await asyncio.sleep(0)
