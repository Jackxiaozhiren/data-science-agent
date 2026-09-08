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
