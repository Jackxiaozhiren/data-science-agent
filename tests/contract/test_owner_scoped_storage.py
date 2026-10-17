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

The negative control in test 1 is load-bearing -- without asserting that the fixture really lacked the
column, an up-to-date fixture would certify a migration that never ran.

Everything here runs against a **file** database, never `:memory:`: an in-memory sqlite is one shared
connection, so a rolled-back request can erase a committed row with no error at all -- a trap already
recorded for this repo.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import create_async_engine

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
    from dsa_api.core.ownership import OWNER_DEFAULT, is_valid_owner, normalise

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
