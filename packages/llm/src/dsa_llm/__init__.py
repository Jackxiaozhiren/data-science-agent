from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str: ...

    @abstractmethod
    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def stream(self, prompt: str, **kwargs: Any) -> Any: ...
