"""`PUT /api/v1/provider` promises it never calls the provider. Here the promise is enforced, not asserted.

`docs/api.md` says of the settings write: "Shape-validated only -- the route never contacts the provider, because
a verification call would spend the operator's credit or ship their data unsolicited." Nothing tested that. The
cheapest decisive witness is to make every outbound connection raise for the duration of the request: a route
that verified credentials would fail here rather than answer 200, and a route that stayed local answers as it
does in production. The recorded attempt list is asserted empty too, because a raise that nobody counted is a
test that passed for the wrong reason.
"""

from __future__ import annotations

import json
import socket
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

#: A credential shaped like a real one, so a call that shipped it would be a leak the test can see.
PROBE_KEY = "sk-or-v1-4f9c2a71be3d085fa6c17e0b2d94k73f"
#: Port 4 is unreachable by design; if the route ever tried to use it, the blocked socket records the attempt.
COMPAT_URL = "http://127.0.0.1:4/v1"

_PAYLOAD = {
    "mode": "real",
    "provider": "openai-compat",
    "base_url": COMPAT_URL,
    "model": "some-free-tier-model",
    "api_key": PROBE_KEY,
}


@pytest.fixture
def private_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    settings_file = tmp_path / "provider.json"
    monkeypatch.setenv("DSA_PROVIDER_CONFIG", str(settings_file))
    monkeypatch.setenv("DSA_LLM_MODE", "heuristic")
    monkeypatch.setenv("DSA_DEMO_SEEDING", "off")
    monkeypatch.delenv("DSA_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DSA_OPENAI_COMPAT_API_KEY", raising=False)
    monkeypatch.delenv("DSA_OPENAI_COMPAT_BASE_URL", raising=False)
    return {"file": settings_file}


@pytest.fixture
def no_sockets(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every way a Python caller can leave the process, counted and refused."""
    attempts: list[str] = []

    def refuse(label: str):
        def _blocked(*args, **kwargs):
            attempts.append(f"{label}: {args[:2]}")
            raise AssertionError(f"the request tried to leave the process ({label})")

        return _blocked

    for name in ("socket", "create_connection"):
        monkeypatch.setattr(socket, name, refuse(name), raising=False)
    monkeypatch.setattr(socket, "getaddrinfo", refuse("getaddrinfo"), raising=False)
    return attempts


@pytest.fixture
async def ac() -> AsyncGenerator[AsyncClient, None]:
    from dsa_api.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("127.0.0.1", 54321)), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_the_settings_write_answers_with_no_route_out(ac, no_sockets, private_env) -> None:
    saved = await ac.put("/api/v1/provider", json=_PAYLOAD)
    assert saved.status_code == 200, saved.text
    assert saved.json()["stored"]["has_credential"] is True
    assert no_sockets == [], f"the write reached the network: {no_sockets}"
    assert PROBE_KEY not in saved.text, "the save response repeated the credential back"
    stored = json.loads(private_env["file"].read_text(encoding="utf-8"))
    assert stored["api_key"] == PROBE_KEY, "the shape-only write did not persist what it was given"


@pytest.mark.asyncio
async def test_reading_the_effective_mode_needs_no_connection(ac, no_sockets, private_env) -> None:
    """`/version` and `GET /provider` both report what `resolve_llm_mode()` decided; deciding must be local."""
    with_key = await ac.put("/api/v1/provider", json=_PAYLOAD)
    assert with_key.status_code == 200, with_key.text
    shown = await ac.get("/api/v1/provider")
    version = await ac.get("/version")
    assert shown.status_code == 200 and version.status_code == 200
    assert version.json()["reasoning_mode"]["provider"] == "openai-compat", version.json()
    assert no_sockets == [], f"resolving the mode reached the network: {no_sockets}"


@pytest.mark.asyncio
async def test_deleting_the_settings_is_local_too(ac, no_sockets, private_env) -> None:
    assert (await ac.put("/api/v1/provider", json=_PAYLOAD)).status_code == 200
    cleared = await ac.delete("/api/v1/provider")
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["cleared"] is True
    assert no_sockets == [], f"erasing the settings reached the network: {no_sockets}"
