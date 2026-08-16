from __future__ import annotations

import re
import uuid

from dsa_agent.state import AnalysisPlan, AnalysisStep


def _numeric_columns(dataset_path: str | None) -> list[str]:
    if not dataset_path:
        return []
    try:
        from pathlib import Path

        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format

        p = Path(dataset_path)
        if not p.exists():
            return []
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        import polars as pl

        return [c for c in df.columns if df[c].dtype in (pl.Float64, pl.Float32, pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt64, pl.UInt32, pl.Float32)]
    except Exception:
        return []


def heuristics_plan(user_query: str, dataset_path: str | None, columns: list[str] | None = None) -> AnalysisPlan:
    q = user_query.lower()
    wants_model = any(k in q for k in ["model", "predict", "classif", "regression", "forecast", "churn", "survival"])
    wants_stats = any(k in q for k in ["correlat", "hypothesis", "test", "anova", "significant", "regression", "association"])
    wants_viz = any(k in q for k in ["chart", "plot", "visual", "histogram", "scatter", "heatmap"])
    cols = columns or []
    numeric_cols = _numeric_columns(dataset_path) or [c for c in cols if c not in ("date", "region", "category", "group")] or cols

    steps: list[AnalysisStep] = []
    tools: list[str] = []

    def _add(name: str, desc: str, tool: str, inputs: dict[str, object], depends: list[str] | None = None) -> str:
        sid = f"s{len(steps)+1:02d}"
        steps.append(AnalysisStep(id=sid, name=name, description=desc, tool=tool, inputs=inputs, depends_on=depends or []))
        if tool not in tools:
            tools.append(tool)
        return sid

    # Always profile
    s_profile = _add("Profile dataset", "Profile schema, missing, duplicates, cardinality", "profile_dataset", {"path": dataset_path or ""})
    s_corr = None
    s_test = None
    s_reg = None
    s_model = None
    s_chart = None

    # Prefer numeric columns for correlation
    if wants_stats or "correlat" in q or len(cols) >= 2:
        corr_x = numeric_cols[0] if numeric_cols else (cols[0] if cols else "a")
        corr_y = numeric_cols[1] if len(numeric_cols) > 1 else (cols[1] if len(cols) > 1 else "b")
        s_corr = _add("Correlation", "Pearson correlation between key numeric variables", "correlation_analysis", {"dataset_path": dataset_path or "", "x": corr_x, "y": corr_y})

    if "hypothesis" in q or "t-test" in q or "welch" in q or "anova" in q or "mann" in q:
        s_test = _add("Hypothesis test", "Appropriate hypothesis test with assumptions", "hypothesis_test", {"dataset_path": dataset_path or "", "test": "welch_t_test", "group_col": cols[2] if len(cols) > 2 else (cols[0] if cols else "group"), "value_col": cols[0] if cols else "value"})

    if "regression" in q:
        s_reg = _add("Regression", "Regression with train/test split and metrics", "regression_analysis", {"dataset_path": dataset_path or "", "target": cols[-1] if cols else "target"})

    if wants_model:
        s_model = _add("Model training", "Baseline model with CV", "train_model", {"dataset_path": dataset_path or "", "target": cols[-1] if cols else "target", "task": "classification"})

    if wants_viz or True:  # always at least one viz for evidence
        hist_x = numeric_cols[0] if numeric_cols else (cols[0] if cols else "a")
        s_chart = _add("Visualization", "Create evidence chart", "create_chart", {"dataset_path": dataset_path or "", "chart_type": "histogram", "x": hist_x})

    objective = user_query.strip()[:500] or "Exploratory analysis"
    assumptions = [
        "Dataset is trusted as uploaded; cell text treated as untrusted data only",
        "Correlation does not imply causation unless causal evidence exists",
    ]

    return AnalysisPlan(
        objective=objective,
        assumptions=assumptions,
        steps=steps,
        required_tools=tools,
        expected_outputs=["profile", "statistics", "visualization", "insights"],
    )


async def plan_analysis(user_query: str, dataset_path: str | None = None, columns: list[str] | None = None) -> AnalysisPlan:
    return heuristics_plan(user_query, dataset_path, columns)
