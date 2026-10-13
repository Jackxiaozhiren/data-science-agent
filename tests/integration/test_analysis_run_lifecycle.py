"""R-03: a run is a job, not an HTTP request.

Measured before this file existed (2026-10-13, `apps/api/src/dsa_api/services/analysis_service.py:33`):
``create_analysis_run`` awaited ``run_analysis`` and only then inserted the row, so during the whole run
there was nothing to read -- ``GET /api/v1/analysis/{id}`` 404s, ``/progress`` 404s, and ``/events`` could
only ever be a replay of a finished state. The web client blocked on the POST for the same reason, which is
B5: with a stub planner it is seconds, with a real model it is minutes of a frozen tab.

The four properties the requirement names, one test each:

1. the create call returns while the run is still executing, and the row is observable at that moment;
2. an exception raised inside the task lands as a terminal error **on the row**, not as a 500 on an
   unrelated read;
3. the event stream carries events for an in-flight run rather than only replaying a completed one;
4. a double submit returns the run already in flight instead of starting a second one.

Plus the case the design creates and the old code could not have: a row left non-terminal by a restart is
swept to a failure, because "a failed run must look failed, never frozen" is exactly what an orphaned
``UNDERSTANDING`` row violates.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session

CSV = b"a,b,group\n" + b"".join(
    f"{i},{i * 1.5},{'A' if i % 2 else 'B'}\n".encode() for i in range(1, 13)
)


def _completed_state(run_id: str) -> Any:
    """A finished run in the shape the graph returns, so the reads have something real to project."""
    from dsa_agent.state import AnalysisState, AnalysisStatus, ToolCallRecord

    return AnalysisState(
        run_id=run_id,
        dataset_id="ds",
        user_query="Analyze correlation between a and b",
        objective="Correlate a and b",
        status=AnalysisStatus.COMPLETED,
        tool_calls=[
            ToolCallRecord(
                call_id="TC-aaaaaaaa",
                tool="correlation_analysis",
                input={},
                output={"r": 0.9},
                status="ok",
                duration_ms=5,
            )
        ],
    )


@pytest.fixture
async def env(tmp_path: Path) -> AsyncGenerator[dict[str, Any], None]:
    """A file-backed database, because the task opens its own session after the request is gone.

    ``sqlite+aiosqlite:///:memory:`` gives each connection its own database, so a background session would
    be reading a different (empty) file from the one the request wrote -- a test artifact that would look
    exactly like a lost write.

    ``dsa_api.main`` is imported before ``create_all`` on purpose: the ORM modules register their tables on
    ``Base.metadata`` when they are first imported, and ``main`` is what imports them. Creating the schema
    before that import produces a database with zero tables and a failure that reads like a broken fixture.
    """
    from dsa_api.core import database
    from dsa_api.main import app

    url = f"sqlite+aiosqlite:///{tmp_path / 'lifecycle.db'}"
    engine = create_async_engine(url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = factory
    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield {"client": client, "factory": factory, "app": app}
    app.dependency_overrides.clear()
    database.AsyncSessionLocal = previous
    await engine.dispose()


async def _dataset(client: AsyncClient) -> str:
    r = await client.post("/api/v1/datasets/", files={"file": ("t.csv", CSV, "text/csv")})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _wait_for_status(
    client: AsyncClient, run_id: str, wanted: Callable[[str], bool], *, attempts: int = 200
) -> dict[str, Any]:
    """Poll the row the way a client does. Fails loudly if the run never leaves its in-flight state."""
    for _ in range(attempts):
        row = await client.get(f"/api/v1/analysis/{run_id}")
        assert row.status_code == 200, row.text
        status = str(row.json().get("status"))
        if wanted(status):
            return row.json()
        await asyncio.sleep(0.02)
    raise AssertionError(f"run {run_id} never reached a wanted status (last: {status})")


async def _create(client: AsyncClient, ds_id: str, query: str, *, within: float = 3.0):
    """POST with a deadline, because a blocking create is the defect under test.

    Without a bound, the current implementation simply never returns while the run is gated and the suite
    hangs -- which is true to the bug and useless as a report. The timeout is stated as the assertion it
    proves.
    """
    try:
        return await asyncio.wait_for(
            client.post("/api/v1/analysis/", json={"dataset_id": ds_id, "user_query": query}),
            within,
        )
    except TimeoutError as exc:
        raise AssertionError(
            f"POST /api/v1/analysis/ returned nothing within {within}s while the run was in flight: the "
            "create path still runs the whole graph before answering (premise B5)"
        ) from exc


class _Gate:
    """A run that stays in flight until the test releases it, with the calls it received."""

    def __init__(self) -> None:
        self.release = asyncio.Event()
        self.calls: list[dict[str, Any]] = []
        self.started = asyncio.Event()

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        on_update = kwargs.get("on_update")
        if on_update is not None:
            await on_update(_progress_state(str(kwargs["run_id"])))
        self.started.set()
        await self.release.wait()
        return _completed_state(str(kwargs["run_id"]))


def _progress_state(run_id: str) -> Any:
    from dsa_agent.state import AnalysisState, AnalysisStatus, ToolCallRecord

    return AnalysisState(
        run_id=run_id,
        dataset_id="ds",
        user_query="Analyze correlation between a and b",
        objective="Correlate a and b",
        status=AnalysisStatus.ANALYSIS,
        tool_calls=[
            ToolCallRecord(
                call_id="TC-bbbbbbbb",
                tool="profile_dataset",
                input={},
                output={"rows": 12},
                status="ok",
                duration_ms=3,
            )
        ],
    )


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> _Gate:
    """Replace the planner+executor at the seam the service actually imports.

    ``create_analysis_run`` does ``from dsa_agent.graph import run_analysis`` inside its body, so patching
    the module attribute is the same seam production uses -- not a parallel path the test invented.
    """
    from dsa_agent import graph

    g = _Gate()
    monkeypatch.setattr(graph, "run_analysis", g)
    return g


@pytest.mark.asyncio
async def test_create_responds_while_the_run_is_still_executing(
    env: dict[str, Any], gate: _Gate
) -> None:
    """The row must exist and read as in-flight at the moment the create call returns."""
    client = env["client"]
    ds_id = await _dataset(client)

    r = await _create(client, ds_id, "does a drive b")
    assert r.status_code == 202, f"expected 202 Accepted, got {r.status_code}: {r.text}"
    body = r.json()
    run_id = str(body["id"])
    assert r.headers.get("location") == f"/api/v1/analysis/{run_id}", dict(r.headers)

    mid = await client.get(f"/api/v1/analysis/{run_id}")
    assert mid.status_code == 200, (
        "the row was not observable while the run executed -- the create path still blocks"
    )
    from dsa_agent.state import AnalysisStatus

    in_flight = {
        s.value for s in AnalysisStatus if s.value not in {"COMPLETED", "FAILED", "HUMAN_REVIEW"}
    }
    assert mid.json()["status"] in in_flight, mid.json()

    progress = await client.get(f"/api/v1/analysis/{run_id}/progress")
    assert progress.status_code == 200, progress.text
    assert progress.json()["steps_total"] >= 0

    gate.release.set()
    final = await _wait_for_status(client, run_id, lambda s: s == "COMPLETED")
    assert final["status"] == "COMPLETED"
    assert len(gate.calls) == 1, gate.calls
    assert gate.calls[0]["run_id"] == run_id, (
        "the task ran a different run id than the row advertises"
    )


@pytest.mark.asyncio
async def test_an_exception_inside_the_task_lands_on_the_row_not_on_the_read(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash after the response cannot become a 500; the row is the only place left to tell the truth."""
    from dsa_agent import graph

    async def boom(**kwargs: Any) -> Any:
        raise RuntimeError("database connection string leaked into a tool traceback")

    monkeypatch.setattr(graph, "run_analysis", boom)
    client = env["client"]
    ds_id = await _dataset(client)

    r = await _create(client, ds_id, "does a drive b")
    assert r.status_code == 202, r.text
    run_id = str(r.json()["id"])

    row = await _wait_for_status(client, run_id, lambda s: s == "FAILED")
    assert row["error"], row
    # The traceback goes to the server log; the public row names the kind of failure and nothing more.
    assert "database connection string" not in json.dumps(row), (
        "the exception message reached a public field -- a client now reads internals off the run"
    )

    for path in (f"/api/v1/analysis/{run_id}/progress", f"/api/v1/analysis/{run_id}/report"):
        got = await client.get(path)
        assert got.status_code != 500, f"{path} answered 500 for a failed run: {got.text[:120]}"


