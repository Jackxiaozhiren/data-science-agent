from __future__ import annotations

from typing import Any

import pytest

from dsa_agent.planner import plan_analysis
from dsa_agent.state import AnalysisPlan, AnalysisStep


class _FakeProvider:
    def __init__(self, plan: AnalysisPlan | None = None, error: Exception | None = None) -> None:
        self.plan = plan
        self.error = error

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        assert "Allowed tools" in prompt
        if self.error is not None:
            raise self.error
        assert self.plan is not None
        return self.plan


@pytest.mark.asyncio
async def test_default_planner_mode_remains_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DSA_LLM_MODE", raising=False)

    plan = await plan_analysis("summarize revenue", "/tmp/data.csv", ["region", "revenue"])

    assert plan.steps
    assert plan.steps[0].tool == "profile_dataset"


@pytest.mark.asyncio
async def test_real_planner_uses_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    model_plan = AnalysisPlan(
        objective="Analyze revenue",
        assumptions=[],
        steps=[
            AnalysisStep(
                id="s01",
                name="Profile",
                description="Profile the dataset",
                tool="profile_dataset",
                inputs={"path": "placeholder"},
            ),
            AnalysisStep(
                id="s02",
                name="Aggregate",
                description="Aggregate revenue by region",
                tool="run_sql",
                inputs={"dataset_path": "placeholder", "sql": "SELECT region FROM dataset"},
                depends_on=["s01"],
            ),
        ],
    )
    fake = _FakeProvider(plan=model_plan)
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: fake)

    plan = await plan_analysis("revenue by region", "/tmp/real.csv", ["region", "revenue"])

    assert [step.tool for step in plan.steps] == ["profile_dataset", "run_sql"]
    assert plan.steps[0].inputs["path"] == "/tmp/real.csv"
    assert plan.steps[1].inputs["dataset_path"] == "/tmp/real.csv"
    assert plan.required_tools == ["profile_dataset", "run_sql"]


@pytest.mark.asyncio
async def test_real_planner_does_not_silently_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.delenv("DSA_LLM_FALLBACK", raising=False)
    fake = _FakeProvider(error=RuntimeError("provider unavailable"))
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: fake)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await plan_analysis("analyze", "/tmp/data.csv", ["value"])


class _SequenceProvider:
    """First call returns schema-echo garbage, then a valid plan (qwen3:8b shape)."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        self.prompts.append(prompt)
        response = self.responses[len(self.prompts) - 1]
        if isinstance(response, Exception):
            raise response
        return response


def _valid_plan() -> AnalysisPlan:
    return AnalysisPlan(
        objective="Analyze revenue",
        assumptions=[],
        steps=[
            AnalysisStep(
                id="s01",
                name="Profile",
                description="Profile the dataset",
                tool="profile_dataset",
                inputs={"path": "placeholder"},
            ),
            AnalysisStep(
                id="s02",
                name="Aggregate",
                description="Aggregate revenue by region",
                tool="run_sql",
                inputs={"dataset_path": "placeholder", "sql": "SELECT region FROM dataset"},
                depends_on=["s01"],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_real_planner_retries_schema_echo_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    fake = _SequenceProvider(
        [
            RuntimeError("Model returned invalid structured output: steps missing"),
            _valid_plan(),
        ]
    )
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: fake)

    plan = await plan_analysis("revenue by region", "/tmp/real.csv", ["region", "revenue"])

    assert len(fake.prompts) == 2
    assert "was rejected" in fake.prompts[1]
    assert [step.tool for step in plan.steps] == ["profile_dataset", "run_sql"]


@pytest.mark.asyncio
async def test_real_planner_raises_loudly_after_second_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    fake = _SequenceProvider(
        [
            RuntimeError("Model returned invalid structured output: steps missing"),
            RuntimeError("Model returned invalid structured output: steps missing"),
        ]
    )
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: fake)

    with pytest.raises(Exception, match="steps|Field required|validation"):
        await plan_analysis("analyze", "/tmp/data.csv", ["value"])
    assert len(fake.prompts) == 2


@pytest.mark.asyncio
async def test_real_planner_heuristic_fallback_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setenv("DSA_LLM_FALLBACK", "heuristic")
    fake = _FakeProvider(error=RuntimeError("provider unavailable"))
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: fake)

    plan = await plan_analysis("analyze", "/tmp/data.csv", ["value"])

    assert plan.steps[0].tool == "profile_dataset"
