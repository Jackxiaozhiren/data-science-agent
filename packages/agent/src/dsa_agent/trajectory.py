from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NodeExecution(BaseModel):
    node: str
    status: Literal["ok", "error"] = "ok"
    duration_ms: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)


class ToolExecution(BaseModel):
    call_id: str
    tool: str
    status: Literal["ok", "error"] = "ok"
    duration_ms: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RetryEvent(BaseModel):
    attempt: int
    trigger: str = ""
    success: bool = False


class Checkpoint(BaseModel):
    id: str
    node: str
    state_keys: list[str] = Field(default_factory=list)


class AgentTrajectory(BaseModel):
    run_id: str
    nodes: list[NodeExecution] = Field(default_factory=list)
    tool_calls: list[ToolExecution] = Field(default_factory=list)
    retries: list[RetryEvent] = Field(default_factory=list)
    checkpoints: list[Checkpoint] = Field(default_factory=list)
    final_state: dict[str, Any] = Field(default_factory=dict)

    def tool_efficiency_score(self, necessary: int | None = None) -> float | None:
        actual = len(self.tool_calls)
        if actual == 0:
            return None
        nec = (
            necessary
            if necessary is not None
            else max(1, actual - sum(1 for t in self.tool_calls if t.status == "error"))
        )
        return nec / actual

    def retry_quality(self) -> dict[str, Any]:
        useful = sum(1 for r in self.retries if r.success)
        pointless = sum(1 for r in self.retries if not r.success)
        return {
            "retry_count": len(self.retries),
            "useful": useful,
            "pointless": pointless,
            "success_rate": (useful / len(self.retries)) if self.retries else None,
        }


def from_analysis_state(state: Any) -> AgentTrajectory:
    calls = (
        getattr(state, "tool_calls", None)
        or (state.get("tool_calls") if isinstance(state, dict) else [])
        or []
    )
    nodes = (
        getattr(state, "agent_messages", None)
        or (state.get("agent_messages") if isinstance(state, dict) else [])
        or []
    )
    rid = getattr(state, "run_id", None) or (
        state.get("run_id", "unknown") if isinstance(state, dict) else "unknown"
    )
    return AgentTrajectory(
        run_id=str(rid),
        nodes=[
            NodeExecution(
                node=getattr(m, "agent", None) or m.get("agent", "unknown")
                if isinstance(m, dict)
                else str(m),
                status="ok",
            )
            for m in (nodes[:20] if isinstance(nodes, list) else [])
        ],
        tool_calls=[
            ToolExecution(
                call_id=c.get("call_id", "") if isinstance(c, dict) else getattr(c, "call_id", ""),
                tool=c.get("tool", "") if isinstance(c, dict) else getattr(c, "tool", ""),
                status=c.get("status", "ok") if isinstance(c, dict) else getattr(c, "status", "ok"),
                duration_ms=int(
                    c.get("duration_ms", 0) if isinstance(c, dict) else getattr(c, "duration_ms", 0)
                ),
            )
            for c in (calls if isinstance(calls, list) else [])
        ],
        retries=[
            RetryEvent(attempt=i + 1, trigger="tool_error", success=False)
            for i in range(
                int(
                    getattr(state, "retry_count", 0)
                    if not isinstance(state, dict)
                    else state.get("retry_count", 0) or 0
                )
            )
        ],
        final_state={
            "status": getattr(state, "status", None)
            or (state.get("status") if isinstance(state, dict) else None)
        },
    )
