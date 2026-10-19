"""R-13h: a report keeps the language the run was asked in, and only its own words move.

`docs/FRONTEND_IA.md` states the rule -- "The deliverable is not translated -- a report keeps the language the
run was asked in" -- and until this file the second half of it was unimplemented: `report_export.py` printed
`## Limitations`, `**Objective:**`, `<h2>Tool Calls</h2>` and `<html lang="en">` no matter what the run was
asked. A Chinese question therefore produced a document that was Chinese in its findings and English in every
word the *product* said about them, and told the browser the whole file was English -- which is what a screen
reader uses to choose a pronunciation, so the lie had a consequence.

The two halves are asserted separately on purpose:

* the product's own labels change with the run's question;
* the run's bytes never change -- a claim, a message or a finding is reproduced verbatim in both renderings,
  because machine-translating a statistician's sentence is how a number gets lost.

The shape of the run state is transcribed from the producers (`AnalysisState`, and the API persists exactly this
mapping through `state_json`), not guessed from what the renderer reads.
"""

from __future__ import annotations

import html as html_module
from typing import Any

import pytest
from dsa_agent import report_export as _module
from dsa_agent.report_export import (
    REPORT_LABELS,
    export_html,
    export_markdown,
    report_language,
)

SHA256 = "05e300aca0537fcc850cbd06c0649e3c869163a180daec4e7a20e002d1ad6044"

ZH_QUERY = "哪些地区的收入增长最快？活动分组之间的差异显著吗？"
EN_QUERY = "Which regions drove revenue, and is the campaign_group gap significant?"


def _run(query: str, **overrides: Any) -> dict[str, Any]:
    """One completed run, in the mapping form the API persists.

    The ids and field names come from the real producers: `run-<hex>` for the run, `TC-<hex>` for a call,
    `E-<hex>` for evidence, `I-<hex>` for an insight, and `statistical_test` as a source type.
    """
    state: dict[str, Any] = {
        "run_id": "run-d43b3d1b9a",
        "dataset_id": "9bdfe7ad-b389-4932-a7cb-25c8aa7ebf94",
        "user_query": query,
        "objective": query,
        "status": "COMPLETED",
        "created_at": "2026-10-11T05:17:46+00:00",
        "plan": [
            {
                "id": "s01",
                "name": "Correlation",
                "description": "Pearson r",
                "tool": "correlation_analysis",
            }
        ],
        "tool_calls": [
            {
                "call_id": "TC-59543dbd",
                "tool": "correlation_analysis",
                "input": {"x": "revenue", "y": "price"},
                "output": {"r": 0.5857584322795393},
                "status": "error",
                "duration_ms": 12,
                "error": "column 'price' not found",
            }
        ],
        "evidence": [
            {
                "id": "E-22b3922b",
                "source_type": "statistical_test",
                "source_id": "TC-59543dbd",
                "claim": "Correlation revenue vs price: r=0.586",
                "result": {"r": 0.5857584322795393},
                "confidence": 0.8,
                "validation_status": "verified",
            }
        ],
        "insights": [
            {
                "id": "I-c9de6a2f",
                "finding": "Tier-1 regions contribute 62% of revenue",
                "evidence_ids": ["E-22b3922b"],
                "limitation": "only one predictor was tested",
            }
        ],
        "validation_results": [
            {"check": "evidence_coverage", "passed": False, "message": "Insight I-c9de6a2f ok"},
        ],
    }
    state.update(overrides)
    return state


def test_the_decision_reads_the_questions_not_the_content() -> None:
    """Chinese question -> Chinese report; English question -> English report, whatever the body says."""
    assert report_language(_run(ZH_QUERY)) == "zh"
    assert report_language(_run(EN_QUERY)) == "en"
    # A mixed question is decided by the prose, not by one pasted token: people paste the file they mean.
    assert report_language(_run("run the EDA on 商品销量.csv")) == "en"
    assert report_language(_run("")) == "en", (
        "a run with no question must not be guessed into a language"
    )


