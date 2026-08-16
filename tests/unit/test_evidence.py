from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dsa_evidence.graph import build_evidence_graph
from dsa_evidence.repro import build_experiment_json, build_notebook_skeleton, build_reproduce_sh
from dsa_evidence.validator import validate_evidence_graph
from dsa_tools import bootstrap, clear, get

# Tools


@pytest.mark.asyncio
async def test_create_evidence_and_validate() -> None:
    clear()
    bootstrap()
    from dsa_tools import get as get_tool

    ce = get_tool("create_evidence")
    r = await ce.run({"claim": "A is associated with B", "source_type": "statistical_test", "source_id": "TC-001", "result": {"r": 0.7}, "confidence": 0.8})
    assert r.status == "ok"
    assert r.output is not None
    assert r.output.evidence_id.startswith("E-")

    vr = get_tool("validate_result")
    r2 = await vr.run({"claim": "A is associated with B", "result": {"r": 0.7}, "check_type": "unsupported_claim"})
    assert r2.status == "ok"
    assert r2.output is not None
    assert r2.output.passed is True

    r3 = await vr.run({"claim": "X causes Y", "result": {"r": 0.5}, "check_type": "unsupported_claim"})
    assert r3.output is not None
    assert r3.output.passed is False


@pytest.mark.asyncio
async def test_save_artifact_and_generate_report() -> None:
    clear()
    bootstrap()
    from dsa_tools import get as get_tool

    sa = get_tool("save_artifact")
    r = await sa.run({"run_id": "run-test-evidence", "type": "report", "filename": "hello.md", "content": "# Hello\n", "metadata": {}})
    assert r.status == "ok"
    assert Path(r.output.path).exists()  # type: ignore[union-attr]

    gr = get_tool("generate_report")
    r2 = await gr.run({"run_id": "run-test-evidence-2", "title": "Test Report", "markdown": "# Test\n\nContent", "include_repro": True})
    assert r2.status == "ok"
    assert Path(r2.output.report_path).exists()  # type: ignore[union-attr]


def test_evidence_graph_and_validator() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        from dsa_agent.state import Evidence, Insight, ToolCallRecord

        ev = Evidence(id="E-001", claim="corr a vs b", source_type="statistical_test", source_id="TC-001", result={"r": 0.9}, confidence=0.8, validation_status="pending")
        ins = Insight(id="I-001", finding="a is associated with b", evidence_ids=["E-001"], limitation="assoc only")
        tc = ToolCallRecord(call_id="TC-001", tool="correlation_analysis", input={"x": "a"}, output={"r": 0.9}, status="ok")
        g = build_evidence_graph(run_id="run-1", dataset_id="ds1", dataset_path=str(p), evidence=[ev], insights=[ins], tool_calls=[tc])
        assert g.dataset_sha256 is not None
        assert len(g.edges) >= 2
        traced = g.trace_insight("I-001")
        assert "evidence" in traced
        assert traced["evidence"][0]["id"] == "E-001"
        vals = validate_evidence_graph(g)
        assert any(v["check"] == "insight_evidence" and v["passed"] for v in vals)
        assert any(v["check"] == "evidence_traceability" and v["passed"] for v in vals)

        # causal guard should fail
        ins2 = Insight(id="I-002", finding="X causes Y", evidence_ids=["E-001"])
        g2 = build_evidence_graph(run_id="run-1", dataset_id="ds1", dataset_path=str(p), evidence=[ev], insights=[ins2], tool_calls=[tc])
        vals2 = validate_evidence_graph(g2)
        assert any(v["check"] == "unsupported_claim" and not v["passed"] for v in vals2)


def test_repro_bundle() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        p = Path(td) / "t.csv"
        p.write_text("a,b\n1,2\n", encoding="utf-8")
        exp = build_experiment_json("run-123", str(p), "abc123", "hello", [], [], [], [], out)
        assert exp.exists()
        repro = build_reproduce_sh("run-123", str(p), "hello", out)
        assert repro.exists()
        nb = build_notebook_skeleton("run-123", out)
        assert nb.exists()
        assert nb.suffix == ".ipynb"
