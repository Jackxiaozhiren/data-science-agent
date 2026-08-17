from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    name: str
    version: str
    type: list[str] = Field(default_factory=list)
    requires: dict[str, str] = Field(default_factory=dict)
    license: str = "MIT"
    entrypoint: dict[str, str] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path | str) -> PluginManifest:
        import yaml

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        return cls.model_validate(data)
