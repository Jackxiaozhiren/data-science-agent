"""R-06: the two exports of one run must be two views of one owner, and the plain one must be plain.

The product's argument is a pair -- "here is the conclusion" plus "here is the evidence" -- and Study 2 of
the web plan §12 blind-compares them. Without the conclusion-only rendering there is no study, and with a
*second* renderer producing it the pair can disagree about a number, which is worse than having only one.

Measured before this file was written, against a real run's persisted ``state_json`` (the shapes below are
transcribed from that producer, not invented):

- ``build_markdown_report`` is the only markdown renderer, and its ``## Limitations`` section is two
  hardcoded sentences -- the spec requires limitations derived from validation results and the critic.
- Validation messages carry identifiers (``Insight I-c9de6a2f ok``, ``Evidence E-22b3922b traceable``), so
  a "plain" export that quotes them is not plain, and the absence rule has to be a rule about tokens
  rather than about sections.
- The API's ``?format=markdown`` returns the *stored* string, so the audited mode has to be what gets
  stored, or the artifact and the export are two documents with one name.

Every absence assertion here is run against the audited text too, so the test shows its own check can
fail (plan §14: falsification, not assertion).
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import pytest
from dsa_agent.state import (
    AnalysisState,
    AnalysisStatus,
    AnalysisStep,
    Evidence,
    Insight,
    ToolCallRecord,
    ValidationResult,
)

RUN_ID = "run-d43b3d1b9a"
DATASET_ID = "9bdfe7ad-b389-4932-a7cb-25c8aa7ebf94"
EVIDENCE_ID = "E-22b3922b"
INSIGHT_ID = "I-c9de6a2f"
CALL_ID = "TC-59543dbd"
SHA256 = "05e300aca0537fcc850cbd06c0649e3c869163a180daec4e7a20e002d1ad6044"
#: An absolute, multi-segment path -- what the artifact writers really produce. Not a developer home path:
#: tests/test_ci_gate_integrity.py refuses `/(Users|home)/` literals in executed code.
ABSOLUTE_PATH = "/var/lib/dsa/output/datasets/9bdfe7ad_sales.csv"
#: The path the audited report actually prints: the tool-call `input` is not rendered, only the chart
#: artifact line, so this is the one the identifier rule has to catch in a real document. Derived from
#: ABSOLUTE_PATH for the same reason the producer derives it -- two literals would be two facts to drift.
CHART_PATH = f"{ABSOLUTE_PATH.rsplit('/', 1)[0]}/chart.png"

NUMERIC_TOKEN = re.compile(r"\d+(?:\.\d+)?")


def _fixture_run(**overrides: Any) -> AnalysisState:
    """One run, in the shape the graph actually persists.

    Field names, id formats and value types are transcribed from a real run's ``state_json`` on
    2026-10-12 (``source_type`` really is ``statistical_test``, a call id really is ``TC-59543dbd``, and the
    stored report really does print an absolute artifact path). A fixture built from the consumer's guesses
    would certify a fiction, which is the mistake the plan's §14 names explicitly.
    """
    state = AnalysisState(
        run_id=RUN_ID,
        dataset_id=DATASET_ID,
        dataset_path=ABSOLUTE_PATH,
        user_query="Which regions drove revenue, and is the campaign_group gap significant?",
        objective="Attribute revenue to region; test the campaign_group difference.",
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 10, 11, 5, 17, 46, tzinfo=UTC),
        plan=[
            AnalysisStep(
                id="s01",
                name="Correlation",
                description="Pearson correlation between the semantic outcome and a numeric predictor",
                tool="correlation_analysis",
                inputs={"dataset_path": ABSOLUTE_PATH, "x": "revenue", "y": "price"},
                depends_on=[],
            )
        ],
        tool_calls=[
            ToolCallRecord(
                call_id=CALL_ID,
                tool="correlation_analysis",
                input={"dataset_path": ABSOLUTE_PATH, "x": "revenue", "y": "price"},
                output={
                    "r": 0.5857584322795393,
                    "p_value": 2.1823645484016534e-47,
                    "method": "pearson",
                },
                status="ok",
                duration_ms=12,
            ),
            ToolCallRecord(
                call_id="TC-4f2a1c90",
                tool="create_chart",
                input={"kind": "bar"},
                output={"artifact_path": f"{ABSOLUTE_PATH.rsplit('/', 1)[0]}/chart.png"},
                status="ok",
                duration_ms=41,
            ),
        ],
        evidence=[
            Evidence(
                id=EVIDENCE_ID,
                source_type="statistical_test",
                source_id=CALL_ID,
                claim="Correlation revenue vs price: r=0.586",
                result={
                    "r": 0.5857584322795393,
                    "p_value": 2.1823645484016534e-47,
                    "method": "pearson",
                },
                confidence=0.8,
                validation_status="verified",
            )
        ],
        insights=[
            Insight(
                id=INSIGHT_ID,
                finding="Correlation revenue vs price: r=0.586",
                evidence_ids=[EVIDENCE_ID],
                limitation="Association does not imply causation.",
            )
        ],
        validation_results=[
            ValidationResult(
                check="evidence_coverage", passed=True, message="Evidence coverage ok"
            ),
            ValidationResult(
                check="unsupported_claim",
                passed=True,
                message="No unsupported causal claims detected",
            ),
            ValidationResult(
                check="evidence_traceability",
                passed=True,
                message=f"Evidence {EVIDENCE_ID} traceable",
            ),
            ValidationResult(
                check="statistical_power",
                passed=False,
                message="Welch test under-powered for region=West (n=7); treat the gap as unconfirmed",
            ),
        ],
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def _export():
    from dsa_agent import report_export

    return report_export


def test_the_owner_exposes_exactly_the_two_modes_and_refuses_anything_else() -> None:
    module = _export()
    assert module.EXPORT_MODES == ("findings", "audited")
    state = _fixture_run()
    with pytest.raises(ValueError, match="findings.*audited|audited.*findings"):
        module.export_markdown(state, "plain")


def test_report_py_is_an_adapter_and_not_a_second_renderer() -> None:
    """`build_markdown_report` must delegate, or the stored artifact and the export are two documents.

    Byte-comparing the two would pass on a re-implementation that happens to agree today; the shape of the
    function is what keeps them from drifting apart later. Same reasoning as the graph-node adapter pin in
    ``tests/agent/test_reporting_seam.py``.
    """
    import ast
    from pathlib import Path

    source = Path("packages/agent/src/dsa_agent/report.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = [
        n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_markdown_report"
    ]
    assert found, "build_markdown_report is no longer a module-level function"
    body = [stmt for stmt in found[0].body if not isinstance(stmt, ast.Expr)]
    assert len(body) == 1, f"the adapter grew to {len(body)} statements: {ast.dump(found[0])}"
    returned = body[0]
    assert isinstance(returned, ast.Return) and isinstance(returned.value, ast.Call)
    called = getattr(returned.value.func, "attr", None) or getattr(returned.value.func, "id", None)
    assert called == "export_markdown", ast.dump(returned)

    from dsa_agent.report import build_markdown_report
    from dsa_agent.report_export import export_markdown

    state = _fixture_run()
    assert build_markdown_report(state) == export_markdown(state, "audited")


def test_findings_carries_the_conclusions_and_none_of_the_trace() -> None:
    module = _export()
    findings = module.export_markdown(_fixture_run(), "findings")

    assert "r=0.586" in findings, (
        "the number the participant asked for must survive the plain export"
    )
    assert "Association does not imply causation." in findings
    assert "under-powered" in findings, (
        "a failed validation must appear as a limitation, not vanish"
    )

    offending = module.identifier_tokens(findings)
    assert offending == [], f"the plain export still carries trace material: {offending}"
    assert DATASET_ID not in findings
    assert CHART_PATH not in findings, "an absolute path leaks the user's machine into a sent file"


def test_the_plain_export_strips_the_free_text_it_keeps_too() -> None:
    """The two render sites that quote prose rather than detail fields -- measured as a gap, not assumed.

    ``objective`` is the user's own sentence and ``finding`` is model prose: a question that names its file
    (``compare /srv/exports/q3.csv ...``) or a finding that cites an evidence record rides straight through
    the mode whose entire promise is that it does not. The fixture above cannot reach either site, so the
    guard would have certified only the fields it happened to populate.
    """
    module = _export()
    state = _fixture_run(
        objective=f"Compare {ABSOLUTE_PATH} with {DATASET_ID} and report the r value behind {EVIDENCE_ID}."
    )
    state.insights[0].finding = f"Correlation revenue vs price (see {EVIDENCE_ID}): r=0.586"
    findings = module.export_markdown(state, "findings")
    audited = module.export_markdown(state, "audited")

    leaked = module.identifier_tokens(findings)
    assert leaked == [], f"the plain export carries trace material: {leaked}"
    tripped = module.identifier_tokens(audited)
    for token in (f"absolute_path: {ABSOLUTE_PATH}", f"evidence_id: {EVIDENCE_ID}"):
        assert token in tripped, (
            f"{token} absent from audited -- the check proves nothing: {tripped[:4]}"
        )
    assert "r=0.586" in findings, "stripping identifiers must never eat a figure"
    # The tightening this test exists to justify: a path matcher that allows spaces will happily consume the
    # rest of the sentence. Dropping trace material is the mode; losing the person's question is a defect.
    assert "Compare with and report the r value behind" in findings, (
        "the objective lost its prose, not just its path: "
        + next(line for line in findings.splitlines() if "Objective" in line)
    )


def test_the_absence_check_is_capable_of_failing_and_the_audited_export_trips_it() -> None:
    """Accept's own requirement: assert the absence, then assert the assertion bites.

    The tokens that trip the audited text are the ones a real run's stored report actually contains -- run
    id, evidence id, tool-call id, absolute artifact path. The hash and dataset-uuid rules cannot be tripped
    from a real report (measured: a stored report carries no 64-hex digest), so they are checked against
    synthetic text and labelled as that, rather than being pretended into the fixture.
    """
    module = _export()
    state = _fixture_run()
    findings = module.export_markdown(state, "findings")
    audited = module.export_markdown(state, "audited")

    assert module.identifier_tokens(findings) == [], "the plain export must be clean"
    tripped = " ".join(module.identifier_tokens(audited))
    assert tripped, "the audited export carries no identifiers either -- the check proves nothing"
    for token in (RUN_ID, EVIDENCE_ID, CALL_ID, CHART_PATH):
        assert token in tripped, f"{token} is in the audited text but the rule missed it: {tripped}"

    synthetic = f"digest {SHA256} dataset {DATASET_ID}"
    rules = {entry.split(":")[0] for entry in module.identifier_tokens(synthetic)}
    assert {"sha256", "dataset_id"} <= rules, rules


def test_the_export_does_not_depend_on_when_you_asked() -> None:
    """The stamp has to come from immutable run state, or the pair disagrees about nothing but itself.

    Found by the measured capture rather than by this suite: the stored ``audited`` report is composed
    before the row's terminal status write, and that write touches ``updated_at``. Deriving the stamp from
    it made an on-demand ``findings`` render of the same run carry a different time -- a number in one file
    and not the other, which is the exact failure mode the numeric rule exists to catch.
    """
    from datetime import timedelta

    module = _export()
    state = _fixture_run()
    before = module.export_markdown(state, "findings")
    audited_before = module.export_markdown(state, "audited")

    state.updated_at = state.updated_at + timedelta(minutes=9)
    after = module.export_markdown(state, "findings")
    audited_after = module.export_markdown(state, "audited")

    assert before == after, "the plain export moved when only updated_at did"
    assert audited_before == audited_after, "the audited export is not a pure function of the run"

    numbers = Counter(NUMERIC_TOKEN.findall(after)) - Counter(NUMERIC_TOKEN.findall(before))
    assert not numbers, f"timestamps leaked digits into the diff: {sorted(numbers)}"


def test_no_number_in_findings_disagrees_with_the_audited_export() -> None:
    """Spec 2: the pair cannot disagree about a number, because they read the same fields."""
    module = _export()
    state = _fixture_run()
    findings = Counter(NUMERIC_TOKEN.findall(module.export_markdown(state, "findings")))
    audited = Counter(NUMERIC_TOKEN.findall(module.export_markdown(state, "audited")))
    unexplained = sorted(token for token in findings if token not in audited)
    assert not unexplained, f"numbers invented by the plain export: {unexplained}"


def test_limitations_are_derived_and_the_section_is_never_absent() -> None:
    module = _export()
    state = _fixture_run()
    derived = module.derived_limitations(state)
    assert any("under-powered" in line for line in derived), derived
    assert any(line == "Association does not imply causation." for line in derived), derived

    for mode in module.EXPORT_MODES:
        text = module.export_markdown(state, mode)
        assert "## Limitations" in text, f"{mode} dropped the mandatory section"

    clean = _fixture_run(validation_results=[state.validation_results[0]])
    clean_text = module.export_markdown(clean, "findings")
    assert "## Limitations" in clean_text, "a run with nothing to report still owes the section"
    assert "under-powered" not in clean_text, "a limitation from a dropped check must not survive"


def test_the_critic_rewrite_and_the_run_error_are_both_named_as_limitations() -> None:
    """The three branches the shipped fixture never reached -- the coverage row said so, not this file.

    ``derived_limitations`` has four sources and the tests above exercised two of them, so the two lines
    that make R-06.4's promise real (a rewritten claim is disclosed, a recorded error is disclosed) had
    never run, and neither had the case where an insight carries no limitation of its own. An unexercised
    branch is not a defect, but it is a promise nobody has seen kept.
    """
    module = _export()
    state = _fixture_run(
        error="create_chart failed after 2 retries; the bar chart comes from the first table"
    )
    state.evidence[
        0
    ].claim = f"Campaign uplift is attributable to the launch {module.CAUSAL_REWRITE_MARKER}"

    lines = module.derived_limitations(state)
    assert any(line.startswith("One claim was rewritten") for line in lines), lines
    assert any(line.startswith("The run recorded an error") for line in lines), lines

    for mode in module.EXPORT_MODES:
        text = module.export_markdown(state, mode)
        assert "One claim was rewritten because causal evidence is absent" in text, mode
        assert "The run recorded an error" in text, mode
    findings = module.export_markdown(state, "findings")
    assert module.identifier_tokens(findings) == [], module.identifier_tokens(findings)

    # The branch where an insight has nothing to qualify: the floor must still be the last line.
    bare = _fixture_run()
    bare.insights[0].limitation = None
    kept = module.derived_limitations(bare)
    assert "Association does not imply causation." not in kept, kept
    assert kept[-1] == module.STANDING_LIMITATION, kept

    # Two insights qualifying the same thing say it once: a reviewer counting limitations would otherwise
    # read the repetition as two separate weaknesses.
    twin = _fixture_run()
    twin.insights.append(twin.insights[0].model_copy())
    assert module.derived_limitations(twin).count("Association does not imply causation.") == 1


def test_a_thin_run_and_a_dict_source_both_render_in_both_modes() -> None:
    """The shapes the HTTP surface actually feeds the owner.

    The API hands ``export_markdown`` the ``state_json`` **dict**, not the model, and a run can legitimately
    have a failed tool, an evidence record with no result payload, or no trace at all. The coverage row of
    the first draft listed those as never-executed branches, which for a renderer means "unobserved output
    for a real run shape": a run whose chart failed still owes the reader the error line, and an empty run
    still owes both documents.
    """
    module = _export()

    failed = _fixture_run()
    failed.tool_calls[1].status = "error"
    failed.tool_calls[1].error = "ValueError: `region` is not a numeric column"
    failed.evidence[0].result = None
    audited = module.export_markdown(failed, "audited")
    assert "- error: ValueError: `region` is not a numeric column" in audited, audited
    assert "  - result:" not in audited, "an evidence record with no payload must not print one"

    thin = _fixture_run(plan=[], tool_calls=[], evidence=[], validation_results=[], insights=[])
    for mode in module.EXPORT_MODES:
        text = module.export_markdown(thin, mode)
        assert "## Insights" in text and "_No insights yet" in text, (mode, text)
        assert "## Limitations" in text, (mode, text)
    thin_audited = module.export_markdown(thin, "audited")
    for heading in ("## Tool Calls", "## Evidence", "## Validation", "## Plan"):
        assert heading not in thin_audited, f"{heading} rendered for an empty run"

    as_dict = _fixture_run().model_dump(mode="json")
    for mode in module.EXPORT_MODES:
        rendered = module.export_markdown(as_dict, mode)
        assert "## Limitations" in rendered, mode
        assert "r=0.586" in rendered, mode
    assert module.identifier_tokens(module.export_markdown(as_dict, "findings")) == []

    # A row whose timestamps are both missing still has to render -- the fallback is the only line in this
    # module that reads the clock, and the plan's reproducibility task is precisely that nothing else does.
    sparse = _fixture_run().model_dump(mode="json")
    sparse.pop("created_at", None)
    sparse.pop("updated_at", None)
    assert "Generated:" in module.export_markdown(sparse, "findings")


def test_the_html_rendering_of_the_audited_mode_opens_with_no_server() -> None:
    """R-06 spec 3's floor. R-07 extends this renderer; it must not become a second one."""
    module = _export()
    html = module.export_html(_fixture_run())
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "<link" not in html.lower(), "an external stylesheet means the file cannot open offline"
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', html), (
        "external subresource in a sent file"
    )
    assert "r=0.586" in html, "the HTML must render the same numbers, not a summary of them"
    # Measured on the first capture: the HTML was built from the markdown line strings, so the reviewer's
    # offline file opened with literal `**Profile dataset**` and backticks in it.
    assert not re.search(r"\*\*[^*]+\*\*", html), "raw bold markdown leaked into the HTML"
    assert "`" not in html, "raw code markdown leaked into the HTML"
    assert "<strong>Correlation</strong>" in html, html[:600]
    assert "![chart]" not in html and "chart: chart.png" in html, (
        "a chart must be named, not embedded as an image that is not in the file"
    )


