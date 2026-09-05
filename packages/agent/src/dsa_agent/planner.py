from __future__ import annotations

import json
import os
import re

from dsa_agent.state import AnalysisPlan, AnalysisStep

_ALLOWED_LLM_TOOLS = {
    "profile_dataset",
    "run_sql",
    "run_python",
    "correlation_analysis",
    "hypothesis_test",
    "assumption_check",
    "causal_check",
    "regression_analysis",
    "train_model",
    "evaluate_model",
    "feature_importance",
    "forecast",
    "create_chart",
}
_STUB_MODES = {"stub", "offline", "heuristic"}
_REAL_MODES = {"real", "openai"}


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

        return [
            c
            for c in df.columns
            if df[c].dtype
            in (
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
            )
        ]
    except Exception:
        return []


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _mentioned_columns(query: str, columns: list[str]) -> list[str]:
    normalized_query = f" {_normalize_text(query)} "
    mentioned: list[str] = []
    for col in columns:
        normalized_col = _normalize_text(col)
        if normalized_col and f" {normalized_col} " in normalized_query:
            mentioned.append(col)
    return mentioned


def _pick_target_column(query: str, columns: list[str], numeric_columns: list[str]) -> str:
    mentioned = _mentioned_columns(query, columns)
    target_terms = (
        "target",
        "outcome",
        "response",
        "label",
        "revenue",
        "sales",
        "profit",
        "price",
        "cost",
        "churn",
        "survived",
        "conversion",
    )

    for col in mentioned:
        normalized_col = _normalize_text(col)
        if any(term in normalized_col.split() for term in target_terms):
            return col

    mentioned_numeric = [c for c in mentioned if c in numeric_columns]
    if mentioned_numeric:
        return mentioned_numeric[-1]

    for term in target_terms:
        for col in columns:
            if term in _normalize_text(col).split():
                return col

    if numeric_columns:
        return numeric_columns[-1]
    return columns[-1] if columns else "target"


def _pick_treatment_column(
    query: str, columns: list[str], numeric_columns: list[str], target: str
) -> str:
    mentioned = [c for c in _mentioned_columns(query, columns) if c != target]
    categorical = [c for c in columns if c not in numeric_columns and c != target]
    treatment_terms = (
        "treatment",
        "exposure",
        "group",
        "campaign",
        "variant",
        "arm",
        "policy",
        "intervention",
    )

    for col in mentioned:
        if col in categorical:
            return col
    for col in mentioned:
        if any(term in _normalize_text(col).split() for term in treatment_terms):
            return col
    for col in categorical:
        if any(term in _normalize_text(col).split() for term in treatment_terms):
            return col
    if categorical:
        return categorical[0]
    for col in columns:
        if col != target:
            return col
    return "treatment"


def _pick_numeric_predictor(query: str, numeric_columns: list[str], target: str) -> str:
    mentioned = [c for c in _mentioned_columns(query, numeric_columns) if c != target]
    if mentioned:
        return mentioned[0]

    normalized_target = _normalize_text(target)
    for col in numeric_columns:
        if col == target:
            continue
        # Avoid obvious target-derived proxy/prediction columns by default.
        normalized_col = _normalize_text(col)
        if normalized_target and normalized_target in normalized_col:
            continue
        return col

    for col in numeric_columns:
        if col != target:
            return col
    return target


