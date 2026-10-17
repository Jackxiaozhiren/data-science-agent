"""R-08: the hosted demo lets one visitor read another's upload, and the fix must survive an old file.

Measured before writing this: `grep owner apps/api/src/dsa_api/models/*.py` returned nothing, `config.py:50`
defaults `auth_token` to `""` (public), and `render.yaml` points the API at
`sqlite+aiosqlite:////tmp/dsa.db`. So B7/B8 hold -- and the honest constraint is the one the plan names: the
lifespan creates tables with `Base.metadata.create_all`, which is **checkfirst** and will never `ALTER` an
existing database. An owner column that exists only in the models is therefore a silent no-op on every
database that already exists -- including the deployed demo, which is the shape of bug that looks shipped
and is not.

Three things are pinned, in this order, because the third is the one that catches a false green:

1. An old database -- built from the real models and then `DROP COLUMN owner`, so its shape comes from the
   producer rather than from a transcription that could drift -- comes out with the column present **and its
   rows still readable**, carrying the single local owner.
2. Every owned table is covered. The migration's list is compared against the models' own table set, so
   adding a fourth table without scoping it reddens this file instead of quietly remaining shared.
3. A database that cannot be upgraded **fails to start**, loudly, and the file's schema is checked
   afterwards: a migration that altered one table and died on the next must not be served.

The second half of the requirement is the part a visitor actually feels, and it is pinned the same way -- two
simulated browsers against one deployed demo, every assertion paired with the clause that proves the request
would have succeeded for the right person:

4. One visitor cannot list, read, or act on another's dataset, run, or experiment. Every route that reaches a
   run is walked, and the answer must be the same 404 with the same words the owner would get for an id that
   never existed -- a 409 or a "report not generated" on someone else's id is an existence oracle.
5. The published sample stays readable by a visitor holding an id of their own, because R-08 that empties
   R-01's first screen is a different product. The shared owner is reserved: asking for it in a header does
   not hand over the public rows to write into.
6. `X-DSA-Owner` is a lookup key, so its shape is validated before it reaches a query.

The negative control in test 1 is load-bearing -- without asserting that the fixture really lacked the
column, an up-to-date fixture would certify a migration that never ran.

Everything here runs against a **file** database, never `:memory:`: an in-memory sqlite is one shared
connection, so a rolled-back request can erase a committed row with no error at all -- a trap already
recorded for this repo.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

TABLES = ("datasets", "analysis_runs", "experiments")

_SEED = (
    "INSERT INTO datasets (id, filename, format, path, sha256, size_bytes, created_at) "
    "VALUES ('ds-old', 'sales.csv', 'csv', '/tmp/ds-old.csv', 'deadbeef', 10, '2026-01-01 00:00:00')",
    "INSERT INTO analysis_runs (id, dataset_id, user_query, status, created_at, updated_at) "
    "VALUES ('run-old', 'ds-old', 'Analyze revenue trends', 'COMPLETED', "
    "'2026-01-01 00:00:00', '2026-01-01 00:00:00')",
    "INSERT INTO experiments (id, run_id, dataset_id, name, created_at) "
    "VALUES ('exp-old', 'run-old', 'ds-old', 'ablation_lr', '2026-01-01 00:00:00')",
)


def _columns(path: Path, table: str) -> set[str]:
    with sqlite3.connect(path) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}  # noqa: S608 - fixed names


def _read(path: Path, table: str, column: str) -> list[tuple]:
    with sqlite3.connect(path) as conn:
        return list(conn.execute(f"SELECT {column} FROM {table}"))  # noqa: S608 - fixed identifiers


def _make_old_database(path: Path) -> None:
    """Create the current schema through the ORM, then drop `owner` from every table.

    Writing the old DDL out by hand would keep passing after a real column is renamed or added, because the
    fixture and the models would be two independent stories. Dropping the column from the produced schema
    keeps this a fact about the models.
    """
    import dsa_api.models.analysis  # noqa: F401 - registers the table on Base.metadata
    import dsa_api.models.dataset  # noqa: F401
    import dsa_api.models.experiment  # noqa: F401
    from sqlalchemy import create_engine

    from dsa_api.core.database import Base

    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    with sqlite3.connect(path) as conn:
        for table in TABLES:
            conn.execute(f'ALTER TABLE "{table}" DROP COLUMN owner')
        for statement in _SEED:
            conn.execute(statement)
        conn.commit()


async def _init_against(path: Path) -> None:
    """Run the lifespan's own schema step against this file, with the module engine pointed at it."""
    from dsa_api.core import database

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    original = database.engine
    database.engine = engine
    try:
        await database.init_db()
    finally:
        database.engine = original
        await engine.dispose()


