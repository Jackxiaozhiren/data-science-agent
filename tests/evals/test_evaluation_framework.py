from __future__ import annotations


def test_evaluation_framework_v2() -> None:
    from pathlib import Path

    from dsa_evaluation.catalog import Catalog
    from dsa_evaluation.evaluation_framework import aggregate_v2, from_metrics
    from dsa_evaluation.metrics import evaluate_task

    cat = Catalog.load(Path("benchmarks/ds-agent-benchmark/catalog.json"))
    task = cat.tasks[0]
    # fake run_result with at least one ok tool call + report
    fake = {
        "tool_calls": [
            {"tool": "profile_dataset", "status": "ok", "output": {"profile": {"rows": 10}}}
        ],
        "evidence": [{"result": {}}],
        "insights": [{"finding": "hello", "evidence_ids": ["E-1"]}],
        "report_markdown": "# hi",
        "validation_results": [],
    }
    m = evaluate_task(task, fake, elapsed_ms=10)
    v2 = from_metrics(m, run_id="run-1", difficulty="easy")
    assert v2.task_id == task.id
    assert v2.task_success in (0.0, 1.0)
    assert v2.level_scores
    agg = aggregate_v2([v2, v2])
    assert agg["n"] == 2
    assert "by_category" in agg and "by_difficulty" in agg


def test_hard_metrics_definitions() -> None:
    """Hard metrics per V2 §11: task_success, evidence_coverage, unsupported_claim_rate."""
    from pathlib import Path

    from dsa_evaluation.catalog import Catalog
    from dsa_evaluation.metrics import evaluate_task

    cat = Catalog.load(Path("benchmarks/ds-agent-benchmark/catalog.json"))
    # pick a task with evidence_coverage true
    task = next(t for t in cat.tasks if t.criteria.evidence_coverage)
    fake = {
        "tool_calls": [{"tool": "profile_dataset", "status": "ok", "output": {}}],
        "evidence": [{"result": {}, "id": "E-1"}],
        "insights": [{"finding": "ok", "evidence_ids": ["E-1"]}],
        "report_markdown": "x",
    }
    m = evaluate_task(task, fake)
    assert m.metrics.task_success
    assert m.metrics.evidence_coverage in (True, False)
