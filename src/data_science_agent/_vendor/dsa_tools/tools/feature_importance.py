from __future__ import annotations

import base64
import io
import uuid
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError


class FeatureImportanceInput(BaseModel):
    dataset_path: str
    target: str
    task: str = Field(default="classification", description="classification|regression")
    top_k: int = Field(default=10, ge=1, le=50)


class FeatureImportanceOutput(BaseModel):
    target: str
    importances: list[dict[str, Any]] = Field(default_factory=list)
    artifact_path: str | None = None
    base64_png: str | None = None


class FeatureImportanceTool(BaseTool[FeatureImportanceInput, FeatureImportanceOutput]):
    name = "feature_importance"
    description = (
        "RandomForest feature importance with chart artifact (explainability, no SHAP dep)"
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
        try:
            X = sub.select(feat_cols).to_numpy().astype(float)
            y = sub[inp.target].to_numpy()
        except Exception as e:
            raise ToolExecutionError(f"Non-numeric: {e}") from e

        if inp.task == "regression":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            y = y.astype(float)
        else:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        importances = model.feature_importances_
        pairs = sorted(zip(feat_cols, importances), key=lambda x: x[1], reverse=True)[: inp.top_k]
        out = [{"feature": k, "importance": float(v)} for k, v in pairs]

        # Chart
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
            target=inp.target, importances=out, artifact_path=str(dest), base64_png=b64
        )