@pytest.mark.asyncio
async def test_an_old_database_gains_the_owner_column_and_keeps_its_rows(tmp_path: Path) -> None:
    from dsa_api.core.ownership import OWNER_DEFAULT

    path = tmp_path / "old.db"
    _make_old_database(path)

    before = {table: _columns(path, table) for table in TABLES}
    assert all("owner" not in cols for cols in before.values()), (
        "the fixture already has an owner column, so this test would certify a migration that never ran: "
        f"{ {t: sorted(c) for t, c in before.items()} }"
    )

    await _init_against(path)

    for table in TABLES:
        after = _columns(path, table)
        assert "owner" in after, f"{table} was not upgraded; its columns are {sorted(after)}"
        owners = [row[0] for row in _read(path, table, "owner")]
        assert owners, f"{table} lost its seeded row during the upgrade"
        assert set(owners) == {OWNER_DEFAULT}, (
            f"{table}'s pre-existing rows carry {set(owners)}, expected the single local owner "
            f"{OWNER_DEFAULT!r}"
        )


def test_every_owned_model_is_in_the_migration_list() -> None:
    """A fourth table that is not scoped is a table where visitors still share rows."""
    import dsa_api.models.analysis  # noqa: F401
    import dsa_api.models.dataset  # noqa: F401
    import dsa_api.models.experiment  # noqa: F401

    from dsa_api.core.database import OWNED_TABLES, Base

    declared = {table.name for table in Base.metadata.sorted_tables}
    assert declared == set(OWNED_TABLES), (
        f"the models declare {sorted(declared)} but the migration upgrades {sorted(OWNED_TABLES)}: "
        "the difference is unscoped storage"
    )


@pytest.mark.asyncio
async def test_a_second_run_over_an_upgraded_database_is_a_no_op(tmp_path: Path) -> None:
    """Idempotence: the lifespan runs on every boot, and the free tier restarts constantly."""
    path = tmp_path / "twice.db"
    _make_old_database(path)
    await _init_against(path)
    first = {table: _columns(path, table) for table in TABLES}
    counts = {table: len(_read(path, table, "id")) for table in TABLES}

    await _init_against(path)

    assert {table: _columns(path, table) for table in TABLES} == first, (
        "the second boot changed the schema"
    )
    assert {table: len(_read(path, table, "id")) for table in TABLES} == counts, (
        "the second boot duplicated or dropped rows"
    )


@pytest.mark.asyncio
async def test_a_database_that_cannot_be_upgraded_refuses_to_start(tmp_path: Path) -> None:
    """The plan's alternative to a silent half-migration: fail, and leave the file exactly as it was."""
    if os.geteuid() == 0:  # pragma: no cover - root ignores the mode bits set here
        pytest.skip("running as root: file modes cannot make a sqlite write fail")

    path = tmp_path / "locked.db"
    _make_old_database(path)
    before = {table: _columns(path, table) for table in TABLES}
    path.chmod(0o444)
    try:
        with pytest.raises(OperationalError):
            await _init_against(path)
    finally:
        path.chmod(0o644)

    assert {table: _columns(path, table) for table in TABLES} == before, (
        "the failed upgrade left a partial schema behind -- one table altered and the rest not is exactly "
        "the half-migrated state that must not be served"
    )


def test_a_forged_or_malformed_owner_id_falls_back_to_the_local_owner() -> None:
    """The column is a lookup key, so its value must not be whatever a client happened to send."""
    from dsa_api.core.ownership import OWNER_DEFAULT, OWNER_SHARED, is_valid_owner, normalise

    assert is_valid_owner("b8cb2f5c_1e3f_4a2a_9d3d_0f1e2d3c4b5a")
    for bad in (
        "",
        "x" * 65,
        "a b",
        "Robert'); DROP TABLE datasets;--",
        "../etc/passwd",
        "é",
        None,
        7,
    ):
        assert not is_valid_owner(bad), f"{bad!r} was accepted as an owner id"
        assert normalise(bad) == OWNER_DEFAULT

    assert is_valid_owner(OWNER_SHARED), (
        "the shared id is a well-shaped string; it is reserved, not invalid"
    )
    assert normalise(OWNER_SHARED) == OWNER_DEFAULT, (
        "a client that names the shared owner would be handed the public rows to write into"
    )


