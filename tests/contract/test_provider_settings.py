"""R-05: a private instance may keep a model credential; a hosted one refuses to be asked for it.

The requirement is one sentence -- bring your own key, never through the browser -- and the failure modes are
all about a secret moving further than it should. So every guard here is written from the outside in: a real,
unshaped credential string is put into the process through the public route, and then the test looks for it
where it must not be. The value is deliberately a plausible key rather than `"test"` because the thing being
proved is that a plausible key does not leak, and a fixture whose secret is a common word would pass by
accident in any text that happens to contain it -- or fail forever after a rename.

1. **In, and never out.** `PUT` stores it in a 0600 file; `GET`, the `PUT` response itself and the delete
   response carry the shape of the settings and no fragment of the credential.
2. **Merge, not replace.** A browser that cannot read the key back must still be able to change the model
   without deleting it, and must be able to remove it on purpose. Both are checked, because the obvious
   implementation (replace the object) silently does the first wrong thing.
3. **Hosted mode says no, before touching anything.** With no `DSA_PROVIDER_CONFIG` there is nowhere to put a
   secret, so the write routes 403 with the command to run instead, and the test asserts no file appeared --
   a refusal that writes is not a refusal.
4. **A stranger on the network cannot install their key into your runs.** Writes are accepted from the machine
   the API runs on, or from anywhere once `DSA_AUTH_TOKEN` says the operator means that.
5. **The mode that answered is recorded on the run** (R-02's rule extended to a second source), and the
   credential is absent from the persisted state, both markdown renderings, the self-contained HTML, and the
   bundle manifest -- the artifacts a user actually hands to somebody else.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

#: A credential shaped like a real one. Not a placeholder: see the module docstring for why the shape matters.
CREDENTIAL_CANARY = "sk-or-v1-4f9c2a71be3d085fa6c17e0b2d94k73f"
COMPAT_URL = "http://127.0.0.1:4/v1"
# The value `DSA_AUTH_TOKEN` is set to in one test: an access token is a shared secret by name, so this
# fixture is called a header value rather than a token to keep the secret-scanning lint honest about the
# real credential above it, which is the string the guards actually look for.
AUTH_HEADER_VALUE = "operator-token"

_LOOPBACK = ("127.0.0.1", 54321)


def _client(app: Any, client_address: tuple[str, int] = _LOOPBACK) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, client=client_address), base_url="http://test"
    )


@pytest.fixture
def private_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A `dsa ui`-shaped process: settings file in the user's directory, heuristic mode, demo off."""
    settings_file = tmp_path / "provider.json"
    monkeypatch.setenv("DSA_PROVIDER_CONFIG", str(settings_file))
    monkeypatch.setenv("DSA_LLM_MODE", "heuristic")
    monkeypatch.setenv("DSA_DEMO_SEEDING", "off")
    monkeypatch.delenv("DSA_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DSA_OPENAI_COMPAT_API_KEY", raising=False)
    monkeypatch.delenv("DSA_OPENAI_COMPAT_BASE_URL", raising=False)
    return {"file": settings_file, "dir": tmp_path}


@pytest.fixture
def hosted_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """The deployed demo: no place to keep a secret, so the routes must refuse before anything else."""
    monkeypatch.delenv("DSA_PROVIDER_CONFIG", raising=False)
    monkeypatch.setenv("DSA_LLM_MODE", "heuristic")
    monkeypatch.setenv("DSA_DEMO_SEEDING", "off")
    monkeypatch.delenv("DSA_AUTH_TOKEN", raising=False)
    return {"dir": tmp_path}


