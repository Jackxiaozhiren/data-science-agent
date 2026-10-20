from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import BaseModel

from dsa_llm.providers import EnvLLMProvider, OpenAIResponsesProvider


class _StructuredAnswer(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_default_mode_stays_stub_even_when_api_key_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DSA_LLM_MODE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    provider = EnvLLMProvider()

    assert provider.active_provider == "stub"
    assert await provider.generate("hello") == "[stub] echo: hello"


def test_real_mode_requires_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        EnvLLMProvider()


@pytest.mark.asyncio
async def test_openai_provider_extracts_responses_api_text(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")

    async def fake_request(prompt: str, **kwargs: Any) -> dict[str, Any]:
        assert prompt == "hello"
        return {
            "id": "resp_test",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "real response"}],
                }
            ],
        }

    monkeypatch.setattr(provider, "_request", fake_request)

    assert await provider.generate("hello") == "real response"


@pytest.mark.asyncio
async def test_openai_provider_validates_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")

    async def fake_generate(prompt: str, **kwargs: Any) -> str:
        assert "JSON" in prompt
        return '```json\n{"answer": "verified"}\n```'

    monkeypatch.setattr(provider, "generate", fake_generate)

    result = await provider.structured_output("answer the question", _StructuredAnswer)

    assert isinstance(result, _StructuredAnswer)
    assert result.answer == "verified"


def test_usd_for_usage_needs_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    from dsa_llm.providers import _usd_for_usage

    monkeypatch.delenv("DSA_INPUT_COST_PER_MILLION", raising=False)
    monkeypatch.delenv("DSA_OUTPUT_COST_PER_MILLION", raising=False)
    assert _usd_for_usage({"input_tokens": 1000, "output_tokens": 500}) is None

    monkeypatch.setenv("DSA_INPUT_COST_PER_MILLION", "0.20")
    monkeypatch.setenv("DSA_OUTPUT_COST_PER_MILLION", "1.20")
    assert _usd_for_usage({"input_tokens": 1_000_000, "output_tokens": 1_000_000}) == pytest.approx(
        1.40
    )
    assert _usd_for_usage({}) == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_spend_cap_refuses_before_any_http(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from dsa_llm.providers import OpenAIResponsesProvider

    monkeypatch.setenv("DSA_MAX_COST_USD", "0.00")

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("HTTP must not be attempted after the cap is reached")

    monkeypatch.setattr(httpx, "AsyncClient", _boom)
    provider = OpenAIResponsesProvider(api_key="test-key", model="test-model")
    with pytest.raises(RuntimeError, match="cap reached"):
        await provider.generate("hello")


class _FakeChatResponse:
    status_code = 200
    text = "{}"

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _FakeChatClient:
    def __init__(self, payload: dict, seen: list) -> None:
        self._payload = payload
        self._seen = seen

    async def __aenter__(self) -> _FakeChatClient:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def post(
        self, url: str, headers: dict | None = None, json: dict | None = None
    ) -> _FakeChatResponse:
        self._seen.append({"url": url, "headers": headers, "json": json})
        return _FakeChatResponse(self._payload)


def _chat_payload(text: str = '{"answer": "yes"}', **usage: int) -> dict:
    return {
        "id": "chatcmpl-test123",
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, **usage},
    }


@pytest.mark.asyncio
async def test_chat_provider_generate_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    seen: list = []
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: _FakeChatClient(_chat_payload("hello"), seen)
    )
    p = OpenAIChatProvider(model="test-model", base_url="http://localhost:11434/v1", local=True)
    assert await p.generate("hi") == "hello"
    assert seen[0]["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in seen[0]["headers"]  # localhost: no key sent
    assert p.last_usage == {"input_tokens": 100, "output_tokens": 50}
    assert p.last_response_id == "chatcmpl-test123"


@pytest.mark.asyncio
async def test_chat_provider_ollama_eval_counts_and_structured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    payload = {
        "choices": [{"message": {"role": "assistant", "content": '{"answer": "ok"}'}}],
        "usage": {"prompt_eval_count": 200, "eval_count": 30},
    }
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeChatClient(payload, []))
    p = OpenAIChatProvider(model="qwen3:8b", base_url="http://localhost:11434/v1", local=True)
    out = await p.structured_output("q?", _StructuredAnswer)
    assert out.answer == "ok"
    assert p.last_usage == {"input_tokens": 200, "output_tokens": 30}
    assert (p.last_response_id or "").startswith("local-")  # honestly labeled, no fake id


@pytest.mark.asyncio
async def test_chat_provider_http_error_is_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    class _Bad:
        status_code = 401
        text = "invalid key"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            return self

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Bad())
    p = OpenAIChatProvider(api_key="k", model="m", base_url="https://example.com/v1")
    with pytest.raises(RuntimeError, match="HTTP 401"):
        await p.generate("hi")


