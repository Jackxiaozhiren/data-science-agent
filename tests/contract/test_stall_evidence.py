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
