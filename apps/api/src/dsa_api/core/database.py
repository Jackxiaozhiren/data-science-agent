from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from dsa_api.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)


class Base(DeclarativeBase):
    pass


AsyncSessionLocal: Any = async_sessionmaker(engine, expire_on_commit=False)


def is_ephemeral_database(url: str) -> bool:
    """True when the DB lives on throwaway storage (data loss on restart).

    The rule itself belongs to `dsa_api.core.storage_state`, which has to answer the same question about the
    dataset and artifact roots too; this stays as the database-named entry point the lifespan and the tests
    use, so the predicate cannot be worded two ways.
    """
    from dsa_api.core.storage_state import is_ephemeral_path

    return is_ephemeral_path(url)


#: Tables whose rows belong to someone. The list is the migration's denominator, and
#: `test_owner_scoped_storage.py` proves it covers every table the models declare -- a table left out here is
#: a table where one visitor still reads another's data.
OWNED_TABLES: tuple[str, ...] = ("datasets", "analysis_runs", "experiments")


async def _upgrade_owned_tables(conn: Any) -> None:
    """ALTER a pre-R-08 database to carry `owner`, because `create_all` will not.

    `Base.metadata.create_all(checkfirst=True)` skips a table that already exists *entirely*: an owner column
    that lives only in the models is a silent no-op on every existing database -- including the deployed
    demo's `/tmp/dsa.db`, which is the case that would have shipped green. All the ALTERs run inside the
    caller's single transaction, so a failure on the second table rolls the first back rather than leaving a
    half-migrated file to be served.

    The DDL cannot be parameter-bound -- SQLite takes no placeholders for identifiers or column defaults --
    so both parts are constants owned here: the table names above, and `OWNER_DEFAULT`, whose identifier shape
    is asserted before it reaches the string.
    """
    from sqlalchemy import text

    from dsa_api.core.ownership import OWNER_DEFAULT, is_valid_owner

    if not is_valid_owner(OWNER_DEFAULT):  # pragma: no cover - guards the DDL construction below
        raise RuntimeError(
            f"OWNER_DEFAULT {OWNER_DEFAULT!r} is not identifier-shaped; refusing to build DDL"
        )

    for table in OWNED_TABLES:
        existing = {
            row[0] for row in (await conn.exec_driver_sql(_TABLE_INFO, (table,))).fetchall()
        }
        if not existing or "owner" in existing:
            continue  # no such table yet (create_all will build it whole), or already upgraded
        ddl = (
            'ALTER TABLE "'
            + table
            + '" ADD COLUMN owner VARCHAR(64) NOT NULL DEFAULT '
            + repr(OWNER_DEFAULT)
        )
        await conn.execute(text(ddl))
        after = {row[0] for row in (await conn.exec_driver_sql(_TABLE_INFO, (table,))).fetchall()}
        if "owner" not in after:
            raise RuntimeError(
                f"the owner column was not added to {table}; the database would keep exposing rows "
                "by id with no owner to scope by"
            )


#: Bound as a parameter, not interpolated: this is the one query in the migration that takes a name from
#: outside itself.
_TABLE_INFO = "SELECT name FROM pragma_table_info(?)"


async def init_db() -> None:
    """Create ORM tables once (lifespan-owned; checkfirst-safe, idempotent)."""
    import logging

    if is_ephemeral_database(settings.database_url):
        logging.getLogger(__name__).warning(
            "database is ephemeral (%s): data will not survive restarts; "
            "use a persistent volume or managed DB for anything beyond demos",
            settings.database_url,
        )
    async with engine.begin() as conn:
        # Upgraded before created: `create_all` is checkfirst and would leave a pre-existing table exactly as
        # it found it, which is how an owner column added only to the models becomes a silent no-op.
        await _upgrade_owned_tables(conn)
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
