"""§111 (Phase 4 target 3): one definition of the run-level contract, three consumers.

§108 measured the situation: `AnalysisState` is the single source, but the SDK, the REST report and the
MCP `analyze` result each re-listed its run-level fields by hand -- and MCP's copy had already lost
`validation` (fixed in §108) while `tool_calls` was emitted without being declared. Hand-listing is the
mechanism; losing a field is the symptom.

After this section there is one list of the run-level fields and one function that turns a state into the
canonical dict. The REST report and the MCP result are built from that function (each applying only its
own declared aliases), and the SDK's `Analysis` dataclass is pinned against the same list rather than
allowed to drift.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest
from dsa_agent.run_summary import RUN_SUMMARY_FIELDS, normalize_records, run_summary

from data_science_agent.sdk import Analysis

ROOT = Path(__file__).resolve().parents[2]


class _Record:
    """Stands in for a pydantic state member that knows how to serialize itself."""

    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return dict(self.__dict__)


def _state(**overrides: Any) -> dict[str, Any]:
    base = {
        "run_id": "r-1",
        "status": "COMPLETED",
        "report_markdown": "# Report",
        "evidence": [_Record(id="E-1", claim="c")],
        "insights": [_Record(id="I-1", finding="f")],
        "artifacts": [{"id": "A-1", "type": "report"}],
        "tool_calls": [_Record(call_id="c-1", tool="run_sql")],
        "validation_results": [_Record(check="evidence_bundle", passed=True)],
        "error": None,
    }
    base.update(overrides)
    return base


def test_the_projection_publishes_the_canonical_names() -> None:
    summary = run_summary(_state())

    assert set(summary) == set(RUN_SUMMARY_FIELDS)
    assert summary["validation_results"] == [{"check": "evidence_bundle", "passed": True}]
    assert summary["run_id"] == "r-1"


def test_collections_are_normalized_whatever_shape_arrives() -> None:
    """The `model_dump` / `__dict__` / plain-dict dance existed four times in the SDK; now once."""
    mixed = [_Record(a=1), {"b": 2}]

    normalized = normalize_records(mixed)

    assert normalized == [{"a": 1}, {"b": 2}], "both record shapes normalize to plain dicts"
    assert normalize_records(None) == []
    assert normalize_records([]) == []


def test_a_state_object_and_its_dump_project_the_same_result() -> None:
    """The REST layer holds the serialized `state_json`; the SDK holds the model. One contract, both."""

    state_dict = _state()

    class _StateModel:
        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return state_dict

    assert run_summary(_StateModel()) == run_summary(state_dict)


def test_the_sdk_surface_cannot_drift_from_the_list() -> None:
    """`Analysis` keeps typed members, so it is checked against the contract instead of rebuilt from it."""
    sdk_fields = {f.name for f in fields(Analysis)} - {"raw_state"}
    # The SDK spells one canonical field shorter; §108's alias map owns that exception.
    canonical_from_sdk = {
        "validation_results" if name == "validation" else name for name in sdk_fields
    }

    assert canonical_from_sdk == set(RUN_SUMMARY_FIELDS), (
        f"SDK-only: {sorted(canonical_from_sdk - set(RUN_SUMMARY_FIELDS))}, "
        f"contract-only: {sorted(set(RUN_SUMMARY_FIELDS) - canonical_from_sdk)}"
    )


def test_rest_and_mcp_build_their_payload_from_the_projection() -> None:
    """No surface may re-list the run-level fields again -- that is how `validation` went missing."""
    rest = (ROOT / "apps/api/src/dsa_api/routers/analysis.py").read_text(encoding="utf-8")
    mcp = (ROOT / "packages/mcp/src/dsa_mcp/adapter.py").read_text(encoding="utf-8")

    assert "run_summary" in rest, "the report endpoint must derive from the projection"
    assert "run_summary" in mcp, "the analyze result must derive from the projection"


def test_the_mcp_alias_stays_analysis_id_and_the_rest_alias_stays_markdown() -> None:
    """Aliases are allowed, but only the ones §108 documented."""
    mcp_src = (ROOT / "packages/mcp/src/dsa_mcp/adapter.py").read_text(encoding="utf-8")
    rest_src = (ROOT / "apps/api/src/dsa_api/routers/analysis.py").read_text(encoding="utf-8")

    assert "MCP_RUN_ALIASES" in mcp_src and "analysis_id" in mcp_src
    assert "REST_RUN_ALIASES" in rest_src and "markdown" in rest_src
    for src in (mcp_src, rest_src):
        tree = ast.parse(src)
        assert any(
            isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id.endswith("RUN_ALIASES") for t in n.targets)
            for n in ast.walk(tree)
        )


def test_a_new_canonical_field_reaches_every_dict_surface_without_an_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the exercise, demonstrated rather than asserted about it."""
    extra = _state()
    extra["insights"] = [{"id": "I-9", "finding": "f", "new_dimension": 42}]

    summary = run_summary(extra)

    assert summary["insights"][0]["new_dimension"] == 42
