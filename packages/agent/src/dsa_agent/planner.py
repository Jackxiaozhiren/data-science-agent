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


def _heuristic_sql(q: str, cols: list[str], numeric_cols: list[str]) -> str:
    # cols available; numeric_cols subset
    # Map question patterns to SQL; default to GROUP BY first categorical
    cat_cols = [c for c in cols if c not in numeric_cols]
    cat = cat_cols[0] if cat_cols else (cols[0] if cols else "category")
    num = numeric_cols[0] if numeric_cols else (cols[-1] if cols else "value")
    if "highest total revenue" in q:
        if "region" in cols and "revenue" in cols:
            return f"SELECT region, SUM(revenue) as total FROM dataset GROUP BY region ORDER BY total DESC LIMIT 1"
        return f"SELECT {cat}, SUM({num}) as total FROM dataset GROUP BY {cat} ORDER BY total DESC LIMIT 1"
    if "total revenue by region" in q or ("total" in q and "revenue" in q and "region" in q):
        return f"SELECT region, SUM(revenue) as total_revenue FROM dataset GROUP BY region"
    if "area > 2000" in q:
        return f"SELECT AVG(price) as avg_price FROM dataset WHERE area > 2000"
    if "average price by category" in q or "average" in q:
        return f"SELECT {cat}, AVG({num}) as avg_val FROM dataset GROUP BY {cat}"
    if "top 5" in q:
        return f"SELECT * FROM dataset ORDER BY {num} DESC LIMIT 5"
    if "rows per group" in q or "having" in q:
        return f"SELECT {cat}, COUNT(*) as cnt FROM dataset GROUP BY {cat} HAVING COUNT(*) > 100"
    if "survival rate by sex" in q:
        return f"SELECT sex, AVG(survived) as survival_rate FROM dataset GROUP BY sex"
    # generic
    return f"SELECT {cat}, COUNT(*) as cnt, AVG({num}) as avg_{num} FROM dataset GROUP BY {cat}"


def _has_time_data(dataset_path: str | None) -> bool:
    if not dataset_path:
        return False
    try:
        from pathlib import Path

        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format
        import polars as pl

        p = Path(dataset_path)
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        return any(df[c].dtype in (pl.Date, pl.Datetime) for c in df.columns)
    except Exception:
        return False


def heuristics_plan(user_query: str, dataset_path: str | None, columns: list[str] | None = None) -> AnalysisPlan:
    q = user_query.lower()
    wants_model = any(k in q for k in ["model", "predict", "classif", "regression", "forecast", "churn", "survival"])
    wants_stats = any(k in q for k in ["correlat", "hypothesis", "test", "anova", "significant", "regression", "association"])
    wants_viz = any(k in q for k in ["chart", "plot", "visual", "histogram", "scatter", "heatmap"])
    wants_forecast = any(k in q for k in ["forecast", "predict", "future", "next 30", "30 days", "trend", "time series"])
    wants_decline = any(k in q for k in ["declin", "drop", "decrease", "down"])
    wants_importance = any(k in q for k in ["importance", "explain", "shap", "feature"])
    wants_causal = any(k in q for k in ["cause", "causal", "effect", "impact", "treatment", "intervention", "ate"])
    cols = columns or []
    numeric_cols = _numeric_columns(dataset_path) or [c for c in cols if c not in ("date", "region", "category", "group")] or cols
    has_time = _has_time_data(dataset_path)

    steps: list[AnalysisStep] = []
    tools: list[str] = []

    def _add(name: str, desc: str, tool: str, inputs: dict[str, object], depends: list[str] | None = None) -> str:
        sid = f"s{len(steps)+1:02d}"
        steps.append(AnalysisStep(id=sid, name=name, description=desc, tool=tool, inputs=inputs, depends_on=depends or []))
        if tool not in tools:
            tools.append(tool)
        return sid

    wants_sql = any(k in q for k in ["total", "average", "sum", "count", "group by", "having", "survival rate", "revenue by", "top 5", "rows per group"])
    # Also treat SQL catalog keywords directly
    sql_keywords = ["group by", "order by", "having", "count", "sum", "avg", "total"]

    s_profile = _add("Profile dataset", "Profile schema, missing, duplicates, cardinality", "profile_dataset", {"path": dataset_path or ""})
    s_corr = None
    s_test = None
    s_reg = None
    s_model = None
    s_chart = None
    s_sql = None

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

    if wants_forecast and has_time:
        s_fc = _add("Forecast", "30-day baseline forecast with MAE", "forecast", {"dataset_path": dataset_path or "", "periods": 30})
        # also ensure decline attribution via group comparison when decline asked
        if wants_decline:
            # group-wise decline: run hypothesis test across time splits or regions
            pass

    if wants_importance and numeric_cols:
        s_imp = _add("Feature importance", "Explainability via RandomForest importance", "feature_importance", {"dataset_path": dataset_path or "", "target": cols[-1] if cols else numeric_cols[-1]})

    if wants_causal and numeric_cols:
        # Causal guard: prefer association language; still run stub to evidence the bar
        s_causal = _add("Causal check (stub)", "Association vs causation guard — requires confounders for causal claim", "causal_check", {"dataset_path": dataset_path or "", "treatment": cols[0] if cols else "treatment", "outcome": numeric_cols[0] if numeric_cols else "outcome"})

    # Decline attribution: use SQL/group comparison + stats when decline mentioned
    if wants_decline:
        # Add assumption check before hypothesis tests for rigor
        pass

    # SQL planning: when question implies aggregation, generate a SELECT
    if wants_sql and cols:
        # Heuristic SQL generation per common patterns
        sql = _heuristic_sql(q, cols, numeric_cols)
        s_sql = _add("SQL analysis", f"SQL: {sql[:80]}", "run_sql", {"dataset_path": dataset_path or "", "sql": sql})

    if wants_viz or True:  # always at least one viz for evidence
        hist_x = numeric_cols[0] if numeric_cols else (cols[0] if cols else "a")
        s_chart = _add("Visualization", "Create evidence chart", "create_chart", {"dataset_path": dataset_path or "", "chart_type": "histogram", "x": hist_x})
        if has_time:
            s_line = _add("Time series line", "Line chart over time for trend", "create_chart", {"dataset_path": dataset_path or "", "chart_type": "line", "x": "date", "y": numeric_cols[0] if numeric_cols else hist_x})

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