# ---------------------------------------------------------------------------------------------
# Part 2: two browsers, one deployed demo.

A = "0f1e2d3c4b5a-visitor-a"
B = "b8cb2f5c1e3f-visitor-b"


@pytest.fixture
async def two_visitors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[dict[str, Any], None]:
    """One API, one database, two visitors who never met.

    `schedule_run` is stubbed for the whole fixture: which rows a request may see does not depend on what the
    agent computes, and executing a graph here would make the read-shape assertions race with a task.
    """
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from dsa_api.core import database
    from dsa_api.core.database import Base, get_session
    from dsa_api.main import app
    from dsa_api.routers import analysis as analysis_router

    def _no_schedule(run_id: str) -> None:
        return None

    monkeypatch.setattr(analysis_router, "schedule_run", _no_schedule)
    monkeypatch.setenv("DSA_DATASET_DIR", str(tmp_path / "datasets"))

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'demo.db'}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = factory
    app.dependency_overrides[get_session] = _get_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield {"client": client, "factory": factory, "db": tmp_path / "demo.db"}
    finally:
        app.dependency_overrides.clear()
        database.AsyncSessionLocal = previous
        await engine.dispose()


def _as(owner: str) -> dict[str, str]:
    from dsa_api.core.ownership import OWNER_HEADER

    return {OWNER_HEADER: owner}


