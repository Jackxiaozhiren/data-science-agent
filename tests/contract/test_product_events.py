"""R-15: the event vocabulary is published as data, and the emitter refuses what it does not declare.

Measured while writing this: the repository had no analytics of any kind, and §12's reporting rule (§18's
census guards) already polices hand-typed numbers in prose -- so the missing half was the counting. This file
guards the counting's three promises:

1. **Consent is the whole switch.** `DSA_TELEMETRY` unset or `off` means nothing is written and no file is
   created -- local mode ships silent, and the falsification is a full loop that produces an empty log.
2. **The schema is enforced at emit time.** A payload carrying query text, dataset content or a
   user-identifying value raises where the write happens; the guard re-checks the log from disk, so a smuggled
   field cannot pass in either place.
3. **The vocabulary ships in git.** The first version of the demo's evidence read a gitignored directory and
    worked only on the machine that wrote it (§182); this vocabulary is asserted tracked for the same reason.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session

REPO = Path(__file__).resolve().parents[2]
EVENTS_FILE = REPO / "apps/api/src/dsa_api/services/product_events.json"

CSV_BYTES = b"a,b\n1,2.0\n2,3.5\n3,4.1\n4,6.0\n"


@pytest.fixture
async def loop_env(tmp_path: Path) -> AsyncGenerator[dict[str, Any], None]:
    """The app on a fresh in-memory database, consent on, the log in the temp dir."""
    import os

    from dsa_api.core import database
    from dsa_api.main import app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with factory() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = factory
    app.dependency_overrides[get_session] = _get_session
    saved = {
        key: os.environ.get(key)
        for key in (
            "DSA_TELEMETRY",
            "DSA_EVENT_LOG",
            "DSA_DATASET_DIR",
            "DSA_ARTIFACT_ROOT",
            "DSA_LLM_MODE",
        )
    }
    os.environ["DSA_TELEMETRY"] = "on"
    os.environ["DSA_EVENT_LOG"] = str(tmp_path / "events.jsonl")
    os.environ["DSA_DATASET_DIR"] = str(tmp_path / "datasets")
    os.environ["DSA_ARTIFACT_ROOT"] = str(tmp_path / "artifacts")
    os.environ["DSA_LLM_MODE"] = "heuristic"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield {"client": client, "tmp": tmp_path, "log": tmp_path / "events.jsonl"}
    finally:
        app.dependency_overrides.clear()
        database.AsyncSessionLocal = previous
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        await engine.dispose()


def _log(env: dict[str, Any]) -> list[dict[str, Any]]:
    from dsa_api.services.telemetry import read_events

    return read_events(Path(env["log"]))


def test_the_vocabulary_is_tracked_and_well_formed() -> None:
    """The demo's first evidence source was gitignored; this one is asserted into git."""
    listed = subprocess.run(
        ["git", "ls-files", "apps/api/src/dsa_api/services/product_events.json"],  # noqa: S603 - fixed argv
        cwd=REPO,
        capture_output=True,
        check=True,
    )
    assert listed.stdout.strip(), (
        "the event vocabulary is not in git: a clone would emit nothing and nobody could tell"
    )
    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    assert spec["consent"]["default"] == "off", (
        "local mode must ship silent; a default-on counter is the thing R-15 refuses to be"
    )
    for event in spec["events"]:
        assert {"name", "emitter", "status", "payload"} <= set(event)
        assert not (set(event["payload"]) & set(spec["prohibited_payload_keys"])), (
            f"{event['name']} declares a payload field the vocabulary itself forbids"
        )


def test_the_prohibited_list_covers_the_classes_the_spec_names() -> None:
    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    banned = set(spec["prohibited_payload_keys"])
    classes = {
        "query text": {"query", "user_query", "task", "objective"},
        "dataset content": {
            "content",
            "filename",
            "dataset_path",
            "rows",
            "columns",
            "profile",
            "result",
        },
        "user-identifying values": {"user_id", "session_id", "email", "ip"},
    }
    for named, representatives in classes.items():
        assert banned & representatives, (
            f"the {named} class lost every representative key from the prohibited list"
        )


