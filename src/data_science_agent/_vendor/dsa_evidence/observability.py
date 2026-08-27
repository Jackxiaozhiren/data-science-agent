from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import BaseModel, Field


class Span(BaseModel):
    name: str
    kind: Literal["planner", "tool", "critic", "report", "llm"] = "tool"
    start_ms: int = 0
    end_ms: int | None = None
    duration_ms: int | None = None
    status: Literal["ok", "error"] = "ok"
    attrs: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    trace_id: str
    run_id: str
    spans: list[Span] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)

    def add_span(self, span: Span) -> None:
        self.spans.append(span)

    def finalize(self) -> None:
        if self.spans:
            total = sum((s.duration_ms or 0) for s in self.spans)
            self.metrics["total_duration_ms"] = float(total)
            for kind in ("planner", "tool", "critic", "report"):
                self.metrics[f"{kind}_duration_ms"] = float(
                    sum((s.duration_ms or 0) for s in self.spans if s.kind == kind)
                )


def span(name: str, kind: str = "tool") -> Span:
    return Span(name=name, kind=kind, start_ms=int(time.perf_counter() * 1000))  # type: ignore[arg-type]
