from __future__ import annotations

import json
import os
import time
import uuid
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


def _usd_for_usage(usage: dict[str, Any]) -> float | None:
    """Estimated USD for one Responses API usage dict using env pricing.

    Returns None when rates are not configured (then no cap can apply).
    """
    try:
        in_rate = float(os.environ["DSA_INPUT_COST_PER_MILLION"])
        out_rate = float(os.environ["DSA_OUTPUT_COST_PER_MILLION"])
    except (KeyError, ValueError):
        return None

    def _n(*keys: str) -> int:
        for k in keys:
            v = usage.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                return int(v)
        return 0

    total_in = _n("input_tokens") + _n("input_tokens_details")
    total_out = _n("output_tokens") + _n("output_tokens_details")
    return total_in / 1_000_000 * in_rate + total_out / 1_000_000 * out_rate


def _spend_cap_usd() -> float | None:
    try:
        cap = float(os.environ.get("DSA_MAX_COST_USD", ""))
    except ValueError:
        return None
    return cap if cap >= 0 else None


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

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        async def _iter() -> AsyncIterator[str]:
            yield await self.generate(prompt, **kwargs)

        return _iter()


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
        self.spent_usd: float = 0.0

    async def _request(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        request: dict[str, Any] = {"model": self.model, "input": prompt}
        max_output_tokens = kwargs.get("max_output_tokens")
        if max_output_tokens is not None:
            request["max_output_tokens"] = int(max_output_tokens)

        cap = _spend_cap_usd()
        if cap is not None and self.spent_usd >= cap:
            raise RuntimeError(
                f"DSA_MAX_COST_USD cap reached (${self.spent_usd:.4f} >= ${cap:.4f}); "
                "refusing further real-model calls."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url}/responses", headers=headers, json=request
            )
        self.last_latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            detail = response.text.replace("\n", " ")[:500]
            raise RuntimeError(
                f"OpenAI Responses API returned HTTP {response.status_code}: {detail}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("OpenAI Responses API returned a non-object payload")
        response_id = payload.get("id")
        self.last_response_id = response_id if isinstance(response_id, str) else None
        usage = payload.get("usage")
        self.last_usage = usage if isinstance(usage, dict) else {}
        cost = _usd_for_usage(self.last_usage)
        if cost is not None:
            self.spent_usd += cost
        _CALL_LOG.append(
            {
                "provider": self.provider_name,
                "model": self.model,
                "response_id": self.last_response_id,
                "latency_ms": self.last_latency_ms,
                "usage": dict(self.last_usage),
                "est_cost_usd": cost,
                "cumulative_spent_usd": round(self.spent_usd, 6),
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

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        async def _iter() -> AsyncIterator[str]:
            # The first real-provider milestone keeps the interface correct without
            # adding a second SSE parser. True token streaming can be layered later.
            yield await self.generate(prompt, **kwargs)

        return _iter()

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "response_id": self.last_response_id,
            "latency_ms": self.last_latency_ms,
            "usage": self.last_usage,
            "spent_usd": round(self.spent_usd, 6),
        }


class OpenAIChatProvider(LLMProvider):
    """Minimal OpenAI-compatible *chat completions* provider (free-tier friendly).

    Speaks ``POST {base_url}/chat/completions`` with ``response_format``
    ``json_object`` for structured output. Covers two free lanes with one class:

    - ``ollama``: ``base_url=http://localhost:11434/v1`` (default), no key needed;
      model from ``DSA_OLLAMA_MODEL`` (default ``qwen3:8b``). Token usage mapped
      from Ollama's ``prompt_eval_count``/``eval_count`` when present.
    - ``openai-compat``: any OpenAI-compatible endpoint via
      ``DSA_OPENAI_COMPAT_BASE_URL`` (+ ``DSA_OPENAI_COMPAT_API_KEY`` unless the
      base URL is localhost, e.g. Gemini/Groq free tiers).

    Free runs are labeled with their real provider+model everywhere; the
    publication validator still requires the paid `openai` lane, so free rows
    can never silently promote to leaderboard claims.
    """

    provider_name = "openai-chat"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: float = 120.0,
        local: bool = False,
    ) -> None:
        self.api_key = api_key
        self.model = model or "qwen3:8b"
        self.base_url = (base_url or "http://localhost:11434/v1").rstrip("/")
        self.timeout_s = timeout_s
        self.local = local
        self.last_usage: dict[str, Any] = {}
        self.last_response_id: str | None = None
        self.last_latency_ms: int | None = None
        self.spent_usd: float = 0.0

    async def _request(self, prompt: str, structured: bool = False, **kwargs: Any) -> str:
        cap = _spend_cap_usd()
        if cap is not None and self.spent_usd >= cap:
            raise RuntimeError(
                f"DSA_MAX_COST_USD cap reached (${self.spent_usd:.4f} >= ${cap:.4f}); "
                "refusing further model calls."
            )
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if structured:
            body["response_format"] = {"type": "json_object"}
        max_output_tokens = kwargs.get("max_output_tokens")
        if max_output_tokens is not None:
            body["max_tokens"] = int(max_output_tokens)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=body
            )
        self.last_latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            detail = response.text.replace("\n", " ")[:500]
            raise RuntimeError(
                f"Chat completions API returned HTTP {response.status_code}: {detail}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Chat completions API returned a non-object payload")
        try:
            text = payload["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Chat completions API returned no message content") from exc
        raw_usage = payload.get("usage")
        usage = raw_usage if isinstance(raw_usage, dict) else {}
        norm = {
            "input_tokens": usage.get("prompt_tokens", usage.get("prompt_eval_count", 0)),
            "output_tokens": usage.get("completion_tokens", usage.get("eval_count", 0)),
        }
        self.last_usage = {k: v for k, v in norm.items() if isinstance(v, int)}
        cost = _usd_for_usage(self.last_usage)
        if cost is not None:
            self.spent_usd += cost
        self.last_response_id = (
            payload.get("id")
            if isinstance(payload.get("id"), str)
            else f"local-{uuid.uuid4().hex[:12]}"
        )
        _CALL_LOG.append(
            {
                "provider": self.provider_name,
                "model": self.model,
                "response_id": self.last_response_id,
                "latency_ms": self.last_latency_ms,
                "usage": dict(self.last_usage),
                "est_cost_usd": cost,
                "cumulative_spent_usd": round(self.spent_usd, 6),
            }
        )
        return text if isinstance(text, str) else ""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        text = await self._request(prompt, **kwargs)
        if not text.strip():
            raise RuntimeError("Chat completions API returned empty content")
        return text

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        if not isinstance(schema, type) or not issubclass(schema, BaseModel):
            return json.loads(_strip_json_fence(await self._request(prompt, **kwargs)))
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        raw = _strip_json_fence(
            await self._request(
                f"{prompt}\n\nReturn only one valid JSON object matching this schema: {schema_json}",
                structured=True,
                **kwargs,
            )
        )
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            raise RuntimeError(f"Model returned invalid structured output: {exc}") from exc

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        async def _iter() -> AsyncIterator[str]:
            yield await self.generate(prompt, **kwargs)

        return _iter()

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model,
            "response_id": self.last_response_id,
            "latency_ms": self.last_latency_ms,
            "usage": self.last_usage,
            "spent_usd": round(self.spent_usd, 6),
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
                " (providers: openai, openai-compat, ollama)"
            )

        provider_name = os.getenv("DSA_LLM_PROVIDER", "openai").strip().lower()
        real_provider: Any
        if provider_name == "openai":
            real_provider = OpenAIResponsesProvider()
        elif provider_name == "ollama":
            # Local free lane: no key required. Daemon + model are operator-side
            # (`ollama serve` + `ollama pull $DSA_OLLAMA_MODEL`); without them
            # calls fail loudly with connection errors, never silently stubbed.
            real_provider = OpenAIChatProvider(
                model=os.getenv("DSA_OLLAMA_MODEL") or "qwen3:8b",
                base_url=os.getenv("DSA_OLLAMA_BASE_URL") or "http://localhost:11434/v1",
                local=True,
            )
            real_provider.provider_name = "ollama"
        elif provider_name == "openai-compat":
            # Free-tier hosted lane (e.g. Gemini/Groq OpenAI-compatible endpoints).
            base_url = os.getenv("DSA_OPENAI_COMPAT_BASE_URL", "").strip()
            if not base_url:
                raise RuntimeError(
                    "DSA_OPENAI_COMPAT_BASE_URL is required for DSA_LLM_PROVIDER=openai-compat."
                )
            api_key = os.getenv("DSA_OPENAI_COMPAT_API_KEY")
            if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
                raise RuntimeError(
                    "DSA_OPENAI_COMPAT_API_KEY is required for non-localhost endpoints."
                )
            real_provider = OpenAIChatProvider(
                api_key=api_key,
                model=os.getenv("DSA_OPENAI_COMPAT_MODEL") or "default",
                base_url=base_url,
            )
            real_provider.provider_name = "openai-compat"
        else:
            raise RuntimeError(
                f"DSA_LLM_PROVIDER={provider_name!r} is not implemented yet. "
                "Use openai, openai-compat, or ollama rather than silently falling back to a stub."
            )
        self.inner = real_provider
        self.active_provider = real_provider.provider_name
        self.active_model = real_provider.model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return await self.inner.generate(prompt, **kwargs)

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        return await self.inner.structured_output(prompt, schema, **kwargs)

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        return self.inner.stream(prompt, **kwargs)

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
