from __future__ import annotations

from typing import Any, Protocol


class DataSciencePlugin(Protocol):
    name: str
    version: str

    def register_tools(self) -> list[Any]: ...

    def register_models(self) -> list[Any]: ...

    def register_evaluators(self) -> list[Any]: ...


class BasePlugin:
    name: str = "base"
    version: str = "0.1.0"
    permissions: list[str] = []
    dependencies: list[str] = []

    def register_tools(self) -> list[Any]:
        return []

    def register_models(self) -> list[Any]:
        return []

    def register_evaluators(self) -> list[Any]:
        return []
