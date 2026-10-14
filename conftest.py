import importlib
import sys
import tomllib
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
for p in [
    ROOT / "apps/api/src",
    ROOT / "packages/agent/src",
    ROOT / "packages/llm/src",
    ROOT / "packages/datasets/src",
    ROOT / "packages/evaluation/src",
    ROOT / "packages/tools/src",
    ROOT / "packages/execution/src",
    ROOT / "packages/statistics/src",
    ROOT / "packages/ml/src",
    ROOT / "packages/visualization/src",
    ROOT / "packages/evidence/src",
    ROOT / "packages/reports/src",
    ROOT / "packages/mcp/src",
    ROOT / "src",
]:
    if p.exists():
        sys.path.insert(0, str(p))

# Dev truth is workspace source: importing data_science_agent inserts its
# _vendor dir at sys.path[0] (needed for the published wheel), which would
# shadow packages/*/src in tests and split coverage onto the vendored copies.
# Demote _vendor to a fallback so `import dsa_*` resolves to workspace source.
try:
    import data_science_agent  # noqa: F401

    _vendor_dir = str(ROOT / "src" / "data_science_agent" / "_vendor")
    while _vendor_dir in sys.path:
        sys.path.remove(_vendor_dir)
    sys.path.append(_vendor_dir)
except Exception:  # noqa: S110 - best-effort test-only path demotion
    pass

# --- per-test isolation of process-global mutable state (audit §87 / Phase 4 target 4) -----------
#
# Derived by AST scan of the shipped trees, not by guesswork: these are the only module-level
# containers whose value is written after import. Before this existed the suite shared them across
# every test -- `tests/unit/test_tool_cache_failure_not_stored.py` hand-rolled its own
# `_TOOL_CACHE.pop()` cleanup, `reset_call_log()` was called by no test at all, and 37 files each
# called `bootstrap()` as if to defend against somebody else clearing the registry. With no ordering
# plugin installed, that coupling is latent rather than absent, and a tool served from another test's
# cache is exactly the green-but-never-ran result audit §76 caught once already.
#
# `tests/test_process_global_isolation.py` reads this tuple back out of the AST, asserts every entry
# still resolves to a real container, and asserts the set is *complete* against the same scan -- so a
# fifth cache added to shipped code turns that test red instead of quietly going unisolated.
_ISOLATED_GLOBALS = (
    ("dsa_agent.graph", "_TOOL_CACHE"),
    ("dsa_llm.cost", "_CALL_LOG"),
    ("dsa_mcp.resources", "_ANALYSIS_STORE"),
    ("dsa_tools.registry", "_REGISTRY"),
    # The in-flight analysis tasks (R-03). A registry of live asyncio tasks leaking across tests would
    # hand one test another's run id, and the stale task would keep writing through a disposed engine.
    ("dsa_api.services.run_lifecycle", "_TASKS"),
)


def _snapshot(obj: object) -> object:
    if isinstance(obj, dict):
        return dict(obj)
    if isinstance(obj, list):
        return list(obj)
    if isinstance(obj, set):
        return set(obj)
    raise TypeError(
        f"unsupported container type {type(obj).__name__}; register a dict/list/set only"
    )


def _restore(obj: object, saved: object) -> None:
    # In place, so that `from dsa_agent.graph import _TOOL_CACHE` aliases still point at the restored
    # object; rebinding the module attribute would leave those aliases holding the stale value.
    if isinstance(obj, dict) and isinstance(saved, dict):
        obj.clear()
        obj.update(saved)
    elif isinstance(obj, list) and isinstance(saved, list):
        obj[:] = saved
    elif isinstance(obj, set) and isinstance(saved, set):
        obj.clear()
        obj.update(saved)
    else:
        raise TypeError(f"snapshot/type mismatch: {type(obj).__name__} vs {type(saved).__name__}")


@pytest.fixture(scope="session")
def declared_version() -> str:
    """The version `pyproject.toml` declares -- the one owner for tests that cite a release line.

    Five assertions used to hard-code the number, so every bump had to edit them and a test that restates
    a literal certifies only the copy. Comparing against the manifest instead checks the property that
    matters: the shipped module, the SDK surface and the notebook metadata all agree with the build.
    """
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]


@pytest.fixture
def await_terminal_run():
    """Wait for a run the API is executing in the background to stop (web plan R-03).

    A create call now answers while the work is still going, so every test that reads a finished report has
    to wait for it the way a client does -- through ``GET /api/v1/analysis/{id}``. A fixed sleep would pass
    on a quiet machine and fail on a loaded runner, and neither outcome would be about the code.
    """

    async def _wait(client: object, run_id: str, *, timeout_s: float = 30.0) -> dict:
        import asyncio
        import time

        from dsa_api.services.run_lifecycle import REVIEW_STATUS, TERMINAL_STATUSES

        stopped = {*TERMINAL_STATUSES, REVIEW_STATUS}
        deadline = time.monotonic() + timeout_s
        last: dict = {}
        while time.monotonic() < deadline:
            row = await client.get(f"/api/v1/analysis/{run_id}")  # type: ignore[attr-defined]
            assert row.status_code == 200, row.text  # type: ignore[attr-defined]
            last = row.json()  # type: ignore[attr-defined]
            if str(last.get("status")) in stopped:
                return last
            await asyncio.sleep(0.05)
        raise AssertionError(
            f"run {run_id} never reached a terminal status within {timeout_s}s; last seen: {last}"
        )

    return _wait


