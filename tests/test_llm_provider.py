from __future__ import annotations

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
