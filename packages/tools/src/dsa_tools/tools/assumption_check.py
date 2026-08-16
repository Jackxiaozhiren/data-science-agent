from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl
from pydantic import BaseModel, Field
from scipy import stats

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class AssumptionCheckInput(BaseModel):
    dataset_path: str
    column: str | None = None
    columns: list[str] | None = None
    check: Literal["normality", "variance_homogeneity", "all"] = "all"
    group_col: str | None = None


class AssumptionCheckOutput(BaseModel):
    checks: list[dict[str, object]] = Field(default_factory=list)
    recommendation: str = ""
    passed: bool = True


class AssumptionCheckTool(BaseTool[AssumptionCheckInput, AssumptionCheckOutput]):
    name = "assumption_check"
    description = "Check statistical assumptions: Shapiro normality, Levene variance homogeneity, with recommendations"
    input_model = AssumptionCheckInput
    output_model = AssumptionCheckOutput

    async def execute(self, inp: AssumptionCheckInput) -> AssumptionCheckOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)

        cols = inp.columns or ([inp.column] if inp.column else [])
        if not cols:
            # default: first numeric col
            numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32)]
            if not numeric:
                raise ToolExecutionError(f"No numeric column found; columns: {df.columns}")
            cols = [numeric[0]]

        checks: list[dict[str, object]] = []
        overall_pass = True
        for col in cols:
            if col not in df.columns:
                raise ToolExecutionError(f"Column {col!r} not found")
            vals = df[col].drop_nulls().to_numpy()
            try:
                arr = vals.astype(float)
            except Exception as e:
                raise ToolExecutionError(f"Column {col!r} not numeric: {e}") from e
            if len(arr) < 8:
                checks.append({"column": col, "check": "normality", "n": len(arr), "note": "n<8, normality unreliable", "passed": True})
                continue
            # Shapiro (n up to 5000) else D'Agostino
            try:
                if len(arr) <= 5000:
                    stat, pval = stats.shapiro(arr)
                    test_name = "shapiro"
                else:
                    stat, pval = stats.normaltest(arr)
                    test_name = "dagostino"
            except Exception as e:
                checks.append({"column": col, "check": "normality", "error": str(e), "passed": True})
                continue
            passed = bool(pval > 0.05)
            checks.append({"column": col, "check": test_name, "statistic": float(stat), "p_value": float(pval), "passed": passed})
            if not passed:
                overall_pass = False

        # Variance homogeneity across groups if requested
        if inp.group_col and inp.group_col in df.columns:
            groups = df[inp.group_col].unique().to_list()
            if len(groups) >= 2:
                arrays = []
                for g in groups[:6]:  # cap
                    vals = df.filter(pl.col(inp.group_col) == g)[cols[0]].drop_nulls().to_numpy()
                    try:
                        arrays.append(vals.astype(float))
                    except Exception:
                        pass
                if len(arrays) >= 2 and all(len(a) >= 3 for a in arrays):
                    try:
                        stat, pval = stats.levene(*arrays)
                        passed = bool(pval > 0.05)
                        checks.append({"check": "levene", "statistic": float(stat), "p_value": float(pval), "passed": passed, "group_col": inp.group_col})
                        if not passed:
                            overall_pass = False
                    except Exception as e:
                        checks.append({"check": "levene", "error": str(e), "passed": True})

        rec = "Assumptions hold (p>0.05)." if overall_pass else "Normality or homogeneity violated: consider Welch/Mann-Whitney, transform or bootstrap; report with caution."
        return AssumptionCheckOutput(checks=checks, recommendation=rec, passed=overall_pass)
