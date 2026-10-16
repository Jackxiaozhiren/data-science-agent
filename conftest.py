import asyncio
import importlib
import logging
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
    # R-14: the original AnalysisState behind each handle, held for the app's report view. A state leaking
    # across tests would let one test render another test's run.
    ("dsa_mcp.resources", "_STATE_STORE"),
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
            + _stall_evidence(run_id)
        )

    return _wait


_LIFECYCLE_RECORDS: list[tuple[str, str]] = []


class _CountLifecycleLines(logging.Handler):
    """Count the run lifecycle's own lines process-wide; never absorb one.

    pytest captures logs per test, so a record emitted while an *earlier* test was running is invisible to the
    report of the test that finally times out. That difference is the whole remaining question -- either a third
    silent exit exists, or the write did say so and the reader was looking in another test's capture window.
    """

    def emit(self, record: logging.LogRecord) -> None:
        _LIFECYCLE_RECORDS.append((str(getattr(record, "run_id", "-")), record.getMessage()[:80]))


@pytest.fixture(scope="session", autouse=True)
def count_lifecycle_log_lines():
    logger = logging.getLogger("dsa_api.services.run_lifecycle")
    handler = _CountLifecycleLines(level=logging.WARNING)
    logger.addHandler(handler)
    yield
    logger.removeHandler(handler)


_SCHEDULED_ON: dict[str, asyncio.AbstractEventLoop] = {}


@pytest.fixture(scope="session", autouse=True)
def record_scheduled_loop():
    """Note which loop each run was scheduled on -- the datum the registry cannot give back once it is empty.

    Every CI timeout read `no task for <run>` plus an empty `all_tasks()` census plus no lifecycle line, and the
    leading reading was an orphan: the coroutine was suspended on a loop that had already closed, so no census
    on the polling loop could see it and no thread scan could show a frame. That reading is unfalsifiable with
    the registry alone -- a closed loop leaves no trace there. The loop object itself is the thing to keep, and
    `schedule_run` is the last moment it is still knowable.

    Installed on every module that holds the name, not only the definition: the router imported `schedule_run`
    directly, so patching `run_lifecycle` alone would record nothing for the runs the route actually creates.
    """
    from dsa_api.routers import analysis as analysis_router
    from dsa_api.services import demo_seed, run_lifecycle

    targets = [run_lifecycle, analysis_router, demo_seed]
    originals = [(module, module.schedule_run) for module in targets]

    def _wrap(original):
        def schedule_run(run_id: str):
            task = original(run_id)
            _SCHEDULED_ON[run_id] = task.get_loop()
            return task

        return schedule_run

    for module, original in originals:
        module.schedule_run = _wrap(original)
    yield
    for module, original in originals:
        module.schedule_run = original


