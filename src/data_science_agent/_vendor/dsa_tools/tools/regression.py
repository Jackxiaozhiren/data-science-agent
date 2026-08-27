from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field
from sklearn.linear_model import ElasticNet, Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class RegressionInput(BaseModel):
    dataset_path: str
    target: str
    features: list[str] | None = None
    model: Literal["linear", "ridge", "lasso", "elastic", "logistic"] = "linear"
    test_size: float = Field(default=0.2, ge=0.05, le=0.5)
    alpha: float = Field(default=1.0, gt=0)


class RegressionOutput(BaseModel):
    model: str
    n_train: int
    n_test: int
    coefficients: dict[str, float]
    intercept: float
    metrics: dict[str, float]
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def _build_model(name: str, alpha: float):  # type: ignore[no-untyped-def]
    if name == "linear":
        return LinearRegression()
    if name == "ridge":
        return Ridge(alpha=alpha)
    if name == "lasso":
        return Lasso(alpha=alpha)
    if name == "elastic":
        return ElasticNet(alpha=alpha, l1_ratio=0.5)
    if name == "logistic":
        return LogisticRegression(max_iter=1000)
    raise ToolExecutionError(f"Unknown model: {name}")


class RegressionTool(BaseTool[RegressionInput, RegressionOutput]):
    name = "regression_analysis"
    description = (
        "Run regression (linear/ridge/lasso/elastic/logistic) with train/test split and metrics"
    )
    input_model = RegressionInput
    output_model = RegressionOutput

    async def execute(self, inp: RegressionInput) -> RegressionOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        if inp.target not in df.columns:
            raise ToolExecutionError(f"Target {inp.target!r} not in columns {df.columns}")
        feat_cols = inp.features or [c for c in df.columns if c != inp.target]
        if not feat_cols:
            raise ToolExecutionError("No feature columns")
        for c in feat_cols:
            if c not in df.columns:
                raise ToolExecutionError(f"Feature {c!r} not found")

        sub = df.select(feat_cols + [inp.target]).drop_nulls()
        if sub.height < 10:
            raise ToolExecutionError("Need >=10 rows after drop_nulls")

        # Coerce features to numeric
        try:
            X = sub.select(feat_cols).to_numpy().astype(float)
            y = sub[inp.target].to_numpy()
            # for regression, y must be numeric; for logistic, y will be label-encoded via sklearn
            if inp.model != "logistic":
                y = y.astype(float)
        except Exception as e:
            raise ToolExecutionError(f"Non-numeric data: {e}") from e

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=inp.test_size, random_state=42
        )

        model = _build_model(inp.model, inp.alpha)
        try:
            model.fit(X_train, y_train)
        except Exception as e:
            raise ToolExecutionError(f"Model fitting failed: {e}") from e

        y_pred = model.predict(X_test)

        if inp.model == "logistic":
            # classification metrics
            from sklearn.metrics import accuracy_score, f1_score

            metrics: dict[str, float] = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            }
        else:
            metrics = {
                "mae": float(mean_absolute_error(y_test, y_pred)),
                "mse": float(mean_squared_error(y_test, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "r2": float(r2_score(y_test, y_pred)),
            }

        coefs = {}
        intercept = 0.0
        try:
            coef_arr = getattr(model, "coef_", None)
            if coef_arr is not None:
                arr = coef_arr[0] if hasattr(coef_arr, "ndim") and coef_arr.ndim > 1 else coef_arr
                for name, val in zip(feat_cols, arr):
                    coefs[name] = float(val)
            raw_intercept = getattr(model, "intercept_", 0.0)
            raw_any: Any = raw_intercept
            intercept = float(raw_any) if np.ndim(raw_any) == 0 else float(raw_any[0])
        except Exception:
            coefs = {}
            intercept = 0.0

        return RegressionOutput(
            model=inp.model,
            n_train=len(X_train),
            n_test=len(X_test),
            coefficients=coefs,
            intercept=intercept,
            metrics=metrics,
            diagnostics={"feature_cols": feat_cols, "target": inp.target},
        )