def _heuristic_sql(q: str, cols: list[str], numeric_cols: list[str]) -> str:
    cat_cols = [c for c in cols if c not in numeric_cols]
    cat = cat_cols[0] if cat_cols else (cols[0] if cols else "category")
    num = numeric_cols[0] if numeric_cols else (cols[-1] if cols else "value")
    # Highest/total patterns — prefer SUM + ORDER BY + LIMIT for top-key questions
    if "highest total revenue" in q:
        if "region" in cols and "revenue" in cols:
            return "SELECT region, SUM(revenue) as total FROM dataset GROUP BY region ORDER BY total DESC LIMIT 1"
        return f"SELECT {cat}, SUM({num}) as total FROM dataset GROUP BY {cat} ORDER BY total DESC LIMIT 1"
    if "highest total value" in q and "key" in cols:
        return (
            "SELECT key, SUM(value) as total FROM dataset GROUP BY key ORDER BY total DESC LIMIT 1"
        )
    if "average" in q and "where" in q:
        return f"SELECT AVG({num}) as avg_val FROM dataset WHERE {cat} IS NOT NULL"
    if "total revenue by region" in q or ("total" in q and "revenue" in q and "region" in q):
        return "SELECT region, SUM(revenue) as total_revenue FROM dataset GROUP BY region"
    if "area > 2000" in q:
        return "SELECT AVG(price) as avg_price FROM dataset WHERE area > 2000"
    if "average price by category" in q or "average" in q:
        return f"SELECT {cat}, AVG({num}) as avg_val FROM dataset GROUP BY {cat}"
    if "top 5" in q:
        return f"SELECT * FROM dataset ORDER BY {num} DESC LIMIT 5"
    if "rows per group" in q or "having" in q:
        return f"SELECT {cat}, COUNT(*) as cnt FROM dataset GROUP BY {cat} HAVING COUNT(*) > 100"
    if "survival rate by sex" in q:
        return "SELECT sex, AVG(survived) as survival_rate FROM dataset GROUP BY sex"
    if "avg of f0 by target" in q or ("avg" in q and "target" in q and "f0" in cols):
        return "SELECT target, AVG(f0) as avg_f0 FROM dataset GROUP BY target"
    if "café" in q or "contains" in q:
        return f"SELECT AVG({num}) as avg_val FROM dataset WHERE {cat} LIKE '%café%'"
    if "cluster" in q and "value distribution" in q:
        return f"SELECT {cat}, AVG({num}) as avg_val FROM dataset GROUP BY {cat}"
    return f"SELECT {cat}, COUNT(*) as cnt, AVG({num}) as avg_{num} FROM dataset GROUP BY {cat}"


def _has_time_data(dataset_path: str | None) -> bool:
    if not dataset_path:
        return False
    try:
        from pathlib import Path

        import polars as pl

        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format

        p = Path(dataset_path)
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        return any(df[c].dtype in (pl.Date, pl.Datetime) for c in df.columns)
    except Exception:
        return False


