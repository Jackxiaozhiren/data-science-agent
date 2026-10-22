"""The pagination sentence in `docs/api.md` describes exactly the routes that paginate.

The bullet used to open "Lists accept `?limit=` (1–1000, default 100)", which read as a property of the API. It
is a property of three routes. `/api/v1/research/experiments` also returns `{experiments, total}`, also looks like
a list, and accepts no query parameter at all -- it truncates to `RESULTS_LIMIT` -- so the generalisation was a
small invitation to write a client that gets ten items and no error.

Everything here is read from `app.openapi()`, because that is the contract a client can actually discover: the
bounds FastAPI publishes are the bounds it enforces, and a route that gains a `limit` parameter appears in the
same structure the test enumerates. The doc's numbers are derived from that schema rather than transcribed, so a
changed ceiling has to be written down before the gate goes green.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.main import app
from dsa_api.routers.artifacts import RESULTS_LIMIT

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "docs/api.md").read_text(encoding="utf-8")


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _paginated_get_paths() -> dict[str, dict[str, dict]]:
    """Every GET route that publishes a `limit` parameter, with the schema the server advertises."""
    found: dict[str, dict[str, dict]] = {}
    for path, operations in app.openapi()["paths"].items():
        get = operations.get("get")
        if not get:
            continue
        params = {p["name"]: p for p in (get.get("parameters") or [])}
        if "limit" in params or "offset" in params:
            found[path] = params
    return found


def _pagination_bullet() -> str:
    """The bullet that makes the `?limit=` promise, found by what it says rather than by how it opens.

    It wraps across three lines, so a single-line search finds nothing, and the sentence that carries the claim
    is free to be reworded -- the parameters are the stable part.
    """
    blocks: list[str] = []
    current: list[str] = []
    for line in DOC.splitlines():
        if line.startswith("- "):
            if current:
                blocks.append(" ".join(current))
            current = [line[2:]]
        elif current and line.strip().startswith(("- ", "| ", "```")):
            blocks.append(" ".join(current))
            current = []
            blocks.append(line)
        elif current and line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    matches = [b for b in blocks if "?limit=" in b and "?offset=" in b]
    assert len(matches) == 1, (
        f"the docs must carry exactly one pagination promise, found {len(matches)}: {matches}"
    )
    return _fold(matches[0])


def test_the_documented_list_of_paginated_routes_is_the_real_one() -> None:
    """Containment in both directions, enumerated from the schema rather than from a list in this test."""
    bullet = _pagination_bullet()
    paginated = set(_paginated_get_paths())
    assert paginated, "no route publishes limit -- this guard has stopped measuring anything"
    documented = set(re.findall(r"`(/api/v1/[a-z_]+(?:/[a-z_]*)?)`", bullet))
    assert documented == paginated, (
        f"documented but not paginated: {sorted(documented - paginated)}, "
        f"paginated but undocumented: {sorted(paginated - documented)}"
    )


def test_the_documented_bounds_are_the_bounds_the_routes_publish() -> None:
    bullet = _pagination_bullet()
    bounds: set[tuple[int, int, int, int]] = set()
    for params in _paginated_get_paths().values():
        limit, offset = params["limit"]["schema"], params["offset"]["schema"]
        bounds.add(
            (
                limit.get("minimum"),
                limit.get("maximum"),
                limit.get("default"),
                offset.get("minimum"),
            )
        )
    assert len(bounds) == 1, f"the routes disagree about their own bounds: {sorted(bounds)}"
    minimum, maximum, default, offset_minimum = bounds.pop()
    assert f"({minimum}–{maximum}, default {default})" in bullet, bullet
    assert f"`?offset=` (default {offset_minimum})" in bullet, bullet


@pytest.fixture(autouse=True)
async def _clean_limiter():
    """These requests are GETs, but the module-level counters are shared with the suites that POST."""
    from dsa_api.core.security import clear_rate_limit_state

    await clear_rate_limit_state()
    yield
    await clear_rate_limit_state()


@pytest.fixture
async def ac():
    from dsa_api.core import database
    from dsa_api.core.database import Base, get_session
    from dsa_api.main import app as api_app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = SessionLocal
    api_app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        yield client
    api_app.dependency_overrides.clear()
    database.AsyncSessionLocal = previous
    await engine.dispose()


@pytest.mark.asyncio
async def test_the_published_bounds_are_enforced_not_just_advertised(ac: AsyncClient) -> None:
    """A schema a server does not obey is a lie a client discovers only by being truncated.

    The positive case is here for the same reason: a guard that only asserts refusals would pass for a route
    that refused everything.
    """
    for path in _paginated_get_paths():
        for query in ("limit=0", "limit=1001", "offset=-1"):
            r = await ac.get(f"{path}?{query}")
            assert r.status_code == 422, f"{path}?{query} answered {r.status_code}: {r.text[:120]}"
        r = await ac.get(f"{path}?limit=1&offset=0")
        assert r.status_code == 200, (
            f"{path} refuses a request inside its own bounds: {r.text[:120]}"
        )
        body = r.json()
        assert "total" in body, (
            f"{path} returns no total, which the docs promise alongside the array: {list(body)}"
        )
        assert any(isinstance(value, list) for value in body.values()), (
            f"{path} returns no array to page through: {list(body)}"
        )


def test_the_list_that_looks_like_the_others_is_said_not_to_paginate() -> None:
    """`/api/v1/research/experiments` returns an array plus a total and accepts no query parameter."""
    path = "/api/v1/research/experiments"
    assert path not in _paginated_get_paths(), (
        f"{path} gained pagination -- its doc row and this test must change with it"
    )
    rows = [line for line in DOC.splitlines() if line.startswith(f"| GET | `{path}`")]
    assert len(rows) == 1, f"the route must appear exactly once in the table: {rows}"
    row = rows[0]
    assert f"first {RESULTS_LIMIT} by name" in row, (
        f"the cap is {RESULTS_LIMIT} but the row does not say so: {row}"
    )
    assert "Not paginated" in row, f"the row does not warn a client away from `?limit=`: {row}"


@pytest.mark.asyncio
async def test_the_capped_list_reports_the_uncapped_total(
    ac: AsyncClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The sentence a client reads is the difference between these two numbers, so both have to be right."""
    from dsa_api.routers import artifacts

    results = tmp_path / Path(artifacts.RESULTS_DIR)
    results.mkdir(parents=True)
    monkeypatch.setattr(artifacts, "REPO_ROOT", tmp_path)
    for i in range(RESULTS_LIMIT + 2):
        (results / f"ablation_{i:02d}.json").write_text("{}", encoding="utf-8")
    r = await ac.get("/api/v1/research/experiments")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["experiments"]) == RESULTS_LIMIT, body
    assert body["total"] == RESULTS_LIMIT + 2, body
