from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from dsa_llm.providers import EnvLLMProvider, OpenAIResponsesProvider


class _StructuredAnswer(BaseModel):
    answer: str


@pytest.mark.asyncio
async def test_default_mode_stays_stub_even_when_api_key_exists(monkeypatch: pytest.MonkeyPatch) -> None:
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
        return "```json\n{\"answer\": \"verified\"}\n```"

    monkeypatch.setattr(provider, "generate", fake_generate)

    result = await provider.structured_output("answer the question", _StructuredAnswer)

    assert isinstance(result, _StructuredAnswer)
    assert result.answer == "verified"
