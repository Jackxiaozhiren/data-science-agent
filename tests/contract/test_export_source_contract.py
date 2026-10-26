"""How an ``export_artifact`` source reference resolves, and what it must never do silently.

Found by reproducing GitHub issue #70 rather than re-reading it. Its planner half was already fixed in §54
(``_TABULAR_TOOLS`` shrank to what really emits ``columns``+``rows``); what remained was the reference contract,
which was written down in exactly one place -- ``_resolve_refs``'s docstring -- and what it said there was false. It
promised "0-based among *executed* calls" while the code filtered ``status == "ok"``, so over
``[run_sql ok, create_chart failed, run_sql ok]`` the reference ``{"$from_step": 1}`` returned the **third** call's
table, the export succeeded, wrote ``sex\\nfemale``, recorded a sha256, and reported nothing. A wrong artifact that
never errors is the failure mode this project's inspectability claim exists to make impossible.

The behaviour now is: positions include failures, a failed target is refused **with the reason** instead of sliding
on, and the exact form is ``{"$from_step_id": "s03"}`` -- the plan step, which survives both a retry (which appends
a second record) and the leading parallel batch (which is executed with ``gather``). These tests pin the behaviour
first and the wording of the three places that state it second, so drift reddens here rather than in a report a user
downloads. ``AUDIT_LEDGER.md`` §303 and §304.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from dsa_agent.graph import _resolve_refs
from dsa_agent.planner import _TABULAR_TOOLS, _validate_real_plan
from dsa_agent.state import AnalysisPlan, AnalysisStep

# The history that used to be survivable in silence: a failed call between two tables.
_ONE_FAILURE = [
    {
        "step_id": "s01",
        "tool": "run_sql",
        "status": "ok",
        "output": {"columns": ["region"], "rows": [["north"]]},
    },
    {"step_id": "s02", "tool": "create_chart", "status": "error", "output": None},
    {
        "step_id": "s03",
        "tool": "run_sql",
        "status": "ok",
        "output": {"columns": ["sex"], "rows": [["female"]]},
    },
]


def _resolve(source: dict[str, Any]) -> dict[str, Any]:
    return _resolve_refs({"source": source}, _ONE_FAILURE)["source"]  # type: ignore[no-any-return]


def test_a_failed_position_is_refused_by_reason_instead_of_returning_the_next_table() -> None:
    """The silent slide is gone: index 1 is the failed chart call, and saying so is the only answer.

    Before this change the same reference returned record #3's rows and the export succeeded.
    """
    resolved = _resolve({"$from_step": 1})
    assert "$reference_reason" in resolved, resolved
    reason = str(resolved["$reference_reason"])
    assert "create_chart" in reason and "did not succeed" in reason, reason
    # The original key survives, so a refusal cannot be mistaken for a payload.
    assert resolved["$from_step"] == 1


def test_positions_count_executed_records_failures_included() -> None:
    """Position 0 and 2 still reach the two tables, and an out-of-range index stays an honest non-resolution."""
    assert _resolve({"$from_step": 0}) == {"columns": ["region"], "rows": [["north"]]}
    assert _resolve({"$from_step": 2}) == {"columns": ["sex"], "rows": [["female"]]}
    assert _resolve({"$from_step": 9}) == {"$from_step": 9}


def test_from_step_id_names_the_step_and_ignores_where_it_landed() -> None:
    """The exact form: a step id selects its own successful result no matter how many records moved."""
    assert _resolve({"$from_step_id": "s01"}) == {"columns": ["region"], "rows": [["north"]]}
    assert _resolve({"$from_step_id": "s03"}) == {"columns": ["sex"], "rows": [["female"]]}
    missing = _resolve({"$from_step_id": "s02"})
    # Key presence asserted first: a resolution that slides to another call answers with no reason at all, and the
    # red should name that guarantee rather than die on a KeyError.
    assert "$reference_reason" in missing, missing
    assert "no successful result" in str(missing["$reference_reason"]), missing
    assert missing["$from_step_id"] == "s02"


def test_a_retry_appends_a_record_without_moving_a_step_id_selection() -> None:
    """Retries are the second way positions lie: a re-run step adds a record, its step id does not shift."""
    history = [
        {
            "step_id": "s01",
            "tool": "run_sql",
            "status": "ok",
            "output": {"columns": ["a"], "rows": [[1]]},
        },
        {"step_id": "s02", "tool": "hypothesis_test", "status": "error", "output": None},
        {
            "step_id": "s02",
            "tool": "hypothesis_test",
            "status": "ok",
            "output": {"columns": ["p"], "rows": [[0.04]]},
        },
    ]
    out = _resolve_refs({"source": {"$from_step_id": "s02"}}, history)["source"]
    assert out == {"columns": ["p"], "rows": [[0.04]]}
    # ...while the positional form now refuses record 1 rather than quietly resolving to record 2.
    positional = _resolve_refs({"source": {"$from_step": 1}}, history)["source"]
    assert "$reference_reason" in positional, positional


def test_from_tool_still_takes_the_latest_successful_call_of_that_name() -> None:
    """Unchanged: name selection is position-independent, which is why the heuristic planner emits it."""
    assert _resolve({"$from_tool": "run_sql"}) == {"columns": ["sex"], "rows": [["female"]]}
    assert _resolve({"$from_tool": "create_chart"}) == {"$from_tool": "create_chart"}


def test_the_export_refuses_a_reasoned_reference_and_writes_nothing(tmp_path: Any) -> None:
    """The refusal has to survive the tool boundary: an error, a reason, and no file on disk."""
    import asyncio

    from dsa_tools.base import ToolExecutionError
    from dsa_tools.tools.export_artifact import ExportArtifactInput, ExportArtifactTool

    with pytest.raises(ToolExecutionError) as exc:
        asyncio.run(
            ExportArtifactTool().execute(
                ExportArtifactInput(
                    source=_resolve({"$from_step": 1}),
                    filename="result_table.csv",
                    format="csv",
                    workspace=str(tmp_path),
                )
            )
        )
    assert "create_chart" in str(exc.value) and "did not succeed" in str(exc.value), exc.value
    assert list(tmp_path.iterdir()) == [], "the refused export still wrote a file"


def test_the_export_still_relocates_the_step_named_by_id(tmp_path: Any) -> None:
    """Positive control for the test above: the same history exports the table step s03 named, bytes included."""
    import asyncio

    from dsa_tools.tools.export_artifact import ExportArtifactInput, ExportArtifactTool

    out = asyncio.run(
        ExportArtifactTool().execute(
            ExportArtifactInput(
                source=_resolve({"$from_step_id": "s03"}),
                filename="result_table.csv",
                format="csv",
                workspace=str(tmp_path),
            )
        )
    )
    assert out.columns == ["sex"]
    assert (tmp_path / "result_table.csv").read_text(encoding="utf-8").strip() == "sex\nfemale"


def test_records_carry_the_plan_step_id_in_both_executors() -> None:
    """`$from_step_id` is only true if every executor records which step produced a call.

    Parsed rather than grepped: a record built without the key would leave every step-id reference unresolvable
    while the resolver itself still looked correct in a unit test. The counts are asserted too, so a construction
    site added later cannot slip past the walk.
    """
    import ast
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[2]
    graph_src = (repo / "packages/agent/src/dsa_agent/graph.py").read_text(encoding="utf-8")
    record_calls = [
        node
        for node in ast.walk(ast.parse(graph_src))
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ToolCallRecord"
    ]
    assert len(record_calls) >= 2, (
        f"expected the initial and the retry construction, saw {len(record_calls)}"
    )
    for node in record_calls:
        assert any(k.arg == "step_id" for k in node.keywords), ast.unparse(node)[:90]

    lang_src = (repo / "packages/agent/src/dsa_agent/langgraph_graph.py").read_text(
        encoding="utf-8"
    )
    dicts = [
        node
        for node in ast.walk(ast.parse(lang_src))
        if isinstance(node, ast.Dict)
        and {k.value for k in node.keys if isinstance(k, ast.Constant)}
        >= {"call_id", "tool", "status"}
    ]
    assert dicts, "the langgraph tool node no longer builds a record literal -- re-read this test"
    for node in dicts:
        keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
        assert "step_id" in keys, sorted(keys)


def test_the_published_schema_states_the_three_forms_and_the_no_slide_rule() -> None:
    """A REST or MCP caller sees the schema and nothing else.

    Keywords alone are a weak check: a description naming all three forms while recommending the positional one
    would pass a token census. So the assertions include the two directional claims a reader needs -- which form to
    prefer, and why the positional one cannot be authored from a plan.
    """
    raw = _schema_description()
    for marker in (
        "$from_step_id",
        "$from_tool",
        "$from_step",
        "execution order",
        "never resolved onward",
        "the form to prefer",
        "cannot be known before the run",
    ):
        assert marker in raw, (marker, raw)
    # The pre-fix description promised only that the executor resolved something.
    assert "reference resolved by the executor" not in raw


def test_the_real_mode_prompt_sends_the_model_the_exact_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert on the prose the provider actually receives, not on a grep of the source file."""
    import asyncio

    import dsa_agent.planner as planner

    captured: dict[str, str] = {}

    class _EchoProvider:
        async def structured_output(self, prompt: str, schema: type, **_kw: Any) -> Any:
            captured["prompt"] = prompt
            return AnalysisPlan(
                objective="Export a table",
                assumptions=[],
                steps=[
                    AnalysisStep(
                        id="s01",
                        name="Profile",
                        description="Profile",
                        tool="profile_dataset",
                        inputs={"path": "p"},
                    ),
                    AnalysisStep(
                        id="s02",
                        name="Query",
                        description="Query",
                        tool="run_sql",
                        inputs={"dataset_path": "p", "sql": "SELECT 1"},
                        depends_on=["s01"],
                    ),
                ],
            )

    monkeypatch.setenv("DSA_LLM_MODE", "real")
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: _EchoProvider())
    plan = asyncio.run(planner.plan_analysis("export the table", "/tmp/d.csv", ["a"]))
    assert plan.steps
    prompt = captured["prompt"]
    assert "$from_step_id" in prompt and "$from_step" in prompt, prompt
    assert "cannot know which record position" in prompt, prompt


