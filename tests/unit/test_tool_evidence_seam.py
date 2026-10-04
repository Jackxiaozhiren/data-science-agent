"""§105 (Phase 4 target 2): the evidence-construction seam out of ``dsa_agent.graph``.

``graph.py`` held two jobs: orchestrating a run and deciding what a tool result proves. The second is
now ``dsa_agent.tool_evidence.build_tool_evidence``. The move is behaviour-preserving -- a 29-case
differential against the pre-split function came back byte-identical -- so these tests do not re-check
formatting. They police the *boundary*: that the mapping lives in one module, that both orchestration
engines consume that one definition, and that the seam has no dependencies to drag an agent into a unit
test.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from dsa_agent.graph import build_tool_evidence as graph_binding
from dsa_agent.langgraph_graph import build_tool_evidence as langgraph_binding
from dsa_agent.tool_evidence import build_tool_evidence

#: The tools the builder turns into evidence. A branch added here without a case below is a gap.
HANDLED_TOOLS = (
    "run_sql",
    "correlation_analysis",
    "hypothesis_test",
    "regression_analysis",
    "train_model",
    "evaluate_model",
    "forecast",
    "feature_importance",
    "assumption_check",
    "causal_check",
    "create_chart",
    "profile_dataset",
    "run_python",
)

AGENT_DIR = Path(__file__).resolve().parents[2] / "packages/agent/src/dsa_agent"


def _tool_branch_names(tree: ast.AST) -> set[str]:
    """Tool names the builder actually branches on, read off the comparisons."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "tool"):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                names.add(comparator.value)
            elif isinstance(comparator, ast.Tuple):
                names |= {
                    el.value
                    for el in comparator.elts
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                }
    return names


def test_both_orchestration_engines_consume_the_same_definition() -> None:
    """The point of the seam: one evidence rule, not two engines mirroring it."""
    assert graph_binding is build_tool_evidence
    assert langgraph_binding is build_tool_evidence


def test_graph_no_longer_defines_the_evidence_mapping() -> None:
    tree = ast.parse((AGENT_DIR / "graph.py").read_text(encoding="utf-8"))
    defined = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}

    assert "_evidence_for_tool_call" not in defined
    assert "build_tool_evidence" not in defined, "graph must import the seam, not re-declare it"


def test_the_builder_branches_on_exactly_the_tools_this_suite_claims() -> None:
    tree = ast.parse((AGENT_DIR / "tool_evidence.py").read_text(encoding="utf-8"))

    assert _tool_branch_names(tree) == set(HANDLED_TOOLS), (
        "a new tool branch needs a case here, and a removed one needs this list trimmed"
    )


def test_every_handled_tool_produces_evidence_and_an_unknown_tool_produces_none() -> None:
    output = SimpleNamespace(
        columns=["a"],
        row_count=3,
        rows=[],
        r=0.5,
        p_value=0.1,
        method="pearson",
        x="a",
        y="b",
        statistic=1.0,
        test="welch",
        metrics={"mae": 1.0},
        model="m",
        cv_scores=[],
        forecast=[],
        importances=[],
        target="y",
        checks=[],
        passed=True,
        recommendation="r",
        estimate=1.0,
        passes_causal_bar=False,
        confidence_note="n",
        artifact_path="p",
        chart_type="bar",
        profile={"rows": 1, "columns": 1},
        stdout="out",
        error=None,
    )

    for tool in HANDLED_TOOLS:
        evidence = build_tool_evidence(tool, "call-1", output)
        assert evidence is not None, tool
        assert evidence.source_id == "call-1"
        assert evidence.validation_status == "pending"
        assert evidence.claim, tool

    assert build_tool_evidence("something_else", "call-1", output) is None


def test_an_absent_result_or_an_unknown_tool_yields_no_evidence() -> None:
    """The two paths that already answer honestly: no output, or a tool with no rule."""
    assert build_tool_evidence("run_sql", "c", None) is None
    assert build_tool_evidence("not_a_known_tool", "c", SimpleNamespace(rows=[])) is None


def test_the_seam_depends_on_nothing_but_the_evidence_type() -> None:
    """A pure mapping is what makes this testable without an agent, so the imports stay minimal."""
    tree = ast.parse((AGENT_DIR / "tool_evidence.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert imported == {"__future__", "uuid", "typing", "dsa_agent.state"}
