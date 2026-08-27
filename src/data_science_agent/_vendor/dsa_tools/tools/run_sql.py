from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_execution.sql_guard import enforce_row_limit, validate_sql
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class RunSQLInput(BaseModel):
    sql: str = Field(description="Read-only SELECT/WITH SQL")
    dataset_path: str | None = Field(
        default=None, description="Path to dataset to expose as 'dataset' table"
    )
    max_rows: int = Field(default=1000, ge=1, le=10000)


class RunSQLOutput(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    sql: str


class RunSQLTool(BaseTool[RunSQLInput, RunSQLOutput]):
    name = "run_sql"
    description = (
        "Execute read-only SQL against a dataset (DuckDB). Exposes dataset as table 'dataset'."
    )
    input_model = RunSQLInput
    output_model = RunSQLOutput

    async def execute(self, inp: RunSQLInput) -> RunSQLOutput:
        sql = validate_sql(inp.sql, max_rows=inp.max_rows)
        sql = enforce_row_limit(sql, inp.max_rows)

        con = duckdb.connect(database=":memory:")
        try:
            if inp.dataset_path:
                p = Path(inp.dataset_path)
                if not p.exists():
                    raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
                fmt = detect_format(p.name)
                # Register as Arrow for uniform handling
                df = load_dataframe(p, fmt)
                con.register("dataset", df.to_arrow())
            result = con.execute(sql)
            cols = [d[0] for d in result.description] if result.description else []
            rows = result.fetchall()
            # coerce rows to list[list]
            rows_list: list[list[Any]] = [list(r) for r in rows]
            return RunSQLOutput(columns=cols, rows=rows_list, row_count=len(rows_list), sql=sql)
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"SQL execution failed: {e}") from e
        finally:
            try:
                con.close()
            except Exception:
                pass