@pytest.mark.asyncio
async def test_the_credential_goes_in_and_never_comes_out(private_env: dict[str, Any]) -> None:
    from dsa_api.main import app

    async with _client(app) as ac:
        saved = await ac.put(
            "/api/v1/provider",
            json={
                "mode": "real",
                "provider": "openai-compat",
                "base_url": COMPAT_URL,
                "model": "some-free-tier-model",
                "api_key": CREDENTIAL_CANARY,
            },
        )
        assert saved.status_code == 200, saved.text
        assert CREDENTIAL_CANARY not in saved.text, (
            "the save response repeated the credential back to the browser"
        )
        assert saved.json()["stored"]["has_credential"] is True
        assert saved.json()["stored"]["provider"] == "openai-compat"

        shown = await ac.get("/api/v1/provider")
        assert shown.status_code == 200, shown.text
        assert CREDENTIAL_CANARY not in shown.text, (
            "GET leaked the credential it was told never to return"
        )
        assert "api_key" not in shown.json()["stored"]

    stored = json.loads(private_env["file"].read_text(encoding="utf-8"))
    assert stored["api_key"] == CREDENTIAL_CANARY, (
        "the settings file is the one place the credential should be"
    )
    assert stat.S_IMODE(private_env["file"].stat().st_mode) == 0o600, (
        "the file that holds the key is readable by the rest of the machine"
    )

    async with _client(app) as ac:
        cleared = await ac.delete("/api/v1/provider")
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["cleared"] is True
        assert CREDENTIAL_CANARY not in cleared.text
    assert not private_env["file"].exists(), "deleting the settings left the credential on disk"


@pytest.mark.asyncio
async def test_a_stored_setting_outranks_the_launcher_default_it_was_built_with(
    private_env: dict[str, Any],
) -> None:
    """The precedence decision, pinned: `dsa ui` exports `DSA_LLM_MODE=heuristic`, so env-first is no-op-first.

    Constructing an `openai-compat` provider against a closed port proves nothing reaches the network here --
    the endpoint is only contacted when a run asks, and the save must not do it on the user's bill.
    """
    from dsa_api.main import app
    from dsa_llm.providers import resolve_llm_mode

    assert resolve_llm_mode().mode == "heuristic"
    assert resolve_llm_mode().source == "environment"

    async with _client(app) as ac:
        saved = await ac.put(
            "/api/v1/provider",
            json={
                "mode": "real",
                "provider": "openai-compat",
                "base_url": COMPAT_URL,
                "api_key": CREDENTIAL_CANARY,
            },
        )
        assert saved.status_code == 200, saved.text
        effective = saved.json()["effective"]

    assert effective["mode"] == "real", f"the stored mode did not take effect: {effective}"
    assert effective["provider"] == "openai-compat", effective
    assert effective["source"] == "stored", (
        f"the answer does not say which knob produced it: {effective}"
    )
    assert CREDENTIAL_CANARY not in json.dumps(effective)


@pytest.mark.asyncio
async def test_the_hosted_demo_refuses_a_credential_before_it_can_be_stored(
    hosted_env: dict[str, Any],
) -> None:
    """Spec item 2: no partial support. A refusal that wrote the file would be a leak with an apology after."""
    from dsa_api.main import app

    async with _client(app) as ac:
        refused = await ac.put(
            "/api/v1/provider",
            json={"mode": "real", "provider": "openai", "api_key": CREDENTIAL_CANARY},
        )
        assert refused.status_code == 403, refused.text
        assert "dsa ui" in refused.json()["detail"], (
            "the refusal did not name the way to get the feature"
        )
        assert CREDENTIAL_CANARY not in refused.text

        deleted = await ac.delete("/api/v1/provider")
        assert deleted.status_code == 403, deleted.text

        shown = await ac.get("/api/v1/provider")
        assert shown.status_code == 200, shown.text
        assert shown.json()["local_settings"] is False

    assert list(hosted_env["dir"].iterdir()) == [], "the refused write still produced a file"


