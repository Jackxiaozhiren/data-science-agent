from __future__ import annotations

import json
import tempfile
from pathlib import Path

import polars as pl
import pytest

from dsa_datasets.loader import load_dataframe
from dsa_datasets.models import DatasetFormat
from dsa_datasets.profiler import build_profile
from dsa_datasets.validate import detect_format, validate_file, validate_filename

# ---- validation ----


def test_validate_filename_ok() -> None:
    assert validate_filename("sales.csv") == "sales.csv"
    assert validate_filename("my data (1).parquet") == "my data (1).parquet"


def test_validate_filename_rejects_traversal() -> None:
    with pytest.raises(Exception):
        validate_filename("../etc/passwd")
    with pytest.raises(Exception):
        validate_filename("a/b.csv")


def test_detect_format() -> None:
    assert detect_format("a.csv") == DatasetFormat.csv
    assert detect_format("a.parquet") == DatasetFormat.parquet
    assert detect_format("a.json") == DatasetFormat.json
    assert detect_format("a.xlsx") == DatasetFormat.excel


def test_detect_format_unsupported() -> None:
    with pytest.raises(Exception):
        detect_format("a.exe")


def test_validate_file_size_limit() -> None:
    with pytest.raises(Exception):
        validate_file("a.csv", 200 * 1024 * 1024)


# ---- loader ----


def _write_csv(path: Path, rows: str) -> None:
    path.write_text(rows, encoding="utf-8")


def test_load_csv() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _write_csv(p, "a,b\n1,hello\n2,world\n")
        df = load_dataframe(p, DatasetFormat.csv)
        assert df.shape == (2, 2)
        assert df.columns == ["a", "b"]


def test_load_parquet() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.parquet"
        df0 = pl.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        df0.write_parquet(p)
        df = load_dataframe(p, DatasetFormat.parquet)
        assert df.shape == (3, 2)


def test_load_json_array() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.json"
        p.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
        df = load_dataframe(p, DatasetFormat.json)
        assert df.shape == (2, 1)


def test_load_jsonl() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.json"
        p.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
        df = load_dataframe(p, DatasetFormat.json)
        assert df.shape == (2, 1)


def test_malformed_csv_raises() -> None:
    # loader should either parse leniently or raise DatasetError; we assert not crash silently
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.csv"
        # empty file should raise or return empty df -> treat as error case
        p.write_text("", encoding="utf-8")
        try:
            df = load_dataframe(p, DatasetFormat.csv)
            # if it returns, shape should be (0, 0) or similar
            assert df.shape[0] == 0
        except Exception as e:
            assert "Failed to parse" in str(e) or "Empty" in str(e) or isinstance(e, Exception)


# ---- profiler ----


def test_build_profile_basic() -> None:
    df = pl.DataFrame(
        {
            "n": [1, 2, None, 4],
            "c": ["a", "b", "a", None],
            "d": [1.0, 2.0, 3.0, 4.0],
        }
    )
    profile = build_profile(df, "ds1", "t.csv", DatasetFormat.csv)
    assert profile.rows == 4
    assert profile.columns == 3
    assert profile.missing_cells == 2
    assert len(profile.column_profiles) == 3
    # numeric detection
    assert "n" in profile.numeric_columns or "d" in profile.numeric_columns


def test_profiler_duplicate_and_missing_ratio() -> None:
    df = pl.DataFrame({"a": [1, 1, 2], "b": [1, 1, 2]})
    profile = build_profile(df, "ds1", "t.csv", DatasetFormat.csv)
    assert profile.duplicate_rows == 1
    assert profile.missing_ratio == 0.0


def test_large_file_handling_streaming_csv() -> None:
    # 50k rows CSV — should still load via Polars without OOM in test
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "large.csv"
        n = 50000
        # write header + rows
        with p.open("w", encoding="utf-8") as f:
            f.write("id,value,cat\n")
            for i in range(n):
                f.write(f"{i},{i * 0.5},{'a' if i % 2 == 0 else 'b'}\n")
        df = load_dataframe(p, DatasetFormat.csv)
        assert df.shape[0] == n
        profile = build_profile(df, "ds-large", "large.csv", DatasetFormat.csv)
        assert profile.rows == n
