"""The report-currency probe in `docs/hosted-demo.md` has to look at the section that owns the wording.

The document told a reader to ask a published run for its HTML report and grep
`<strong>[a-z]+_[a-z_]+</strong>`, reading a hit as "this container predates the validation-label localization".
Measured on the instance redeployed on 2026-10-24, that command printed five hits on a build that is current:
every one of them sat in the **Tool Calls** section, where naming the tool by its wire identifier is the correct
output (`correlation_analysis`, `profile_dataset`). The instruction therefore asked for a value the product never
writes anywhere else, and `False` was unreachable -- so the reading that decided "a redeploy is owed" twice was
not a reading about the deployment at all.

The fix is not a different word list but a different *section*, so this file pins the three things the scoped
probe quietly depends on:

* validation is the last `<h2>` the exporter writes (the probe finds it by position, not by heading text, so
  it answers the same question on an English and a Chinese document);
* the scoped probe is empty on a current rendering in both languages;
* the scoped probe is not a decoration -- a validation item written with the engine's key is caught.

The unscoped shape is asserted too, in the direction that shows the two sections differ: the old pattern must
still hit, and only in Tool Calls. Delete that assertion and a later edit could re-widen the probe without
anything reddening.
"""

from __future__ import annotations

import re
from typing import Any

from dsa_agent.report_export import export_html

ZH_QUERY = "哪些特征对收入最重要？活动分组之间的差异显著吗？"
EN_QUERY = "Which features matter most for revenue, and is the campaign_group gap significant?"

#: The pattern `docs/hosted-demo.md` carried until 2026-10-24: every lower-case identifier anywhere in the file.
_UNSCOPED = re.compile(r"<strong>([a-z]+_[a-z_]+)</strong>")
#: The identifier shape the engine uses for a check key and for a tool name alike.
_ENGINE_KEY = re.compile(r"[a-z][a-z0-9_]*")


def _state(query: str) -> dict[str, Any]:
    """A completed run in the mapping the API persists, with both identifier-bearing sections populated."""
    return {
        "run_id": "run-5127fbfa7e",
        "dataset_id": "ec856391-45d0-4739-b2da-20f6e042d090",
        "user_query": query,
        "objective": query,
        "status": "COMPLETED",
        "created_at": "2026-10-24T03:20:14",
        "plan": ["- profile the dataset"],
        "tool_calls": [
            {
                "call_id": "TC-0a1b2c3d",
                "tool": "correlation_analysis",
                "status": "ok",
                "duration_ms": 12,
                "error": None,
            },
            {
                "call_id": "TC-4e5f6a7b",
                "tool": "profile_dataset",
                "status": "ok",
                "duration_ms": 8,
                "error": None,
            },
        ],
        "evidence": [
            {
                "id": "E-5b30bc2a",
                "source_type": "correlation_analysis",
                "claim": "corr(spend, conversions) = 0.61",
            }
        ],
        "insights": [
            {
                "id": "I-05c8b943",
                "finding": "Spend tracks conversions.",
                "limitation": "Association does not imply causation.",
                "evidence_ids": ["E-5b30bc2a"],
            }
        ],
        "validation_results": [
            {"check": "evidence_coverage", "passed": True, "message": "Evidence coverage ok"},
            {
                "check": "unsupported_claim",
                "passed": True,
                "message": "No unsupported causal claims detected",
            },
            {"check": "tool_errors", "passed": True, "message": "No tool errors"},
            {
                "check": "evidence_traceability",
                "passed": True,
                "message": "Evidence E-5b30bc2a traceable",
            },
        ],
    }


def _validation_tail(document: str) -> str:
    """Everything after the final `<h2>` -- the section the exporter writes last."""
    return document.rsplit("<h2>", 1)[-1]


def _raw_engine_keys_in_validation_section(document: str) -> list[str]:
    """The scoped probe `docs/hosted-demo.md` now tells a reader to run."""
    return [
        s
        for s in re.findall(r"<strong>(.*?)</strong>", _validation_tail(document))
        if _ENGINE_KEY.fullmatch(s)
    ]


def test_validation_is_the_last_section_the_exporter_writes() -> None:
    """The probe finds the section by position, so the position is the precondition it rests on."""
    document = export_html(_state(EN_QUERY))
    assert _validation_tail(document).startswith("Validation</h2>")
    zh = export_html(_state(ZH_QUERY))
    assert _validation_tail(zh).startswith("校验</h2>")
    # An `<h2>` after validation would make the rsplit read the wrong section, and the probe would go quiet.
    assert "<h2>" not in _validation_tail(document)


def test_scoped_probe_is_empty_in_the_language_the_run_was_asked_in() -> None:
    assert _raw_engine_keys_in_validation_section(export_html(_state(EN_QUERY))) == []
    assert _raw_engine_keys_in_validation_section(export_html(_state(ZH_QUERY))) == []


def test_unscoped_probe_hits_only_the_tool_calls_section() -> None:
    """Why the old command could not answer its own question.

    It finds the tool names, so it printed the same verdict for a stale container and a current one, and the
    document read that as staleness. The hits are real -- the Tool Calls section legitimately names the tool by
    its wire identifier -- which is exactly why the probe may not look there.
    """
    document = export_html(_state(EN_QUERY))
    hits = _UNSCOPED.findall(document)
    assert {"correlation_analysis", "profile_dataset"} <= set(hits)
    assert _UNSCOPED.findall(_validation_tail(document)) == []
    for hit in _UNSCOPED.finditer(document):
        assert hit.start() < document.rindex("<h2>"), (
            f"{hit.group(1)} moved out of the Tool Calls section"
        )


def test_scoped_probe_fails_when_the_engine_key_reaches_the_document() -> None:
    """A guard that cannot fail is not a guard. Plant the pre-localization shape and catch it."""
    stale = export_html(_state(EN_QUERY)).replace(
        "<strong>Evidence coverage</strong>", "<strong>evidence_coverage</strong>"
    )
    assert _raw_engine_keys_in_validation_section(stale) == ["evidence_coverage"]
    # The unscoped probe cannot tell these two documents apart; the scoped one can.
    assert (
        len(_UNSCOPED.findall(stale)) == len(_UNSCOPED.findall(export_html(_state(EN_QUERY)))) + 1
    )
