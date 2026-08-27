from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class CreateEvidenceInput(BaseModel):
    claim: str
    source_type: Literal["sql", "python", "statistical_test", "model", "visualization"] = "python"
    source_id: str = Field(description="ToolCall id or artifact id backing this claim")
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class CreateEvidenceOutput(BaseModel):
    evidence_id: str
    claim: str
    source_type: str
    source_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float
    validation_status: str = "pending"


class CreateEvidenceTool(BaseTool[CreateEvidenceInput, CreateEvidenceOutput]):
    name = "create_evidence"
    description = "Create an evidence record linking a claim to its computation source"
    input_model = CreateEvidenceInput
    output_model = CreateEvidenceOutput

    async def execute(self, inp: CreateEvidenceInput) -> CreateEvidenceOutput:
        if not inp.claim.strip():
            raise ToolExecutionError("claim required")
        eid = f"E-{uuid.uuid4().hex[:8]}"
        return CreateEvidenceOutput(
            evidence_id=eid,
            claim=inp.claim,
            source_type=inp.source_type,
            source_id=inp.source_id,
            result=inp.result,
            confidence=inp.confidence,
            validation_status="pending",
        )
