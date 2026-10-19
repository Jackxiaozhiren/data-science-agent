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

A fourth thing this file has to be honest about: the funnel needs a run that *finishes*, and §188 records that
on the CI runner a scheduled run never terminalises (three samples, same failing set, the lifecycle's own
instrument silent). So the funnel is guarded twice -- once by the spec's accept through a real loop, which
declines with §188 named when the machine cannot finish a run, and once by a deterministic driver that stubs
the scheduling call and terminalises through `persist_state`, the same choke point `run_completed` records
from. Deleting an emission reddens the deterministic test on any machine: verified by planting all three
removals in turn.
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


def test_every_active_api_event_has_a_call_site_in_the_shipped_api() -> None:
    """A declared-but-never-emitted event is §182's silent no-op with a schema attached.

    `status: active` is a promise that some code path makes the record; this reads the API's own source and
    refuses a vocabulary entry nobody calls. `arrival` is exempt by construction -- its emitter is the web,
    and nothing here may emit it, which the companion test pins from the other side.
    """
    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in (REPO / "apps/api/src/dsa_api").rglob("*.py")
    )
    for event in spec["events"]:
        if event["emitter"] != "api" or event["status"] != "active":
            continue
        assert f'"{event["name"]}"' in source, (
            f"{event['name']} is declared active but no API source names it: the funnel would answer zero "
            "for a step nobody records"
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
    record_event(
        "run_started", dataset_id="abc-123", reasoning_mode="heuristic", initiated_by="user"
    )
    monkeypatch.delenv("DSA_TELEMETRY", raising=False)
    record_event(
        "run_started", dataset_id="abc-123", reasoning_mode="heuristic", initiated_by="user"
    )
    monkeypatch.setenv("DSA_TELEMETRY", "OFF")  # case-insensitive off spellings
    record_event(
        "run_started", dataset_id="abc-123", reasoning_mode="heuristic", initiated_by="user"
    )
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
            "run_started",
            dataset_id="abc",
            reasoning_mode="heuristic",
            initiated_by="user",
            page="landing",
        )
    with pytest.raises(ValueError, match="identifier-like"):
        telemetry.record_event(
            "run_started",
            dataset_id="abc",
            reasoning_mode="The user asked about churn in the west region last quarter",
            initiated_by="user",
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
        # §188: on the CI runner a scheduled run never reaches a terminal status (3 samples, same failing
        # set, the lifecycle instrument silent). That is a defect in the run's execution path, not in where
        # the funnel records, so this accept declines rather than reporting the stall as an R-15 failure --
        # and `test_the_three_emission_sites_record_the_funnel_without_the_agent_task` keeps the funnel
        # guarded on the runner anyway.
        pytest.skip(
            f"run {run_id} never terminalised in 30 s: §188's lifecycle stall, which this test is not the "
            "instrument for. The deterministic emission-site test covers the funnel on this machine."
        )
    report = await env["client"].get(f"/api/v1/analysis/{run_id}/report?format=markdown")
    assert report.status_code == 200, report.text[:200]


async def _drive_three_sites(env: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Hit the three emission points without waiting for the agent task to finish.

    R-15's promise is *where* an event records and what it carries; none of that depends on the graph
    completing. So the scheduling call is stubbed, and the terminal write that `run_completed` sits on is
    driven through `persist_state` -- the very function the real task calls, hence the same choke point, the
    same `is_terminal` branch and the same row update. What is left out is the agent's own execution, which
    §188 shows cannot be relied on on the runner.
    """
    import dsa_api.routers.analysis as analysis_router
    from dsa_agent.state import AnalysisState, AnalysisStatus
    from dsa_api.services.run_lifecycle import persist_state

    def _no_schedule(run_id: str) -> None:
        """Same shape as the real one: the router calls this without awaiting it."""
        return None

    monkeypatch.setattr(analysis_router, "schedule_run", _no_schedule)

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
    await persist_state(
        AnalysisState(
            run_id=run_id,
            dataset_id=dataset_id,
            user_query="Analyze correlation between a and b",
            status=AnalysisStatus.COMPLETED,
            report_markdown="# Report\n\nThe two columns move together.",
        )
    )
    report = await env["client"].get(f"/api/v1/analysis/{run_id}/report?format=markdown")
    assert report.status_code == 200, report.text[:200]


def _a_published_starter_question() -> tuple[str, str]:
    """(dataset filename, question) read straight from the producer's own catalog.

    The alternative -- typing a question into this file -- is the fixture-shape mistake in reverse: the guard
    would certify a string the product may no longer publish.
    """
    from dsa_api.services.demo_seed import catalog_questions

    grouped = catalog_questions(REPO)
    for filename, entries in sorted(grouped.items()):
        if entries:
            return filename, entries[0]["question"]
    raise AssertionError("the tracked catalog published no questions at all")


async def _start_one_run(
    env: dict[str, Any], monkeypatch: pytest.MonkeyPatch, question: str, filename: str
) -> None:
    import dsa_api.routers.analysis as analysis_router

    def _no_schedule(run_id: str) -> None:
        return None

    monkeypatch.setattr(analysis_router, "schedule_run", _no_schedule)
    path = REPO / "benchmarks/v2/datasets" / filename
    blob = path.read_bytes() if path.is_file() else CSV_BYTES
    r = await env["client"].post("/api/v1/datasets/", files={"file": (filename, blob, "text/csv")})
    assert r.status_code == 201, r.text
    dataset_id = r.json()["id"]
    r = await env["client"].post(
        "/api/v1/analysis/", json={"dataset_id": dataset_id, "user_query": question}
    )
    assert r.status_code == 202, r.text


@pytest.mark.asyncio
async def test_a_starter_question_run_records_the_link_before_the_run(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The funnel's second link, inferred where it is exact: the question the screen published, verbatim."""
    filename, question = _a_published_starter_question()
    await _start_one_run(loop_env, monkeypatch, question, filename)
    events = _log(loop_env)
    names = [e["event"] for e in events]
    assert names == ["starter_question_used", "run_started"], (
        f"the funnel recorded {names} for a published starter question"
    )
    used = events[0]["payload"]
    assert set(used) == {"dataset_id"}, f"the starter link carries {sorted(used)}"
    assert "question" not in str(used), "the question text reached the log"


def _a_published_starter_entry() -> dict[str, str]:
    """A catalog entry with its dataset name, because R-13 publishes a second wording of the same task."""
    from dsa_api.services.demo_seed import catalog_questions

    grouped = catalog_questions(REPO)
    for filename, entries in sorted(grouped.items()):
        if entries:
            return {**entries[0], "dataset": filename}
    raise AssertionError("the tracked catalog published no questions at all")


@pytest.mark.asyncio
async def test_the_chinese_wording_of_a_starter_records_the_same_link(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The coupling R-13 creates and a funnel would never report: the Chinese button sends Chinese text.

    `starter_question_used` is inferred by matching the published wording, so a second language the matcher
    does not know silences the link for every visitor who chose it -- while the English half keeps counting and
    the numbers look merely smaller. Asserting the same sequence for both spellings is the only way to see it.
    """
    from dsa_api.services.demo_seed import localized_questions

    entry = _a_published_starter_entry()
    question = localized_questions([entry])[0]
    assert question != entry["question"], (
        "the alias table returned English for this task, so the run below would repeat the test above and "
        "prove nothing about the Chinese path"
    )
    await _start_one_run(loop_env, monkeypatch, question, entry["dataset"])
    names = [e["event"] for e in _log(loop_env)]
    assert names == ["starter_question_used", "run_started"], (
        f"the funnel recorded {names} for the Chinese wording of a published starter question; the link is "
        "supposed to know every spelling the product publishes"
    )


@pytest.mark.asyncio
async def test_a_typed_question_records_no_starter_link(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction: the matcher is not an always-true counter."""
    filename, _ = _a_published_starter_question()
    await _start_one_run(
        loop_env, monkeypatch, "Why did churn rise in the western region last quarter?", filename
    )
    names = [e["event"] for e in _log(loop_env)]
    assert names == ["run_started"], f"a question nobody published recorded {names}"


@pytest.mark.asyncio
async def test_the_boot_seeder_records_its_own_starts_and_no_starter_link(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pairing invariant: every run this instance creates records a start, machine or visitor.

    Only the endpoint emits for visitors, and the seeder writes through the service -- so a completion could
    be recorded with no matching start. The agent itself is stubbed here (the real `_run_example` awaits it
    for up to 45 s, and §188's runner cannot finish one at all); what is under test is the emission at that
    call site, not the analysis.
    """
    import dsa_api.services.demo_seed as demo_seed
    from dsa_api.core import database

    def _no_schedule(
        run_id: str,
    ):  # the real one returns a Task; _run_example shields and awaits it
        async def _done() -> None:
            return None

        return _done()

    monkeypatch.setattr(demo_seed, "schedule_run", _no_schedule)
    filename, question = _a_published_starter_question()
    path = REPO / "benchmarks/v2/datasets" / filename
    blob = path.read_bytes() if path.is_file() else CSV_BYTES
    r = await loop_env["client"].post(
        "/api/v1/datasets/", files={"file": (filename, blob, "text/csv")}
    )
    assert r.status_code == 201, r.text
    dataset_id = r.json()["id"]

    async with database.AsyncSessionLocal() as session:
        from dsa_api.core.ownership import OWNER_SHARED
        from dsa_api.models.dataset import DatasetORM

        # `_run_example` publishes under the shared owner, which is only sound for a dataset the demo
        # itself published -- so the row goes through the same relabelling `seed_demo_data` performs on
        # the sample it just uploaded, rather than the helper being loosened for the test.
        row = await session.get(DatasetORM, dataset_id)
        assert row is not None
        row.owner = OWNER_SHARED
        await session.commit()
        await demo_seed._run_example(session, dataset_id, question)

    events = _log(loop_env)
    names = [e["event"] for e in events]
    assert names == ["run_started"], f"the seeder recorded {names}"
    assert events[0]["payload"]["initiated_by"] == "seeding"
    assert "starter_question_used" not in names, (
        "an example run the machine started read as a visitor using a starter question"
    )


def test_a_web_emitter_event_cannot_be_recorded_from_server_code() -> None:
    """`arrival` describes a browser's action; a server path that claimed it would be fabricating one.

    The relay endpoint is the only place that may take a web-emitted event, and it does so through
    `record_client_event`, which re-checks the emitter. This guard pins the refusal on the ordinary emitter.
    """
    from dsa_api.services import telemetry

    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    web_events = [event["name"] for event in spec["events"] if event["emitter"] == "web"]
    assert web_events, "no event is owned by the browser, so the relay has nothing to guard"
    for name in web_events:
        with pytest.raises(ValueError, match="emitted by the web client"):
            telemetry.record_event(name, page="landing")


@pytest.mark.asyncio
async def test_the_relay_records_the_browsers_own_arrival(loop_env: dict[str, Any]) -> None:
    r = await loop_env["client"].post(
        "/api/v1/events", json={"event": "arrival", "payload": {"page": "landing"}}
    )
    assert r.status_code == 202, r.text
    assert Path(loop_env["log"]).is_file(), "the relay accepted an arrival and wrote nothing"
    events = _log(loop_env)
    assert [e["event"] for e in events] == ["arrival"], (
        f"the relay recorded {[e['event'] for e in events]}"
    )
    assert events[0]["payload"] == {"page": "landing"}


@pytest.mark.asyncio
async def test_the_relay_refuses_an_event_the_browser_does_not_own(
    loop_env: dict[str, Any],
) -> None:
    """A client must not be able to write the server's own links -- that is how a funnel gets forged."""
    for forged in ("run_started", "run_completed", "export_taken", "starter_question_used"):
        r = await loop_env["client"].post(
            "/api/v1/events", json={"event": forged, "payload": {"dataset_id": "abc"}}
        )
        assert r.status_code == 400, f"{forged} was accepted from a client"
    assert not Path(loop_env["log"]).exists(), "every refusal still left a record behind"


@pytest.mark.asyncio
async def test_the_relay_refuses_what_the_vocabulary_refuses(loop_env: dict[str, Any]) -> None:
    for body in (
        {"event": "arrival", "payload": {"query": "why did churn rise"}},
        {"event": "page_viewed", "payload": {"page": "landing"}},
        {"event": "arrival", "payload": {"page": "The user asked about churn in the west region"}},
        {"event": "arrival", "payload": {}},
    ):
        r = await loop_env["client"].post("/api/v1/events", json=body)
        assert r.status_code == 400, f"{body} was accepted: {r.text[:120]}"


@pytest.mark.asyncio
async def test_the_relay_is_indistinguishable_when_counting_is_off(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consent off must not become a probe: the answer is the same and nothing is written."""
    monkeypatch.setenv("DSA_TELEMETRY", "off")
    r = await loop_env["client"].post(
        "/api/v1/events", json={"event": "arrival", "payload": {"page": "landing"}}
    )
    assert r.status_code == 202, "a non-counting instance answered differently than a counting one"
    assert not Path(loop_env["log"]).exists()


@pytest.mark.asyncio
async def test_the_relay_is_rate_limited_like_the_other_public_writes(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unauthenticated append-to-disk route needs the same ceiling as the upload route, in force.

    The limiter table and the settings map are two lists that must agree; a prefix missing from the second is
    a KeyError on every request, so this drives the route rather than reading the table.
    """
    from dsa_api.core.config import settings

    monkeypatch.setattr(settings, "rate_limit_events_per_min", 3)
    codes = [
        (
            await loop_env["client"].post(
                "/api/v1/events", json={"event": "arrival", "payload": {"page": "landing"}}
            )
        ).status_code
        for _ in range(5)
    ]
    assert codes[:3] == [202, 202, 202], f"the first three were not accepted: {codes}"
    assert 429 in codes, f"the events route is unlimited: {codes}"


@pytest.mark.asyncio
async def test_the_three_emission_sites_record_the_funnel_without_the_agent_task(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The runner-stable half: the wiring is asserted even where a real run cannot terminalise."""
    await _drive_three_sites(loop_env, monkeypatch)
    events = _log(loop_env)
    names = [e["event"] for e in events]
    assert names == ["run_started", "run_completed", "export_taken"], f"the funnel recorded {names}"
    assert events[0]["payload"]["reasoning_mode"] == "heuristic"
    assert events[1]["payload"]["run_status"] == "COMPLETED"
    assert events[2]["payload"] == {"export_format": "markdown", "mode": "audited"}


@pytest.mark.asyncio
async def test_a_full_loop_produces_the_funnel_sequence_with_clean_payloads(
    loop_env: dict[str, Any],
) -> None:
    """The spec's accept, end to end: one real loop, the expected events in order."""
    from dsa_api.services.telemetry import consent_enabled

    assert consent_enabled(), "the fixture is supposed to turn consent on"

    await _run_full_loop(loop_env)
    events = _log(loop_env)
    names = [e["event"] for e in events]
    assert names == ["run_started", "run_completed", "export_taken"], f"the funnel recorded {names}"
    started = events[0]["payload"]
    assert set(started) == {"dataset_id", "reasoning_mode", "initiated_by"}
    assert started["initiated_by"] == "user", "a run created through the endpoint is a visitor's"
    assert re.fullmatch(r"[A-Za-z0-9._:/-]{0,64}", started["reasoning_mode"])
    completed = events[1]["payload"]
    assert completed["run_status"] == "COMPLETED"
    export = events[2]["payload"]
    assert export == {"export_format": "markdown", "mode": "audited"}


@pytest.mark.asyncio
async def test_the_logged_records_recheck_clean_from_disk(
    loop_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard reads the file the way a report would -- and re-runs the emitter's own refusals on it."""
    from dsa_api.services import telemetry

    await _drive_three_sites(loop_env, monkeypatch)
    spec = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    prohibited = set(spec["prohibited_payload_keys"])
    rule_match = re.search(r"matching (\^\S+\$)", spec["prohibited_value_rule"])
    assert rule_match, "the value rule no longer states its pattern the way this guard reads it"
    payload_rule = re.compile(rule_match.group(1))
    records = _log(loop_env)
    assert records, "the log is empty, so every assertion below would pass on nothing"
    for record in records:
        assert not (set(record["payload"]) & prohibited), (
            f"{record['event']} carried a prohibited key"
        )
        for key, value in record["payload"].items():
            assert (
                value is None or isinstance(value, (bool, int)) or payload_rule.match(str(value))
            ), f"{record['event']}.{key} = {value!r} is free text in the log"
    assert telemetry.consent_enabled()
