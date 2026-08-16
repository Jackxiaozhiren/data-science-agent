from __future__ import annotations

from pathlib import Path
from typing import Literal

import polars as pl
from pydantic import BaseModel, Field

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class CausalCheckInput(BaseModel):
    dataset_path: str
    treatment: str = Field(description="Treatment / exposure column")
    outcome: str = Field(description="Outcome column")
    confounders: list[str] = Field(
        default_factory=list, description="Optional confounder columns for adjustment"
    )
    method: Literal["difference_in_means", "adjusted_regression"] = "difference_in_means"


class CausalCheckOutput(BaseModel):
    treatment: str
    outcome: str
    estimate: float
    method: str
    sample_size: int
    adjusted: bool
    confidence_note: str
    passes_causal_bar: bool = False
    details: dict[str, object] = Field(default_factory=dict)


class CausalCheckTool(BaseTool[CausalCheckInput, CausalCheckOutput]):
    name = "causal_check"
    description = "Causal stub (DoWhy-lite): association vs causation guard — never returns a causal effect without adjustment and confidence note"
    input_model = CausalCheckInput
    output_model = CausalCheckOutput

    async def execute(self, inp: CausalCheckInput) -> CausalCheckOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        for col in [inp.treatment, inp.outcome] + inp.confounders:
            if col not in df.columns:
                raise ToolExecutionError(f"Column {col!r} not found; columns: {df.columns}")
        sub = df.select([inp.treatment, inp.outcome] + inp.confounders).drop_nulls()
        if sub.height < 10:
            raise ToolExecutionError("Need >=10 rows after drop_nulls for causal check")
        # Heuristic: treatment should be near-binary or categorical for stub; otherwise flag
        uniq_t = sub[inp.treatment].n_unique()
        if uniq_t > 20:
            return CausalCheckOutput(
                treatment=inp.treatment,
                outcome=inp.outcome,
                estimate=0.0,
                method=inp.method,
                sample_size=sub.height,
                adjusted=False,
                confidence_note="Treatment not near-binary; causal stub cannot estimate an effect without proper design. Association only.",
                passes_causal_bar=False,
                details={"unique_treatment": uniq_t},
            )
        if inp.method == "difference_in_means":
            # naive diff in means between top 2 treatment levels
            levels = sub[inp.treatment].unique().to_list()[:2]
            if len(levels) < 2:
                raise ToolExecutionError("Need >=2 treatment levels")
            a = sub.filter(pl.col(inp.treatment) == levels[0])[inp.outcome].to_numpy()
            b = sub.filter(pl.col(inp.treatment) == levels[1])[inp.outcome].to_numpy()
            try:
                est = float(b.astype(float).mean() - a.astype(float).mean())
            except Exception as e:
                raise ToolExecutionError(f"Outcome not numeric: {e}") from e
            return CausalCheckOutput(
                treatment=inp.treatment,
                outcome=inp.outcome,
                estimate=est,
                method="difference_in_means",
                sample_size=sub.height,
                adjusted=False,
                confidence_note="Naive difference-in-means is association, not causation, without randomization or confounder control.",
                passes_causal_bar=False,
                details={"levels": [str(x) for x in levels]},
            )
        # adjusted_regression: regress outcome on treatment + confounders
        try:
            X_cols = [inp.treatment] + inp.confounders
            # Encode treatment if categorical to numeric via one-hot style: use first confounder handling? Keep simple: map unique to 0/1 if binary
            # For stub, require confounders numeric; if treatment is categorical, map to 0/1 by first two levels
            import numpy as np
            from sklearn.linear_model import LinearRegression

            t_series = sub[inp.treatment]
            if t_series.dtype in (pl.String, pl.Utf8):
                mapping = {v: i for i, v in enumerate(t_series.unique().to_list()[:2])}
                t_num = t_series.map_elements(
                    lambda x: mapping.get(x, 0), return_dtype=pl.Int64
                ).to_numpy()
            else:
                t_num = t_series.to_numpy().astype(float)
            X_list = [t_num.reshape(-1, 1)]
            for c in inp.confounders:
                arr = sub[c].to_numpy().astype(float).reshape(-1, 1)
                X_list.append(arr)
            X = np.hstack(X_list) if len(X_list) > 1 else X_list[0]
            y = sub[inp.outcome].to_numpy().astype(float)
            model = LinearRegression()
            model.fit(X, y)
            est = float(model.coef_[0])
            return CausalCheckOutput(
                treatment=inp.treatment,
                outcome=inp.outcome,
                estimate=est,
                method="adjusted_regression",
                sample_size=sub.height,
                adjusted=True,
                confidence_note="Regression-adjusted estimate; causation still not established without identification assumptions (no unmeasured confounding, positivity, consistency).",
                passes_causal_bar=False,
                details={"confounders": inp.confounders},
            )
        except Exception as e:
            raise ToolExecutionError(f"Adjusted regression failed: {e}") from e
