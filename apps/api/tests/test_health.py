import pytest
from httpx import ASGITransport, AsyncClient

from dsa_api.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded")
        assert "details" in body
        r2 = await ac.get("/ready")
        assert r2.status_code == 200
        assert r2.json()["status"] in ("ok", "degraded")
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
