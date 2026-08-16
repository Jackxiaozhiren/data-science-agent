from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from dsa_tools.errors import ToolExecutionError

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolMeta(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"


class ToolResult(BaseModel, Generic[OutputT]):
    tool: str
    call_id: str
    status: str  # ok | error
    duration_ms: int
    output: OutputT | None = None
    error: str | None = None
    meta: dict[str, Any] = {}


class BaseTool(ABC, Generic[InputT, OutputT]):
    name: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]

    def meta(self) -> ToolMeta:
        return ToolMeta(name=self.name, description=self.description)

    async def run(self, payload: dict[str, Any] | InputT) -> ToolResult[OutputT]:
        call_id = uuid.uuid4().hex[:12]
        t0 = time.perf_counter()
        try:
            inp = self._coerce_input(payload)
            out = await self.execute(inp)
            dur = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                tool=self.name, call_id=call_id, status="ok", duration_ms=dur, output=out
            )
        except ToolExecutionError as e:
            dur = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                tool=self.name, call_id=call_id, status="error", duration_ms=dur, error=str(e)
            )
        except Exception as e:
            dur = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                tool=self.name,
                call_id=call_id,
                status="error",
                duration_ms=dur,
                error=f"{type(e).__name__}: {e}",
            )

    def _coerce_input(self, payload: dict[str, Any] | InputT) -> InputT:
        if isinstance(payload, self.input_model):
            return payload
        return self.input_model.model_validate(payload)

    @abstractmethod
    async def execute(self, inp: InputT) -> OutputT: ...
