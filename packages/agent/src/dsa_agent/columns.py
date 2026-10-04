"""Column inspection for the planner: read a dataset, name what is in it.

Extracted from ``dsa_agent.planner`` by audit §97 (Phase 4 target 2, seam #1). Planner
imports these by name, so ``monkeypatch.setattr(planner, "_numeric_columns", ...)`` keeps
working -- the seam moved the code, not the binding. Nothing here decides a plan; each
function answers one question about a file, which is what makes them testable apart from
the heuristics that consume them.
"""

from __future__ import annotations

import re


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


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def mentioned_columns(query: str, columns: list[str]) -> list[str]:
    normalized_query = f" {normalize_text(query)} "
    mentioned: list[str] = []
    for col in columns:
        normalized_col = normalize_text(col)
        if normalized_col and f" {normalized_col} " in normalized_query:
            mentioned.append(col)
    return mentioned


def _pick_target_column(query: str, columns: list[str], numeric_columns: list[str]) -> str:
    mentioned = mentioned_columns(query, columns)
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
        normalized_col = normalize_text(col)
        if any(term in normalized_col.split() for term in target_terms):
            return col

    mentioned_numeric = [c for c in mentioned if c in numeric_columns]
    if mentioned_numeric:
        return mentioned_numeric[-1]

    for term in target_terms:
        for col in columns:
            if term in normalize_text(col).split():
                return col

    if numeric_columns:
        return numeric_columns[-1]
    return columns[-1] if columns else "target"


def _pick_treatment_column(
    query: str, columns: list[str], numeric_columns: list[str], target: str
) -> str:
    mentioned = [c for c in mentioned_columns(query, columns) if c != target]
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
        if any(term in normalize_text(col).split() for term in treatment_terms):
            return col
    for col in categorical:
        if any(term in normalize_text(col).split() for term in treatment_terms):
            return col
    if categorical:
        return categorical[0]
    for col in columns:
        if col != target:
            return col
    return "treatment"


def _pick_numeric_predictor(query: str, numeric_columns: list[str], target: str) -> str:
    mentioned = [c for c in mentioned_columns(query, numeric_columns) if c != target]
    if mentioned:
        return mentioned[0]

    normalized_target = normalize_text(target)
    for col in numeric_columns:
        if col == target:
            continue
        # Avoid obvious target-derived proxy/prediction columns by default.
        normalized_col = normalize_text(col)
        if normalized_target and normalized_target in normalized_col:
            continue
        return col

    for col in numeric_columns:
        if col != target:
            return col
    return target


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
