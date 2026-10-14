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
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
