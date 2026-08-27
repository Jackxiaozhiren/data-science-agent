from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import polars as pl

from dsa_datasets.models import ColumnKind, ColumnProfile, DatasetFormat, DatasetProfile

_NUMERIC_DTYPES = {
    pl.Int8,
    pl.Int16,
    pl.Int32,
    pl.Int64,
    pl.UInt8,
    pl.UInt16,
    pl.UInt32,
    pl.UInt64,
    pl.Float32,
    pl.Float64,
}
_DATETIME_DTYPES = {pl.Date, pl.Datetime, pl.Time, pl.Duration}
_BOOL_DTYPE = pl.Boolean


def _kind_for_dtype(dtype: Any, series: pl.Series) -> ColumnKind:
    if dtype == _BOOL_DTYPE:
        return ColumnKind.boolean
    if dtype in _DATETIME_DTYPES:
        return ColumnKind.datetime
    if dtype in _NUMERIC_DTYPES:
        return ColumnKind.numeric
    # Polars may report Object/String
    if dtype in (pl.Utf8, pl.String, pl.Categorical, pl.Enum):
        # heuristic: high cardinality numeric-looking strings -> text
        return ColumnKind.categorical if series.n_unique() < len(series) * 0.5 else ColumnKind.text
    # fallback by sample
    return ColumnKind.categorical if series.n_unique() < 50 else ColumnKind.text


def _column_profile(series: pl.Series, total_rows: int) -> ColumnProfile:
    name = series.name
    dtype_str = str(series.dtype)
    null_count = int(series.null_count())
    null_ratio = null_count / total_rows if total_rows else 0.0
    kind = _kind_for_dtype(series.dtype, series)
    try:
        unique_count = int(series.n_unique())
    except Exception:
        unique_count = None
    unique_ratio = (unique_count / total_rows) if unique_count is not None and total_rows else None

    # numeric stats
    mean: float | None = None
    std: float | None = None
    mn: float | None = None
    mx: float | None = None
    median: float | None = None
    q25: float | None = None
    q75: float | None = None
    if kind == ColumnKind.numeric:
        try:
            v_any: object = series.mean()
            mean = float(v_any) if v_any is not None else None  # type: ignore[arg-type]
            v_any = series.std()
            std = float(v_any) if v_any is not None else None  # type: ignore[arg-type]
            v_any = series.min()
            mn = float(v_any) if v_any is not None else None  # type: ignore[arg-type]
            v_any = series.max()
            mx = float(v_any) if v_any is not None else None  # type: ignore[arg-type]
            v_any = series.median()
            median = float(v_any) if v_any is not None else None  # type: ignore[arg-type]
            v_any = series.quantile(0.25)
            q25 = float(v_any) if v_any is not None else None
            v_any = series.quantile(0.75)
            q75 = float(v_any) if v_any is not None else None
        except Exception:
            pass

    # sample values (non-null, up to 5)
    try:
        sample = [v for v in series.drop_nulls().head(5).to_list()]
    except Exception:
        sample = []

    return ColumnProfile(
        name=name,
        dtype=dtype_str,
        kind=kind,
        count=total_rows,
        null_count=null_count,
        null_ratio=null_ratio,
        unique_count=unique_count,
        unique_ratio=unique_ratio,
        mean=mean,
        std=std,
        min=mn,
        max=mx,
        median=median,
        q25=q25,
        q75=q75,
        sample_values=sample,
    )


def build_profile(
    df: pl.DataFrame,
    dataset_id: str,
    filename: str,
    fmt: DatasetFormat,
) -> DatasetProfile:
    rows, cols = df.shape
    col_profiles = [_column_profile(df[col], rows) for col in df.columns]
    duplicate_rows = int(rows - len(df.unique())) if rows else 0
    missing_cells = sum(p.null_count for p in col_profiles)
    total_cells = rows * cols if rows and cols else 0
    missing_ratio = (missing_cells / total_cells) if total_cells else 0.0
    try:
        memory_bytes = int(df.estimated_size("bytes"))
    except Exception:
        memory_bytes = None

    numeric_cols = [p.name for p in col_profiles if p.kind == ColumnKind.numeric]
    categorical_cols = [p.name for p in col_profiles if p.kind == ColumnKind.categorical]
    datetime_cols = [p.name for p in col_profiles if p.kind == ColumnKind.datetime]
    # heuristic potential target: low-card categorical / boolean near binary
    potential_targets = []
    for p in col_profiles:
        if (
            p.kind in (ColumnKind.categorical, ColumnKind.boolean)
            and p.unique_count is not None
            and 2 <= p.unique_count <= 10
            and p.null_ratio < 0.3
        ):
            potential_targets.append(p.name)

    return DatasetProfile(
        dataset_id=dataset_id,
        filename=filename,
        format=fmt,
        rows=rows,
        columns=cols,
        column_profiles=col_profiles,
        duplicate_rows=duplicate_rows,
        missing_cells=missing_cells,
        missing_ratio=missing_ratio,
        memory_bytes=memory_bytes,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        datetime_columns=datetime_cols,
        potential_target_columns=potential_targets,
    )


def quick_profile_for_path(
    path: Path, fmt: DatasetFormat, dataset_id: str | None = None
) -> tuple[pl.DataFrame, DatasetProfile]:
    from dsa_datasets.loader import load_dataframe

    df = load_dataframe(path, fmt)
    ds_id = dataset_id or str(uuid.uuid4())
    profile = build_profile(df, ds_id, path.name, fmt)
    return df, profile