def test_the_heuristic_planner_still_emits_the_position_independent_reference() -> None:
    """The shipped demo path selects by name, so a run of the hosted demo never depended on this."""
    from dsa_agent.planner import _terminal_export_steps

    steps = [AnalysisStep(id="s01", name="Q", description="q", tool="run_sql", inputs={})]
    specs = _terminal_export_steps("average value by key", steps)
    assert specs, "the tabular export branch stopped being emitted at all"
    assert specs[0][2] in _TABULAR_TOOLS, specs


def test_the_validator_passes_a_step_id_reference_through_untouched() -> None:
    """Plan validation checks structure, not payload shape: the reference resolves only at execution."""
    plan = AnalysisPlan(
        objective="o",
        assumptions=[],
        steps=[
            AnalysisStep(
                id="s01",
                name="Profile",
                description="Profile",
                tool="profile_dataset",
                inputs={"path": "p"},
            ),
            AnalysisStep(
                id="s02",
                name="Query",
                description="Query",
                tool="run_sql",
                inputs={"dataset_path": "p", "sql": "SELECT 1"},
                depends_on=["s01"],
            ),
            AnalysisStep(
                id="s03",
                name="Export result table",
                description="Export",
                tool="export_artifact",
                inputs={"source": {"$from_step_id": "s02"}, "format": "csv"},
                depends_on=["s02"],
            ),
        ],
    )
    checked = _validate_real_plan(plan, "export the table", "p")
    assert checked.steps[2].inputs["source"] == {"$from_step_id": "s02"}


def _schema_description() -> str:
    import dsa_tools

    dsa_tools.bootstrap()
    tool = dsa_tools.get("export_artifact")
    assert tool is not None
    schema = tool.input_model.model_json_schema()
    return str(schema["properties"]["source"]["description"])
