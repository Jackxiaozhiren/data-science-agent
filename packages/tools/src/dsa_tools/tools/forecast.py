from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl
from pydantic import BaseModel, Field
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class ForecastInput(BaseModel):
    dataset_path: str
    date_col: str | None = None
    value_col: str | None = None
    periods: int = Field(default=30, ge=1, le=365, description="Number of future periods to forecast")
    method: Literal["naive_trend", "moving_average", "linear_trend"] = "linear_trend"


class ForecastOutput(BaseModel):
    method: str
    date_col: str
    value_col: str
    n_train: int
    periods: int
    forecast: list[float]
    metrics: dict[str, float] = Field(default_factory=dict)
    diagnostics: dict[str, object] = Field(default_factory=dict)


def _detect_cols(df: pl.DataFrame, date_col: str | None, value_col: str | None) -> tuple[str, str]:
    # auto-detect datetime + numeric if not provided
    if date_col and value_col:
        if date_col not in df.columns or value_col not in df.columns:
            raise ToolExecutionError(f"Columns not found: {df.columns}")
        return date_col, value_col
    # try to find datetime column
    date_candidates = [c for c in df.columns if df[c].dtype in (pl.Date, pl.Datetime)]
    # fallback: column named date/time
    if not date_candidates:
        for c in df.columns:
            if c.lower() in ("date", "time", "datetime", "timestamp", "ds"):
                date_candidates.append(c)
                break
    if not date_candidates:
        raise ToolExecutionError(f"No datetime column found; available: {df.columns}. Provide date_col explicitly.")
    # numeric value column: prefer revenue/price/value/numeric with most non-null
    numeric = [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8)]
    if value_col:
        if value_col not in numeric:
            raise ToolExecutionError(f"value_col {value_col!r} is not numeric; numeric cols: {numeric}")
        return date_candidates[0], value_col
    # pick best numeric: largest variance or named revenue/price/value
    preferred = [c for c in ["revenue", "value", "price", "sales", "demand"] if c in numeric]
    vc = preferred[0] if preferred else (numeric[0] if numeric else None)
    if not vc:
        raise ToolExecutionError(f"No numeric value column found; columns: {df.columns}")
    return date_candidates[0], vc


class ForecastTool(BaseTool[ForecastInput, ForecastOutput]):
    name = "forecast"
    description = "Baseline time-series forecast (linear_trend/moving_average/naive_trend) with MAE and future periods"
    input_model = ForecastInput
    output_model = ForecastOutput

    async def execute(self, inp: ForecastInput) -> ForecastOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        if df.height < 10:
            raise ToolExecutionError("Need >=10 rows for forecast")
        date_col, value_col = _detect_cols(df, inp.date_col, inp.value_col)

        # sort by date
        try:
            sub = df.select([date_col, value_col]).drop_nulls().sort(date_col)
        except Exception as e:
            raise ToolExecutionError(f"Failed to sort by date: {e}") from e
        if sub.height < 10:
            raise ToolExecutionError("Not enough non-null rows after drop")

        # numeric series
        try:
            y = sub[value_col].to_numpy().astype(float)
        except Exception as e:
            raise ToolExecutionError(f"value_col not numeric: {e}") from e

        n = len(y)
        t = np.arange(n).reshape(-1, 1)
        # holdout for metrics (last min(20%, 30) rows)
        holdout = min(max(5, n // 5), 30)
        t_train, t_test = t[:-holdout], t[-holdout:]
        y_train, y_test = y[:-holdout], y[-holdout:]

        if inp.method == "linear_trend":
            model = LinearRegression()
            model.fit(t_train, y_train)
            y_pred_test = model.predict(t_test)
            mae = float(mean_absolute_error(y_test, y_pred_test))
            # forecast future
            t_future = np.arange(n, n + inp.periods).reshape(-1, 1)
            fc = model.predict(t_future).tolist()
            slope = float(model.coef_[0])
            intercept = float(model.intercept_)
            diagnostics: dict[str, object] = {"slope": slope, "intercept": intercept, "holdout": holdout}
        elif inp.method == "moving_average":
            window = min(7, len(y_train))
            ma = float(np.mean(y_train[-window:]))
            y_pred_test = np.full_like(y_test, ma, dtype=float)
            mae = float(mean_absolute_error(y_test, y_pred_test))
            fc = [ma] * inp.periods
            diagnostics = {"window": window, "holdout": holdout}
        else:  # naive_trend: last value
            last = float(y_train[-1])
            y_pred_test = np.full_like(y_test, last, dtype=float)
            mae = float(mean_absolute_error(y_test, y_pred_test))
            fc = [last] * inp.periods
            diagnostics = {"last_value": last, "holdout": holdout}

        # clamp extreme? no — keep raw for evidence
        return ForecastOutput(
            method=inp.method,
            date_col=date_col,
            value_col=value_col,
            n_train=int(len(y_train)),
            periods=inp.periods,
            forecast=[float(v) for v in fc],
            metrics={"mae": mae, "mae_holdout": mae, "n_holdout": float(holdout)},
            diagnostics=diagnostics,
        )
