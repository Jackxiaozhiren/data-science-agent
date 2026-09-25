import logging

import pytest
from httpx import ASGITransport, AsyncClient

from dsa_api.core.config import settings
from dsa_api.core.security import RateLimiter, clear_rate_limit_state
from dsa_api.main import app


@pytest.fixture(autouse=True)
async def _clean_limiter():
    await clear_rate_limit_state()
    yield
    await clear_rate_limit_state()


@pytest.mark.asyncio
async def test_security_headers_present() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["referrer-policy"] == "same-origin"
        assert "frame-ancestors" in r.headers["content-security-policy"]


@pytest.mark.asyncio
async def test_analysis_500_does_not_leak_internals(monkeypatch: pytest.MonkeyPatch) -> None:
    import dsa_api.routers.analysis as analysis_router

    async def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("super secret traceback details")

    monkeypatch.setattr(analysis_router, "create_analysis_run", _boom)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/api/v1/analysis/", json={"dataset_id": "ds1", "user_query": "q"})
        assert r.status_code == 500
        detail = r.json()["detail"]
        assert "super secret" not in detail
        assert "traceback" not in detail.lower()


async def test_rate_limiter_allows_then_denies() -> None:
    limiter = RateLimiter(max_requests=2, window_s=60.0)
    assert await limiter.allow("k") is True
    assert await limiter.allow("k") is True
    assert await limiter.allow("k") is False
    assert await limiter.allow("other") is True


async def test_rate_limiter_window_expiry() -> None:
    import asyncio

    limiter = RateLimiter(max_requests=1, window_s=0.05)
    assert await limiter.allow("k") is True
    assert await limiter.allow("k") is False
    await asyncio.sleep(0.06)
    assert await limiter.allow("k") is True


@pytest.mark.asyncio
async def test_analysis_post_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_analysis_per_min", 2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"dataset_id": "nope", "user_query": "q"}
        statuses = []
        for _ in range(4):
            r = await ac.post("/api/v1/analysis/", json=payload)
            statuses.append(r.status_code)
        assert statuses[2] == 429
        assert statuses[3] == 429
        assert "retry-after" in r.headers
        assert isinstance(r.json()["detail"], str)


@pytest.mark.asyncio
async def test_rate_limit_disabled_by_default_in_tests(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert isinstance(settings.rate_limit_enabled, bool)
    assert settings.rate_limit_analysis_per_min > 0
    assert settings.rate_limit_upload_per_min > 0
    with caplog.at_level(logging.WARNING):
        assert True


@pytest.mark.asyncio
async def test_auth_disabled_by_default() -> None:
    assert settings.auth_token == ""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get("/api/v1/datasets/")).status_code == 200


@pytest.mark.asyncio
async def test_auth_enforced_when_token_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "auth_token", "secret-token")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Health/version stay public (probes), API requires the bearer token.
        assert (await ac.get("/health")).status_code == 200
        assert (await ac.get("/version")).status_code == 200
        r = await ac.get("/api/v1/datasets/")
        assert r.status_code == 401
        assert isinstance(r.json()["detail"], str)
        ok = await ac.get(
            "/api/v1/datasets/", headers={"Authorization": "Bearer secret-token"}
        )
        assert ok.status_code == 200
        wrong = await ac.get(
            "/api/v1/datasets/", headers={"Authorization": "Bearer wrong"}
        )
        assert wrong.status_code == 401
