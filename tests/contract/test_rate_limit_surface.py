"""The limit an operator reads about has to be the limit the middleware applies.

Three structures describe one control: `_DEFAULT_RULES` (which route gets limited), `_RULE_KNOBS` (which setting
sizes it), and the rate-limit paragraph in `docs/api.md` (what an operator plans capacity around). They agreed on
three of four rules -- `/api/v1/experiments` has answered `429` at 60/min since the rule existed and was named
nowhere -- and the middleware resolves a rule's size through a dict literal, so a route added to one list and not
the other raises `KeyError` inside the request path and reaches the client as a 500 on that route.

The behavioural test below is the half that a documentation pin cannot do: it shows the borrowed knob actually
governs the route that borrows it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.core import security
from dsa_api.core.config import settings
from dsa_api.core.database import Base, get_session
from dsa_api.main import app

REPO = Path(__file__).resolve().parents[2]


def _rate_limit_paragraph() -> str:
    lines = (REPO / "docs/api.md").read_text(encoding="utf-8").splitlines()
    start = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("- Expensive `POST`s are IP rate-limited")
    )
    out = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip() == "" or line.startswith("- "):
            break
        out.append(line)
    # Folded because the bullet wraps: a literal-space pattern goes blind when the text reflows.
    return re.sub(r"\s+", " ", "\n".join(out))


def test_the_limited_routes_and_their_knobs_are_the_same_set() -> None:
    """Neither list may gain a member the other does not know about."""
    limited = {prefix for prefix, _, _ in security._DEFAULT_RULES}
    assert limited == set(security._RULE_KNOBS), (
        f"rules without knobs: {sorted(limited - set(security._RULE_KNOBS))}, "
        f"knobs without rules: {sorted(set(security._RULE_KNOBS) - limited)}"
    )
    for field in security._RULE_KNOBS.values():
        assert hasattr(settings, field), f"{field} is not a Settings attribute"


def test_every_rule_is_documented_at_the_number_it_enforces() -> None:
    paragraph = _rate_limit_paragraph()
    for prefix, _, _ in security._DEFAULT_RULES:
        want = getattr(settings, security._RULE_KNOBS[prefix])
        assert f"`{prefix}` {want}/min" in paragraph, (
            f"{prefix} is limited at {want}/min but the docs do not say so: {paragraph}"
        )


def test_every_knob_the_rules_read_is_named_as_an_env_var() -> None:
    paragraph = _rate_limit_paragraph()
    for field in set(security._RULE_KNOBS.values()):
        name = f"DSA_{field.upper()}"
        assert name in paragraph, f"{field} sizes a rule but the docs never name {name}"


def test_the_switch_the_docs_offer_is_the_one_the_middleware_reads() -> None:
    """`DSA_RATE_LIMIT_ENABLED=false` is the documented way out, so it has to reach `rate_limit_enabled`."""
    paragraph = _rate_limit_paragraph()
    assert "DSA_RATE_LIMIT_ENABLED=false" in paragraph, paragraph
    assert "Retry-After" in paragraph
    assert "rate_limit_enabled" in security.RateLimitMiddleware.dispatch.__code__.co_names


@pytest.fixture(autouse=True)
async def _clean_limiter():
    """The counters are module-level and keyed by client IP, so they outlive the request that filled them."""
    await security.clear_rate_limit_state()
    yield
    await security.clear_rate_limit_state()


@pytest.fixture
async def ac():
    from dsa_api.core import database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    previous = database.AsyncSessionLocal
    database.AsyncSessionLocal = SessionLocal
    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    database.AsyncSessionLocal = previous
    await engine.dispose()


@pytest.mark.asyncio
async def test_experiments_is_limited_and_follows_the_analysis_knob(
    ac: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fourth rule has no knob of its own, so `DSA_RATE_LIMIT_ANALYSIS_PER_MIN` moves it too."""
    monkeypatch.setattr(settings, "rate_limit_analysis_per_min", 2)
    payload = {"run_id": "run-witness", "dataset_id": "ds-witness", "name": "witness"}
    statuses = []
    for _ in range(3):
        r = await ac.post("/api/v1/experiments/", json=payload)
        statuses.append(r.status_code)
    assert statuses[0] != 429, f"the very first request was refused: {statuses}"
    assert statuses[2] == 429, f"the experiments route is unlimited: {statuses}"
    assert "retry-after" in r.headers


@pytest.mark.asyncio
async def test_the_documented_switch_really_stops_the_refusals(
    ac: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_analysis_per_min", 1)
    payload = {"run_id": "run-switch", "dataset_id": "ds-switch", "name": "switch"}
    for _ in range(3):
        r = await ac.post("/api/v1/experiments/", json=payload)
    assert r.status_code != 429, f"the switch did not disable the limiter: {r.status_code}"
