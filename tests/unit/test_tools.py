from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest

# ensure bootstrap
import dsa_tools
from dsa_tools import bootstrap, clear, get


@pytest.fixture(autouse=True)
def _bootstrap_tools():
    clear()
    bootstrap()
    yield
    clear()


def _make_csv(path: Path, rows: int = 50) -> Path:
    with path.open("w", encoding="utf-8") as f:
        f.write("a,b,c,group,target\n")
        for i in range(rows):
            f.write(f"{i},{i*0.7+ (i%3)},hello_{i%5},{'A' if i%2==0 else 'B'},{i%2}\n")
    return path


@pytest.mark.asyncio
async def test_run_sql_basic() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        tool = get("run_sql")
        r = await tool.run({"sql": "SELECT COUNT(*) as n FROM dataset", "dataset_path": str(p), "max_rows": 100})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert r.output.row_count == 1
        assert r.output.columns == ["n"]


@pytest.mark.asyncio
async def test_run_sql_blocks_mutation() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        tool = get("run_sql")
        r = await tool.run({"sql": "DROP TABLE dataset", "dataset_path": str(p)})
        assert r.status == "error"
        assert "Disallowed" in (r.error or "")


@pytest.mark.asyncio
async def test_run_sql_row_limit_enforced() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p, rows=100)
        tool = get("run_sql")
        r = await tool.run({"sql": "SELECT * FROM dataset", "dataset_path": str(p), "max_rows": 10})
        assert r.status == "ok"
        assert r.output is not None
        assert r.output.row_count <= 10


@pytest.mark.asyncio
async def test_run_python_basic() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        tool = get("run_python")
        r = await tool.run({"code": "print(df.shape)\nresult = df.select(pl.col('a').mean()).item()", "dataset_path": str(p)})
        assert r.status == "ok", r.error or r.output.stderr if r.output else r.error
        assert r.output is not None
        assert r.output.error is None


@pytest.mark.asyncio
async def test_run_python_blocks_os_import() -> None:
    tool = get("run_python")
    r = await tool.run({"code": "import os\nos.system('ls')"})
    assert r.status == "error"
    assert "denied" in (r.error or "").lower()


@pytest.mark.asyncio
async def test_run_python_blocks_socket() -> None:
    tool = get("run_python")
    r = await tool.run({"code": "import socket\ns=socket.socket()"})
    assert r.status == "error"


@pytest.mark.asyncio
async def test_correlation_pearson() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        # strongly correlated a and b
        with p.open("w") as f:
            f.write("x,y\n")
            for i in range(30):
                f.write(f"{i},{i*2+ (i%2)}\n")
        tool = get("correlation_analysis")
        r = await tool.run({"dataset_path": str(p), "x": "x", "y": "y", "method": "pearson"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert r.output.r > 0.9
        assert r.output.p_value is not None
        assert r.output.p_value < 0.05


@pytest.mark.asyncio
async def test_hypothesis_welch() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p, rows=60)
        tool = get("hypothesis_test")
        r = await tool.run({"dataset_path": str(p), "test": "welch_t_test", "group_col": "group", "value_col": "a"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert 0 <= r.output.p_value <= 1


@pytest.mark.asyncio
async def test_hypothesis_mannwhitney() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p, rows=40)
        tool = get("hypothesis_test")
        r = await tool.run({"dataset_path": str(p), "test": "mann_whitney", "group_col": "group", "value_col": "b"})
        assert r.status == "ok", r.error


@pytest.mark.asyncio
async def test_regression_linear() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p, rows=100)
        tool = get("regression_analysis")
        r = await tool.run({"dataset_path": str(p), "target": "a", "features": ["b"], "model": "linear"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert "r2" in r.output.metrics


@pytest.mark.asyncio
async def test_train_and_evaluate() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        # classification dataset
        df = pl.DataFrame({"f1": list(range(100)), "f2": [i % 5 for i in range(100)], "target": [i % 2 for i in range(100)]})
        df.write_csv(p)
        train = get("train_model")
        r1 = await train.run({"dataset_path": str(p), "target": "target", "task": "classification", "model": "logistic", "cv_folds": 3})
        assert r1.status == "ok", r1.error
        assert r1.output is not None
        assert len(r1.output.cv_scores) == 3

        eval_tool = get("evaluate_model")
        r2 = await eval_tool.run({"dataset_path": str(p), "target": "target", "task": "classification", "model": "logistic"})
        assert r2.status == "ok", r2.error
        assert r2.output is not None
        assert "accuracy" in r2.output.metrics
        assert r2.output.confusion_matrix is not None


@pytest.mark.asyncio
async def test_create_chart_histogram() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        tool = get("create_chart")
        r = await tool.run({"dataset_path": str(p), "chart_type": "histogram", "x": "a"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert Path(r.output.artifact_path).exists()
        assert len(r.output.base64_png) > 1000


@pytest.mark.asyncio
async def test_create_chart_scatter_and_bar() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        # scatter
        t1 = get("create_chart")
        r1 = await t1.run({"dataset_path": str(p), "chart_type": "scatter", "x": "a", "y": "b"})
        assert r1.status == "ok", r1.error
        # bar
        r2 = await t1.run({"dataset_path": str(p), "chart_type": "bar", "x": "group", "y": "a"})
        assert r2.status == "ok", r2.error


@pytest.mark.asyncio
async def test_profile_dataset_tool() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        tool = get("profile_dataset")
        r = await tool.run({"path": str(p), "filename": "t.csv"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert r.output.profile["rows"] == 50


def test_registry_lists_tools() -> None:
    from dsa_tools import list_tools

    tools = list_tools()
    assert "run_sql" in tools
    assert "run_python" in tools
    assert "correlation_analysis" in tools
    assert len(tools) >= 9
