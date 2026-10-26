from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    DATA_PROFILING = "DATA_PROFILING"
    ANALYSIS = "ANALYSIS"
    MODELING = "MODELING"
    VALIDATION = "VALIDATION"
    SYNTHESIS = "SYNTHESIS"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class AnalysisStep(BaseModel):
    id: str
    name: str
    description: str
    tool: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class AnalysisPlan(BaseModel):
    objective: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[AnalysisStep]
    required_tools: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)


class AgentMessage(BaseModel):
    agent: str
    role: Literal["system", "user", "assistant", "tool"] = "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolCallRecord(BaseModel):
    call_id: str
    tool: str
    #: The plan step that produced this call, when the executor knew one. `$from_step_id` selects on it, which is
    #: the only reference form that survives a retry or a parallel batch -- a position in this list does not.
    step_id: str | None = None
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    status: Literal["ok", "error"] = "ok"
    error: str | None = None
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Evidence(BaseModel):
    id: str
    claim: str
    source_type: Literal["sql", "python", "statistical_test", "model", "visualization"]
    source_id: str
    result: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    validation_status: Literal["pending", "verified", "failed"] = "pending"


class Insight(BaseModel):
    id: str
    finding: str
    evidence_ids: list[str] = Field(default_factory=list)
    magnitude: str | None = None
    significance: str | None = None
    limitation: str | None = None


class ValidationResult(BaseModel):
    check: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    id: str
    type: str  # dataset|code|sql|table|chart|model|notebook|report|evidence
    path: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = "agent"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Budget(BaseModel):
    max_steps: int = 20
    max_tool_calls: int = 40
    max_retries: int = 3
    max_tokens: int = 50000


class ReasoningRecord(BaseModel):
    """What produced this run, captured when it began.

    R-02 made the effective mode a fact the process reports rather than a label the operator sets, and R-05
    added a second place a mode can come from. Neither is auditable from a later reading: a row computed by
    the deterministic planner and a row computed by a model look identical otherwise, and `/version` answers
    with whatever the process resolves *now*. `source` says which knob answered -- the settings stored through
    the interface, the environment, or neither.
    """

    mode: str
    provider: str
    model: str | None = None
    source: str = "environment"


class AnalysisState(BaseModel):
    run_id: str
    project_id: str = "default"
    dataset_id: str
    dataset_path: str | None = None
    user_query: str
    objective: str = ""
    plan: list[AnalysisStep] = Field(default_factory=list)
    current_step: int = 0
    agent_messages: list[AgentMessage] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    validation_results: list[ValidationResult] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    report_id: str | None = None
    report_markdown: str | None = None
    status: AnalysisStatus = AnalysisStatus.UNDERSTANDING
    error: str | None = None
    retry_count: int = 0
    tool_call_count: int = 0
    budget: Budget = Field(default_factory=Budget)
    reasoning: ReasoningRecord | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
