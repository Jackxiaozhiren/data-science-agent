"""``$from_step`` means "i-th call that succeeded", and three surfaces have to say so.

Found by reproducing GitHub issue #70 rather than re-reading it. The planner-side half of that defect was fixed in
§54 (``_TABULAR_TOOLS`` shrank to what really emits ``columns``+``rows``), but the reference contract itself was
written down in exactly one place -- ``_resolve_refs``'s docstring -- and what it said there was false: it promised
"0-based among *executed* calls" while the code filters ``status == "ok"``. Measured over
``[run_sql ok, create_chart failed, run_sql ok]``, ``{"$from_step": 1}`` returns the **third** call's table, so an
export asked for one result silently relocates a different one, succeeds, and records a sha256 for a file nobody
requested. A wrong artifact that never errors is worse than the failure issue #70 described, and this project's whole
claim is that a produced number can be traced back to what made it.

So the contract is now stated where its three readers actually look: the executor's docstring, the
``export_artifact`` schema a REST or MCP client is handed, and the prompt the real-mode planner sends. These tests
pin the behaviour, then pin that all three statements describe *that* behaviour -- wording drift reddens here, not in
a report the user downloads.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from dsa_agent.graph import _resolve_refs
from dsa_agent.planner import _TABULAR_TOOLS, _validate_real_plan
from dsa_agent.state import AnalysisPlan, AnalysisStep

# The measured shift: a failed call in the middle moves every later index down by one.
_ONE_FAILURE = [
    {"tool": "run_sql", "status": "ok", "output": {"columns": ["region"], "rows": [["north"]]}},
    {"tool": "create_chart", "status": "error", "output": {}},
    {"tool": "run_sql", "status": "ok", "output": {"columns": ["sex"], "rows": [["female"]]}},
]


def _resolved(source: dict[str, Any]) -> dict[str, Any]:
    return _resolve_refs({"source": source}, _ONE_FAILURE)["source"]  # type: ignore[no-any-return]


def test_from_step_counts_only_the_calls_that_succeeded() -> None:
    """The behaviour the contract now promises, pinned rather than paraphrased.

    Index 1 is the second *successful* call -- the third executed one -- because the failed chart call is not
    counted. If counting ever becomes position-based this assertion is where it becomes visible.
    """
    assert _resolved({"$from_step": 1}) == {"columns": ["sex"], "rows": [["female"]]}
    assert _resolved({"$from_step": 0}) == {"columns": ["region"], "rows": [["north"]]}


def test_from_tool_is_immune_to_the_shift_because_it_selects_by_name() -> None:
    """``$from_tool`` takes the latest successful call of that tool, so a failure cannot move it."""
    assert _resolved({"$from_tool": "run_sql"}) == {"columns": ["sex"], "rows": [["female"]]}
    # ...and the shape of an unresolved reference stays honest rather than becoming a guessed payload.
    assert _resolved({"$from_step": 9}) == {"$from_step": 9}


def test_the_resolved_source_is_what_the_export_actually_relocates(tmp_path: Any) -> None:
    """The shift is not a trivia fact: a csv export of index 1 writes the other table and reports no error.

    Nothing below raises. That is the point -- a wrong artifact that succeeds is what a reader of the old
    docstring would have got, and no validation check would have named it.
    """
    import asyncio

    from dsa_tools.tools.export_artifact import ExportArtifactInput, ExportArtifactTool

    out = asyncio.run(
        ExportArtifactTool().execute(
            ExportArtifactInput(
                source=_resolved({"$from_step": 1}),
                filename="result_table.csv",
                format="csv",
                workspace=str(tmp_path),
            )
        )
    )
    assert out.columns == ["sex"], "the export followed the resolved payload, not the requested one"
    assert (tmp_path / "result_table.csv").read_text(encoding="utf-8").strip() == "sex\nfemale"


def _schema_description() -> str:
    import dsa_tools

    dsa_tools.bootstrap()
    tool = dsa_tools.get("export_artifact")
    assert tool is not None
    schema = tool.input_model.model_json_schema()
    return str(schema["properties"]["source"]["description"])


def test_the_executor_docstring_no_longer_promises_the_false_counting() -> None:
    """The only place the rule was written down used to state the opposite of what the code does.

    "0-based among *executed* calls" described a counting the implementation never had, so a reader who trusted it
    got a different table than the one they named. Pinning the wording against the behaviour is the cheap half of
    the fix; the semantics themselves belong to ``test_from_step_counts_only_the_calls_that_succeeded``.
    """
    doc = " ".join((inspect.getdoc(_resolve_refs) or "").split()).lower()
    assert "succeeded" in doc and "0-based" in doc, doc
    assert "executed calls" not in doc, doc


def test_the_published_schema_states_the_index_rule_a_client_would_need() -> None:
    """A REST or MCP caller sees the schema and nothing else; the rule has to be in it."""
    raw = _schema_description()
    text = raw.lower()
    assert "succeeded" in text and "0-based" in text, raw
    assert "not the plan" in text, raw
    assert "failed calls are not counted" in text, raw
    # The old description said only "resolved by the executor", which is what let a wrong-but-successful
    # export look like correct behaviour to whoever wrote the plan.
    assert "resolved by the executor" not in text


def test_the_real_mode_prompt_tells_the_planner_the_same_thing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The model is asked in prose; assert on the prose it actually receives, not on a source-string grep."""
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
    prompt = captured["prompt"].lower()
    for marker in ("succeeded", "0-based", "$from_tool"):
        assert marker in prompt, f"the prompt never tells the model about {marker!r}"


def test_the_heuristic_planner_still_emits_the_shift_immune_reference() -> None:
    """The shipped demo path selects by name, which is why the shift never showed up there.

    ``_terminal_export_steps`` is called directly because the heuristic planner only emits ``run_sql`` for a
    narrow set of preprocessing intents; routing through ``heuristics_plan`` would leave the tabular branch
    unexecuted and the assertion silently unrun -- the vacuous-guard shape §54 recorded.
    """
    from dsa_agent.planner import _terminal_export_steps

    steps = [AnalysisStep(id="s01", name="Q", description="q", tool="run_sql", inputs={})]
    specs = _terminal_export_steps("average value by key", steps)
    assert specs, "the tabular export branch stopped being emitted at all"
    assert specs[0][2] in _TABULAR_TOOLS, specs


def test_the_validator_passes_a_name_selected_export_reference_through_untouched() -> None:
    """Plan validation checks structure, not payload shape: the reference is resolved only at execution.

    Naming which step produced a table is the executor's job (`_resolve_refs`), so what the validator must not do
    is rewrite or reject a well-formed reference -- that is where a shape rule for real-mode plans would have to
    be added, and issue #70's remaining half stays open pending that decision.
    """
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
                inputs={"source": {"$from_tool": "run_sql"}, "format": "csv"},
                depends_on=["s02"],
            ),
        ],
    )
    checked = _validate_real_plan(plan, "export the table", "p")
    assert checked.steps[2].inputs["source"] == {"$from_tool": "run_sql"}