def test_env_selects_ollama_and_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    from dsa_llm.providers import EnvLLMProvider

    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("DSA_OLLAMA_MODEL", "llama3.1:8b")
    p = EnvLLMProvider()
    assert p.active_provider == "ollama"

    monkeypatch.setenv("DSA_LLM_PROVIDER", "openai-compat")
    monkeypatch.delenv("DSA_OPENAI_COMPAT_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DSA_OPENAI_COMPAT_BASE_URL"):
        EnvLLMProvider()

    monkeypatch.setenv("DSA_OPENAI_COMPAT_BASE_URL", "https://example.com/v1")
    monkeypatch.delenv("DSA_OPENAI_COMPAT_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="DSA_OPENAI_COMPAT_API_KEY"):
        EnvLLMProvider()


@pytest.mark.asyncio
async def test_chat_provider_think_flag_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    seen: list = []
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: _FakeChatClient(_chat_payload("ok"), seen)
    )
    p = OpenAIChatProvider(model="qwen3:8b", base_url="http://x/v1", local=True, think=True)
    assert await p.generate("hi") == "ok"
    assert seen[0]["json"]["think"] is True

    p2 = OpenAIChatProvider(model="m", base_url="https://example.com/v1", api_key="k")
    await p2.generate("hi")
    assert "think" not in seen[1]["json"]


def test_env_ollama_think_default_on(monkeypatch: pytest.MonkeyPatch) -> None:
    from dsa_llm.providers import EnvLLMProvider

    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("DSA_OLLAMA_THINK", raising=False)
    assert EnvLLMProvider().inner.think is True
    monkeypatch.setenv("DSA_OLLAMA_THINK", "0")
    assert EnvLLMProvider().inner.think is False


def test_chat_provider_temperature_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    seen: list = []
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: _FakeChatClient(_chat_payload("ok"), seen)
    )
    p = OpenAIChatProvider(model="m", base_url="http://x/v1", local=True)
    p.temperature = 0.1
    import asyncio

    asyncio.run(p.generate("hi"))
    assert seen[0]["json"]["temperature"] == pytest.approx(0.1)


def test_env_ollama_temperature_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from dsa_llm.providers import EnvLLMProvider

    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("DSA_OLLAMA_TEMPERATURE", raising=False)
    assert EnvLLMProvider().inner.temperature == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_a_local_model_is_reached_even_when_a_proxy_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The free path -- Ollama on this machine -- must not be routed out through a proxy.

    Measured on a Mac with the system proxy enabled: `httpx` with its default `trust_env=True` asks
    `urllib.request.getproxies()`, which falls back to the operating system's proxy configuration, and every
    request to `http://127.0.0.1:<port>` comes back as **HTTP 502 with an empty body** -- the same URL answered
    `200` the instant `trust_env=False` was set. The provider's documented default base URL is
    `http://localhost:11434/v1`, so a configured proxy silently makes the no-cost local model unreachable, and
    the settings screen reports it as a model failure.

    The premise is forced rather than inherited from the machine: `HTTP_PROXY` is set to a port nothing listens
    on, so this is red for the same reason on any host, including CI. The direct `httpx.post` two lines below is
    the negative control -- if it ever succeeds, the premise has gone vacuous and this test proves nothing.
    """
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    body = json.dumps(_chat_payload("planned on this machine")).encode()

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - the http.server method name is fixed
            self.rfile.read(int(self.headers.get("content-length", "0")))
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    try:
        with pytest.raises(httpx.ConnectError):
            await httpx.AsyncClient(timeout=3).post(f"{url}/chat/completions", json={})

        provider = OpenAIChatProvider(model="m", base_url=url, local=True, timeout_s=5)
        assert await provider.generate("hi") == "planned on this machine"
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_proxy_settings_still_apply_to_a_remote_model_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bypass is scoped to this machine -- a corporate host must keep the proxy it requires.

    One-sided would be the easy test: it would pass by disabling proxy handling everywhere. So the same fake
    client records the kwargs for both shapes and this asserts them in both directions.
    """
    import httpx

    from dsa_llm.providers import OpenAIChatProvider

    recorded: list[dict[str, Any]] = []

    def _spy(**kwargs: Any) -> _FakeChatClient:
        recorded.append(kwargs)
        return _FakeChatClient(_chat_payload("ok"), [])

    monkeypatch.setattr(httpx, "AsyncClient", _spy)

    await OpenAIChatProvider(model="m", base_url="http://127.0.0.1:11434/v1", local=True).generate(
        "hi"
    )
    await OpenAIChatProvider(
        model="m", base_url="https://api.example.invalid/v1", api_key="k"
    ).generate("hi")

    assert recorded[0].get("trust_env") is False, recorded[0]
    assert recorded[1].get("trust_env", True) is not False, recorded[1]


def test_the_loopback_rule_names_the_forms_a_local_model_actually_uses() -> None:
    """`localhost`, `127.0.0.1` and `::1` are all written in real settings; a miss re-creates the 502."""
    from dsa_llm.providers import _honours_configured_proxy

    for local in (
        "http://localhost:11434/v1",
        "http://127.0.0.1:11434/v1",
        "http://LOCALHOST:11434/v1",
        "http://[::1]:11434/v1",
        "http://localhost",
    ):
        assert not _honours_configured_proxy(local), local
    for remote in (
        "https://api.openai.com/v1",
        "https://generativelanguage.googleapis.com/v1beta",
        "http://x/v1",
        "http://ollama.internal:11434/v1",
        "",
    ):
        assert _honours_configured_proxy(remote), remote
