"""ADR-002 export_artifact track: tool, executor refs, planner, adapter preference."""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from dsa_tools import bootstrap, clear, get

# 1x1 transparent PNG
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture(autouse=True)
def _bootstrap_tools():
    clear()
    bootstrap()
    yield
    clear()


def _table():
    return {"columns": ["a", "b"], "rows": [[1, "x"], [2, "y"], [3, "z"]]}


@pytest.mark.asyncio
async def test_export_registered() -> None:
    assert get("export_artifact").name == "export_artifact"


@pytest.mark.asyncio
async def test_export_csv_roundtrip_identical_bytes() -> None:
    with tempfile.TemporaryDirectory() as td:
        tool = get("export_artifact")
        r = await tool.run(
            {"source": _table(), "filename": "predictions.csv", "format": "csv", "workspace": td}
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        p = Path(r.output.path)
        assert p.is_file()
        with p.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        assert rows[0] == ["a", "b"]
        assert rows[1:] == [["1", "x"], ["2", "y"], ["3", "z"]]
        assert r.output.rows == 3
        assert r.output.columns == ["a", "b"]
        assert r.output.sha256 == hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_export_xlsx_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        tool = get("export_artifact")
        r = await tool.run(
            {"source": _table(), "filename": "out.xlsx", "format": "xlsx", "workspace": td}
        )
        assert r.status == "ok", r.error
        import openpyxl

        wb = openpyxl.load_workbook(r.output.path)
        ws = wb.active
        assert [c.value for c in ws[1]] == ["a", "b"]
        assert ws.max_row == 4


@pytest.mark.asyncio
async def test_export_png_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        tool = get("export_artifact")
        b64 = base64.b64encode(_PNG).decode()
        r = await tool.run(
            {
                "source": {"base64_png": b64},
                "filename": "chart.png",
                "format": "png",
                "workspace": td,
            }
        )
        assert r.status == "ok", r.error
        assert Path(r.output.path).read_bytes() == _PNG


@pytest.mark.asyncio
async def test_export_rejects_traversal_and_mismatch() -> None:
    with tempfile.TemporaryDirectory() as td:
        tool = get("export_artifact")
        base = {"source": _table(), "format": "csv", "workspace": td}
        for bad in ["../evil.csv", "sub/x.csv", "x.png", ""]:
            r = await tool.run({**base, "filename": bad})
            assert r.status == "error", bad
        r = await tool.run(
            {"source": {"$from_step": 0}, "filename": "x.csv", "format": "csv", "workspace": td}
        )
        assert r.status == "error"
        r = await tool.run(
            {"source": {"nope": 1}, "filename": "x.csv", "format": "csv", "workspace": td}
        )
        assert r.status == "error"


def test_resolve_refs_step_tool_missing() -> None:
    from dsa_agent.graph import _resolve_refs

    prior = [
        {"tool": "run_sql", "status": "ok", "output": {"columns": ["a"], "rows": [[1]]}},
        {"tool": "run_sql", "status": "error", "output": None},
        {"tool": "create_chart", "status": "ok", "output": {"base64_png": "eA=="}},
    ]
    out = _resolve_refs(
        {
            "source": {"$from_step": 0},
            "other": {"$from_tool": "create_chart"},
            "latest_sql": {"$from_tool": "run_sql"},
            "missing": {"$from_step": 9},
            "plain": 1,
        },
        prior,
    )
    assert out["source"] == {"columns": ["a"], "rows": [[1]]}
    assert out["other"] == {"base64_png": "eA=="}
    assert out["latest_sql"] == {"columns": ["a"], "rows": [[1]]}  # skips the error call
    assert out["missing"] == {"$from_step": 9}  # left for honest tool error
    assert out["plain"] == 1


def test_planner_export_steps_conventional_names() -> None:
    """Export filenames come from the question, and every source can satisfy the tool.

    This asserted that ``predictions.csv`` was exported from ``train_model``. That
    pairing could never run: ``train_model`` keeps its result in memory and
    ``export_artifact`` refuses a source without ``columns``/``rows`` rather than
    synthesizing one. The convention still holds for a source that is genuinely
    tabular, which is what is checked now, plus the chart export and the negative
    control that no benchmark-specific filename leaks in.
    """
    from dsa_agent.planner import _TABULAR_TOOLS, heuristics_plan

    plan = heuristics_plan("Predict churn for customers", "dummy.csv", ["age", "churn", "tenure"])
    exp = [s for s in plan.steps if s.tool == "export_artifact"]
    plan_tools = {s.tool for s in plan.steps}
    assert "create_chart" in plan_tools
    assert {s.inputs["filename"] for s in exp} == {"chart.png"}, (
        "chart export must still be planned"
    )

    for spec in exp:
        source = spec.inputs["source"]
        origin = source.get("$from_tool")
        if origin is None or origin == "create_chart":
            continue
        assert origin in _TABULAR_TOOLS, (
            f"{spec.inputs['filename']} sourced from {origin}, which cannot be exported"
        )

    # the tabular branch is exercised directly: heuristics_plan never emits run_sql,
    # so reaching it through the planner would leave the assertion silently unrun
    from types import SimpleNamespace

    from dsa_agent.planner import _terminal_export_steps

    steps = [SimpleNamespace(tool="profile_dataset"), SimpleNamespace(tool="run_sql")]
    specs = _terminal_export_steps("Clean missing values and dedup", steps)
    assert ("cleaned_data.csv", "run_sql") in [(name, src) for _, name, src, _ in specs]
    assert all(src in _TABULAR_TOOLS for _, _, src, fmt in specs if fmt == "csv")

    plan2 = heuristics_plan("Analyze revenue trends", "dummy.csv", ["region", "revenue"])
    names2 = [s.inputs["filename"] for s in plan2.steps if s.tool == "export_artifact"]
    assert "predictions.csv" not in names2


def test_adapter_prefers_exact_workspace_export(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dsc_adapter_test", Path("benchmarks/external/datascibench/adapter.py")
    )
    dsc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dsc)
    from dsa_evaluation.external_benchmark import AgentTaskView, ExternalRun

    exported = tmp_path / "predictions.csv"
    exported.write_text("a\n1\n", encoding="utf-8")
    run = ExternalRun(
        task_id="probe_task",
        benchmark_name="DataSciBench",
        agent_view=AgentTaskView(task_id="probe_task", question="", dataset_path=""),
        status="COMPLETED",
        run_id="r1",
        tool_calls=[
            {
                "call_id": "TC-1",
                "tool": "run_sql",
                "status": "ok",
                "output": {"columns": ["z"], "rows": [[9]]},
            },
            {
                "call_id": "TC-2",
                "tool": "export_artifact",
                "status": "ok",
                "output": {
                    "filename": "predictions.csv",
                    "path": str(exported),
                    "sha256": "x",
                },
            },
        ],
    )
    a = dsc.DataSciBenchAdapter()
    a._expected_output_files = lambda task_id: ["predictions.csv"]  # noqa: E731
    run_dir = tmp_path / "rundir"
    run_dir.mkdir()
    fmap = a._materialize_expected_files(run, run_dir)
    assert (run_dir / "predictions.csv").read_text(encoding="utf-8") == "a\n1\n"
    assert "workspace export from TC-2" in json.dumps(fmap["mapped"])


def test_declared_tabular_sources_really_are_tabular() -> None:
    """The planner's export source list must match what the tools actually emit.

    ``_TABULAR_TOOLS`` named five tools whose output models carry no ``columns``/
    ``rows``, and ``export_artifact`` refuses such a source by contract -- it relocates
    bytes and never synthesizes content. Every plan whose question matched the predict
    or evaluate intent therefore carried a step that could only fail, invisibly, until
    status consulted ``tool_errors``. Deriving the list from the registry is what keeps
    the declaration honest when a tool changes.
    """
    import dsa_tools
    from dsa_agent.planner import _TABULAR_TOOLS

    dsa_tools.bootstrap()
    assert _TABULAR_TOOLS, "an empty list would silently disable every tabular export"
    for name in _TABULAR_TOOLS:
        tool = dsa_tools.get(name)
        assert tool is not None, f"{name} is declared tabular but is not a registered tool"
        fields = set(tool.output_model.model_fields)
        assert {"columns", "rows"} <= fields, (
            f"{name} is declared an exportable table but its output has {sorted(fields)}"
        )
