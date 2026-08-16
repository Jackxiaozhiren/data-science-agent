from __future__ import annotations


def test_trajectory_and_retry_quality() -> None:
    from dsa_agent.trajectory import (
        AgentTrajectory,
        Checkpoint,
        NodeExecution,
        RetryEvent,
        ToolExecution,
        from_analysis_state,
    )

    traj = AgentTrajectory(
        run_id="run-1",
        nodes=[
            NodeExecution(node="plan", duration_ms=10),
            NodeExecution(node="exec_step", duration_ms=20),
        ],
        tool_calls=[
            ToolExecution(call_id="TC-1", tool="run_sql", status="ok", duration_ms=5),
            ToolExecution(call_id="TC-2", tool="run_sql", status="error", duration_ms=5),
        ],
        retries=[
            RetryEvent(attempt=1, trigger="evidence_coverage", success=True),
            RetryEvent(attempt=2, trigger="tool_error", success=False),
        ],
        checkpoints=[Checkpoint(id="cp-1", node="exec_step", state_keys=["tool_calls"])],
        final_state={"status": "COMPLETED"},
    )
    assert traj.tool_efficiency_score(necessary=1) == 0.5
    q = traj.retry_quality()
    assert q["retry_count"] == 2 and q["useful"] == 1
    # from_analysis_state adaptor
    fake_state = {
        "run_id": "r2",
        "tool_calls": [{"call_id": "TC-x", "tool": "run_sql", "status": "ok", "duration_ms": 1}],
        "agent_messages": [{"agent": "planner", "content": "hi"}],
        "retry_count": 1,
        "status": "COMPLETED",
    }
    t2 = from_analysis_state(fake_state)
    assert t2.run_id == "r2" and len(t2.tool_calls) == 1


def test_critic_effectiveness_stub() -> None:
    """Critic with/without comparison is via EvaluationResultV2 comparison in research runner; sanity check here."""
    from dsa_agent.critic import check_unsupported_claims
    from dsa_agent.state import AnalysisState

    s = AnalysisState(run_id="r", dataset_id="ds", user_query="q")
    s.tool_calls = []  # type: ignore[attr-defined]
    s.insights = []  # type: ignore[assignment]
    from dsa_agent.state import Insight

    s.insights.append(Insight(id="I-1", finding="x causes y", evidence_ids=[]))
    r = check_unsupported_claims(s.insights)
    assert not r.passed
