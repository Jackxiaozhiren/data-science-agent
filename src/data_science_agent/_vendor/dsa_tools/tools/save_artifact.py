from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class SaveArtifactInput(BaseModel):
    run_id: str = Field(description="Analysis run id for artifact folder")
    type: str = Field(
        description="Artifact type: dataset|code|sql|table|chart|model|notebook|report|evidence"
    )
    filename: str = Field(description="Filename, e.g. report.md")
    content: str = Field(description="Text content to save (base64 for binary handled elsewhere)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SaveArtifactOutput(BaseModel):
    artifact_id: str
    path: str
    type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SaveArtifactTool(BaseTool[SaveArtifactInput, SaveArtifactOutput]):
    name = "save_artifact"
    description = "Save an artifact under artifacts/<run_id>/"
    input_model = SaveArtifactInput
    output_model = SaveArtifactOutput

    async def execute(self, inp: SaveArtifactInput) -> SaveArtifactOutput:
        if ".." in inp.filename or "/" in inp.filename or "\\" in inp.filename:
            raise ToolExecutionError("Invalid filename")
        root = Path(__file__).resolve().parents[4] / "artifacts" / inp.run_id
        root.mkdir(parents=True, exist_ok=True)
        dest = root / inp.filename
        # Prevent overwrite traversal
        try:
            dest.resolve().relative_to(root.resolve())
        except ValueError:
            raise ToolExecutionError("Path escapes artifact root")
        dest.write_text(inp.content, encoding="utf-8")
        aid = f"A-{uuid.uuid4().hex[:8]}"
        return SaveArtifactOutput(
            artifact_id=aid, path=str(dest), type=inp.type, metadata=inp.metadata
        )