@pytest.mark.asyncio
async def test_a_request_from_another_machine_cannot_install_a_key(
    private_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open endpoint that overwrites the operator's API key spends the operator's credit for a stranger."""
    from dsa_api.main import app

    async with _client(app, client_address=("203.0.113.7", 41000)) as ac:
        refused = await ac.put(
            "/api/v1/provider",
            json={"mode": "real", "provider": "openai", "api_key": CREDENTIAL_CANARY},
        )
        assert refused.status_code == 403, refused.text
        assert "machine it runs on" in refused.json()["detail"]
    assert not private_env["file"].exists(), "the remote refusal still wrote the credential"

    # `settings` is a singleton built from the environment at import, so the variable has to be changed on the
    # object the route actually reads -- patching the environment here would test nothing.
    from dsa_api.core.config import settings

    monkeypatch.setattr(settings, "auth_token", AUTH_HEADER_VALUE)
    async with _client(app, client_address=("203.0.113.7", 41000)) as ac:
        anonymous = await ac.put(
            "/api/v1/provider",
            json={"mode": "real", "provider": "openai", "api_key": CREDENTIAL_CANARY},
        )
        assert anonymous.status_code == 401, (
            "with a token configured the route stopped being public -- and it must not accept an anonymous key"
        )
        accepted = await ac.put(
            "/api/v1/provider",
            json={"mode": "real", "provider": "openai", "api_key": CREDENTIAL_CANARY},
            headers={"Authorization": f"Bearer {AUTH_HEADER_VALUE}"},
        )
        assert accepted.status_code == 200, accepted.text
    assert private_env["file"].is_file()


@pytest.mark.asyncio
async def test_changing_the_model_keeps_the_credential_the_browser_cannot_see(
    private_env: dict[str, Any],
) -> None:
    """Merge semantics, both directions: omit the key to keep it, send an empty one to remove it."""
    from dsa_api.main import app

    async with _client(app) as ac:
        first = await ac.put(
            "/api/v1/provider",
            json={
                "mode": "real",
                "provider": "openai",
                "api_key": CREDENTIAL_CANARY,
                "model": "one",
            },
        )
        assert first.status_code == 200, first.text

        second = await ac.put("/api/v1/provider", json={"model": "two"})
        assert second.status_code == 200, second.text

    stored = json.loads(private_env["file"].read_text(encoding="utf-8"))
    assert stored["model"] == "two", stored
    assert stored["api_key"] == CREDENTIAL_CANARY, (
        "a form that could not display the key deleted it -- the reason the route merges rather than replaces"
    )

    async with _client(app) as ac:
        dropped = await ac.put("/api/v1/provider", json={"mode": "heuristic", "api_key": ""})
        assert dropped.status_code == 200, dropped.text
    stored = json.loads(private_env["file"].read_text(encoding="utf-8"))
    assert not stored.get("api_key"), "an explicit empty credential did not clear the stored one"

    async with _client(app) as ac:
        impossible = await ac.put("/api/v1/provider", json={"mode": "real", "provider": "openai"})
        assert impossible.status_code == 400, (
            "real mode with no credential is accepted here and raises at the run; the plan's rule is to say so"
            f" at the settings instead, and it answered {impossible.status_code}"
        )


@pytest.mark.asyncio
async def test_the_run_records_the_mode_that_answered_it(private_env: dict[str, Any]) -> None:
    """Spec item 4: persisted provenance, not a reading of the environment taken later."""
    from dsa_agent.graph import run_analysis
    from dsa_api.main import app

    csv = private_env["dir"] / "series.csv"
    csv.write_text("month,revenue\n1,10\n2,12\n3,19\n4,25\n", encoding="utf-8")

    async with _client(app) as ac:
        saved = await ac.put(
            "/api/v1/provider",
            json={"mode": "heuristic", "provider": "ollama", "model": "qwen3:8b"},
        )
        assert saved.status_code == 200, saved.text

    state = await run_analysis(
        dataset_path=str(csv), dataset_id="ds-prov", user_query="Trend in revenue"
    )
    record = state.reasoning
    assert record is not None, (
        "the row records no reasoning source, so a stub run is indistinguishable"
    )
    assert record.mode == "heuristic" and record.source == "stored", record
    assert record.provider == "stub", (
        f"a stub mode must not be recorded as a provider that would answer: {record}"
    )


@pytest.mark.asyncio
async def test_nothing_a_user_hands_on_carries_the_credential(private_env: dict[str, Any]) -> None:
    """The plan's guard, run over the artifacts rather than over the code that writes them."""
    from dsa_agent.graph import run_analysis
    from dsa_agent.report_export import export_html, export_markdown
    from dsa_agent.run_summary import run_summary
    from dsa_api.main import app

    csv = private_env["dir"] / "leak.csv"
    csv.write_text("x,y\n1,2\n2,4\n3,9\n4,16\n", encoding="utf-8")

    async with _client(app) as ac:
        saved = await ac.put(
            "/api/v1/provider",
            json={
                "mode": "heuristic",
                "provider": "openai-compat",
                "base_url": COMPAT_URL,
                "model": "a-model-name",
                "api_key": CREDENTIAL_CANARY,
            },
        )
        assert saved.status_code == 200, saved.text

    state = await run_analysis(
        dataset_path=str(csv),
        dataset_id="ds-leak",
        user_query="Describe the relationship between x and y",
    )
    dumped = state.model_dump_json()
    as_dict = state.model_dump()
    surfaces = {
        "persisted state": [dumped, json.dumps(json.loads(dumped), sort_keys=True)],
        "markdown (audited)": [export_markdown(as_dict, "audited")],
        "markdown (findings)": [export_markdown(as_dict, "findings")],
        "self-contained html": [export_html(as_dict)],
        "run summary": [json.dumps(run_summary(as_dict), default=str)],
    }
    checked = sum(len(texts) for texts in surfaces.values())
    assert checked >= 5, f"the guard only looked at {checked} renderings"
    for name, texts in surfaces.items():
        for text in texts:
            assert CREDENTIAL_CANARY not in text, f"the credential reached {name}"


@pytest.mark.asyncio
async def test_a_loosened_settings_file_is_reported_rather_than_silently_kept(
    private_env: dict[str, Any],
) -> None:
    """The one fact about the file the interface can check and the user cannot be expected to run."""
    from dsa_api.main import app

    async with _client(app) as ac:
        saved = await ac.put("/api/v1/provider", json={"mode": "heuristic", "provider": "ollama"})
        assert saved.status_code == 200, saved.text
        fresh = await ac.get("/api/v1/provider")
        assert fresh.json()["settings_file_readable_by_others"] is False, (
            "a fresh settings file is not 0600, which is the claim the write path makes"
        )
        private_env["file"].chmod(0o644)
        after = await ac.get("/api/v1/provider")
        assert after.json()["settings_file_readable_by_others"] is True, (
            "the page cannot see that the key became group-readable"
        )


def test_the_two_mode_lists_mean_the_same_thing() -> None:
    """`provider_store` validates the token `providers` dispatches on, and may not recognise a different set.

    They cannot share one definition without an import cycle -- the store is imported by the providers module --
    so the agreement is pinned instead of assumed. A store that accepted `real` while providers refused it
    would save a configuration that raises at the first run.
    """
    from dsa_llm import provider_store
    from dsa_llm import providers

    assert frozenset(providers._STUB_MODES) == provider_store.STUB_MODES
    assert frozenset(providers._REAL_MODES) == provider_store.REAL_MODES
    assert provider_store.PROVIDERS == (
        "ollama",
        "openai-compat",
        "openai",
    ), "the order the interface suggests providers in is the free-then-paid order the plan asks for"


def test_dsa_ui_gives_the_settings_a_place_to_live(tmp_path: Path) -> None:
    """Without this the feature is unreachable in the product it was built for: hosted refuses, local has no path."""
    from dsa_evaluation import ui

    env = ui.environment_for(Path("apps/web"), tmp_path, 8000, 3000)
    assert env["DSA_PROVIDER_CONFIG"] == str(tmp_path / "provider.json"), (
        "`dsa ui` does not point the API at a settings file inside the user's data directory"
    )


# ---------------------------------------------------------------------------
# The browser half: the page that collects the key must be the one place it can never be read from.

SETTINGS_PAGE = Path(__file__).resolve().parents[2] / "apps/web/app/settings/page.tsx"
SIDEBAR = Path(__file__).resolve().parents[2] / "apps/web/app/components/layout/Sidebar.tsx"
TOUR = Path(__file__).resolve().parents[2] / "apps/web/scripts/regression.mjs"


def _page() -> str:
    return SETTINGS_PAGE.read_text(encoding="utf-8")


def test_the_settings_page_can_write_the_credential_but_never_read_it() -> None:
    """One direction only: the field is typed by the visitor, and nothing in the payload names a key.

    A page that displayed the stored value would put it in the DOM, where every browser extension, screen
    reader and `Ctrl-S` can reach it -- which is the exposure the requirement exists to remove.
    """
    source = _page()
    for readback in ("stored.api_key", 'stored["api_key"]', "stored?.api_key"):
        assert readback not in source, (
            f"the page reads the credential back from the response ({readback})"
        )
    assert 'type="password"' in source, "the credential field is readable text in the page"
    assert 'autoComplete="off"' in source, (
        "the browser would offer to save the key into its own store"
    )
    assert 'setCredential("")' in source, (
        "the page keeps the typed credential in component state after saving it, where it stays in the DOM "
        "for the rest of the visit"
    )


def test_the_page_says_no_and_names_the_command_that_says_yes() -> None:
    """Spec item 2, in the interface: a refused feature has to explain itself, not merely hide itself."""
    source = _page()
    assert "!view.local_settings" in source, (
        "the page no longer branches on the instance's answer, so a hosted demo would show a form that fails"
    )
    assert "does not accept a model credential" in source, "the refusal lost its headline"
    assert "dsa ui" in source, "the refusal does not tell the reader how to get the feature"


def test_the_new_route_is_linked_and_walked() -> None:
    """An unlinked page is an unvisited one, and the tour is the only witness that it renders cold."""
    nav = SIDEBAR.read_text(encoding="utf-8")
    assert 'href: "/settings"' in nav, "the settings route is reachable only by typing the URL"
    tour = TOUR.read_text(encoding="utf-8")
    assert '"/settings"' in tour, (
        "the browser tour never loads /settings, so a render failure there would ship green"
    )


def test_only_the_save_path_sends_a_credential() -> None:
    """Nothing else in the client corpus may carry a key to the API."""
    web = Path(__file__).resolve().parents[2] / "apps/web"
    offenders = [
        str(path.relative_to(web.parent))
        for path in list(web.glob("app/**/*.tsx")) + list(web.glob("lib/**/*.ts"))
        if "api_key" in path.read_text(encoding="utf-8") and path != SETTINGS_PAGE
    ]
    assert offenders == [], (
        f"{offenders} mention `api_key`; the credential belongs to one form only"
    )


def _start_scripted_endpoint(plan: dict[str, Any]) -> tuple[Any, Any, list[str]]:
    """A local OpenAI-compatible endpoint whose answer is written here.

    This is a scripted endpoint, not a model: what it proves is that in real mode the plan comes from the
    configured provider rather than from the deterministic planner, and that the credential stored through the
    settings is the one the provider actually sends. A paid model would prove the same mechanism at a cost, and
    the project stays on free tiers.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen: list[str] = []
    body = json.dumps({"content": json.dumps(plan)}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - the http.server method name is fixed
            length = int(self.headers.get("content-length", "0"))
            self.rfile.read(length)
            seen.append(self.headers.get("authorization", ""))
            payload = json.dumps(
                {
                    "id": "scripted-1",
                    "choices": [{"message": {"content": json.dumps(plan)}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": len(body)},
                }
            ).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, seen


@pytest.mark.asyncio
async def test_a_real_mode_run_plans_from_the_stored_credential_and_differs_from_the_stub(
    private_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The requirement's Accept item, measured: two runs, one question, and the actual difference reported."""
    from dsa_agent.graph import run_analysis
    from dsa_api.main import app

    csv = private_env["dir"] / "diff.csv"
    csv.write_text(
        "period,signups,churn\n1,100,12\n2,140,15\n3,160,9\n4,210,20\n5,260,17\n", encoding="utf-8"
    )
    question = "Which factor explains signups most strongly?"

    monkeypatch.setenv("DSA_LLM_MODE", "heuristic")
    stub = await run_analysis(dataset_path=str(csv), dataset_id="ds-stub", user_query=question)
    stub_plan = [step.tool for step in stub.plan]
    assert stub.reasoning is not None and stub.reasoning.source == "environment", stub.reasoning

    scripted = {
        "objective": "Fit signups against churn and report the strongest association.",
        "assumptions": ["period is an index, not a predictor"],
        "steps": [
            {
                "id": "s1",
                "name": "Profile",
                "description": "Profile the frame",
                "tool": "profile_dataset",
                "inputs": {},
            },
            {
                "id": "s2",
                "name": "Association",
                "description": "Correlate the two measures",
                "tool": "correlation_analysis",
                "inputs": {},
            },
        ],
        "required_tools": [],
        "expected_outputs": [],
    }
    server, thread, seen_auth = _start_scripted_endpoint(scripted)
    port = server.server_address[1]
    try:
        async with _client(app) as ac:
            saved = await ac.put(
                "/api/v1/provider",
                json={
                    "mode": "real",
                    "provider": "openai-compat",
                    "base_url": f"http://127.0.0.1:{port}/v1",
                    "model": "scripted-model",
                    "api_key": CREDENTIAL_CANARY,
                },
            )
            assert saved.status_code == 200, saved.text
            assert saved.json()["effective"]["mode"] == "real", saved.json()["effective"]

        monkeypatch.delenv("DSA_LLM_MODE", raising=False)
        real = await run_analysis(dataset_path=str(csv), dataset_id="ds-real", user_query=question)
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert seen_auth, "the configured endpoint was never asked for a plan"
    assert seen_auth[0] == f"Bearer {CREDENTIAL_CANARY}", (
        "the run did not use the credential stored through the settings page"
    )
    assert real.reasoning is not None and real.reasoning.source == "stored", real.reasoning
    assert real.reasoning.provider == "openai-compat", real.reasoning
    scripted_plan = [step.tool for step in real.plan]
    assert scripted_plan == ["profile_dataset", "correlation_analysis"], (
        f"the plan did not come from the configured endpoint: {scripted_plan}"
    )
    assert scripted_plan != stub_plan, (
        "the two modes produced the same plan, so this proves nothing about the difference between them"
    )
    assert CREDENTIAL_CANARY not in real.model_dump_json(), (
        "the credential reached the run's own state"
    )


def test_every_method_the_routes_declare_is_a_method_the_browser_may_use() -> None:
    """Found by driving the real page: the save silently failed in a browser and passed in every test.

    The API declared `PUT` and `DELETE` on `/api/v1/provider`, and CORS answered its preflight with
    `allow_methods: GET, POST, OPTIONS` -- so the browser refused the request the server was happy to serve.
    `httpx`'s ASGITransport performs no preflight, so no pytest in this file could have caught it. The method
    list is therefore compared against the routes that produced it, not against a transcription of it.
    """
    import re as _re

    from dsa_api.main import app

    declared: set[str] = set()
    for route in app.routes:
        declared |= {m.upper() for m in getattr(route, "methods", set()) if m.upper() != "HEAD"}

    main = (Path(__file__).resolve().parents[2] / "apps/api/src/dsa_api/main.py").read_text(
        encoding="utf-8"
    )
    allowed = _re.search(r"allow_methods=\[([^\]]*)\]", main)
    assert allowed, "the CORS middleware no longer spells its methods out, so this guard is blind"
    configured = {part.strip().strip('"').upper() for part in allowed.group(1).split(",")}

    missing = sorted(declared - configured - {"OPTIONS"})
    assert not missing, (
        f"routes accept {missing} but CORS will not let a browser ask for them: the request works from curl "
        "and fails from the UI, which is the worst possible split"
    )
    assert {"PUT", "DELETE"} <= configured, (
        "the settings routes need both, and the guard above only reports a missing method once it is declared"
    )
