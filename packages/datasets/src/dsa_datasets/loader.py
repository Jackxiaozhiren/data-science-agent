from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from dsa_datasets.errors import DatasetError, UnsupportedFormatError
from dsa_datasets.models import DatasetFormat


def load_dataframe(path: Path, fmt: DatasetFormat) -> pl.DataFrame:
    if fmt == DatasetFormat.csv:
        # Polars handles large CSV streaming; infer schema
        try:
            return pl.read_csv(path, infer_schema_length=10000, try_parse_dates=True)
        except Exception as e:
            raise DatasetError(f"Failed to parse CSV {path.name}: {e}") from e
    if fmt == DatasetFormat.parquet:
        try:
            return pl.read_parquet(path)
        except Exception as e:
            raise DatasetError(f"Failed to parse Parquet {path.name}: {e}") from e
    if fmt == DatasetFormat.json:
        # Try JSON array or JSONL
        try:
            text = path.read_text(encoding="utf-8-sig")
            text_stripped = text.strip()
            if text_stripped.startswith("["):
                data = json.loads(text_stripped)
                return pl.DataFrame(data)
            # JSONL fallback
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            if not rows:
                raise DatasetError("Empty JSON file")
            return pl.DataFrame(rows)
        except DatasetError:
            raise
        except Exception as e:
            raise DatasetError(f"Failed to parse JSON {path.name}: {e}") from e
    if fmt == DatasetFormat.excel:
        try:
            return pl.read_excel(str(path))
        except Exception as e:
            raise DatasetError(f"Failed to parse Excel {path.name}: {e}") from e
    raise UnsupportedFormatError(f"Unsupported format: {fmt}")


def duckdb_query_parquet_or_csv(path: Path, sql: str):  # type: ignore[no-untyped-def]
    import duckdb

    con = duckdb.connect()
    # Expose file as 'dataset' view via read_csv/read_parquet depending on ext
    ext = path.suffix.lower()
    if ext == ".csv":
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM read_csv('{path}', AUTO_DETECT=TRUE, SAMPLE_SIZE=-1)")
    elif ext == ".parquet":
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{path}')")
    else:
        # fallback: register polars df

        fmt_fallback = DatasetFormat.excel if ext in (".xlsx", ".xls") else DatasetFormat.json if ext == ".json" else DatasetFormat.csv
        df = load_dataframe(path, fmt_fallback)
        con.register("dataset", df.to_arrow())
    return con.execute(sql).fetchall()
