"""V4.3 Phase C (W3 §22-27) — DataSciBench adapter tests (offline, no network)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from dsa_evaluation.external_benchmark import (
    AgentBackedRunner,
    ExternalBenchmarkAdapter,
    ExternalRun,
    RunConfig,
    TaskOutcome,
    classify_outcome,
)

REPO = Path(__file__).resolve().parents[2]
ADAPTER_PATH = REPO / "benchmarks" / "external" / "datascibench" / "adapter.py"
MANIFEST_PATH = REPO / "benchmarks" / "external" / "datascibench" / "manifest.json"
PINNED_COMMIT = "84ef3d4d94d7362a5149cf14a73dc168fc4f2f33"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("datascibench_adapter", ADAPTER_PATH)
    assert spec and spec.loader
    mod: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def dsc() -> Any:
    return _load_module()


def _fake_workspace(tmp_path: Path) -> Path:
    """Upstream-shaped workspace with one task per category (no network)."""
    ws = tmp_path / "workspace"
    for task_id, prompt in [
        ("human_2", "Analyze campaign ROI from campaign_data.csv."),
        ("csv_excel_3", "Aggregate sales by region from sales.xlsx."),
        ("dl_0", "Train a CNN image classifier from scratch."),
        ("bcb9", "Implement the BigCodeBench function f_9."),
    ]:
        d = ws / "data" / task_id
        d.mkdir(parents=True)
        (d / "prompt.json").write_text(json.dumps({"prompt": prompt}), encoding="utf-8")
    return ws


def _adapter(dsc: Any, ws: Path) -> Any:
    return dsc.DataSciBenchAdapter(workspace=ws)


def test_adapter_satisfies_phase_b_protocol(dsc: Any, tmp_path: Path) -> None:
    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    assert isinstance(adapter, ExternalBenchmarkAdapter)


def test_lists_all_categories_with_honest_support(dsc: Any, tmp_path: Path) -> None:
    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    tasks = {t.task_id: t for t in adapter.list_tasks()}
    assert set(tasks) == {"human_2", "csv_excel_3", "dl_0", "bcb9"}
    assert tasks["human_2"].supported and tasks["csv_excel_3"].supported
    assert not tasks["dl_0"].supported
    assert "GPU" in (tasks["dl_0"].unsupported_reason or "")
    assert not tasks["bcb9"].supported
    assert "TMC" in (tasks["bcb9"].unsupported_reason or "")
    # §23/§19: gold never travels with listed tasks
    assert all(t.gold == {} for t in tasks.values())


def test_run_task_unsupported_reports_without_running_agent(dsc: Any, tmp_path: Path) -> None:
    class Boom:
        def analyze_sync(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise AssertionError("agent must not run for unsupported tasks")

    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    adapter._runner = AgentBackedRunner(agent_factory=Boom)
    task = next(t for t in adapter.list_tasks() if t.task_id == "dl_0")
    run = adapter.run_task(task, RunConfig())
    assert run.status == "skipped_unsupported"
    assert classify_outcome(run) == TaskOutcome.UNSUPPORTED
    assert "GPU" in (run.error or "")


def test_run_task_supported_invokes_runner_and_materializes_logs(dsc: Any, tmp_path: Path) -> None:
    class FakeResult:
        status = "COMPLETED"
        run_id = "run-x"
        elapsed_s = 1.25

    class FakeAgent:
        def analyze_sync(self, dataset: str, question: str) -> FakeResult:
            assert "campaign" in question
            return FakeResult()

    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    adapter._runner = AgentBackedRunner(agent_factory=FakeAgent)
    task = next(t for t in adapter.list_tasks() if t.task_id == "human_2")
    run = adapter.run_task(task, RunConfig(model="deterministic"))
    assert run.status == "COMPLETED" and run.run_id == "run-x"
    run_dir = Path(task.dataset_path) / "dsa_run-x"
    logs = (run_dir / "logs.txt").read_text(encoding="utf-8")
    assert "## Current Plan" in logs and "## Current Task" in logs
    plan_json = logs.split("## Current Plan\n")[1].split("## Current Task")[0]
    assert isinstance(json.loads(plan_json), list)


def test_run_task_execution_error_is_honest(dsc: Any, tmp_path: Path) -> None:
    class Boom:
        def analyze_sync(self, *_a: object, **_k: object) -> object:
            raise RuntimeError("sandbox unavailable")

    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    adapter._runner = AgentBackedRunner(agent_factory=Boom)
    task = next(t for t in adapter.list_tasks() if t.task_id == "human_2")
    run = adapter.run_task(task, RunConfig())
    assert run.status == "execution_error"
    assert classify_outcome(run) == TaskOutcome.EXECUTION_ERROR
    assert "sandbox unavailable" in (run.error or "")


def test_build_logs_txt_maps_tool_calls(dsc: Any) -> None:
    from dsa_evaluation.external_benchmark import AgentTaskView

    run = ExternalRun(
        task_id="human_2",
        benchmark_name="DataSciBench",
        agent_view=AgentTaskView(task_id="human_2", question="q", dataset_path="d"),
        status="COMPLETED",
        tool_calls=[
            {"tool": "profile", "ok": True, "result": "500 rows"},
            {"tool": "run_sql", "ok": False, "error": "bad sql"},
        ],
    )
    logs = dsc.build_logs_txt(run)
    plan = json.loads(logs.split("## Current Plan\n")[1].split("## Current Task")[0])
    assert len(plan) == 2
    assert plan[0]["success"] is True and plan[0]["instruction"] == "profile"
    assert plan[1]["success"] is False and plan[1]["result"] == "bad sql"


def test_prepare_missing_workspace_raises_with_setup_instructions(dsc: Any, tmp_path: Path) -> None:
    adapter = _adapter(dsc, tmp_path / "empty")
    with pytest.raises(FileNotFoundError, match="Setup") as exc:
        adapter.prepare()
    msg = str(exc.value)
    assert PINNED_COMMIT in msg
    assert "codeload.github.com" in msg  # exact pinned tarball URL is documented
    assert "huggingface.co/datasets/zd21/DataSciBench" in msg  # gated GT disclosed


def test_prepare_at_pinned_commit_is_idempotent_and_reports_gt_status(
    dsc: Any, tmp_path: Path
) -> None:
    ws = _fake_workspace(tmp_path)
    (ws / ".upstream_commit").write_text(PINNED_COMMIT + "\n.\n", encoding="utf-8")
    adapter = _adapter(dsc, ws)
    adapter.prepare()  # marker matches: pure filesystem verification, no network
    status = (ws / "GT_STATUS.txt").read_text(encoding="utf-8")
    assert "ground_truth_present: false" in status  # honest — GT is gated, absent here
    gt_dir = ws / "gt"
    gt_dir.mkdir()
    (gt_dir / "gt_human_2.json").write_text("{}", encoding="utf-8")  # operator placed GT
    adapter.prepare()  # re-run refreshes the status honestly
    status = (ws / "GT_STATUS.txt").read_text(encoding="utf-8")
    assert "ground_truth_present: true" in status


def test_prepare_is_idempotent_at_pinned_commit(dsc: Any, tmp_path: Path) -> None:
    ws = _fake_workspace(tmp_path)
    (ws / ".upstream_commit").write_text(PINNED_COMMIT + "\n.\n", encoding="utf-8")
    adapter = _adapter(dsc, ws)
    adapter.prepare()  # marker matches: verification only, no fetch attempted
    assert (ws / ".upstream_commit").read_text().splitlines()[0] == PINNED_COMMIT


def test_manifest_json_is_complete_and_pinned() -> None:
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = {
        "benchmark_name",
        "benchmark_version",
        "benchmark_commit",
        "source",
        "license",
        "task_count",
        "evaluator_version",
        "environment",
        "prompt_versions",
        "seed",
    }
    assert required <= set(m)
    assert m["benchmark_commit"] == PINNED_COMMIT
    assert m["task_count"] == 222
    assert m["task_count_by_category"] == {
        "human_": 25,
        "csv_excel_": 20,
        "dl_": 10,
        "bcb*": 167,
    }


def test_no_benchmark_content_vendored_into_repo() -> None:
    """§23: upstream has no LICENSE — nothing from it may live in this repo."""
    d = REPO / "benchmarks" / "external" / "datascibench"
    allowed = {
        "adapter.py",
        "manifest.json",
        "README.md",
        "LICENSE_NOTES.md",
        "results",
        "logs",
        "__pycache__",  # bytecode cache; globally gitignored, not repo content
    }
    assert {p.name for p in d.iterdir()} <= allowed
    assert (REPO / ".gitignore").read_text(encoding="utf-8").find(
        "benchmarks/external/datascibench/.workspace/"
    ) != -1


def test_export_results_writes_manifest(
    dsc: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = _adapter(dsc, _fake_workspace(tmp_path))
    out = adapter.export_results()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["benchmark_name"] == "DataSciBench"
    assert payload["benchmark_commit"] == PINNED_COMMIT