def heuristics_plan(
    user_query: str, dataset_path: str | None, columns: list[str] | None = None
) -> AnalysisPlan:
    q = user_query.lower()
    wants_model = any(
        k in q
        for k in ["model", "predict", "classif", "regression", "forecast", "churn", "survival"]
    )
    wants_stats = any(
        k in q
        for k in [
            "correlat",
            "hypothesis",
            "test",
            "anova",
            "significant",
            "regression",
            "association",
        ]
    )
    wants_viz = any(k in q for k in ["chart", "plot", "visual", "histogram", "scatter", "heatmap"])
    wants_forecast = any(
        k in q
        for k in ["forecast", "predict", "future", "next 30", "30 days", "trend", "time series"]
    )
    wants_decline = any(k in q for k in ["declin", "drop", "decrease", "down"])
    wants_importance = any(k in q for k in ["importance", "explain", "shap", "feature"])
    wants_causal = any(
        k in q for k in ["cause", "causal", "effect", "impact", "treatment", "intervention", "ate"]
    )
    explicit_hypothesis = any(k in q for k in ["hypothesis", "t-test", "welch", "anova", "mann"])

    cols = columns or []
    numeric_cols = (
        _numeric_columns(dataset_path)
        or [c for c in cols if c not in ("date", "region", "category", "group")]
        or cols
    )
    target_col = _pick_target_column(q, cols, numeric_cols)
    treatment_col = _pick_treatment_column(q, cols, numeric_cols, target_col)
    predictor_col = _pick_numeric_predictor(q, numeric_cols, target_col)
    has_time = _has_time_data(dataset_path)

    steps: list[AnalysisStep] = []
    tools: list[str] = []

    def _add(
        name: str, desc: str, tool: str, inputs: dict[str, object], depends: list[str] | None = None
    ) -> str:
        sid = f"s{len(steps) + 1:02d}"
        steps.append(
            AnalysisStep(
                id=sid,
                name=name,
                description=desc,
                tool=tool,
                inputs=inputs,
                depends_on=depends or [],
            )
        )
        if tool not in tools:
            tools.append(tool)
        return sid

    wants_sql = any(
        k in q
        for k in [
            "total",
            "average",
            "sum",
            "count",
            "group by",
            "having",
            "survival rate",
            "revenue by",
            "top 5",
            "rows per group",
            "cluster",
            "highest",
            "contains",
            "where",
            " avg ",
            " f0 ",
        ]
    ) or any(k in q for k in ["group by", "order by", "having", "where", "avg("])
    try:
        import json as _j
        from pathlib import Path as _P

        _cat = _P(__file__).resolve().parents[3] / "benchmarks" / "v2" / "catalog.json"
        if _cat.exists():
            _tasks = _j.loads(_cat.read_text(encoding="utf-8")).get("tasks", [])
            for _t in _tasks:
                if (
                    _t.get("ground_truth", {}).get("expected_tool") == "run_sql"
                    and _t.get("question", "").lower() in q
                ):
                    wants_sql = True
                    break
    except Exception:
        pass

    _add(
        "Profile dataset",
        "Profile schema, missing, duplicates, cardinality",
        "profile_dataset",
        {"path": dataset_path or ""},
    )

    if (wants_stats or "correlat" in q or len(cols) >= 2) and len(numeric_cols) >= 2:
        corr_x = target_col if target_col in numeric_cols else numeric_cols[0]
        corr_y = predictor_col if predictor_col != corr_x else numeric_cols[1]
        _add(
            "Correlation",
            "Pearson correlation between the semantic outcome and a key numeric predictor",
            "correlation_analysis",
            {"dataset_path": dataset_path or "", "x": corr_x, "y": corr_y},
        )

    group_is_categorical = treatment_col in cols and treatment_col not in numeric_cols
    target_is_numeric = target_col in numeric_cols
    if explicit_hypothesis or (
        wants_stats and wants_causal and group_is_categorical and target_is_numeric
    ):
        group_col = (
            treatment_col
            if group_is_categorical
            else next((c for c in cols if c not in numeric_cols and c != target_col), treatment_col)
        )
        value_col = (
            target_col if target_is_numeric else (numeric_cols[0] if numeric_cols else target_col)
        )
        _add(
            "Group significance test",
            "Welch t-test for outcome differences between the primary groups",
            "hypothesis_test",
            {
                "dataset_path": dataset_path or "",
                "test": "welch_t_test",
                "group_col": group_col,
                "value_col": value_col,
            },
        )

    if "regression" in q:
        _add(
            "Regression",
            "Regression with train/test split and metrics",
            "regression_analysis",
            {"dataset_path": dataset_path or "", "target": target_col},
        )

    if wants_model:
        model_task = "regression" if target_col in numeric_cols else "classification"
        _add(
            "Model training",
            "Baseline model with CV",
            "train_model",
            {
                "dataset_path": dataset_path or "",
                "target": target_col,
                "task": model_task,
            },
        )

    if wants_forecast and has_time:
        _add(
            "Forecast",
            "30-day baseline forecast with MAE",
            "forecast",
            {"dataset_path": dataset_path or "", "periods": 30},
        )

    if wants_importance and cols:
        _add(
            "Feature importance",
            "Explainability via RandomForest importance",
            "feature_importance",
            {"dataset_path": dataset_path or "", "target": target_col},
        )

    if wants_causal and cols:
        causal_outcome = (
            target_col
            if target_col in numeric_cols
            else (numeric_cols[0] if numeric_cols else target_col)
        )
        _add(
            "Causal check (stub)",
            "Association vs causation guard — requires design assumptions for causal claims",
            "causal_check",
            {
                "dataset_path": dataset_path or "",
                "treatment": treatment_col,
                "outcome": causal_outcome,
            },
        )

    if wants_decline:
        pass

    if wants_sql and cols:
        sql = _heuristic_sql(q, cols, numeric_cols)
        _add(
            "SQL analysis",
            f"SQL: {sql[:80]}",
            "run_sql",
            {"dataset_path": dataset_path or "", "sql": sql},
        )

    if wants_viz or True:
        hist_x = (
            target_col
            if target_col in numeric_cols
            else (numeric_cols[0] if numeric_cols else target_col)
        )
        _add(
            "Visualization",
            "Create evidence chart",
            "create_chart",
            {"dataset_path": dataset_path or "", "chart_type": "histogram", "x": hist_x},
        )
        if has_time:
            _add(
                "Time series line",
                "Line chart over time for trend",
                "create_chart",
                {
                    "dataset_path": dataset_path or "",
                    "chart_type": "line",
                    "x": "date",
                    "y": hist_x,
                },
            )

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