def test_the_product_own_words_move_with_the_run() -> None:
    """Every heading and field name the exporter owns follows the language, in both renderings."""
    zh = export_markdown(_run(ZH_QUERY))
    en = export_markdown(_run(EN_QUERY))
    for heading in ("## 洞察", "## 局限", "## 工具调用", "## 证据", "## 校验", "## 计划"):
        assert heading in zh, f"a Chinese run's markdown lost {heading}"
        assert heading not in en
    for english in ("## Insights", "## Limitations", "## Tool Calls", "**Objective:**"):
        assert english in en, (
            f"the English rendering changed -- it must stay byte-identical: {english}"
        )
        assert english not in zh
    assert "**目标：**" in zh
    assert "# 分析报告 — run-d43b3d1b9a" in zh


def test_the_html_declares_the_language_it_actually_uses() -> None:
    """`lang` is not decoration: it is how a screen reader picks a pronunciation table."""
    zh = export_html(_run(ZH_QUERY))
    en = export_html(_run(EN_QUERY))
    assert '<html lang="zh">' in zh
    assert "<title>分析报告</title>" in zh
    assert "<h2>工具调用</h2>" in zh and "<h2>Tool Calls</h2>" not in zh
    assert "局限：" in zh and "错误：" in zh and "置信度" in zh
    assert '<html lang="en">' in en and "<h2>Tool Calls</h2>" in en
    assert "error:" in en and "confidence" in en


def test_the_runs_own_bytes_are_never_translated() -> None:
    """The finding, the claim and the validation message are reproduced verbatim in both documents.

    This is the half the rule protects: if a label translation ever grew into re-rendering content, the number
    a reviewer came to check would be a number nobody computed.
    """
    for render in (export_markdown, export_html):
        # The HTML rendering escapes an apostrophe the way a document must; comparing the unescaped text keeps
        # the claim about *content* rather than about escaping.
        out = html_module.unescape(render(_run(ZH_QUERY)))
        assert "Tier-1 regions contribute 62% of revenue" in out
        assert "Correlation revenue vs price: r=0.586" in out
        assert "0.5857584322795393" in out
        assert "column 'price' not found" in out
        assert "Insight I-c9de6a2f ok" in out


def test_every_label_exists_in_both_languages() -> None:
    """One table, two complete columns -- the same shape the web dictionary is held to."""
    assert len(REPORT_LABELS) >= 20, (
        f"{len(REPORT_LABELS)} keys -- the table shrank under what the renderers use"
    )
    incomplete = sorted(
        key
        for key, forms in REPORT_LABELS.items()
        if set(forms) != {"en", "zh"} or not all(v.strip() for v in forms.values())
    )
    assert not incomplete, f"{incomplete} do not carry both languages"
    latin_only = sorted(key for key, forms in REPORT_LABELS.items() if forms["zh"] == forms["en"])
    assert not latin_only, (
        f"{latin_only} say the same thing in Chinese, so switching changes nothing"
    )


