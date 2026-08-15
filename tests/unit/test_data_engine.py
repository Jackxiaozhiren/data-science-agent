import pytest


def test_optional_data_engines() -> None:
    duckdb = pytest.importorskip("duckdb", reason="Phase 2: duckdb not yet required")
    pl = pytest.importorskip("polars", reason="Phase 2: polars not yet required")
    con = duckdb.connect()
    con.execute("SELECT 1 AS a").fetchall()
    df = pl.DataFrame({"a": [1, 2, 3]})
    assert df.shape == (3, 1)
