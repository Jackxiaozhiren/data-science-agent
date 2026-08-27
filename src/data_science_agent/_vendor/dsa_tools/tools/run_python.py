from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_execution.python_sandbox import execute_python
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class RunPythonInput(BaseModel):
    code: str = Field(
        description="Python code to execute in sandbox. Available: pl, np, math, statistics, df (if dataset_path given)"
    )
    dataset_path: str | None = None
    timeout_ms: int = Field(default=5000, ge=100, le=30000)


class RunPythonOutput(BaseModel):
    stdout: str
    stderr: str
    error: str | None = None
    variables: dict[str, str] = Field(default_factory=dict)
    duration_ms: int


class RunPythonTool(BaseTool[RunPythonInput, RunPythonOutput]):
    name = "run_python"
    description = "Execute Python code in a restricted sandbox. Dataset exposed as 'df' (Polars DataFrame) if dataset_path provided."
    input_model = RunPythonInput
    output_model = RunPythonOutput

    async def execute(self, inp: RunPythonInput) -> RunPythonOutput:
        extra: dict[str, Any] = {}
        if inp.dataset_path:
            p = Path(inp.dataset_path)
            if not p.exists():
                raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
            fmt = detect_format(p.name)
            try:
                df = load_dataframe(p, fmt)
            except Exception as e:
                raise ToolExecutionError(str(e)) from e
            extra["df"] = df
            # also provide dataset path var
            extra["dataset_path"] = str(p)

        result = execute_python(inp.code, extra_globals=extra, timeout_ms=inp.timeout_ms)
        return RunPythonOutput(
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            error=result.get("error"),
            variables=result.get("variables", {}),
            duration_ms=int(result.get("duration_ms", 0)),
        )
