from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path
from typing import Any, Literal

import matplotlib
import numpy as np
import polars as pl

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError

_NUMERIC_DTYPES = {
    pl.Float64,
    pl.Float32,
    pl.Int64,
    pl.Int32,
    pl.Int16,
    pl.Int8,
    pl.UInt64,
    pl.UInt32,
    pl.UInt16,
    pl.UInt8,
}


def _is_numeric(dtype: pl.DataType) -> bool:
    return dtype in _NUMERIC_DTYPES


class FeatureImportanceInput(BaseModel):
    dataset_path: str
    target: str
    task: Literal["auto", "classification", "regression"] = Field(
        default="auto", description="auto|classification|regression"
    )
    top_k: int = Field(default=10, ge=1, le=50)


class FeatureImportanceOutput(BaseModel):
    target: str
    importances: list[dict[str, Any]] = Field(default_factory=list)
    excluded_features: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    base64_png: str | None = None


class FeatureImportanceTool(BaseTool[FeatureImportanceInput, FeatureImportanceOutput]):
    name = "feature_importance"
    description = (
        "RandomForest feature importance with categorical encoding and chart artifact "
        "(explainability, no SHAP dep)"
    )
    input_model = FeatureImportanceInput
    output_model = FeatureImportanceOutput

    async def execute(self, inp: FeatureImportanceInput) -> FeatureImportanceOutput:
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

        # Exact target copies are deterministic leakage, not explanatory features.
        # Exclude them before model fitting and expose the exclusion in the output.
        excluded_features: list[str] = []
        for col in list(feat_cols):
            try:
                if sub[col].equals(sub[inp.target]):
                    excluded_features.append(col)
            except Exception:  # noqa: S112 - incomparable dtypes mean "not a copy"; keep column
                continue
        feat_cols = [c for c in feat_cols if c not in excluded_features]
        if not feat_cols:
            raise ToolExecutionError("No usable feature columns after target-leakage checks")
        sub = sub.select(feat_cols + [inp.target])

        numeric_cols = [c for c in feat_cols if _is_numeric(sub[c].dtype)]
        categorical_cols = [c for c in feat_cols if c not in numeric_cols]
        matrices: list[np.ndarray] = []
        source_features: list[str] = []

        try:
            if numeric_cols:
                matrices.append(sub.select(numeric_cols).to_numpy().astype(float))
                source_features.extend(numeric_cols)

            if categorical_cols:
                categorical_frame = sub.select(
                    [pl.col(c).cast(pl.String).alias(c) for c in categorical_cols]
                )
                encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
                encoded = encoder.fit_transform(categorical_frame.to_numpy())
                matrices.append(encoded.astype(float))
                for col, categories in zip(categorical_cols, encoder.categories_):
                    source_features.extend([col] * len(categories))

            if not matrices:
                raise ToolExecutionError("No usable feature columns")
            X = matrices[0] if len(matrices) == 1 else np.hstack(matrices)
            y = sub[inp.target].to_numpy()
        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(f"Feature encoding failed: {e}") from e

        task = inp.task
        if task == "auto":
            target_is_numeric = _is_numeric(sub[inp.target].dtype)
            task = (
                "regression"
                if target_is_numeric and sub[inp.target].n_unique() > 10
                else "classification"
            )

        if task == "regression":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            try:
                y = y.astype(float)
            except Exception as e:
                raise ToolExecutionError(f"Regression target is non-numeric: {e}") from e
        else:
            model = RandomForestClassifier(n_estimators=100, random_state=42)

        try:
            model.fit(X, y)
        except Exception as e:
            raise ToolExecutionError(f"RandomForest fit failed: {e}") from e

        # Aggregate one-hot encoded categories back to their original feature so
        # the report remains interpretable at the source-column level.
        importance_by_feature = {c: 0.0 for c in feat_cols}
        for source, importance in zip(source_features, model.feature_importances_):
            importance_by_feature[source] += float(importance)
        pairs = sorted(importance_by_feature.items(), key=lambda x: x[1], reverse=True)[: inp.top_k]
        out = [{"feature": k, "importance": float(v)} for k, v in pairs]

        fig, ax = plt.subplots(figsize=(7, max(3, len(pairs) * 0.45)))
        ax.barh([k for k, _ in reversed(pairs)], [v for _, v in reversed(pairs)])
        ax.set_xlabel("importance")
        ax.set_title(f"Feature importance — {inp.target}")
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        png = buf.getvalue()
        b64 = base64.b64encode(png).decode()
        out_dir = Path(__file__).resolve().parents[4] / "artifacts" / "charts"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{uuid.uuid4().hex[:8]}_featimp.png"
        dest.write_bytes(png)

        return FeatureImportanceOutput(
            target=inp.target,
            importances=out,
            excluded_features=excluded_features,
            artifact_path=str(dest),
            base64_png=b64,
        )
