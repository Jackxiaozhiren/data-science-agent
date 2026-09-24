"""REST contract: 201 + Location on creates, limit/offset pagination on lists."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session
from dsa_api.main import app


@pytest.fixture
async def client_with_tmp_db() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


async def _make_experiment(ac: AsyncClient, name: str, run_id: str = "run-1") -> str:
    r = await ac.post(
        "/api/v1/experiments/",
        json={"run_id": run_id, "dataset_id": "ds1", "name": name},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_create_experiment_returns_201_and_location(
    client_with_tmp_db: AsyncClient,
) -> None:
    ac = client_with_tmp_db
    r = await ac.post(
        "/api/v1/experiments/",
        json={"run_id": "run-1", "dataset_id": "ds1", "name": "exp1"},
    )
    assert r.status_code == 201
    exp_id = r.json()["id"]
    assert r.headers["location"] == f"/api/v1/experiments/{exp_id}"


@pytest.mark.asyncio
async def test_upload_dataset_returns_201_and_location(
    client_with_tmp_db: AsyncClient,
) -> None:
    ac = client_with_tmp_db
    files: Any = {"file": ("sales.csv", b"a,b\n1,2\n", "text/csv")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code == 201, r.text
    ds_id = r.json()["id"]
    assert r.headers["location"] == f"/api/v1/datasets/{ds_id}"


@pytest.mark.asyncio
async def test_experiment_list_pagination(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    for i in range(3):
        await _make_experiment(ac, f"exp-{i}")
    page1 = await ac.get("/api/v1/experiments/", params={"limit": 2})
    assert page1.status_code == 200
    body1 = page1.json()
    assert len(body1["experiments"]) == 2
    assert body1["total"] == 3
    page2 = await ac.get("/api/v1/experiments/", params={"limit": 2, "offset": 2})
    assert len(page2.json()["experiments"]) == 1
    assert page2.json()["total"] == 3
    # Backward compat: no params still shaped the same way.
    all_items = await ac.get("/api/v1/experiments/")
    assert len(all_items.json()["experiments"]) == 3


@pytest.mark.asyncio
async def test_dataset_list_pagination(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    for i in range(3):
        files: Any = {"file": (f"d{i}.csv", b"a,b\n1,2\n", "text/csv")}
        r = await ac.post("/api/v1/datasets/", files=files)
        assert r.status_code == 201, r.text
    page = await ac.get("/api/v1/datasets/", params={"limit": 2})
    assert len(page.json()["datasets"]) == 2
    assert page.json()["total"] == 3


@pytest.mark.asyncio
async def test_approve_unknown_run_404(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    r = await ac.post("/api/v1/analysis/nope/approve", json={"note": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_approve_wrong_status_409() -> None:
    import json as _json

    from httpx import ASGITransport
    from httpx import AsyncClient as _AC
    from sqlalchemy.ext.asyncio import async_sessionmaker as _sm
    from sqlalchemy.ext.asyncio import create_async_engine as _eng

    from dsa_api.core.database import Base as _Base
    from dsa_api.core.database import get_session as _get_session
    from dsa_api.main import app as _app
    from dsa_api.models.analysis import AnalysisRunORM

    engine = _eng("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    factory = _sm(engine, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    _app.dependency_overrides[_get_session] = _override
    try:
        async with factory() as seed:
            seed.add(
                AnalysisRunORM(
                    id="run-seed1",
                    dataset_id="ds1",
                    dataset_path="/tmp/x.csv",  # noqa: S108 - fake path string, no file created
                    user_query="q",
                    status="COMPLETED",
                    state_json=_json.dumps({}),
                    error=None,
                )
            )
            await seed.commit()
        async with _AC(transport=ASGITransport(app=_app), base_url="http://test") as ac:
            r = await ac.post("/api/v1/analysis/run-seed1/approve", json={"note": "x"})
            assert r.status_code == 409
    finally:
        _app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_experiment_get_404_and_compare_400(
    client_with_tmp_db: AsyncClient,
) -> None:
    ac = client_with_tmp_db
    assert (await ac.get("/api/v1/experiments/nope")).status_code == 404
    r = await ac.post("/api/v1/experiments/compare", json={"ids": []})
    assert r.status_code == 400
    r2 = await ac.post("/api/v1/experiments/compare", json={"ids": ["missing"]})
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_missing_resources_404(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    assert (await ac.get("/api/v1/analysis/nope")).status_code == 404
    assert (await ac.get("/api/v1/analysis/nope/progress")).status_code == 404
    assert (await ac.get("/api/v1/analysis/nope/events")).status_code == 404
    assert (await ac.get("/api/v1/analysis/nope/report")).status_code == 404
    assert (await ac.get("/api/v1/analysis/nope/artifacts")).status_code == 404
    assert (await ac.get("/api/v1/analysis/nope/evidence/E1")).status_code == 404
    assert (await ac.get("/api/v1/datasets/nope")).status_code == 404
    r = await ac.post("/api/v1/analysis/", json={"dataset_id": "", "user_query": "  "})
    assert r.status_code == 400
    r2 = await ac.post("/api/v1/experiments/", json={"run_id": "", "dataset_id": "d", "name": "x"})
    assert r2.status_code == 400
