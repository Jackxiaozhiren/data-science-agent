import pytest
from httpx import ASGITransport, AsyncClient

from dsa_api.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert set(body["details"]) == {"process"}
        assert body["details"]["process"]["status"] == "ok"

        r2 = await ac.get("/ready")
        assert r2.status_code == 200
        ready_body = r2.json()
        assert ready_body["status"] in ("ok", "degraded")
        assert set(ready_body["details"]) == {"process", "db"}

        deep = await ac.get("/health/dependencies")
        assert deep.status_code == 200
        deep_body = deep.json()
        assert deep_body["status"] in ("ok", "degraded")
        assert set(deep_body["details"]) == {"duckdb", "polars", "llm"}

        rv = await ac.get("/version")
        assert rv.status_code == 200
        assert "version" in rv.json()


@pytest.mark.asyncio
async def test_root() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/")
        assert r.status_code == 200
        assert "Data Science Agent" in r.json()["name"]


@pytest.mark.asyncio
async def test_local_web_origin_is_allowed_by_default() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
