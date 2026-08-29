from __future__ import annotations

import hashlib
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import AsyncIterator
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError

    @abstractmethod
    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError


class CachedLLMProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, max_entries: int = 128, ttl_s: float = 600) -> None:
        self.inner = inner
        self._cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self.max_entries = max_entries
        self.ttl = ttl_s

    def _key(self, prompt: str, kwargs: dict[str, Any]) -> str:
        raw = f"{prompt}::{sorted(kwargs.items())}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        k = self._key(prompt, kwargs)
        now = time.monotonic()
        if k in self._cache:
            ts, val = self._cache[k]
            if now - ts < self.ttl:
                self._cache.move_to_end(k)
                return val
            del self._cache[k]
        val = await self.inner.generate(prompt, **kwargs)
        self._cache[k] = (now, val)
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)
        return val

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        return await self.inner.structured_output(prompt, schema, **kwargs)

    def stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        return self.inner.stream(prompt, **kwargs)