def test_consent_off_writes_nothing_at_all(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from dsa_api.services.telemetry import record_event

    monkeypatch.setenv("DSA_TELEMETRY", "off")
    record_event("run_started", dataset_id="abc-123", reasoning_mode="heuristic")
    monkeypatch.delenv("DSA_TELEMETRY", raising=False)
    record_event("run_started", dataset_id="abc-123", reasoning_mode="heuristic")
    monkeypatch.setenv("DSA_TELEMETRY", "OFF")  # case-insensitive off spellings
    record_event("run_started", dataset_id="abc-123", reasoning_mode="heuristic")
    assert not Path(loop_env["log"]).exists(), (
        "the consent gate let a write through: no variable may mean counting"
    )


def test_the_emitter_refuses_what_the_vocabulary_does_not_declare() -> None:
    """Falsification of the emit-time contract: each refusal is the schema working, in the request's path."""
    from dsa_api.services import telemetry

    with pytest.raises(ValueError, match="not in the published vocabulary"):
        telemetry.record_event("page_viewed", page="landing")
    with pytest.raises(ValueError, match="prohibited keys"):
        telemetry.record_event(
            "run_started",
            dataset_id="abc",
            reasoning_mode="heuristic",
            user_query="why did churn rise",
        )
    with pytest.raises(ValueError, match="undeclared payload keys"):
        # `page` is neither declared for run_started nor in a prohibited class: it is simply not part of
        # this event -- the vocabulary is per-event, not global.
        telemetry.record_event(
            "run_started", dataset_id="abc", reasoning_mode="heuristic", page="landing"
        )
    with pytest.raises(ValueError, match="identifier-like"):
        telemetry.record_event(
            "run_started",
            dataset_id="abc",
            reasoning_mode="The user asked about churn in the west region last quarter",
        )


async def _run_full_loop(env: dict[str, Any]) -> None:
    files = {"file": ("t.csv", CSV_BYTES, "text/csv")}
    r = await env["client"].post("/api/v1/datasets/", files=files)
    assert r.status_code == 201, r.text
    dataset_id = r.json()["id"]
    r = await env["client"].post(
        "/api/v1/analysis/",
        json={"dataset_id": dataset_id, "user_query": "Analyze correlation between a and b"},
    )
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]
    for _ in range(600):
        row = await env["client"].get(f"/api/v1/analysis/{run_id}")
        assert row.status_code == 200, row.text
        if str(row.json().get("status")) in ("COMPLETED", "FAILED"):
            break
        import anyio

        await anyio.sleep(0.05)
    else:
        raise AssertionError(f"run {run_id} never reached a terminal status")
    report = await env["client"].get(f"/api/v1/analysis/{run_id}/report?format=markdown")
    assert report.status_code == 200, report.text[:200]


@pytest.mark.asyncio
async def test_a_full_loop_produces_the_funnel_sequence_with_clean_payloads(
    loop_env: dict[str, Any],
) -> None:
    """The accept, end to end: one loop, the expected events in order, re-checked from the file on disk."""
    from dsa_api.services.telemetry import consent_enabled

    assert consent_enabled(), "the fixture is supposed to turn consent on"

    await _run_full_loop(loop_env)
    events = _log(loop_env)
    names = [e["event"] for e in events]
    assert names == ["run_started", "run_completed", "export_taken"], f"the funnel recorded {names}"
    started = events[0]["payload"]
    assert set(started) == {"dataset_id", "reasoning_mode"}
    assert re.fullmatch(r"[A-Za-z0-9._:/-]{0,64}", started["reasoning_mode"])
    completed = events[1]["payload"]
    assert completed["run_status"] == "COMPLETED"
    export = events[2]["payload"]
    assert export == {"export_format": "markdown", "mode": "audited"}


@pytest.mark.asyncio
async def test_the_logged_records_recheck_clean_from_disk(loop_env: dict[str, Any]) -> None:
    """The guard reads the file the way a report would -- and re-runs the emitter's own refusals on it."""
    from dsa_api.services import telemetry

    await _run_full_loop(loop_env)
    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    prohibited = set(spec["prohibited_payload_keys"])
    rule_match = re.search(r"matching (\^\S+\$)", spec["prohibited_value_rule"])
    assert rule_match, "the value rule no longer states its pattern the way this guard reads it"
    payload_rule = re.compile(rule_match.group(1))
    for record in _log(loop_env):
        assert not (set(record["payload"]) & prohibited), (
            f"{record['event']} carried a prohibited key"
        )
        for key, value in record["payload"].items():
            assert (
                value is None or isinstance(value, (bool, int)) or payload_rule.match(str(value))
            ), f"{record['event']}.{key} = {value!r} is free text in the log"
    assert telemetry.consent_enabled()
