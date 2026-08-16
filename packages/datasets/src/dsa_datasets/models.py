from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DatasetFormat(str, Enum):
    csv = "csv"
    parquet = "parquet"
    json = "json"
    excel = "excel"


class ColumnKind(str, Enum):
    numeric = "numeric"
    categorical = "categorical"
    datetime = "datetime"
    boolean = "boolean"
    text = "text"
    unknown = "unknown"


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    kind: ColumnKind
    count: int
    null_count: int
    null_ratio: float
    unique_count: int | None = None
    unique_ratio: float | None = None
    mean: float | None = None
    std: float | None = None
    min: Any | None = None
    max: Any | None = None
    median: float | None = None
    q25: float | None = None
    q75: float | None = None
    sample_values: list[Any] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    dataset_id: str
    filename: str
    format: DatasetFormat
    rows: int
    columns: int
    column_profiles: list[ColumnProfile]
    duplicate_rows: int = 0
    missing_cells: int = 0
    missing_ratio: float = 0.0
    memory_bytes: int | None = None
    numeric_columns: list[str] = Field(default_factory=list)
    categorical_columns: list[str] = Field(default_factory=list)
    datetime_columns: list[str] = Field(default_factory=list)
    potential_target_columns: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DatasetRecord(BaseModel):
    id: str
    project_id: str | None = None
    filename: str
    format: DatasetFormat
    path: str
    sha256: str
    size_bytes: int
    rows: int | None = None
    cols: int | None = None
    profile: DatasetProfile | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
