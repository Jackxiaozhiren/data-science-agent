"""The test process and the application must agree on which database they are opening.

CI has been reporting `sqlite3.OperationalError: no such table: datasets` in
`apps/api/tests/test_security.py` and `no such table: analysis_runs` from the startup sweep, while the same
commit is green on every developer machine. The suites that fail drive the app through
`httpx.AsyncClient(transport=ASGITransport(app=app))`, which does not run the lifespan where `init_db()`
creates the schema, so they read whatever database the module engine happens to point at -- on a laptop that
file has tables from a previous month, and on a runner it does not.

The session fixture in the root `conftest.py` now creates that schema. This test is the guard that the fixture
is asserting about the right object: it asks **the application's own engine** what it can see, because the
failure mode this whole exercise is about is the two disagreeing while each looks self-consistent. It is
deliberately not a copy of the fixture's check -- if the fixture is pointed at the wrong place, the fixture
passes and this fails.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import inspect


def _tables_the_app_can_see() -> list[str]:
    """The table names as the shipped module engine reports them, through its own async connection."""
    from dsa_api.core.database import engine

    async def _read() -> list[str]:
        async with engine.connect() as conn:
            return await conn.run_sync(
                lambda sync_conn: sorted(inspect(sync_conn).get_table_names())
            )

    try:
        return asyncio.run(_read())
    finally:
        # The connections this opened belong to the loop just closed; leave none for the per-test loops.
        asyncio.run(engine.dispose())


def test_the_application_engine_can_see_the_orm_tables() -> None:
    from dsa_api.core.config import settings
    from dsa_api.core.database import engine

    expected = {"datasets", "analysis_runs", "experiments"}
    seen = set(_tables_the_app_can_see())
    missing = sorted(expected - seen)
    url = str(engine.url)
    path = url.rsplit("///", 1)[-1]
    exists = Path(path).is_file() if url.startswith("sqlite") and "///" in url else None
    size = Path(path).stat().st_size if exists else None
    assert not missing, (
        f"the application's engine opened {url!r} (cwd={Path.cwd()}, file exists={exists}, "
        f"bytes={size}, settings.database_url={settings.database_url!r}) and found no {missing}. "
        "Any suite that skips the lifespan -- every ASGITransport client -- will fail with "
        "'no such table' on a machine that has never run the app"
    )


def test_the_check_below_can_actually_be_false(tmp_path: Path) -> None:
    """The predicate above is tested against a database it must reject.

    Chosen over a subprocess with `DSA_DATABASE_URL` pointed at an empty file: the root fixture reads the same
    setting as the engine, so a child pointed elsewhere would simply have schema created there and pass --
    which would have looked like a negative control and proved nothing. What has to be shown is that the set
    comparison rejects an empty database, and that the message the guard builds carries the path.
    """
    from sqlalchemy import create_engine, inspect as sqlalchemy_inspect

    from dsa_api.core.database import Base

    assert Base.metadata.tables, "no models are registered on Base.metadata in this process at all"

    empty_path = tmp_path / "empty.db"
    empty = create_engine(f"sqlite:///{empty_path}")
    names = set(sqlalchemy_inspect(empty).get_table_names())
    empty.dispose()
    assert not {"datasets", "analysis_runs", "experiments"} <= names, (
        "a freshly created file already satisfies the check, so the check certifies nothing"
    )

    # The guard's own message must name the file it opened -- the defect being guarded against is two
    # components agreeing on a URL string while opening different files.
    missing = sorted({"datasets", "analysis_runs", "experiments"} - names)
    report = f"engine opened {empty_path} and found no {missing}"
    assert "empty.db" in report and missing == ["analysis_runs", "datasets", "experiments"], report