def _stall_evidence(run_id: str) -> str:
    """Name the condition the timeout is actually in, instead of leaving it to be inferred from a traceback.

    A wait that expires says only "not terminal yet", which reads the same whether the run is slow, deadlocked
    on a database connection belonging to an event loop that has since closed, or parked in an await that never
    returns. Each line below is read without touching the database (a probe that awaited the hung resource would
    replace the report with a second hang) and each one discriminates a different cause: the task's loop versus
    the running loop, the task's own stack at the suspended await, the pool's checked-out count, and whether the
    registry still holds a task for this run at all.

    Nothing here is wrapped in a handler: this text is appended to a failure that is already real, so a probe
    that can fail quietly would hide the one thing the report exists to show.
    """
    import asyncio
    import threading
    from io import StringIO
    from pathlib import Path

    from dsa_api.core import database as app_database
    from dsa_api.services import run_lifecycle

    lines = ["", "  --- stall evidence ---"]
    running = asyncio.get_running_loop()
    tasks: dict = run_lifecycle._TASKS
    own = tasks.get(run_id)
    if own is None:
        # No task for this run is the answer by itself: nothing remains that could move the row, so the row is
        # frozen because its writer is gone, not because the writer is slow.
        lines.append(
            f"  task registry: no task for {run_id}; {len(tasks)} registered ({sorted(tasks)[:4]})"
        )
    else:
        frame = StringIO()
        if own.done():
            outcome = "cancelled" if own.cancelled() else f"raised {own.exception()!r}"
        else:
            own.print_stack(file=frame)
            outcome = "pending"
        own_loop = own.get_loop()
        lines.append(
            f"  task {run_id}: {outcome}; same loop as running={own_loop is running}; "
            f"task loop closed={own_loop.is_closed()}"
        )
        for entry in [e.strip() for e in frame.getvalue().splitlines() if e.strip()][-4:]:
            lines.append(f"    await: {entry}")

    # The line the CI samples have been missing: with no registry entry the census and the thread scan can only
    # say "not here", which fits both "the writer finished" and "the writer is parked on a loop that closed".
    # The loop captured at schedule time discriminates them -- `same as polling loop=False, closed=True` is the
    # orphan, and `True` says the run was on the loop that is still asking about it.
    scheduled = _SCHEDULED_ON.get(run_id)
    if scheduled is None:
        lines.append(
            f"  scheduled loop: never recorded for {run_id}; "
            f"{len(_SCHEDULED_ON)} run(s) recorded this session ({list(_SCHEDULED_ON)[:4]})"
        )
    else:
        lines.append(
            f"  scheduled loop: {id(scheduled):#x}; same as polling loop={scheduled is running}; "
            f"that loop closed={scheduled.is_closed()}"
        )

    # The discriminator the registry alone cannot supply: an absent entry means either "the writer finished" or
    # "the writer is running and nothing points at it", and those two have different owners. So ask the loop
    # directly -- by coroutine name, and by the run id in that frame's locals -- instead of inferring it.
    live_by_name: dict[str, int] = {}
    for candidate in asyncio.all_tasks():
        if candidate is asyncio.current_task() or candidate.done():
            continue
        coro = candidate.get_coro()
        name = getattr(coro, "__name__", type(coro).__name__)
        live_by_name[name] = live_by_name.get(name, 0) + 1
        if name != "execute":
            continue
        held = getattr(coro, "cr_frame", None)
        if held is None or held.f_locals.get("run_id") != run_id:
            continue
        stack = StringIO()
        candidate.print_stack(file=stack)
        suspended = [e.strip() for e in stack.getvalue().splitlines() if e.strip()]
        lines.append(
            f"  a live execute() for {run_id} IS on this loop while the registry says otherwise -- "
            "the entry was dropped, the task was not. Suspended at:"
        )
        lines.extend(f"    {entry}" for entry in suspended[-4:])
    lines.append(
        f"  live tasks on THIS loop (all_tasks() cannot see another loop's tasks): {live_by_name}"
    )
    # ...so an empty census above is not by itself proof the writer finished: verified against a live task on a
    # second thread's loop, which `all_tasks()` does not list. Frames are thread-wide, so this scan is what
    # licenses the stronger reading -- a coroutine still inside the lifecycle would show its line here, and an
    # empty result with an empty registry means the writer really is gone rather than merely elsewhere.
    frames = []
    for tid, held_frame in sys._current_frames().items():
        node, depth = held_frame, 0
        while node is not None and depth < 30:
            name = node.f_code.co_filename
            if "run_lifecycle.py" in name or "dsa_agent/graph.py" in name:
                frames.append(
                    f"    thread {tid}: {name.rsplit('/', 1)[-1]}:{node.f_lineno} "
                    f"in {node.f_code.co_name}"
                )
                break
            node, depth = node.f_back, depth + 1
    lines.append(f"  threads still inside the lifecycle or the graph: {len(frames)}")
    lines.extend(frames[:6])
    # Two module objects for one file would explain a census that says no task while a task runs: the registry
    # written by the route and the registry read here would be different dicts. The vendored copies under
    # `_vendor` are omitted from coverage, so nothing else in the report would ever show the split. Matched on
    # the shipped module path rather than the bare suffix: `test_analysis_run_lifecycle` ends the same way and
    # is a test module -- the first CI run of this line reported it as though it were a second copy of the code.
    lines.append(
        "  lifecycle module objects loaded: "
        f"{sorted(m for m in sys.modules if m.endswith('dsa_api.services.run_lifecycle'))}"
    )
    seen_for_run = sorted({m for rid, m in _LIFECYCLE_RECORDS if rid == run_id})
    sample = [f"{rid}: {m}" for rid, m in _LIFECYCLE_RECORDS[:4]]
    lines.append(
        f"  lifecycle lines emitted for {run_id} anywhere in this process: "
        f"{seen_for_run or 'none'}; {len(_LIFECYCLE_RECORDS)} WARNING+ line(s) seen session-wide"
    )
    # Whose lines they are matters as much as how many: a session that spoke about other runs while staying
    # quiet about this one is a different failure from a session that never reached either branch.
    if sample:
        lines.append(f"  session-wide lines (first {len(sample)}): {sample}")
    lines.append(f"  engine pool: {app_database.engine.pool.status()}")
    lines.append(
        f"  engine url={app_database.engine.url!r}; cwd={Path.cwd()}; "
        f"threads={[t.name for t in threading.enumerate() if 'Thread' in t.name][:6]}"
    )
    return "\n".join(lines)


@pytest.fixture(scope="session", autouse=True)
def demo_seeding_off_by_default() -> None:
    """No test asks for the demo, so no test should pay for it or be disturbed by it.

    `dsa_api.main`'s lifespan seeds the sample datasets and, in a mode that calls no model, runs one analysis
    per seeded dataset so the first screen has a finished report to show (web plan R-01). Eight unrelated
    files open `TestClient(app)`, and that context manager runs the lifespan -- so a default-on boot would
    execute the agent inside each of them, add seconds per file, and write rows into whichever database the
    process happens to have configured. Measured on 2026-10-15: with the hook live and the flag absent,
    `tests/integration/test_agent_analysis.py::test_api_analysis_flow` timed out waiting for its own run to
    finish, because two boot-generated analyses were writing to the same sqlite file.

    The default in the product stays on -- an opt-in demo would leave a plain `docker compose up` showing the
    empty list the requirement exists to end. `tests/integration/test_demo_seeding.py` turns it back on, and
    one of its tests asserts the flag is what makes the difference, so this line cannot silently stop working.
    """
    import os

    os.environ.setdefault("DSA_DEMO_SEEDING", "off")


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
