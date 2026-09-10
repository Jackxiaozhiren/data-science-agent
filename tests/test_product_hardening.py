from __future__ import annotations

import asyncio

import polars as pl

from dsa_agent import planner
from dsa_agent.critic import critic_validate
from dsa_agent.state import AnalysisState, AnalysisStatus, Evidence, ToolCallRecord
from dsa_tools.tools.feature_importance import FeatureImportanceInput, FeatureImportanceTool


def test_semantic_planner_targets_outcome_and_group(monkeypatch) -> None:
    columns = [
        "campaign_group",
        "revenue_proxy",
        "ad_spend",
        "customers",
        "discount_rate",
        "conversion_rate",
        "cost",
        "revenue",
    ]
    numeric = [c for c in columns if c != "campaign_group"]
    monkeypatch.setattr(planner, "_numeric_columns", lambda _: numeric)
    monkeypatch.setattr(planner, "_has_time_data", lambda _: False)

    plan = planner.heuristics_plan(
        "Explain which features are most important for revenue, test whether the main associations "
        "are statistically significant, and assess the impact of campaign_group on the outcome.",
        "/tmp/fake.csv",
        columns,
    )
    steps = {step.tool: step for step in plan.steps}

    assert steps["feature_importance"].inputs["target"] == "revenue"
    assert steps["causal_check"].inputs["treatment"] == "campaign_group"
    assert steps["causal_check"].inputs["outcome"] == "revenue"
    assert steps["hypothesis_test"].inputs["group_col"] == "campaign_group"
    assert steps["hypothesis_test"].inputs["value_col"] == "revenue"
    assert steps["correlation_analysis"].inputs["x"] == "revenue"
    assert steps["correlation_analysis"].inputs["y"] == "ad_spend"


def test_feature_importance_excludes_exact_target_copy(tmp_path) -> None:
    rows = 30
    revenue = [100_000 + i * 2_000 for i in range(rows)]
    df = pl.DataFrame(
        {
            "campaign_group": ["A" if i % 2 == 0 else "B" for i in range(rows)],
            "revenue_proxy": revenue,
            "ad_spend": [10_000 + i * 300 for i in range(rows)],
            "customers": [800 + i * 15 for i in range(rows)],
            "revenue": revenue,
        }
    )
    path = tmp_path / "acceptance.csv"
    df.write_csv(path)

    output = asyncio.run(
        FeatureImportanceTool().execute(
            FeatureImportanceInput(dataset_path=str(path), target="revenue")
        )
    )

    assert "revenue_proxy" in output.excluded_features
    assert all(item["feature"] != "revenue_proxy" for item in output.importances)


def test_critic_finalizes_evidence_status() -> None:
    state = AnalysisState(
        run_id="run-test",
        dataset_id="dataset-test",
        user_query="test",
        status=AnalysisStatus.VALIDATION,
        tool_call_count=1,
        tool_calls=[
            ToolCallRecord(
                call_id="TC-ok",
                tool="correlation_analysis",
                input={},
                output={"r": 0.5},
                status="ok",
            )
        ],
        evidence=[
            Evidence(
                id="E-1",
                claim="supported",
                source_type="statistical_test",
                source_id="TC-ok",
                result={"r": 0.5},
                confidence=0.8,
            )
        ],
    )

    critic_validate(state)

    assert state.evidence[0].validation_status == "verified"
