from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from dsa_datasets.errors import DatasetError, UnsupportedFormatError
from dsa_datasets.models import DatasetFormat

# .xlsx above this size avoids the openpyxl DOM (human_7 79 MB OOM) and uses
# read_only streaming instead. The final DataFrame is still O(n) — the win is
# peak memory (DOM ≈ 5-10× file size → chunked ≈ O(chunk)).
STREAM_XLSX_THRESHOLD_BYTES = 10 * 1024 * 1024


def _load_excel_streaming(path: Path, chunk_rows: int = 5000) -> pl.DataFrame:
    """Read .xlsx with openpyxl read_only + iter_rows, batched into Polars.

    Peak memory is O(chunk_rows × cols) instead of O(file DOM).
    """
    import openpyxl

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise DatasetError(f"Excel {path.name} has no active sheet")
        rows_iter = ws.iter_rows(values_only=True)
        header = next(rows_iter, None)
        if header is None:
            wb.close()
            return pl.DataFrame()
        columns = [str(c) if c is not None else f"col_{i}" for i, c in enumerate(header)]
        chunks: list[pl.DataFrame] = []
        batch: list[tuple[object, ...]] = []
        for row in rows_iter:
            batch.append(tuple(row))
            if len(batch) >= chunk_rows:
                chunks.append(pl.DataFrame(batch, schema=columns, orient="row"))
                batch = []
        if batch:
            chunks.append(pl.DataFrame(batch, schema=columns, orient="row"))
        wb.close()
    except DatasetError:
        raise
    except Exception as e:
        raise DatasetError(f"Failed to stream Excel {path.name}: {e}") from e
    if not chunks:
        return pl.DataFrame({c: [] for c in columns})
    if len(chunks) == 1:
        return chunks[0]
    return pl.concat(chunks, how="diagonal")


def _quote_duckdb_path(path: Path) -> str:
    return str(path).replace("'", "''")


def load_dataframe(
    path: Path, fmt: DatasetFormat, stream_threshold_bytes: int = STREAM_XLSX_THRESHOLD_BYTES
) -> pl.DataFrame:
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
            # Polars defaults to the calamine/fastexcel engine for modern Excel
            # files. The project already ships openpyxl, so use it explicitly for
            # .xlsx to keep the hosted API image lean and avoid an undeclared
            # fastexcel runtime dependency. Legacy .xls retains Polars' default
            # engine behavior. Large .xlsx (>threshold) streams via read_only to
            # avoid the openpyxl DOM OOM (human_7 79 MB).
            if path.suffix.lower() == ".xlsx":
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                if size >= stream_threshold_bytes:
                    return _load_excel_streaming(path)
                return pl.read_excel(str(path), engine="openpyxl")
            return pl.read_excel(str(path))
        except DatasetError:
            raise
        except Exception as e:
            raise DatasetError(f"Failed to parse Excel {path.name}: {e}") from e
    raise UnsupportedFormatError(f"Unsupported format: {fmt}")


def duckdb_query_parquet_or_csv(path: Path, sql: str):  # type: ignore[no-untyped-def]
    import duckdb

    con = duckdb.connect()
    # Expose file as 'dataset' view via read_csv/read_parquet depending on ext.
    # Paths are single-quote escaped (no user SQL is interpolated here).
    ext = path.suffix.lower()
    safe = _quote_duckdb_path(path)
    if ext == ".csv":
        con.execute(
            f"CREATE VIEW dataset AS SELECT * FROM read_csv('{safe}', AUTO_DETECT=TRUE, SAMPLE_SIZE=-1)"
        )
    elif ext == ".parquet":
        con.execute(f"CREATE VIEW dataset AS SELECT * FROM read_parquet('{safe}')")
    else:
        # fallback: register polars df

        fmt_fallback = (
            DatasetFormat.excel
            if ext in (".xlsx", ".xls")
            else DatasetFormat.json
            if ext == ".json"
            else DatasetFormat.csv
        )
        df = load_dataframe(path, fmt_fallback)
        con.register("dataset", df.to_arrow())
    return con.execute(sql).fetchall()
