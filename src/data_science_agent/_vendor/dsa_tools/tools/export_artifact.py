"""Export a prior tool result (or inline table/chart) to a file — ADR-002.

General-purpose persistence: turns in-memory tool outputs into downloadable
files inside the run workspace, with a content hash recorded for evidence.
The tool authors no content: only byte-identical relocation of agent-computed
results (CSV/XLSX from tabular outputs, PNG from chart bytes).

References to prior calls ({"$from_step": i} / {"$from_tool": name}) are
resolved by the executor *before* dispatch (graph._resolve_refs); reaching
execute() unresolved is an honest error, never silent invention.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError

_ALLOWED_FORMATS = ("csv", "xlsx", "png")
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class ExportArtifactInput(BaseModel):
    source: dict[str, Any] = Field(
        description="Prior tool output payload (columns+rows table or base64 chart), "
        "or a {$from_step: i} / {$from_tool: name} reference resolved by the executor"
    )
    filename: str = Field(description="Target filename, e.g. predictions.csv (no dirs)")
    format: str = Field(description="csv | xlsx | png (must match filename suffix)")
    workspace: str = Field(description="Run workspace directory (injected by executor)")


class ExportArtifactOutput(BaseModel):
    path: str
    sha256: str
    filename: str
    rows: int = 0
    columns: list[str] = Field(default_factory=list)
    bytes: int = 0


class ExportArtifactTool(BaseTool[ExportArtifactInput, ExportArtifactOutput]):
    name = "export_artifact"
    description = (
        "Persist a prior tool result to a file in the run workspace "
        "(tabular results to csv/xlsx, chart results to png). Byte-identical "
        "relocation only — never synthesizes content."
    )
    input_model = ExportArtifactInput
    output_model = ExportArtifactOutput

    async def execute(self, inp: ExportArtifactInput) -> ExportArtifactOutput:
        fmt = (inp.format or "").lower()
        if fmt not in _ALLOWED_FORMATS:
            raise ToolExecutionError(f"Unsupported format: {inp.format!r}")
        name = inp.filename or ""
        if (
            not name
            or "/" in name
            or "\\" in name
            or ".." in name
            or not name.lower().endswith("." + fmt)
        ):
            raise ToolExecutionError(f"Invalid filename for format {fmt}: {name!r}")
        src = inp.source or {}
        if not isinstance(src, dict):
            raise ToolExecutionError("source must be a tool-output object")
        if "$from_step" in src or "$from_tool" in src:
            raise ToolExecutionError("unresolved source reference (executor did not resolve it)")
        root = Path(inp.workspace or "")
        if not str(root):
            raise ToolExecutionError("workspace is required")
        root.mkdir(parents=True, exist_ok=True)
        dest = root / name
        try:
            dest.resolve().relative_to(root.resolve())
        except ValueError:
            raise ToolExecutionError("Path escapes workspace")
        rows, cols, nbytes = 0, [], 0
        if fmt in ("csv", "xlsx"):
            columns = src.get("columns")
            data = src.get("rows")
            if (
                not isinstance(columns, list)
                or not columns
                or not all(isinstance(c, str) for c in columns)
                or not isinstance(data, list)
            ):
                raise ToolExecutionError("csv/xlsx export needs source with columns+rows")
            rows, cols = len(data), list(columns)
            if fmt == "csv":
                import csv as _csv

                with dest.open("w", newline="", encoding="utf-8") as fh:
                    w = _csv.writer(fh)
                    w.writerow(cols)
                    w.writerows(data)
            else:
                try:
                    import openpyxl as _oxl
                except ImportError:
                    raise ToolExecutionError("openpyxl unavailable for xlsx export")
                wb = _oxl.Workbook()
                ws = wb.active
                ws.append(cols)
                for r in data:
                    ws.append(list(r) if isinstance(r, (list, tuple)) else [r])
                wb.save(dest)
        else:  # png
            import base64 as _b64

            b64 = src.get("base64_png") or src.get("png_base64")
            if not isinstance(b64, str) or not b64:
                raise ToolExecutionError("png export needs source with base64 chart bytes")
            try:
                raw = _b64.b64decode(b64)
            except Exception:
                raise ToolExecutionError("invalid base64 chart payload")
            if raw[:8] != _PNG_MAGIC:
                raise ToolExecutionError("chart payload is not a PNG")
            dest.write_bytes(raw)
            nbytes = len(raw)
        digest = hashlib.sha256(dest.read_bytes()).hexdigest()
        return ExportArtifactOutput(
            path=str(dest),
            sha256=digest,
            filename=name,
            rows=rows,
            columns=cols,
            bytes=nbytes or dest.stat().st_size,
        )
