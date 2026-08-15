import pytest
from httpx import ASGITransport, AsyncClient

from dsa_api.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_root() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/")
        assert r.status_code == 200
        assert "Data Science Agent" in r.json()["name"]
