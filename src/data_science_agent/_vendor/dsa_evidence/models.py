from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceNode(BaseModel):
    id: str
    claim: str
    source_type: Literal["sql", "python", "statistical_test", "model", "visualization"]
    source_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    validation_status: Literal["pending", "verified", "failed"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InsightNode(BaseModel):
    id: str
    finding: str
    evidence_ids: list[str] = Field(default_factory=list)
    magnitude: str | None = None
    significance: str | None = None
    limitation: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceEdge(BaseModel):
    from_id: str
    to_id: str
    kind: Literal["supports", "derives_from", "validates"] = "supports"


class EvidenceGraph(BaseModel):
    run_id: str
    dataset_id: str
    dataset_path: str | None = None
    dataset_sha256: str | None = None
    nodes: list[EvidenceNode] = Field(default_factory=list)
    insights: list[InsightNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def trace_insight(self, insight_id: str) -> dict[str, Any]:
        ins = next((i for i in self.insights if i.id == insight_id), None)
        if ins is None:
            return {"error": f"Insight not found: {insight_id}"}
        evs = [e for e in self.nodes if e.id in ins.evidence_ids]
        call_ids = [e.source_id for e in evs]
        calls = [c for c in self.tool_calls if c.get("call_id") in call_ids]
        return {
            "insight": ins.model_dump(mode="json"),
            "evidence": [e.model_dump(mode="json") for e in evs],
            "tool_calls": calls,
            "dataset": {
                "dataset_id": self.dataset_id,
                "path": self.dataset_path,
                "sha256": self.dataset_sha256,
            },
        }