def test_the_limitations_the_product_writes_are_in_the_runs_language() -> None:
    """Three limitation sentences are the product's own prose, so they move; the run's do not.

    Distinguishing them matters more here than anywhere else in the report: a caveat is the one line a reader
    acts on, and a Chinese report whose caveat is English is a report whose warning gets skipped.
    """
    state = _run(
        ZH_QUERY,
        insights=[
            {
                "id": "I-9a0b1c2d",
                "finding": "x",
                "evidence_ids": [],
                "limitation": "样本量偏小，估计不稳",
            }
        ],
        evidence=[
            {
                "id": "E-1",
                "source_type": "test",
                "source_id": "TC-1",
                "claim": "Uplift (Causal inference is not established.)",
                "result": {},
                "confidence": 0.5,
                "validation_status": "verified",
            }
        ],
        error="tool timed out",
    )
    zh = "\n".join(_module.derived_limitations(state))
    en = "\n".join(
        _module.derived_limitations(
            _run(
                EN_QUERY,
                **{
                    "insights": state["insights"],
                    "evidence": state["evidence"],
                    "error": state["error"],
                },
            )
        )
    )
    assert "一条结论被改写了，因为缺少因果证据：" in zh
    assert "本次运行记录了错误：" in zh
    assert "在建立因果证据之前，相关不等于因果。" in zh
    assert "One claim was rewritten" not in zh and "The run recorded an error" not in zh
    assert "Correlation does not imply causation" in en and "One claim was rewritten" in en
    # the caveat the critic wrote and the error the run recorded are quoted, never translated, in either
    assert "样本量偏小，估计不稳" in zh and "样本量偏小，估计不稳" in en
    assert "tool timed out" in zh and "tool timed out" in en
    # and the report the reader opens carries the same prose in both renderings
    assert "在建立因果证据之前" in export_markdown(state)
    assert "在建立因果证据之前" in html_module.unescape(export_html(state))


def test_every_label_is_reachable_and_both_forms_are_rendered() -> None:
    """No label may exist in the table without a code path that prints it.

    The conditional ones -- an artifact line, a chart, a dataset hash, a check that failed without saying why, a
    run with no insights -- are reached by a second fixture rather than excused, because an unread label is a
    label somebody stopped rendering, and the pair then silently disagrees with the table. Each key is checked
    in English *and* Chinese, so a branch that only ever prints one language is named here too.
    """

    def conditional(query: str) -> dict[str, Any]:
        base = _run(query)
        base["insights"] = []
        base["error"] = "tool timed out"
        # A claim carrying the critic's marker is what makes the "rewritten" caveat render, and an empty
        # validation message the fallback -- both branches are conditional, so reaching them is the point.
        base["evidence"] = [
            {
                "id": "E-22b3922b",
                "source_type": "statistical_test",
                "source_id": "TC-1",
                "claim": f"Uplift attributable to launch {_module.CAUSAL_REWRITE_MARKER}",
                "result": {},
                "confidence": 0.5,
                "validation_status": "verified",
            }
        ]
        base["validation_results"] = [
            {"check": "statistical_power", "passed": False, "message": ""}
        ]
        base["tool_calls"] = [
            {
                "call_id": "TC-4f2a1c90",
                "tool": "create_chart",
                "input": {"kind": "bar"},
                "output": {"artifact_path": "/var/lib/dsa/output/charts/chart.png"},
                "status": "ok",
                "duration_ms": 41,
            },
            # The hash a report prints is the one the profile call computed, read out of that call's own output.
            # It is not a field of the run, so a fixture that set one at the top level would certify a fiction
            # and the label would still be unreachable.
            {
                "call_id": "TC-77c1d2e0",
                "tool": "profile_dataset",
                "input": {"dataset_path": "/var/lib/dsa/datasets/sales.csv"},
                "output": {"sha256": SHA256, "rows": 1200},
                "status": "ok",
                "duration_ms": 88,
            },
        ]
        return base

    both = {
        "en": export_markdown(_run(EN_QUERY))
        + export_html(_run(EN_QUERY))
        + export_markdown(conditional(EN_QUERY))
        + export_html(conditional(EN_QUERY)),
        "zh": export_markdown(_run(ZH_QUERY))
        + export_html(_run(ZH_QUERY))
        + export_markdown(conditional(ZH_QUERY))
        + export_html(conditional(ZH_QUERY)),
    }
    unread: list[str] = []
    for key, forms in REPORT_LABELS.items():
        for lang in ("en", "zh"):
            text = html_module.unescape(both[lang])
            value = forms[lang]
            # A markdown italic marker and a trailing colon are formatting around the label, not part of it.
            needle = value.strip(":._ ")
            if needle not in text:
                unread.append(f"{key}[{lang}]={value!r}")
    assert not unread, f"{unread} are in the table but printed by no rendering"
