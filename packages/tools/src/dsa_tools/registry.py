from __future__ import annotations

from typing import Any

from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolNotFoundError

_REGISTRY: dict[str, BaseTool[Any, Any]] = {}


def register(tool: BaseTool[Any, Any]) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> BaseTool[Any, Any]:
    t = _REGISTRY.get(name)
    if t is None:
        raise ToolNotFoundError(f"Tool not found: {name}. Available: {sorted(_REGISTRY)}")
    return t


def list_tools() -> list[str]:
    return sorted(_REGISTRY)


def clear() -> None:
    _REGISTRY.clear()
