"""V4.3 Phase B (W2 §15-21) — external benchmark adapter architecture tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dsa_evaluation.external_benchmark import (
    AgentBackedRunner,
    AgentTaskView,
    ExternalBenchmarkAdapter,
    ExternalBenchmarkManifest,
    ExternalEvaluation,
    ExternalRun,
    ExternalTask,
    RunConfig,
    TaskOutcome,
    assert_gold_isolation,
    classify_outcome,
    dataset_sha256,
)


class FakeAdapter:
    """Minimal adapter used to verify the §17 protocol shape."""

    name = "fakebench"
    version = "0.1.0"

    def __init__(self, results_dir: Path) -> None:
        self._dir = results_dir
        self._tasks = [
            ExternalTask(
                task_id="fb-1",
                question="What is the mean of x?",
                dataset_path="datasets/fb1.csv",
                benchmark_name="fakebench",
                benchmark_task_ref="fakebench#1",
                permitted_tools=("profile", "run_sql"),
                gold={"mean": 3.14},
            ),
            ExternalTask(
                task_id="fb-2",
                question="Train a transformer from scratch",
                dataset_path="datasets/fb2.csv",
                benchmark_name="fakebench",
                supported=False,
                unsupported_reason="no GPU training surface in DSA",
            ),
        ]

    def prepare(self) -> None:  # pragma: no cover - trivial
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_tasks(self) -> list[ExternalTask]:
        return list(self._tasks)

    def run_task(self, task: ExternalTask, config: RunConfig) -> ExternalRun:
        view = task.agent_view()
        assert_gold_isolation(view)
        if not task.supported:
            return ExternalRun(
                task_id=task.task_id,
                benchmark_name=self.name,
                agent_view=view,
                status="skipped_unsupported",
                error=task.unsupported_reason,
            )
        return ExternalRun(
            task_id=task.task_id,
            benchmark_name=self.name,
            agent_view=view,
            status="completed",
            run_id="run-fb1",
            report="mean is 3.14",
            evidence=[{"claim": "mean x = 3.14", "source_id": "TC-1"}],
            tool_calls=[{"tool": "profile", "ok": True}],
        )

    def evaluate(self, run: ExternalRun) -> ExternalEvaluation:
        gold = {"fb-1": {"mean": 3.14}}[run.task_id]  # gold stays inside the adapter
        ok = "3.14" in (run.report or "")
        return ExternalEvaluation(
            task_id=run.task_id,
            benchmark_name=self.name,
            outcome=TaskOutcome.PASSED if ok else TaskOutcome.FAILED,
            score=1.0 if ok else 0.0,
            evaluator="fakebench-official",
            evaluator_version="1.0",
            details={"tolerance": 1e-6, "gold_ref": bool(gold)},
        )

    def export_results(self) -> Path:
        out = self._dir / "results.json"
        out.write_text(
            json.dumps({"benchmark": self.name, "version": self.version}), encoding="utf-8"
        )
        return out


@pytest.fixture()
def adapter(tmp_path: Path) -> FakeAdapter:
    return FakeAdapter(tmp_path / "results")


def test_adapter_satisfies_protocol(adapter: FakeAdapter) -> None:
    assert isinstance(adapter, ExternalBenchmarkAdapter)


def test_agent_view_drops_gold_and_isolation_guard(adapter: FakeAdapter) -> None:
    task = adapter.list_tasks()[0]
    assert task.gold, "fixture must carry gold material"
    view = task.agent_view()
    assert isinstance(view, AgentTaskView)
    assert "3.14" not in view.model_dump_json()
    assert_gold_isolation(view)
    # Structural block: gold keys cannot even be constructed into the view.
    with pytest.raises(ValidationError, match="solution"):
        AgentTaskView(task_id="t", question="q", dataset_path="d", solution="leak")
    # Runtime tripwire: payloads that already carry a gold key are rejected.
    with pytest.raises(ValueError, match="gold leakage firewall"):
        assert_gold_isolation('{"task_id": "t", "gold": {"mean": 3.14}}')


def test_unsupported_task_is_reported_not_failed(adapter: FakeAdapter) -> None:
    config = RunConfig(model="deterministic", prompt_version="p1")
    supported, unsupported = adapter.list_tasks()
    run_ok = adapter.run_task(supported, config)
    run_un = adapter.run_task(unsupported, config)
    assert classify_outcome(run_ok, adapter.evaluate(run_ok)) is TaskOutcome.PASSED
    assert classify_outcome(run_un) is TaskOutcome.UNSUPPORTED
    assert adapter.list_tasks()[1].unsupported_reason  # §26: reason is recorded


def test_completed_but_unevaluated_run_is_not_a_pass(adapter: FakeAdapter) -> None:
    config = RunConfig()
    run = adapter.run_task(adapter.list_tasks()[0], config)
    assert classify_outcome(run) is TaskOutcome.FAILED


def test_execution_error_classification() -> None:
    run = ExternalRun(
        task_id="t",
        benchmark_name="b",
        agent_view=AgentTaskView(task_id="t", question="q", dataset_path="d"),
        status="error",
        error="sandbox timeout",
    )
    assert classify_outcome(run) is TaskOutcome.EXECUTION_ERROR


def test_manifest_covers_all_required_fields(tmp_path: Path) -> None:
    manifest = ExternalBenchmarkManifest(
        benchmark_name="fakebench",
        benchmark_version="0.1.0",
        benchmark_commit="abc1234",
        source="https://example.com/fakebench",
        license="MIT",
        task_count=2,
        dataset_hashes={"fb1.csv": "a" * 64},
        evaluator_version="1.0",
        environment={"python": "3.12"},
        dsa_commit="c8903d4",
        dsa_version="4.2.10",
        model="deterministic",
        prompt_versions={"system": "p1"},
        tool_versions={"polars": "1.0"},
        seed=42,
    )
    path = manifest.write(tmp_path / "manifest.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "benchmark_name",
        "benchmark_version",
        "benchmark_commit",
        "source",
        "license",
        "task_count",
        "dataset_hashes",
        "evaluator_version",
        "environment",
        "dsa_commit",
        "dsa_version",
        "model",
        "prompt_versions",
        "tool_versions",
        "seed",
    }
    assert required <= set(loaded)


def test_export_results_returns_path(adapter: FakeAdapter) -> None:
    adapter.prepare()
    adapter.prepare()  # §17: prepare must be idempotent
    out = adapter.export_results()
    assert isinstance(out, Path)
    assert json.loads(out.read_text(encoding="utf-8"))["benchmark"] == "fakebench"


def test_dataset_sha256(tmp_path: Path) -> None:
    ds = tmp_path / "d.csv"
    ds.write_bytes(b"a,b\n1,2\n")
    assert dataset_sha256(ds) == dataset_sha256(ds)
    assert len(dataset_sha256(ds)) == 64


def test_agent_backed_runner_skips_unsupported_and_preserves_firewall() -> None:
    task = ExternalTask(
        task_id="u1",
        question="q",
        dataset_path="d",
        benchmark_name="b",
        supported=False,
        unsupported_reason="not applicable",
        gold={"answer": 1},
    )

    class Boom:
        def analyze_sync(self, *_a: object, **_k: object) -> object:  # pragma: no cover
            raise AssertionError("agent must not run for unsupported tasks")

    run = AgentBackedRunner(agent_factory=Boom).run(task, RunConfig())
    assert classify_outcome(run) is TaskOutcome.UNSUPPORTED
    assert_gold_isolation(run.agent_view)


def test_agent_backed_runner_maps_completed_result() -> None:
    class FakeResult:
        status = "COMPLETED"
        run_id = "run-x"
        elapsed_s = 0.5

    class FakeAgent:
        def analyze_sync(self, dataset: str, question: str) -> FakeResult:
            assert dataset == "d.csv" and question == "q?"
            return FakeResult()

    task = ExternalTask(
        task_id="t1",
        question="q?",
        dataset_path="d.csv",
        benchmark_name="b",
        gold={"answer": 42},
    )
    run = AgentBackedRunner(agent_factory=FakeAgent).run(task, RunConfig())
    assert run.status == "COMPLETED"
    assert run.run_id == "run-x"
    assert run.latency_s == 0.5
    assert_gold_isolation(run.agent_view)


def test_agent_backed_runner_converts_dataclass_evidence_to_dicts() -> None:
    """Runner must tolerate dataclass Evidence objects (as returned by the SDK),
    converting them to plain dicts for the JSON-safe ExternalRun (§18/§48)."""
    from dataclasses import dataclass, field as dc_field

    @dataclass
    class FakeEvidence:
        id: str
        claim: str
        source_id: str
        result: dict = dc_field(default_factory=dict)

    class FakeResult:
        status = "COMPLETED"
        run_id = "run-y"
        report_markdown = "# Report"
        tool_calls = [{"tool": "profile_dataset", "ok": True}]
        evidence = [FakeEvidence(id="ev-1", claim="mean x = 3.14", source_id="tc-1")]

    class FakeAgent:
        def analyze_sync(self, dataset: str, question: str) -> FakeResult:
            return FakeResult()

    task = ExternalTask(task_id="t2", question="q?", dataset_path="d.csv", benchmark_name="b")
    run = AgentBackedRunner(agent_factory=FakeAgent).run(task, RunConfig())
    assert run.report == "# Report"
    assert run.tool_calls == [{"tool": "profile_dataset", "ok": True}]
    assert run.evidence == [
        {"id": "ev-1", "claim": "mean x = 3.14", "source_id": "tc-1", "result": {}}
    ]
    assert_gold_isolation(run.agent_view)
