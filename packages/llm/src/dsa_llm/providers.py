from __future__ import annotations

import json
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from dsa_llm import LLMProvider

DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
_REAL_MODES = {"real", "openai"}
_STUB_MODES = {"stub", "offline", "heuristic"}
_CALL_LOG: list[dict[str, Any]] = []


def reset_call_log() -> None:
    _CALL_LOG.clear()


def get_call_log() -> list[dict[str, Any]]:
    return [dict(item) for item in _CALL_LOG]


def _strip_json_fence(text: str) -> str:
    value = text.strip()
    if not value.startswith("```"):
        return value
    lines = value.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Extract text from a raw Responses API payload without relying on SDK helpers."""

    texts: list[str] = []
    output = payload.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str):
                texts.append(text)
    return "".join(texts).strip()


class StubLLMProvider(LLMProvider):
    """Deterministic provider for tests and local-first runs without external calls."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return f"[stub] echo: {prompt[:200]}"

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        try:
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                return schema.model_validate({})
        except Exception:
            pass
        return {}

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        yield await self.generate(prompt, **kwargs)


class OpenAIResponsesProvider(LLMProvider):
    """Minimal async OpenAI Responses API provider using the existing httpx dependency."""

    provider_name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 90.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when DSA_LLM_MODE=real. "
                "DSA never silently substitutes the stub provider for a requested real-model run."
            )
        self.model = (
            model
            or os.getenv("DSA_OPENAI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or DEFAULT_OPENAI_MODEL
        )
        configured_base = (
            base_url or os.getenv("DSA_OPENAI_BASE_URL") or "https://api.openai.com/v1"
        )
        self.base_url = configured_base.rstrip("/")
        self.timeout_s = timeout_s
        self.last_usage: dict[str, Any] = {}
        self.last_response_id: str | None = None
        self.last_latency_ms: int | None = None

    async def _request(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        request: dict[str, Any] = {"model": self.model, "input": prompt}
        max_output_tokens = kwargs.get("max_output_tokens")
        if max_output_tokens is not None:
            request["max_output_tokens"] = int(max_output_tokens)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(f"{self.base_url}/responses", headers=headers, json=request)
        self.last_latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            detail = response.text.replace("\n", " ")[:500]
            raise RuntimeError(f"OpenAI Responses API returned HTTP {response.status_code}: {detail}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI Responses API returned a non-object payload")
        response_id = payload.get("id")
        self.last_response_id = response_id if isinstance(response_id, str) else None
        usage = payload.get("usage")
        self.last_usage = usage if isinstance(usage, dict) else {}
        _CALL_LOG.append(
            {
                "provider": self.provider_name,
                "model": self.model,
                "response_id": self.last_response_id,
                "latency_ms": self.last_latency_ms,
                "usage": dict(self.last_usage),
            }
        )
        return payload

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        payload = await self._request(prompt, **kwargs)
        text = _extract_output_text(payload)
        if not text:
            raise RuntimeError("OpenAI Responses API returned no output_text content")
        return text

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        if not isinstance(schema, type) or not issubclass(schema, BaseModel):
            raw = _strip_json_fence(await self.generate(prompt, **kwargs))
            return json.loads(raw)

        model_cls: type[BaseModel] = schema
        schema_json = json.dumps(model_cls.model_json_schema(), ensure_ascii=False)
        structured_prompt = (
            f"{prompt}\n\n"
            "Return only one valid JSON object. Do not use Markdown fences or commentary. "
            f"The JSON must validate against this schema: {schema_json}"
        )
        raw = _strip_json_fence(await self.generate(structured_prompt, **kwargs))
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError as exc:
            raise RuntimeError(f"Real LLM returned invalid structured output: {exc}") from exc

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        # The first real-provider milestone keeps the interface correct without adding
        # a second SSE parser. True token streaming can be layered on independently.
        yield await self.generate(prompt, **kwargs)

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "response_id": self.last_response_id,
            "latency_ms": self.last_latency_ms,
            "usage": self.last_usage,
        }


class EnvLLMProvider(LLMProvider):
    """Select a deterministic or real provider explicitly from environment settings."""

    def __init__(self, fallback: LLMProvider | None = None) -> None:
        self.fallback = fallback or StubLLMProvider()
        self.mode = os.getenv("DSA_LLM_MODE", "stub").strip().lower()
        self.active_provider = "stub"
        self.active_model: str | None = None
        self.inner: LLMProvider = self.fallback

        if self.mode in _STUB_MODES:
            return
        if self.mode not in _REAL_MODES:
            raise RuntimeError(
                f"Unsupported DSA_LLM_MODE={self.mode!r}; use stub/offline/heuristic or real/openai"
            )

        provider_name = os.getenv("DSA_LLM_PROVIDER", "openai").strip().lower()
        if provider_name != "openai":
            raise RuntimeError(
                f"DSA_LLM_PROVIDER={provider_name!r} is not implemented yet. "
                "Use openai rather than silently falling back to a stub."
            )
        real_provider = OpenAIResponsesProvider()
        self.inner = real_provider
        self.active_provider = real_provider.provider_name
        self.active_model = real_provider.model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self.inner.generate(prompt, **kwargs)

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        return await self.inner.structured_output(prompt, schema, **kwargs)

    async def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        async for chunk in self.inner.stream(prompt, **kwargs):
            yield chunk

    def metadata(self) -> dict[str, Any]:
        inner_metadata = getattr(self.inner, "metadata", None)
        details = inner_metadata() if callable(inner_metadata) else {}
        return {
            "mode": self.mode,
            "provider": self.active_provider,
            "model": self.active_model,
            **details,
        }


def auto_provider() -> LLMProvider:
    return EnvLLMProvider(StubLLMProvider())