@pytest.mark.asyncio
async def test_the_event_stream_carries_events_before_the_run_finishes(
    env: dict[str, Any], gate: _Gate
) -> None:
    """Spec 3: live for an in-flight run, tested at the generator seam rather than over HTTP.

    httpx's ``ASGITransport`` buffers a response body until the application finishes writing it, so reading
    a live stream over it cannot return before the run ends -- the test would deadlock while the product
    behaved correctly. The frames come from ``analysis_event_frames``, which is what the route formats; the
    HTTP-level framing of a finished run stays covered by ``tests/integration/test_phase6_api.py``.
    """
    from dsa_api.routers.analysis import analysis_event_frames

    client = env["client"]
    ds_id = await _dataset(client)
    r = await _create(client, ds_id, "does a drive b")
    run_id = str(r.json()["id"])
    await asyncio.wait_for(gate.started.wait(), 5)

    first = await client.get(f"/api/v1/analysis/{run_id}")
    assert first.status_code == 200, first.text

    frames: list[dict[str, Any]] = []
    stream = analysis_event_frames(run_id, first.json(), poll_s=0.05)
    for _ in range(60):
        try:
            frame = await asyncio.wait_for(anext(stream), 5)
        except StopAsyncIteration:
            break
        frames.append(frame)
        if len(frames) == 1:
            still = await client.get(f"/api/v1/analysis/{run_id}")
            assert still.json()["status"] != "COMPLETED", (
                "the run had already finished, so this proves nothing about liveness"
            )
            gate.release.set()
    else:
        raise AssertionError(f"the stream never terminated; frames so far: {frames}")

    kinds = [f.get("event") for f in frames]
    assert "tool_completed" in kinds, kinds
    assert kinds[-1] == "analysis_completed", kinds
    assert len({json.dumps(f, sort_keys=True) for f in frames}) == len(frames), (
        f"the stream re-emitted an event it had already sent: {kinds}"
    )

    fallback = await client.get(
        f"/api/v1/analysis/{run_id}/events", headers={"Accept": "application/json"}
    )
    assert fallback.status_code == 200, fallback.text
    assert fallback.headers.get("content-type", "").startswith("application/json")
    assert "events" in fallback.json(), "the JSON fallback stopped working"

    await _wait_for_status(client, run_id, lambda s: s == "COMPLETED")


