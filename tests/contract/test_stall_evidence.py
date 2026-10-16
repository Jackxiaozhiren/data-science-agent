"""The stall report is an instrument, so it is asserted the way one is: each line must be able to say two things.

A timeout message nobody checks quietly becomes decoration -- the census line in this file once implied more than
`asyncio.all_tasks()` can see (it is loop-local), and nothing failed until the reading was leaned on. Each test
here drives one branch of the report with a fabricated condition and requires the specific words that carry the
discrimination, so a future edit that drops a line, or restores an over-claiming label, is red.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncGenerator
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
    finally:
        database.AsyncSessionLocal = previous
        await engine.dispose()

    recorded = conftest._SCHEDULED_ON.get("run-wiring")
    assert recorded is asyncio.get_running_loop(), (
        f"the router's binding recorded {recorded!r}, not the loop that ran it"
    )
    text = conftest._stall_evidence("run-wiring")
    assert "same as polling loop=True; that loop closed=False" in text, text


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