@pytest.fixture(scope="session", autouse=True)
def default_database_has_schema() -> None:
    """Guarantee the ORM tables exist in the database the app's module engine points at, once per run.

    Several suites drive the app with `httpx.AsyncClient(transport=ASGITransport(app=app))`, which never runs
    the lifespan where `init_db()` lives. Those tests therefore issue reads against a database nobody in
    their own process created: they pass only because some earlier test opened a `TestClient` (whose context
    manager does run the lifespan), or because the machine already had a populated `data/dsa.db`. On a clean
    checkout the outcome depends on collection order, and that is exactly what CI showed -- `no such table:
    datasets` from `apps/api/tests/test_security.py` and `no such table: analysis_runs` from the startup
    sweep, green on every developer machine that had run the app. The application guarantees its own schema at
    boot; this guarantees the same fact for the test process rather than borrowing it from a neighbour.

    The DDL goes through a sync engine on purpose. The module-level async engine binds to whichever event loop
    touches it first, and a session-scoped fixture cannot claim the per-test loops that follow; a sqlite file
    created by one driver is fully visible to the other.

    CI status of this fixture: at `bccb4e0` it created the file and the same seven tests still failed, so
    writing the DDL is necessary but not sufficient -- what is asserted below is the disagreement itself.
    """
    from pathlib import Path

    from sqlalchemy import create_engine

    # Register the models on Base.metadata, the same three imports apps/api/src/dsa_api/main.py makes.
    import dsa_api.models.analysis  # noqa: F401
    import dsa_api.models.dataset  # noqa: F401
    import dsa_api.models.experiment  # noqa: F401
    from dsa_api.core.config import settings
    from dsa_api.core.database import Base

    url = settings.database_url
    if "+aiosqlite" in url:
        url = url.replace("+aiosqlite", "")
    if url.startswith("sqlite:"):
        Path(url.rsplit("///", 1)[-1]).parent.mkdir(parents=True, exist_ok=True)

    sync_engine = create_engine(url)
    Base.metadata.create_all(sync_engine, checkfirst=True)
    sync_engine.dispose()

    # Verify through the seam the application itself uses, not only through the engine that wrote the DDL.
    # The first CI run of this fixture created the file and the auth suite still failed with `no such table`,
    # which can only mean the two ends disagree about which database this URL names. Saying so here is the
    # point: a named failure at session setup beats seven downstream ones whose cause is inferred from a
    # traceback that cannot show what the process actually opened.
    import asyncio

    from sqlalchemy import inspect as sqlalchemy_inspect

    from dsa_api.core import database as app_database

    async def _tables() -> list[str]:
        async with app_database.engine.connect() as conn:
            return await conn.run_sync(
                lambda sync_conn: sorted(sqlalchemy_inspect(sync_conn).get_table_names())
            )

    seen = asyncio.run(_tables())
    # Connections created above are bound to this throwaway loop; drop them before the per-test loops start.
    asyncio.run(app_database.engine.dispose())
    missing = sorted({"datasets", "analysis_runs", "experiments"} - set(seen))
    if missing:
        # Warned here rather than raised: a session-scoped autouse fixture that raises reddens every test in the
        # run, which is a worse signal than one named failure. The hard assertion lives in
        # tests/contract/test_test_database_is_reachable.py, where it can fail on its own and name both urls.
        warnings.warn(
            f"schema was written through {url!r} but the application's engine sees no {missing} "
            f"(engine url={app_database.engine.url!r}, cwd={Path.cwd()}) -- the test process and the "
            "application are opening different databases",
            stacklevel=1,
        )


@pytest.fixture(autouse=True)
def isolate_database_binding(request: pytest.FixtureRequest):
    """Pin the two names the routes resolve through, and say who moved them.

    `isolate_process_global_state` restores the *contents* of known containers, which cannot see a rebinding:
    a suite that assigns `database.AsyncSessionLocal = async_sessionmaker(tmp_engine)` and leaves it in place
    sends every later route to a different database than the one `engine` -- and therefore the schema-creating
    fixture -- refers to. That is the shape CI is reporting: the session's own guard sees the tables through
    `engine` while `apps/api/tests/test_security.py`, in the same run, gets `no such table: datasets`. So the
    binding goes back, and the test that moved it is named rather than left to be inferred from a failure
    forty files away.
    """
    from dsa_api.core import database

    before = (database.AsyncSessionLocal, database.engine)
    yield
    after = (database.AsyncSessionLocal, database.engine)
    if after != before:
        warnings.warn(
            f"{request.node.nodeid} rebound dsa_api.core.database.AsyncSessionLocal/engine "
            f"(before={before[0].kw.get('bind')!r} after={after[0].kw.get('bind')!r}) without restoring it; "
            "the binding has been put back for the rest of the run",
            stacklevel=1,
        )
        database.AsyncSessionLocal, database.engine = before


@pytest.fixture(autouse=True)
def isolate_process_global_state():
    """Reset every writable module-level container after each test, whatever the test did to it."""
    live = []
    for module_name, attr in _ISOLATED_GLOBALS:
        obj = getattr(importlib.import_module(module_name), attr)
        live.append((obj, _snapshot(obj)))
    yield
    for obj, saved in live:
        _restore(obj, saved)
