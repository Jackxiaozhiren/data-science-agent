"""The report says who produced it, and the conclusion-only export deliberately does not.

Issue #135, measured on the live demo: a heuristic run's `report.md` named no reasoner at all -- the words
`heuristic` and `stub` appeared nowhere in it -- while `/version` and the web UI did label the mode. So the honest
signal lived on the screen and vanished from the one artifact a visitor hands to a colleague, which is what
`WEB_PRODUCT_MASTER_PROMPT.md` §2 ("No unmarked stub output presented as agent analysis") is about.

Two things were found on the way and both are pinned here rather than assumed. The run state already carried the
provenance (`AnalysisState.reasoning`, captured by the executor at run start under R-02), so this was a rendering
gap and not a data gap -- except in `compose_report`, which rebuilds a state object from a stored dict and dropped
the field. And the `findings` export keeps provenance out on purpose: §12's paired-blind review asks a reader to
rate the writing without knowing which producer made it, and this line is exactly the cue that would unblind them.

A run recorded before the field existed says "not recorded". It does not resolve the mode from the environment that
happens to be rendering it, because that is the two-readings defect R-02 was raised to remove, one layer later.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dsa_agent.report_export import export_html, export_markdown
from dsa_agent.reporting import compose_report

_STUB = {
    "mode": "heuristic",
    "provider": "stub",
    "model": None,
    "source": "environment",
    "stub": True,
}
_REAL = {
    "mode": "real",
    "provider": "openai",
    "model": "gpt-4o-mini",
    "source": "stored",
    "stub": False,
}


def _state(
    reasoning: Any, objective: str = "Which groups had the highest survival rate?"
) -> dict[str, Any]:
    return {
        "run_id": "run-prov-1",
        "dataset_id": "ds-1",
        "user_query": objective,
        "objective": objective,
        "status": "COMPLETED",
        "created_at": "2026-10-26T00:00:00+00:00",
        "plan": [],
        "tool_calls": [],
        "evidence": [],
        "insights": [{"id": "I-1", "finding": "r=-0.27", "evidence_ids": ["E-1"]}],
        "validation_results": [],
        "reasoning": reasoning,
    }


def _line(md: str) -> str:
    hits = [
        line
        for line in md.splitlines()
        if line.startswith("**Reasoning:**") or line.startswith("**推理来源：**")
    ]
    assert len(hits) == 1, (hits, md[:200])
    return hits[0]


def test_a_stub_run_says_so_in_the_audited_report() -> None:
    """The claim that matters: a deterministic run is labelled as one, in the file that leaves the product."""
    line = _line(export_markdown(_state(_STUB), "audited"))
    assert "heuristic" in line and "stub" in line, line
    assert "no language model was consulted" in line, line
    assert "source: environment" in line, line


def test_a_real_run_names_the_model_and_does_not_claim_abstinence() -> None:
    line = _line(export_markdown(_state(_REAL), "audited"))
    assert "real" in line and "gpt-4o-mini" in line, line
    assert "no language model" not in line, line


def test_a_record_without_the_stub_field_states_facts_but_not_the_absence_claim() -> None:
    """Rows written before `stub` was captured keep naming mode and provider, and stop short of the stronger claim.

    `provider == "stub"` would let the renderer infer the absence of a model from a name; the claim is only made
    when the run itself recorded it.
    """
    legacy = {k: v for k, v in _STUB.items() if k != "stub"}
    line = _line(export_markdown(_state(legacy), "audited"))
    assert "heuristic" in line and "stub" in line, line
    assert "no language model" not in line, line


def test_a_run_with_no_record_says_not_recorded_and_does_not_adopt_the_current_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two-readings guard: rendering an old run under a new configuration must not restate the new one.

    Forged red by reading the live mode in the renderer instead of the record -- with `DSA_LLM_MODE=real` set here,
    such a renderer would print `real` for a run that never had one.
    """
    monkeypatch.setenv("DSA_LLM_MODE", "real")
    line = _line(export_markdown(_state(None), "audited"))
    assert "not recorded" in line, line
    assert "real" not in line, line


def test_the_findings_export_omits_it_because_blinding_depends_on_that(tmp_path: Any) -> None:
    """§12's paired-blind review: the conclusion-only document must not disclose which producer made it.

    Asserted on both directions, because a regression either way changes the experiment: absent from `findings`,
    present in `audited`, and the rest of the two documents keep differing only by the sections R-06 defined.
    """
    findings = export_markdown(_state(_STUB), "findings")
    assert "Reasoning" not in findings, findings[:200]
    assert "no language model" not in findings, findings[:200]
    assert "heuristic" not in findings, findings


def test_the_html_deliverable_carries_it_and_escapes_the_provenance_strings() -> None:
    """The standalone HTML is the file people open offline, and its fields come from stored state."""
    hostile = {
        "mode": "heuristic<script>",
        "provider": 'stub" onload="alert(1)',
        "model": None,
        "source": "environment",
        "stub": False,
    }
    html = export_html(_state(hostile))
    assert "<script>" not in html, "a stored mode reached the page unescaped"
    assert "heuristic&lt;script&gt;" in html, html[:400]
    assert "推理来源" not in html and "Reasoning:" in html


