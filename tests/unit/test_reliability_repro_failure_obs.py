from __future__ import annotations


def test_reproducibility_levels() -> None:
    from dsa_evidence.reproducibility import compare_runs

    orig = {
        "user_query": "q",
        "dataset_path": "/tmp/a.csv",
        "dataset_id": "a",
        "dataset_sha256": "abc",
        "tool_calls": [{"tool": "run_sql"}],
        "insights": [{"finding": "hi"}],
        "evidence": [{"id": "E-1"}],
        "environment": {"python_version": "3.12.0"},
    }
    fresh_same = dict(orig)
    s = compare_runs(orig, fresh_same)
    assert s.score >= 0.9 and s.level in ("L4", "L5")
    fresh_diff_traj = {**orig, "tool_calls": [{"tool": "run_python"}]}
    s2 = compare_runs(orig, fresh_diff_traj)
    assert s2.tool_trajectory_match is False


def test_failure_taxonomy() -> None:
    from dsa_evidence.failure_taxonomy import (
        classify_tool_error,
        from_validation_results,
    )

    assert classify_tool_error("run_sql", "Disallowed SQL pattern") == "F03"
    assert classify_tool_error("run_python", "Import denied: os") == "F04"
    logs = from_validation_results(
        "run-1",
        [
            {"check": "unsupported_claim", "passed": False, "message": "cause without evidence"},
            {"check": "evidence_coverage", "passed": True, "message": "ok"},
        ],
    )
    assert len(logs) == 1 and logs[0].failure_code == "F09"


def test_observability_trace() -> None:
    from dsa_evidence.observability import Span, Trace

    t = Trace(trace_id="t-1", run_id="run-1")
    t.add_span(Span(name="planner", kind="planner", duration_ms=10))
    t.add_span(Span(name="run_sql", kind="tool", duration_ms=5))
    t.add_span(Span(name="critic", kind="critic", duration_ms=3))
    t.finalize()
    assert "total_duration_ms" in t.metrics
    assert t.metrics["planner_duration_ms"] == 10.0
