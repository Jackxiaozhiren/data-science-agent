from __future__ import annotations

import os
from typing import Any

from dsa_llm import LLMProvider


class StubLLMProvider(LLMProvider):
    """Deterministic stub for tests and local-first runs without API keys."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[stub] echo: {prompt[:200]}"

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        # Return minimal valid instance if schema is a Pydantic model
        try:
            from pydantic import BaseModel

            if isinstance(schema, type) and issubclass(schema, BaseModel):
                # try to construct with defaults
                return schema.model_validate({})
        except Exception:
            pass
        return {}

    async def stream(self, prompt: str, **kwargs: Any) -> Any:
        yield await self.generate(prompt, **kwargs)


class EnvLLMProvider(LLMProvider):
    """Thin wrapper that would delegate to OpenAI/Anthropic if keys present; falls back to stub."""

    active_provider: str = "stub"

    def __init__(self, fallback: LLMProvider | None = None) -> None:
        self.fallback = fallback or StubLLMProvider()
        if os.getenv("OPENAI_API_KEY"):
            self.active_provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            self.active_provider = "anthropic"
        elif os.getenv("GOOGLE_API_KEY"):
            self.active_provider = "google"

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        _ = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        return await self.fallback.generate(prompt, **kwargs)

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        return await self.fallback.structured_output(prompt, schema, **kwargs)

    async def stream(self, prompt: str, **kwargs: Any) -> Any:
        async for chunk in self.fallback.stream(prompt, **kwargs):  # type: ignore[attr-defined]
            yield chunk


def auto_provider() -> LLMProvider:
    return EnvLLMProvider(StubLLMProvider())
