from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_datasets.artifact_paths import artifact_root, is_safe_segment
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
    #: ADR-004 D3. The digest of the bytes this call wrote, computed from the payload it handed to
    #: the file and then checked against what the file holds.
    sha256: str
    bytes: int


class SaveArtifactTool(BaseTool[SaveArtifactInput, SaveArtifactOutput]):
    name = "save_artifact"
    description = "Save an artifact under artifacts/<run_id>/"
    input_model = SaveArtifactInput
    output_model = SaveArtifactOutput

    async def execute(self, inp: SaveArtifactInput) -> SaveArtifactOutput:
        if ".." in inp.filename or "/" in inp.filename or "\\" in inp.filename:
            raise ToolExecutionError("Invalid filename")
        if not is_safe_segment(inp.run_id):
            raise ToolExecutionError(f"Invalid run_id {inp.run_id!r}: use one path component")
        root = artifact_root(inp.run_id)
        root.mkdir(parents=True, exist_ok=True)
        dest = root / inp.filename
        # Prevent overwrite traversal
        try:
            dest.resolve().relative_to(root.resolve())
        except ValueError:
            raise ToolExecutionError("Path escapes artifact root")
        payload = inp.content.encode("utf-8")
        dest.write_bytes(payload)
        # ADR-004 D3: the writer re-reads what it wrote. A digest computed from the payload alone
        # would describe what this process intended to write; the read-back is what makes the number
        # a fact about the file, and a mismatch is loud rather than a digest nobody compares.
        readback = dest.read_bytes()
        if readback != payload:
            raise ToolExecutionError(
                f"wrote {len(payload)} bytes to {dest.name} and read back {len(readback)}; "
                "refusing to report a digest the file does not hold"
            )
        digest = hashlib.sha256(payload).hexdigest()
        metadata = dict(inp.metadata)
        metadata["sha256"] = digest
        aid = f"A-{uuid.uuid4().hex[:8]}"
        return SaveArtifactOutput(
            artifact_id=aid,
            path=str(dest),
            type=inp.type,
            metadata=metadata,
            sha256=digest,
            bytes=len(payload),
        )
