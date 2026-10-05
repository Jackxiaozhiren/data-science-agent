"""§115, Phase 4 target 2 seam #7: report composition lives outside the graph module.

``dsa_agent.langgraph_graph._node_report`` was 179 lines -- the largest function in the shipped tree --
doing six things inside one ``async def``: rebuilding the state model twice, rendering markdown,
persisting artifacts, building the reproducibility bundle, merging its validation results, and shaping
the graph's return envelope. That is report composition sitting inside graph orchestration, and it is
the same boundary §105 drew around ``graph.py``.

Red on arrival: `dsa_agent.reporting` does not exist yet.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT_SRC = REPO / "packages" / "agent" / "src" / "dsa_agent"


def _func_source(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name]
    assert found, f"{path.name} no longer defines `async def {name}`"
    return found[0]


def test_compose_report_lives_in_its_own_module() -> None:
    reporting = AGENT_SRC / "reporting.py"
    assert reporting.is_file(), "dsa_agent.reporting does not exist"
    tree = ast.parse(reporting.read_text(encoding="utf-8"))
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}
    assert "compose_report" in names, sorted(names)


def test_the_graph_node_is_an_adapter_not_a_second_implementation() -> None:
    """`_node_report` must be one call, or the split produced two places to change."""
    node = _func_source(AGENT_SRC / "langgraph_graph.py", "_node_report")
    body = node.body
    assert len(body) == 1, f"the node grew to {len(body)} statements; it should delegate"
    stmt = body[0]
    assert isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call), ast.dump(stmt)
    called = stmt.value.func
    name = getattr(called, "id", None) or getattr(called, "attr", None)
    assert name == "compose_report", f"the node returns a call to {name!r}, not compose_report"
    positional = [a.id for a in stmt.value.args if isinstance(a, ast.Name)]
    assert positional == ["state"], ast.dump(stmt.value)


def test_composition_does_not_import_the_graph_module() -> None:
    """Dependency direction: the report builder must not reach back into the orchestrator."""
    tree = ast.parse((AGENT_SRC / "reporting.py").read_text(encoding="utf-8"))
    modules = {(n.module or "") for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    offenders = [m for m in modules if m.endswith("langgraph_graph")]
    assert not offenders, f"reporting.py imports the graph: {offenders}"


def test_a_failed_report_write_still_reports_completed(monkeypatch) -> None:
    """GREEN ON ARRIVAL. The verdict shape today, encoded as a test rather than left unnoticed.

    Measured on 2026-10-05: forcing ``write_report_artifacts`` to raise makes the node return
    ``status: COMPLETED`` with ``error: 'Report write failed: ...'`` and no artifacts, and the MCP
    adapter publishes that error field (``dsa_mcp/adapter.py:274``) beside the COMPLETED status.
    Blast radius measured on this tree: 0 of 50 benchmark runs carry an ``error`` field, because the
    source layout puts ``artifacts/`` under a writable repo root -- the branch is live wherever the
    install is read-only, which is filed as D-L4-08 together with D-L4-07 (the artifact root is
    derived from ``__file__``'s great-grandparent directory, so a wheel install writes reports into
    the interpreter's own tree).

    This assertion is deliberately a pin on the *current*, known-wrong shape: fixing the verdict must
    turn this red rather than slip through as an unobservable change.
    """
    from dsa_agent import report as dsa_report

    def boom(*args, **kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(dsa_report, "write_report_artifacts", boom)

    from dsa_agent.langgraph_graph import _node_report

    out = asyncio.run(
        _node_report(
            {
                "run_id": "seam115-verdict",
                "dataset_id": "ds",
                "dataset_path": None,
                "user_query": "q",
                "objective": "o",
                "plan": [],
                "analysis_state": {
                    "tool_calls": [],
                    "evidence": [],
                    "insights": [],
                    "validation_results": [],
                },
                "messages": [],
            }
        )
    )
    assert out["status"] == "COMPLETED", out
    assert out["analysis_state"]["status"] == "COMPLETED", out
    assert "Report write failed" in out["analysis_state"]["error"], out


def test_the_success_envelope_is_the_node_own_shape(monkeypatch, tmp_path) -> None:
    """Keys the graph depends on, asserted rather than assumed: the seam must not change them.

    Artifact writing is redirected at the same patch point the existing graph tests use, so this
    stays hermetic; the real end-to-end equivalence is what §115's capture differential proves.
    """
    from dsa_agent import report as dsa_report

    md = tmp_path / "report.md"
    md.write_text("# Report\n", encoding="utf-8")

    def fake_write(state, out_dir=None):
        return {"markdown": str(md), "experiment": str(md)}

    monkeypatch.setattr(dsa_report, "write_report_artifacts", fake_write)

    from dsa_agent.langgraph_graph import _node_report

    out = asyncio.run(
        _node_report(
            {
                "run_id": "seam115-ok",
                "dataset_id": "ds",
                "dataset_path": None,
                "user_query": "q",
                "objective": "o",
                "plan": [],
                "analysis_state": {
                    "tool_calls": [],
                    "evidence": [],
                    "insights": [],
                    "validation_results": [],
                },
                "messages": [],
            }
        )
    )
    assert set(out) == {"analysis_state", "status", "messages"}, sorted(out)
    assert out["status"] == "COMPLETED"
    assert set(out["analysis_state"]) >= {
        "report_markdown",
        "run_id",
        "status",
        "artifacts",
    }, sorted(out["analysis_state"])
