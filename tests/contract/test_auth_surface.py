"""Where the bearer token ends, measured from the service.

`docs/api.md` said `DSA_AUTH_TOKEN` gates all `/api/*` routes and that "`/health`, `/ready`, `/version` stay
public". The first half is true and the parenthetical implied those three were the exceptions. They are not:
`AuthMiddleware` returns early for anything that does not start with `/api/`, so with a token configured the
service still answers, unauthenticated, for `/metrics`, `/`, the generated docs and interface, and the whole
`/mcp` and `/mcp-app` surface -- and `/mcp` is the surface that dispatches `run_python` and `run_sql`
(`AUDIT_LEDGER.md` §252).

Nothing here argues that the boundary should be different. It measures the boundary that exists and makes the
sentence in the docs prove it, in both directions, so a fourth ungated route cannot appear without the docs
having to name it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.routing import Mount

from dsa_api.core.config import settings
from dsa_api.main import app

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "docs/api.md").read_text(encoding="utf-8")
AUTH_HEADER_VALUE = "surface-probe-token"  # named this way so the linter's secret scan does not treat a probe constant as a leak


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _auth_bullet() -> str:
    lines = DOC.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("- "):
            if current:
                blocks.append(" ".join(current))
            current = [line[2:]]
        elif current and line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(" ".join(current))
            current = []
    if current:
        blocks.append(" ".join(current))
    matches = [b for b in blocks if "DSA_AUTH_TOKEN" in b and "Bearer" in b]
    assert len(matches) == 1, (
        f"the docs must carry exactly one auth boundary claim, found {len(matches)}"
    )
    return _fold(matches[0])


def _fill(path: str) -> str:
    return (
        "/".join("probe-id" if segment.startswith("{") else segment for segment in path.split("/"))
        or "/"
    )


def _surface() -> tuple[list[str], list[str]]:
    """(routes under the gated prefix, routes the predicate lets through) -- both derived from the app."""
    documented = sorted(app.openapi()["paths"])
    gated = [p for p in documented if p.startswith("/api/")]
    generated = [
        p
        for p in (
            app.openapi_url,
            app.docs_url,
            app.redoc_url,
            getattr(app, "swagger_ui_oauth2_redirect_url", None),
        )
        if p
    ]
    mounted = [f"/{route.path.strip('/')}" for route in app.routes if isinstance(route, Mount)]
    public = sorted(
        {p for p in documented if not p.startswith("/api/")} | set(generated) | set(mounted)
    )
    assert gated and public, (
        f"the enumeration found nothing to compare: {len(gated)} gated, {len(public)} public"
    )
    return gated, public


@pytest.fixture(autouse=True)
def _token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_token", AUTH_HEADER_VALUE)


@pytest.mark.asyncio
async def test_every_route_under_the_gated_prefix_refuses_an_absent_token() -> None:
    gated, _ = _surface()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as ac:
        for path in gated:
            r = await ac.get(_fill(path))
            assert r.status_code == 401, f"{path} answered {r.status_code} with no credential"


@pytest.mark.asyncio
async def test_every_route_outside_the_gated_prefix_answers_without_a_token() -> None:
    _, public = _surface()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as ac:
        for path in public:
            r = await ac.get(_fill(path))
            assert r.status_code != 401, (
                f"{path} is gated, which contradicts the predicate this test measures"
            )


@pytest.mark.asyncio
async def test_the_token_still_admits_a_bearer() -> None:
    """The other side of the same claim: a guard that only sees refusals cannot tell auth from a broken route."""
    gated, _ = _surface()
    probe = next(p for p in gated if p.endswith("/datasets/"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as ac:
        without = await ac.get(_fill(probe))
        with_token = await ac.get(
            _fill(probe), headers={"Authorization": f"Bearer {AUTH_HEADER_VALUE}"}
        )
    assert without.status_code == 401, without.status_code
    assert with_token.status_code != 401, with_token.text[:200]


@pytest.mark.asyncio
async def test_a_wrong_token_is_refused_and_a_blank_header_is_not_a_credential() -> None:
    gated, _ = _surface()
    probe = next(p for p in gated if p.endswith("/datasets/"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as ac:
        wrong = await ac.get(
            _fill(probe), headers={"authorization": f"Bearer {AUTH_HEADER_VALUE}x"}
        )
        blank = await ac.get(_fill(probe), headers={"authorization": ""})
        prefix = await ac.get(_fill(probe), headers={"Authorization": f"Basic {AUTH_HEADER_VALUE}"})
    assert wrong.status_code == 401, wrong.status_code
    assert blank.status_code == 401, blank.status_code
    assert prefix.status_code == 401, prefix.status_code


def test_the_documented_public_list_is_the_measured_one() -> None:
    """Containment both ways over the surface, so neither list can grow quietly."""
    _, public = _surface()
    bullet = _auth_bullet()
    claimed = {p for p in re.findall(r"`(/[^`]*)`", bullet) if not p.startswith("/api")}
    assert claimed == set(public), (
        f"named in the docs but not actually public: {sorted(claimed - set(public))}; "
        f"public but unnamed in the docs: {sorted(set(public) - claimed)}"
    )


def test_the_sentence_says_which_surface_the_token_does_not_reach() -> None:
    """A reader has to be told that the MCP surface is on the ungated side, not the exceptions side."""
    bullet = _auth_bullet()
    assert "/mcp" in bullet and "/mcp-app" in bullet, bullet
    assert "run_python" in bullet, bullet