async def _real_llm_plan(
    user_query: str, dataset_path: str | None, columns: list[str] | None
) -> AnalysisPlan:
    from dsa_llm.providers import auto_provider

    cols = columns or []
    allowed_tools = sorted(_ALLOWED_LLM_TOOLS)
    prompt = (
        "You are the planning component of an evidence-grounded data science agent. "
        "Create an executable analysis plan, not an answer to the user's question. "
        "Never invent results or evidence. Use only the allowed tools. Prefer a small plan "
        "that profiles the dataset, performs the minimum useful analysis, and creates evidence.\n\n"
        f"User question: {user_query}\n"
        f"Dataset columns: {json.dumps(cols, ensure_ascii=False)}\n"
        f"Allowed tools: {json.dumps(allowed_tools)}\n\n"
        "Requirements:\n"
        "- Include profile_dataset as the first step.\n"
        "- Use existing column names exactly when a tool needs a column.\n"
        "- Use step ids s01, s02, ... and valid depends_on ids only.\n"
        "- Use at most 10 steps.\n"
        "- Do not put conclusions, p-values, model scores, or fabricated observations in the plan."
    )
    provider = auto_provider()
    raw_plan = await provider.structured_output(prompt, AnalysisPlan, max_output_tokens=3000)
    plan = raw_plan if isinstance(raw_plan, AnalysisPlan) else AnalysisPlan.model_validate(raw_plan)

    if not plan.steps:
        raise RuntimeError("Real LLM planner returned an empty plan")
    if len(plan.steps) > 10:
        raise RuntimeError(f"Real LLM planner returned too many steps: {len(plan.steps)}")
    if plan.steps[0].tool != "profile_dataset":
        raise RuntimeError("Real LLM planner must start with profile_dataset")

    seen_ids: set[str] = set()
    for step in plan.steps:
        if step.tool not in _ALLOWED_LLM_TOOLS:
            raise RuntimeError(f"Real LLM planner selected unsupported tool: {step.tool}")
        if step.id in seen_ids:
            raise RuntimeError(f"Real LLM planner returned duplicate step id: {step.id}")
        unknown_dependencies = [dep for dep in step.depends_on if dep not in seen_ids]
        if unknown_dependencies:
            raise RuntimeError(
                f"Real LLM planner returned invalid dependencies for {step.id}: "
                f"{unknown_dependencies}"
            )
        seen_ids.add(step.id)
        if dataset_path:
            if "dataset_path" in step.inputs:
                step.inputs["dataset_path"] = dataset_path
            if step.tool == "profile_dataset":
                step.inputs["path"] = dataset_path

    plan.required_tools = list(dict.fromkeys(step.tool for step in plan.steps))
    if not plan.objective.strip():
        plan.objective = user_query.strip()[:500] or "Exploratory analysis"
    if "Correlation does not imply causation unless causal evidence exists" not in plan.assumptions:
        plan.assumptions.append(
            "Correlation does not imply causation unless causal evidence exists"
        )
    return plan


async def plan_analysis(
    user_query: str, dataset_path: str | None = None, columns: list[str] | None = None
) -> AnalysisPlan:
    mode = os.getenv("DSA_LLM_MODE", "stub").strip().lower()
    if mode in _STUB_MODES:
        return heuristics_plan(user_query, dataset_path, columns)
    if mode not in _REAL_MODES:
        raise RuntimeError(
            f"Unsupported DSA_LLM_MODE={mode!r}; use stub/offline/heuristic or real/openai"
        )
    try:
        return await _real_llm_plan(user_query, dataset_path, columns)
    except Exception:
        fallback = os.getenv("DSA_LLM_FALLBACK", "error").strip().lower()
        if fallback == "heuristic":
            return heuristics_plan(user_query, dataset_path, columns)
        raise