def test_a_chinese_run_reports_its_provenance_in_chinese() -> None:
    """R-13h: the deliverable's own words follow the run's language, including this new sentence."""
    md = export_markdown(_state(_STUB, objective="哪些乘客群体的存活率最高？"), "audited")
    line = _line(md)
    assert line.startswith("**推理来源：**"), line
    assert "未调用任何语言模型" in line, line
    assert "（来源：environment）" in line, line
    # The English form must not leak into a Chinese document, and vice versa.
    assert "no language model" not in md, line


def test_compose_report_carries_the_record_into_the_file_it_writes(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The langgraph reporting path rebuilds a state object from stored dicts, twice.

    Both rebuilds have to see the record: `compose_report` returns a markdown string *and* writes the artifact a
    visitor downloads, and the second construction is what produces the file. A provenance line that reaches only
    the returned copy would mean the screen and the downloaded document disagree about who made the run -- the exact
    divergence this module was extracted to prevent.
    """
    monkeypatch.setenv("DSA_ARTIFACT_ROOT", str(tmp_path))
    out = compose_report(
        {
            "run_id": "run-prov-2",
            "dataset_id": "ds-1",
            "user_query": "summarize",
            "analysis_state": {"reasoning": _STUB, "created_at": "2026-10-26T09:00:00+00:00"},
        }
    )
    analysis = out.get("analysis_state") or {}
    md = analysis.get("report_markdown") or ""
    assert "no language model was consulted" in md, md[:300]
    # The stamp is the run's own, not the renderer's clock: a report re-composed later must read identically.
    # Rendered from the parsed datetime, so the separator is the space `str()` gives rather than the stored `T`.
    assert "2026-10-26 09:00:00+00:00" in md, md[:300]
    written = [
        a
        for a in (analysis.get("artifacts") or [])
        if (a.get("metadata") or {}).get("kind") == "markdown"
    ]
    assert written, analysis.get("artifacts")
    body = Path(written[0]["path"]).read_text(encoding="utf-8")
    assert "no language model was consulted" in body, body[:300]
    assert body == md, "the downloaded report and the returned one are different documents"


def test_the_record_can_hold_everything_the_resolver_reports() -> None:
    """A provenance line cannot claim more than the record holds, so the record must not be narrower than the source.

    `resolve_llm_mode()` is the single owner of this answer (R-02, R-05); `ReasoningRecord` is the copy persisted
    per run. If a field is added upstream and not downstream, the report silently loses that half of the truth.
    """
    from dsa_llm.providers import resolve_llm_mode
    from dsa_agent.state import ReasoningRecord

    reported = set(resolve_llm_mode().as_dict())
    held = set(ReasoningRecord.model_fields)
    assert not reported - held, (
        f"the resolver reports {sorted(reported - held)} but the per-run record cannot hold them"
    )


def test_the_executor_records_every_field_the_resolver_reports(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The report can only be as honest as the row the executor wrote.

    `ReasoningRecord` is built field by field in `run_analysis`, so a field added upstream and not downstream is
    invisible until something needs it -- which is exactly how a "no model was consulted" claim would quietly
    disappear. Each marker value here is distinctive, so a dropped assignment names itself.
    """
    import asyncio

    import dsa_agent.graph as graph
    from dsa_llm.providers import LlmMode

    monkeypatch.setattr("dsa_llm.providers.configured_llm_mode", lambda: "heuristic")
    monkeypatch.setenv("DSA_LLM_MODE", "heuristic")
    monkeypatch.setenv("DSA_ARTIFACT_ROOT", str(tmp_path))
    marker = LlmMode(
        mode="mode-marker",
        provider="provider-marker",
        model="model-marker",
        source="source-marker",
        stub=True,
        error="refusal-marker",
    )
    monkeypatch.setattr(graph, "resolve_llm_mode", lambda: marker)

    ds = tmp_path / "tiny.csv"
    ds.write_text("grp,val\na,1\nb,2\na,3\n", encoding="utf-8")
    state = asyncio.run(graph.run_analysis(str(ds), "ds-tiny", "average val by grp"))

    held = state.reasoning.model_dump() if state.reasoning else {}
    reported = marker.as_dict()
    assert held == reported, f"the run recorded {held}, the resolver reported {reported}"


def test_a_configured_but_unrunnable_model_says_so_in_the_report() -> None:
    """``DSA_LLM_MODE=real`` with no key is a run whose model never answered, and the file must not imply it did.

    The resolver already refuses in words; the record has to carry that refusal, or the report names a provider that
    could not have produced the rows underneath it.
    """
    broken = {
        "mode": "real",
        "provider": "openai",
        "model": None,
        "source": "environment",
        "stub": False,
        "error": "OPENAI_API_KEY is not set",
    }
    line = _line(export_markdown(_state(broken), "audited"))
    assert "could not answer" in line and "OPENAI_API_KEY is not set" in line, line
    zh = _line(export_markdown(_state(broken, objective="哪些群体存活率最高？"), "audited"))
    assert "所配置的模型未能应答" in zh, zh