@pytest.mark.asyncio
async def test_a_second_submit_returns_the_run_already_in_flight(
    env: dict[str, Any], gate: _Gate
) -> None:
    """Spec 5: the button no longer blocks, so double-submit protection belongs on the create path."""
    client = env["client"]
    ds_id = await _dataset(client)

    first = await _create(client, ds_id, "does a drive b")
    assert first.status_code == 202, first.text
    await asyncio.wait_for(gate.started.wait(), 5)

    second = await _create(client, ds_id, "does a drive b")
    assert second.json()["id"] == first.json()["id"], (
        "a double click started a second run of the same question"
    )
    assert second.status_code == 200, (
        f"a reused run should not claim to have been created: {second.status_code}"
    )

    listing = await client.get("/api/v1/analysis/")
    assert listing.json()["total"] == 1, listing.json()
    assert len(gate.calls) == 1, gate.calls

    gate.release.set()
    await _wait_for_status(client, str(first.json()["id"]), lambda s: s == "COMPLETED")


@pytest.mark.asyncio
async def test_a_run_left_in_flight_by_a_restart_is_swept_to_failed(env: dict[str, Any]) -> None:
    """The new failure mode this design creates: a row whose task died with the previous process.

    Before R-03 there was no window where a row could exist unfinished, so nothing had to answer for it.
    Now there is, and a reader staring at ``UNDERSTANDING`` forever is the frozen page the requirement is
    about. The sweep must leave terminal rows alone -- rewriting a completed run is worse than the bug.
    """
    from dsa_api.models.analysis import AnalysisRunORM
    from dsa_api.services.run_lifecycle import sweep_abandoned_runs

    factory = env["factory"]
    async with factory() as session:
        session.add(
            AnalysisRunORM(
                id="run-abandoned1",
                dataset_id="ds",
                user_query="q",
                status="ANALYSIS",
                state_json=None,
            )
        )
        session.add(
            AnalysisRunORM(
                id="run-donethere",
                dataset_id="ds",
                user_query="q",
                status="COMPLETED",
                state_json=None,
            )
        )
        await session.commit()

    swept = await sweep_abandoned_runs()
    assert swept == 1, swept

    client = env["client"]
    abandoned = await client.get("/api/v1/analysis/run-abandoned1")
    assert abandoned.json()["status"] == "FAILED", abandoned.json()
    assert "restart" in str(abandoned.json()["error"]).lower(), abandoned.json()
    kept = await client.get("/api/v1/analysis/run-donethere")
    assert kept.json()["status"] == "COMPLETED", "the sweep touched a finished run"

    # Sweeping an already-clean set must be a no-op, not a second write: the startup hook runs on every
    # boot, and a sweep that kept rewriting would turn a restart into a rewrite of history.
    assert await sweep_abandoned_runs() == 0


