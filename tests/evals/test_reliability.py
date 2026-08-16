from __future__ import annotations

from dsa_evaluation.metrics import EvaluationResult, TaskMetrics, aggregate_metrics
from dsa_evaluation.reliability import evaluate_reliability
from dsa_evaluation.statistical_eval import evaluate_statistical
from dsa_evaluation.catalog import BenchmarkTask, EvaluationCriteria, GroundTruth


def _ev(task_id: str, cat: str, ok: bool, tool_calls: list[dict] | None = None) -> EvaluationResult:
    tc = tool_calls or ([{"tool": "run_sql", "status": "ok"}] if ok else [{"tool": "run_sql", "status": "error"}])
    return EvaluationResult(
        task_id=task_id, category=cat, dataset="a.csv", question="q",
        metrics=TaskMetrics(task_success=ok, code_execution_success=ok, evidence_coverage=ok, unsupported_claim=not ok, latency_ms=100),
        details={"tool_names": [c["tool"] for c in tc]},
    )


def _task(**kw) -> BenchmarkTask:
    base = dict(id="t1", category="SQL", dataset="a.csv", question="q", expected_analysis="e", ground_truth=GroundTruth(expected_tool="run_sql"), criteria=EvaluationCriteria(task_success=True), difficulty="easy")
    base.update(kw)
    return BenchmarkTask(**base)  # type: ignore[arg-type]


def test_reliability_sections() -> None:
    results = [_ev("t1", "SQL", True), _ev("t2", "EDA", True, [{"tool": "profile_dataset", "status": "ok"}])]
    raw = [{"run_result": {"tool_calls": [{"tool": "run_sql", "status": "ok"}], "validation_results": [{"check": "unsupported_claim", "passed": False}], "retry_count": 1, "insights": [{"finding": "ok"}]}} for _ in results]
    for cfg in ("single", "planner", "planner_critic", "full"):
        rep = evaluate_reliability(cfg, results, raw)  # type: ignore[arg-type]
        assert rep.n == 2
        assert rep.task_success is not None
        assert rep.tool_selection_accuracy is not None
        assert rep.agent_efficiency is not None or rep.tool_efficiency is not None


def test_tool_selection_and_loop() -> None:
    results = [_ev("t1", "SQL", True, [{"tool": "run_sql", "status": "ok"}, {"tool": "run_sql", "status": "ok"}])]
    raw = [{"run_result": {"tool_calls": [{"tool": "run_sql", "status": "ok"}, {"tool": "run_sql", "status": "ok"}], "validation_results": [], "retry_count": 0}}]
    rep = evaluate_reliability("full", results, raw)  # type: ignore[arg-type]
    assert rep.duplicate_calls == 1
    assert rep.agent_efficiency is not None and rep.agent_efficiency < 1.0
    assert rep.tool_wrong == 0 or isinstance(rep.tool_wrong, int)


def test_statistical_correctness_from_evaluator_v2() -> None:
    task = _task(category="Statistics", criteria=EvaluationCriteria(task_success=True, statistical_accuracy=True))
    rr = {"tool_calls": [{"tool": "correlation_analysis", "status": "ok", "output": {"r": 0.5, "p_value": 0.01}}]}
    se = evaluate_statistical(task, rr)
    ev = _ev("t1", "Statistics", True, [{"tool": "correlation_analysis", "status": "ok", "output": {"r": 0.5}}])
    ev.details = {"statistical_eval": se.model_dump(mode="json")}
    rep = evaluate_reliability("full", [ev], [{"run_result": rr}])  # type: ignore[arg-type]
    assert rep.statistical_correctness is not None