async def _upload(env: dict[str, Any], owner: str, filename: str, blob: bytes) -> str:
    r = await env["client"].post(
        "/api/v1/datasets/",
        files={"file": (filename, blob, "text/csv")},
        headers=_as(owner),
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _ask(env: dict[str, Any], owner: str, dataset_id: str, question: str) -> str:
    r = await env["client"].post(
        "/api/v1/analysis/",
        json={"dataset_id": dataset_id, "user_query": question},
        headers=_as(owner),
    )
    assert r.status_code == 202, r.text
    return str(r.json()["id"])


@pytest.mark.asyncio
async def test_one_visitor_never_sees_another_s_dataset(two_visitors: dict[str, Any]) -> None:
    env = two_visitors
    ds_a = await _upload(env, A, "revenue-a.csv", b"month,revenue\n1,10\n2,12\n")
    ds_b = await _upload(env, B, "salaries-b.csv", b"dept,salary\na,1\nb,2\n")

    mine = await env["client"].get("/api/v1/datasets/", headers=_as(A))
    assert [d["filename"] for d in mine.json()["datasets"]] == ["revenue-a.csv"], (
        "the list is not the requester's own"
    )
    theirs = await env["client"].get("/api/v1/datasets/", headers=_as(B))
    assert [d["filename"] for d in theirs.json()["datasets"]] == ["salaries-b.csv"]

    forbidden = await env["client"].get(f"/api/v1/datasets/{ds_b}", headers=_as(A))
    assert forbidden.status_code == 404, forbidden.text
    own = await env["client"].get(f"/api/v1/datasets/{ds_a}", headers=_as(A))
    assert own.status_code == 200, own.text


@pytest.mark.asyncio
async def test_no_run_can_be_started_on_another_visitor_s_dataset(
    two_visitors: dict[str, Any],
) -> None:
    """The write path has to be scoped too, or reading is a courtesy the next POST undoes."""
    env = two_visitors
    ds_a = await _upload(env, A, "revenue-a.csv", b"month,revenue\n1,10\n")
    ds_b = await _upload(env, B, "salaries-b.csv", b"dept,salary\na,1\n")

    r = await env["client"].post(
        "/api/v1/analysis/",
        json={"dataset_id": ds_b, "user_query": "What drives revenue?"},
        headers=_as(A),
    )
    assert r.status_code == 404, r.text
    listed = await env["client"].get("/api/v1/analysis/", headers=_as(A))
    assert listed.json()["analyses"] == [], "the refused run still wrote a row"

    own = await _ask(env, A, ds_a, "What drives revenue?")
    assert own.startswith("run-")


@pytest.mark.asyncio
async def test_every_route_onto_a_run_answers_the_same_404_to_a_stranger(
    two_visitors: dict[str, Any],
) -> None:
    """Existence is the leak these routes could still have.

    A 409 on someone's run id says "that run exists and is waiting for approval"; a "Report not yet
    generated" says the same thing more helpfully. Every route therefore has to fail with the answer an id
    that was never issued would get -- and the owner's half of each pair is what proves the route was
    reachable at all.
    """
    env = two_visitors
    ds_a = await _upload(env, A, "revenue-a.csv", b"month,revenue\n1,10\n")
    run_a = await _ask(env, A, ds_a, "What drives revenue?")

    #: (method, path, the status the owner sees, a phrase only the owner may see)
    routes = [
        ("get", "", 200, '"UNDERSTANDING"'),
        ("get", "/progress", 200, "progress_pct"),
        ("get", "/events", 200, '"events"'),
        ("get", "/report", 200, '"run_id"'),
        ("get", "/artifacts", 200, "artifacts"),
        ("get", "/bundle", 404, "no artifact file"),
        ("get", "/evidence/ev-1", 404, "Evidence not found"),
        ("post", "/approve", 409, "not awaiting approval"),
        ("get", "/report?format=markdown", 404, "Report not yet generated"),
    ]
    base = f"/api/v1/analysis/{run_a}"
    for method, suffix, owner_status, owner_phrase in routes:
        url = base + suffix
        headers = _as(A) if method == "get" else {**_as(A), "Accept": "application/json"}
        if suffix == "/events":
            headers["Accept"] = "application/json"
        mine = await getattr(env["client"], method)(url, headers=headers)
        assert mine.status_code == owner_status, (
            f"{url}: owner got {mine.status_code} {mine.text[:160]}"
        )
        assert owner_phrase in mine.text, (
            f"{url}: the owner's answer does not contain {owner_phrase!r}"
        )

        foreign = await getattr(env["client"], method)(url, headers=_as(B))
        assert foreign.status_code == 404, f"{url}: a stranger got {foreign.status_code}"
        assert foreign.json()["detail"] == "Analysis not found", (
            f"{url}: the 404 says {foreign.json()['detail']!r} rather than what an id that never "
            "existed would say, which tells the caller this run is real"
        )


@pytest.mark.asyncio
async def test_an_experiment_belongs_to_the_visitor_who_recorded_it(
    two_visitors: dict[str, Any],
) -> None:
    env = two_visitors
    ds_a = await _upload(env, A, "revenue-a.csv", b"month,revenue\n1,10\n")
    run_a = await _ask(env, A, ds_a, "What drives revenue?")
    created = await env["client"].post(
        "/api/v1/experiments/",
        json={"run_id": run_a, "dataset_id": ds_a, "name": "ablation_lr"},
        headers=_as(A),
    )
    assert created.status_code == 201, created.text
    exp_id = str(created.json()["id"])

    listed = await env["client"].get("/api/v1/experiments/", headers=_as(B))
    assert listed.json()["experiments"] == [], "one visitor's experiments are in another's list"
    fetched = await env["client"].get(f"/api/v1/experiments/{exp_id}", headers=_as(B))
    assert fetched.status_code == 404, fetched.text
    compared = await env["client"].post(
        "/api/v1/experiments/compare", json={"ids": [exp_id]}, headers=_as(B)
    )
    assert compared.status_code == 404, compared.text

    own = await env["client"].get(f"/api/v1/experiments/{exp_id}", headers=_as(A))
    assert own.status_code == 200, own.text
    own_list = await env["client"].get("/api/v1/experiments/", headers=_as(A))
    assert [e["id"] for e in own_list.json()["experiments"]] == [exp_id]


@pytest.mark.asyncio
async def test_the_duplicate_submit_guard_does_not_answer_for_two_visitors(
    two_visitors: dict[str, Any],
) -> None:
    """The suppression is a courtesy to one browser, not a global lock on one question.

    Two visitors can only ever share a dataset through the published sample, so that is how this is set up --
    the same question, the same id, two different owners.
    """
    from dsa_api.core.ownership import OWNER_SHARED
    from dsa_api.services.dataset_service import save_dataset

    env = two_visitors
    tmp = env["db"].parent / "sample.csv"
    tmp.write_bytes(b"month,revenue\n1,10\n2,12\n")
    async with env["factory"]() as session:
        published = await save_dataset(
            session,
            filename="sample.csv",
            tmp_path=tmp,
            size_bytes=tmp.stat().st_size,
            content_type="text/csv",
            head=tmp.read_bytes()[:4096],
            owner=OWNER_SHARED,
        )
    dataset_id = str(published["id"])
    question = "What drives revenue?"

    first = await _ask(env, A, dataset_id, question)
    again = await env["client"].post(
        "/api/v1/analysis/",
        json={"dataset_id": dataset_id, "user_query": question},
        headers=_as(A),
    )
    assert again.status_code == 200 and str(again.json()["id"]) == first, (
        "the duplicate-submit guard stopped working for the visitor it belongs to"
    )

    other = await env["client"].post(
        "/api/v1/analysis/",
        json={"dataset_id": dataset_id, "user_query": question},
        headers=_as(B),
    )
    assert other.status_code == 202, (
        f"the second visitor was told the first one's run: {other.text[:200]}"
    )
    assert str(other.json()["id"]) != first, (
        "two visitors' identical questions collapsed into one row"
    )


@pytest.mark.asyncio
async def test_a_forged_shared_owner_gets_the_public_rows_and_no_extra_ones(
    two_visitors: dict[str, Any],
) -> None:
    """Claiming the reserved id must not be a key to someone else's data, or a way to publish your own."""
    from dsa_api.core.ownership import OWNER_DEFAULT, OWNER_SHARED

    env = two_visitors
    ds_b = await _upload(env, B, "salaries-b.csv", b"dept,salary\na,1\n")

    claimed = await env["client"].get("/api/v1/datasets/", headers=_as(OWNER_SHARED))
    assert [d["filename"] for d in claimed.json()["datasets"]] == [], (
        "a client that names the shared owner read another visitor's upload"
    )
    assert (
        await env["client"].get(f"/api/v1/datasets/{ds_b}", headers=_as(OWNER_SHARED))
    ).status_code == 404

    upload = await _upload(env, OWNER_SHARED, "everyone-can-see.csv", b"x,y\n1,2\n")
    as_default = await env["client"].get(f"/api/v1/datasets/{upload}", headers=_as(OWNER_DEFAULT))
    assert as_default.status_code == 200, (
        "the forged upload did not land in the local owner's rows, so the reservation is not holding it back"
    )
    still_private = await env["client"].get(f"/api/v1/datasets/{upload}", headers=_as(A))
    assert still_private.status_code == 404, "an upload made while claiming `shared` became public"
    owners = {row[0] for row in _read(env["db"], "datasets", "owner")}
    assert OWNER_SHARED not in owners, (
        f"{sorted(owners)}: a client wrote a row under the reserved owner"
    )


def test_every_route_that_touches_an_owned_table_asks_who_is_calling() -> None:
    """The drift this file cannot afford: a new endpoint that reads through a scoped service, unscoped.

    Each service function makes `owner` a required keyword, so a route that forgets it is a ``TypeError`` -- but
    only once a request reaches it. This is the check that fails at import time instead, over the parser rather
    than over a line scan, because a handler whose signature grew a body still has to be read correctly.
    """
    import ast

    scoped = {
        "create_pending_run",
        "get_analysis_run",
        "list_analysis_runs",
        "get_dataset",
        "list_datasets",
        "save_dataset",
        "create_experiment",
        "get_experiment",
        "list_experiments",
    }
    root = Path(__file__).resolve().parents[2] / "apps/api/src/dsa_api/routers"
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            body = ast.get_source_segment(source, node) or ""
            if not any(name in body for name in scoped):
                continue
            if "Depends(resolve_owner)" not in body:
                offenders.append(f"{path.name}::{node.name}")
    assert not offenders, (
        f"{offenders} read or write an owned table without resolving the caller's owner; give the handler "
        "`owner: str = Depends(resolve_owner)` and pass it down"
    )
