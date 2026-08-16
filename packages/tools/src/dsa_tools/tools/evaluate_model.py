from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class EvaluateModelInput(BaseModel):
    dataset_path: str
    target: str
    task: Literal["classification", "regression"] = "classification"
    model: Literal["logistic", "random_forest"] = "logistic"
    test_size: float = Field(default=0.2, ge=0.05, le=0.5)


class EvaluateModelOutput(BaseModel):
    task: str
    model: str
    metrics: dict[str, float]
    confusion_matrix: list[list[int]] | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class EvaluateModelTool(BaseTool[EvaluateModelInput, EvaluateModelOutput]):
    name = "evaluate_model"
    description = "Evaluate a model on holdout split (classification: accuracy/precision/recall/F1/ROC-AUC; regression: MAE/MSE/RMSE/R2)"
    input_model = EvaluateModelInput
    output_model = EvaluateModelOutput

    async def execute(self, inp: EvaluateModelInput) -> EvaluateModelOutput:
        p = Path(inp.dataset_path)
        if not p.exists():
            raise ToolExecutionError(f"dataset_path not found: {inp.dataset_path}")
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        if inp.target not in df.columns:
            raise ToolExecutionError(f"Target {inp.target!r} not found")
        feat_cols = [c for c in df.columns if c != inp.target]
        sub = df.select(feat_cols + [inp.target]).drop_nulls()
        if sub.height < 10:
            raise ToolExecutionError("Need >=10 rows")
        try:
            X = sub.select(feat_cols).to_numpy().astype(float)
            y = sub[inp.target].to_numpy()
            if inp.task == "regression":
                y = y.astype(float)
        except Exception as e:
            raise ToolExecutionError(f"Non-numeric: {e}") from e

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=inp.test_size,
            random_state=42,
            stratify=y if inp.task == "classification" and len(np.unique(y)) < 20 else None,
        )

        if inp.task == "classification":
            clf = (
                LogisticRegression(max_iter=1000)
                if inp.model == "logistic"
                else RandomForestClassifier(n_estimators=100, random_state=42)
            )
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)
            metrics: dict[str, float] = {
                "accuracy": float(accuracy_score(y_test, y_pred)),
                "precision": float(
                    precision_score(y_test, y_pred, average="weighted", zero_division=0)
                ),
                "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
                "f1": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
            }
            try:
                if len(np.unique(y)) == 2 and hasattr(clf, "predict_proba"):
                    proba = clf.predict_proba(X_test)[:, 1]
                    metrics["roc_auc"] = float(roc_auc_score(y_test, proba))
            except Exception:
                pass
            cm = confusion_matrix(y_test, y_pred).tolist()
            return EvaluateModelOutput(
                task=inp.task,
                model=inp.model,
                metrics=metrics,
                confusion_matrix=cm,
                diagnostics={"features": feat_cols},
            )
        else:
            # regression
            reg = RandomForestRegressor(n_estimators=100, random_state=42)
            reg.fit(X_train, y_train)
            y_pred = reg.predict(X_test)
            metrics = {
                "mae": float(mean_absolute_error(y_test, y_pred)),
                "mse": float(mean_squared_error(y_test, y_pred)),
                "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                "r2": float(r2_score(y_test, y_pred)),
            }
            return EvaluateModelOutput(
                task=inp.task,
                model="random_forest",
                metrics=metrics,
                confusion_matrix=None,
                diagnostics={"features": feat_cols},
            )
