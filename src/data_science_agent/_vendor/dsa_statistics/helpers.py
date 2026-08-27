from __future__ import annotations

import numpy as np
import polars as pl


def _to_numpy(series: pl.Series) -> np.ndarray:
    return series.drop_nulls().to_numpy()


def ensure_numeric(series: pl.Series) -> np.ndarray:
    arr = _to_numpy(series)
    if arr.size == 0:
        raise ValueError(f"Column {series.name!r} has no non-null values")
    # try coerce
    try:
        return arr.astype(float)
    except Exception as e:
        raise ValueError(f"Column {series.name!r} is not numeric: {e}") from e
