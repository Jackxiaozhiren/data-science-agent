from __future__ import annotations

from pathlib import Path

import pytest

from dsa_agent.critic import evidence_critic_enabled
from dsa_agent.state import AnalysisPlan


def test_evidence_critic_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSA_EVIDENCE_CRITIC", raising=False)

    assert evidence_critic_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "FALSE", "off", "No"])
def test_evidence_critic_can_be_disabled(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("DSA_EVIDENCE_CRITIC", value)

    assert evidence_critic_enabled() is False


@pytest.mark.asyncio
async def test_run_analysis_skips_critic_when_ablation_is_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import dsa_agent.graph as graph

    monkeypatch.setenv("DSA_EVIDENCE_CRITIC", "off")

    async def fake_plan_analysis(
        user_query: str, dataset_path: str | None, columns: list[str]
    ) -> AnalysisPlan:
        return AnalysisPlan(objective=user_query, steps=[])

    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("critic_validate must not run when the critic ablation is off")

    def fake_write_report_artifacts(state: object) -> dict[str, str]:
        report = tmp_path / "report.md"
        experiment = tmp_path / "experiment.json"
        report.write_text("# report\n", encoding="utf-8")
        experiment.write_text("{}\n", encoding="utf-8")
        return {"markdown": str(report), "experiment": str(experiment)}

    monkeypatch.setattr(graph, "plan_analysis", fake_plan_analysis)
    monkeypatch.setattr(graph, "critic_validate", fail_if_called)
    monkeypatch.setattr(graph, "build_markdown_report", lambda state: "# report\n")
    monkeypatch.setattr(graph, "write_report_artifacts", fake_write_report_artifacts)

    state = await graph.run_analysis(
        dataset_path=None,
        dataset_id="critic-ablation-test",
        user_query="Summarize this dataset",
        run_id="critic-ablation-test",
    )

    assert state.status.value == "COMPLETED"
    assert not any(
        result.check in {"evidence_coverage", "tool_errors"} for result in state.validation_results
    )
    assert any(
        message.agent == "critic" and "disabled for evaluation ablation" in message.content
        for message in state.agent_messages
    )
