from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, Field
from scipy.stats import kendalltau, pearsonr, spearmanr

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class CorrelationInput(BaseModel):
    dataset_path: str
    x: str = Field(description="Column name for x")
    y: str = Field(description="Column name for y")
    method: Literal["pearson", "spearman", "kendall"] = "pearson"


class CorrelationOutput(BaseModel):
    method: str
    x: str
    y: str
    n: int
    r: float
    p_value: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    interpretation: str
    limitations: str = "Correlation does not imply causation."


def _pearson_ci(r: float, n: int, alpha: float = 0.05) -> tuple[float | None, float | None]:
    import math

    if n < 4 or abs(r) >= 1.0:
        return None, None
    # Fisher z transform
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    z_crit = 1.96  # 95%
    lo_z = z - z_crit * se
    hi_z = z + z_crit * se
    lo = (math.exp(2 * lo_z) - 1) / (math.exp(2 * lo_z) + 1)
    hi = (math.exp(2 * hi_z) - 1) / (math.exp(2 * hi_z) + 1)
    return lo, hi


class CorrelationTool(BaseTool[CorrelationInput, CorrelationOutput]):
    name = "correlation_analysis"
    description = "Compute correlation (Pearson/Spearman/Kendall) between two numeric columns"
    input_model = CorrelationInput
    output_model = CorrelationOutput

    async def execute(self, inp: CorrelationInput) -> CorrelationOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        if inp.x not in df.columns or inp.y not in df.columns:
            raise ToolExecutionError(f"Columns not found. Available: {df.columns}")
        sub = df.select([inp.x, inp.y]).drop_nulls()
        if sub.height < 3:
            raise ToolExecutionError("Not enough non-null rows for correlation (need >=3)")
        try:
            x = sub[inp.x].to_numpy().astype(float)
            y = sub[inp.y].to_numpy().astype(float)
        except Exception as e:
            raise ToolExecutionError(f"Columns must be numeric: {e}") from e

        if inp.method == "pearson":
            r, pval = pearsonr(x, y)
            ci_low, ci_high = _pearson_ci(float(r), len(x))
        elif inp.method == "spearman":
            r, pval = spearmanr(x, y)
            ci_low, ci_high = None, None
        else:
            r, pval = kendalltau(x, y)
            ci_low, ci_high = None, None

        r = float(r)
        pval_f = float(pval) if pval is not None else None
        # interpretation
        abs_r = abs(r)
        strength = "negligible" if abs_r < 0.1 else "weak" if abs_r < 0.3 else "moderate" if abs_r < 0.5 else "strong" if abs_r < 0.7 else "very strong"
        direction = "positive" if r > 0 else "negative" if r < 0 else "no"
        sig = ""
        if pval_f is not None:
            sig = " (statistically significant at p<0.05)" if pval_f < 0.05 else " (not significant)"

        interpretation = f"{strength} {direction} association (r={r:.3f}){sig}."

        return CorrelationOutput(
            method=inp.method,
            x=inp.x,
            y=inp.y,
            n=len(x),
            r=r,
            p_value=pval_f,
            ci_low=ci_low,
            ci_high=ci_high,
            interpretation=interpretation,
        )