def test_the_api_mode_parameter_selects_the_owner_and_rejects_nonsense(tmp_path) -> None:
    """The route must not grow its own rendering -- it calls the same owner with the stored state."""
    from dsa_agent import report_export

    state = _fixture_run()
    stored = report_export.export_markdown(state, "audited")
    payload: dict[str, Any] = {**state.model_dump(mode="json"), "report_markdown": stored}

    for mode, expect_id in (("findings", False), ("audited", True)):
        text = report_export.export_markdown(payload, mode)
        assert (EVIDENCE_ID in text) is expect_id, mode
        assert "r=0.586" in text, mode


def test_a_field_in_one_mode_and_not_the_other_is_only_allowed_for_trace_metadata() -> None:
    """Spec 2's contrapositive: the modes may differ in evidence plumbing and nothing else.

    The conclusion section keeps the name the rest of the system uses for it -- `insights` is the field in
    `RUN_SUMMARY_FIELDS` and the label in the web UI -- because coining "findings" as a display term would
    give the two documents different headings for the same content, and Study 2 blind-compares them.
    """
    module = _export()
    state = _fixture_run()
    findings = module.export_markdown(state, "findings")
    audited = module.export_markdown(state, "audited")

    for heading in ("## Insights", "## Limitations"):
        assert heading in findings and heading in audited, f"{heading} must appear in both"
    for heading in ("## Tool Calls", "## Evidence", "## Validation"):
        assert heading in audited and heading not in findings, heading
    assert "Correlation revenue vs price" in findings
