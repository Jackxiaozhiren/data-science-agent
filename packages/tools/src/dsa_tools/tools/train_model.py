from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class TrainModelInput(BaseModel):
    dataset_path: str
    target: str
    task: Literal["classification", "regression"] = "classification"
    model: Literal["logistic", "random_forest"] = "logistic"
    cv_folds: int = Field(default=3, ge=2, le=10)
    test_size: float | None = None


class TrainModelOutput(BaseModel):
    task: str
    model: str
    cv_scores: list[float]
    cv_mean: float
    cv_std: float
    n_rows: int
    features: list[str]
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def _build_classifier(name: str):  # type: ignore[no-untyped-def]
    if name == "logistic":
        return LogisticRegression(max_iter=1000)
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, random_state=42)
    raise ToolExecutionError(f"Unknown classifier: {name}")


def _build_regressor(name: str):  # type: ignore[no-untyped-def]
    if name == "random_forest":
        return RandomForestRegressor(n_estimators=100, random_state=42)
    raise ToolExecutionError(f"Unknown regressor: {name}")


class TrainModelTool(BaseTool[TrainModelInput, TrainModelOutput]):
    name = "train_model"
    description = "Train a baseline model with cross-validation (classification/regression)"
    input_model = TrainModelInput
    output_model = TrainModelOutput

    async def execute(self, inp: TrainModelInput) -> TrainModelOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        if inp.target not in df.columns:
            raise ToolExecutionError(f"Target {inp.target!r} not found")
        feat_cols = [c for c in df.columns if c != inp.target]
        if not feat_cols:
            raise ToolExecutionError("No feature columns")
        sub = df.select(feat_cols + [inp.target]).drop_nulls()
        if sub.height < 10:
            raise ToolExecutionError("Need >=10 rows")
        try:
            X = sub.select(feat_cols).to_numpy().astype(float)
            y = sub[inp.target].to_numpy()
            if inp.task == "regression":
                y = y.astype(float)
        except Exception as e:
            raise ToolExecutionError(f"Non-numeric features: {e}") from e

        if inp.task == "classification":
            model = _build_classifier(inp.model)
            cv = StratifiedKFold(n_splits=inp.cv_folds, shuffle=True, random_state=42)
            try:
                scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
            except Exception as e:
                raise ToolExecutionError(f"CV failed: {e}") from e
        else:
            # regression only supports random_forest for now
            rf_model = inp.model if inp.model == "random_forest" else "random_forest"
            model = _build_regressor(rf_model)
            try:
                scores = cross_val_score(model, X, y, cv=inp.cv_folds, scoring="r2")
            except Exception as e:
                raise ToolExecutionError(f"CV failed: {e}") from e

        return TrainModelOutput(
            task=inp.task,
            model=inp.model if inp.task == "classification" else "random_forest",
            cv_scores=[float(s) for s in scores],
            cv_mean=float(np.mean(scores)),
            cv_std=float(np.std(scores)),
            n_rows=sub.height,
            features=feat_cols,
            diagnostics={"target": inp.target},
        )
