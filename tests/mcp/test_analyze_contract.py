"""§108 (Phase 4 target 3): one contract, four interfaces -- measured, not assumed.

The promise is "one runtime, many interfaces". Measured against the canonical shape
(``dsa_agent.state.AnalysisState``, 23 fields, serialized as ``state_json`` and read verbatim by the web
inspector and the SSE stream):

| interface | report text | critic verdicts |
| --- | --- | --- |
| canonical `AnalysisState` | ``report_markdown`` | ``validation_results`` |
| SDK `Analysis` projection | ``report_markdown`` | ``validation`` (renamed) |
| API `GET /analysis/{id}/report` | ``markdown`` (renamed) | ``validation`` (renamed) |
| MCP `analyze` output | ``report_markdown`` | **absent** |
| Jupyter | consumes the SDK object | inherits |

So three surfaces mirror the same concept under three names, and the MCP surface drops the verdicts
altogether -- a capability gap, not a spelling difference: an MCP client cannot see whether the evidence
critic passed, while the notebook, the SDK and the REST API all can. These tests close the gap and then
pin the naming so drift has to be declared instead of discovered.
"""

from __future__ import annotations

from typing import Any

import pytest
from dsa_mcp import adapter

from data_science_agent import Analysis, Evidence, Insight

#: Canonical field -> the name each interface uses for it. A surface may only use a name listed here,
#: so a fourth spelling of "the report text" fails the gate below rather than silently appearing.
ALIASES: dict[str, dict[str, str]] = {
    "report_markdown": {
        "sdk": "report_markdown",
        "api": "markdown",
        "mcp": "report_markdown",
        "canonical": "report_markdown",
    },
    "validation_results": {
        "sdk": "validation",
        "api": "validation",
        "mcp": "validation",
        "canonical": "validation_results",
    },
    "evidence": {
        "sdk": "evidence",
        "api": "evidence",
        "mcp": "evidence",
        "canonical": "evidence",
    },
    "insights": {
        "sdk": "insights",
        "api": "insights",
        "mcp": "insights",
        "canonical": "insights",
    },
    "artifacts": {
        "sdk": "artifacts",
        "api": "artifacts",
        "mcp": "artifacts",
        "canonical": "artifacts",
    },
    "tool_calls": {
        "sdk": "tool_calls",
        "api": "tool_calls",
        "mcp": "tool_calls",
        "canonical": "tool_calls",
    },
}

_VERDICTS = [{"check": "evidence_bundle", "passed": True, "message": "3 claims backed"}]


class _StubAgent:
    """Stand in for the real agent: the test is about the published shape, not about analysis."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def analyze(self, dataset: str, task: str, run_id: str | None = None) -> Analysis:
        return Analysis(
            run_id=run_id or "run-stub-1",
            status="COMPLETED",
            report_markdown="# Report",
            evidence=[
                Evidence(
                    id="E-1",
                    claim="sales grew",
                    source_type="sql",
                    source_id="c-1",
                    result={"rows": 3},
                    confidence=0.9,
                )
            ],
            insights=[Insight(id="I-1", finding="growth", evidence_ids=["E-1"])],
            artifacts=[],
            tool_calls=[{"call_id": "c-1", "tool": "run_sql", "status": "ok"}],
            validation=list(_VERDICTS),
            error=None,
            raw_state={},
        )


@pytest.fixture
def stub_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    import data_science_agent

    monkeypatch.setattr(data_science_agent, "Agent", _StubAgent)


async def _mcp_output() -> dict[str, Any]:
    result = await adapter.call_mcp_tool(
        "analyze", {"dataset": "sales.csv", "task": "did sales grow", "run_id": "run-stub-1"}
    )
    assert result.get("isError") is False, result
    return result["output"]


async def test_the_mcp_analyze_result_carries_the_critic_verdicts(stub_agent: None) -> None:
    """The gap this section closes: MCP was the only surface that hid the validation results."""
    output = await _mcp_output()

    assert output["validation"] == _VERDICTS, (
        "an MCP client could not see whether the evidence critic passed, while the SDK, REST API and "
        "notebook all could"
    )


async def test_every_key_the_mcp_result_emits_is_declared_in_its_schema(stub_agent: None) -> None:
    """A payload key the advertised schema omits is a key a validating client is entitled to drop."""
    output = await _mcp_output()
    declared = set(adapter._analyze_output_schema()["properties"])

    undeclared = set(output) - declared
    assert not undeclared, f"emitted but not declared: {sorted(undeclared)}"


def test_each_shared_concept_is_declared_under_the_mapped_mcp_name() -> None:
    """The alias map is only useful if it describes the real surface."""
    declared = set(adapter._analyze_output_schema()["properties"])

    for concept, names in ALIASES.items():
        assert names["mcp"] in declared, f"{concept}: schema lacks {names['mcp']}"


def test_no_interface_invents_a_fourth_name_for_a_shared_concept() -> None:
    """A new spelling of an existing concept must be declared in ALIASES, not discovered downstream."""
    import dataclasses

    from dsa_agent.state import AnalysisState

    canonical = set(AnalysisState.model_fields)
    sdk_names = {f.name for f in dataclasses.fields(Analysis)}
    sdk_extra = {"run_id", "status", "error", "raw_state"}
    mcp_extra = {"run_id", "status", "analysis_id", "error"}

    for concept, names in ALIASES.items():
        assert names["canonical"] in canonical, f"{concept} is not a canonical field"
        assert names["sdk"] in sdk_names, f"{concept}: the SDK has no {names['sdk']}"

    unmapped_sdk = sdk_names - {n["sdk"] for n in ALIASES.values()} - sdk_extra
    assert not unmapped_sdk, f"SDK fields with no canonical concept: {sorted(unmapped_sdk)}"

    unmapped_mcp = (
        set(adapter._analyze_output_schema()["properties"])
        - {n["mcp"] for n in ALIASES.values()}
        - mcp_extra
    )
    assert not unmapped_mcp, f"MCP declares keys with no canonical concept: {sorted(unmapped_mcp)}"