@pytest.mark.asyncio
async def test_the_stream_does_not_replay_an_event_it_already_sent() -> None:
    """The dedupe branch, driven directly: the same snapshot read twice must yield the event once.

    The integration test above cannot see this branch -- its polls each observe something new -- so a stream
    that re-emitted every event on every tick would still pass it. The reader is injected because that is
    why ``analysis_event_frames`` takes one.
    """
    from dsa_api.routers.analysis import analysis_event_frames

    snapshot: dict[str, Any] = {
        "id": "run-dedup",
        "status": "ANALYSIS",
        "state": {
            "agent_messages": [],
            "tool_calls": [
                {
                    "call_id": "TC-dedup01",
                    "tool": "profile_dataset",
                    "status": "ok",
                    "duration_ms": 3,
                }
            ],
            "validation_results": [],
        },
    }
    polls = {"n": 0}

    async def read_row(_run_id: str) -> dict[str, Any]:
        polls["n"] += 1
        if polls["n"] == 1:
            return {**snapshot}
        return {
            **snapshot,
            "status": "COMPLETED",
            "state": {**snapshot["state"], "report_markdown": "# r"},
        }

    frames: list[dict[str, Any]] = []
    stream = analysis_event_frames("run-dedup", {**snapshot}, read_row=read_row, poll_s=0.0)
    while True:
        try:
            frames.append(await asyncio.wait_for(anext(stream), 5))
        except StopAsyncIteration:
            break

    kinds = [f.get("event") for f in frames]
    assert polls["n"] >= 2, "the stream never polled twice, so the dedupe branch was not exercised"
    assert kinds.count("tool_completed") == 1, f"an event was re-emitted across polls: {kinds}"
    assert kinds[-1] == "analysis_completed", kinds


@pytest.mark.asyncio
async def test_executing_a_row_that_no_longer_exists_is_a_no_op(env: dict[str, Any]) -> None:
    """The row can go away between the create response and the task's first read (ephemeral demo disk).

    Reaching for ``row.dataset_id`` on a missing row would raise inside the task and be logged as a crash of
    a run that never existed; the guard is the difference between silence and a false incident.
    """
    from dsa_api.services.run_lifecycle import execute

    await asyncio.wait_for(execute("run-never-stored"), 5)
    gone = await env["client"].get("/api/v1/analysis/run-never-stored")
    assert gone.status_code == 404, gone.text
