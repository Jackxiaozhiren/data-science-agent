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

import ast
import html as html_module
import re
from pathlib import Path

from typing import Any

import pytest
from dsa_agent import report_export as _module
from dsa_agent.report_export import (
    REPORT_LABELS,
    export_html,
    export_markdown,
    report_language,
)

_REPO = Path(__file__).resolve().parents[2]

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
        # A run records who produced it when it begins, and the audited report says so; the label table below
        # reaches its templated forms through this field, so a fixture without it would certify a dead label.
        "reasoning": {
            "mode": "heuristic",
            "provider": "stub",
            "model": None,
            "source": "environment",
            "stub": True,
        },
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
        # The other provenance branch: a named model, and the resolver's own refusal when that model could not
        # answer. Both are conditional sentences, so reaching them here is what keeps their labels alive.
        base["reasoning"] = {
            "mode": "real",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "source": "stored",
            "stub": False,
            "error": "quota exhausted",
        }
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

    def unrecorded(query: str) -> dict[str, Any]:
        """A run stored before the provenance field existed -- the one case the report must not guess about."""
        base = _run(query)
        base["reasoning"] = None
        return base

    both = {
        "en": export_markdown(_run(EN_QUERY))
        + export_html(_run(EN_QUERY))
        + export_markdown(conditional(EN_QUERY))
        + export_html(conditional(EN_QUERY))
        + export_markdown(unrecorded(EN_QUERY))
        + export_html(unrecorded(EN_QUERY)),
        "zh": export_markdown(_run(ZH_QUERY))
        + export_html(_run(ZH_QUERY))
        + export_markdown(conditional(ZH_QUERY))
        + export_html(conditional(ZH_QUERY))
        + export_markdown(unrecorded(ZH_QUERY))
        + export_html(unrecorded(ZH_QUERY)),
    }
    # Every label the module can ask for, read from its own `_lbl(lang, "key")` call sites rather than guessed.
    used_keys: set[str] = set()
    for node in ast.walk(ast.parse(Path(_module.__file__).read_text(encoding="utf-8"))):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", "") == "_lbl"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
        ):
            used_keys.add(str(node.args[1].value))

    unread: list[str] = []
    for key, forms in REPORT_LABELS.items():
        for lang in ("en", "zh"):
            text = html_module.unescape(both[lang])
            value = forms[lang]
            if "{" in value:
                # A templated label never appears verbatim, so it is checked two ways: the module must ask for it,
                # and the longest static run of the sentence must actually be printed by one of these renderings.
                assert key in used_keys, (
                    f"{key}[{lang}] is templated but no `_lbl` call asks for it"
                )
                pieces = [
                    p.strip(":._ ") for p in re.split(r"\{[a-z_]+\}", value) if p.strip(":._ ")
                ]
                needle = max(pieces, key=len) if pieces else ""
            else:
                # A markdown italic marker and a trailing colon are formatting around the label, not part of it.
                needle = value.strip(":._ ")
            if needle and needle not in text:
                unread.append(f"{key}[{lang}]={value!r} (looked for {needle!r})")
    assert not unread, f"{unread} are in the table but printed by no rendering"


def _ts_map(name: str) -> dict[str, str]:
    """One `Record<string, string>` literal from a TypeScript module, parsed rather than trusted."""
    source = _web_file("app/lib/limitations.ts")
    start = source.index(f"export const {name}: Record<string, string> = {{")
    body = source[start : source.index("};", start)]
    return dict(re.findall(r'^\s*"((?:[^"\\]|\\.)*)": "((?:[^"\\]|\\.)*)",', body, re.MULTILINE))


def _web_file(relative: str) -> str:
    return (_REPO / "apps/web" / relative).read_text(encoding="utf-8")


def test_the_limitation_prose_maps_agree() -> None:
    """The producer's constants, the renderer's table and the web's table are one fact, checked in both directions.

    Three places touch these sentences: the engine writes them, `report_export` renders the downloaded document,
    and the run page renders the stored value from the API. Two of those are different languages, so the map
    exists twice -- and a mapping maintained twice is how the report and the panel start telling the reader two
    different things about the same caveat.

    The keys are therefore derived from the producer sources, not retyped here: a fourth constant added to a tool
    shows up as a missing entry in both maps. And each Chinese form is checked to carry the *same severity* as
    the English one, because the web decides how loud a caveat is by keyword matching -- a translation that
    happened to contain a severe word would silently escalate every report that uses it.
    """
    producers = {
        "packages/agent/src/dsa_agent/graph.py",
        "packages/agent/src/dsa_agent/langgraph_graph.py",
        "packages/tools/src/dsa_tools/tools/correlation.py",
        "packages/tools/src/dsa_tools/tools/hypothesis_test.py",
    }
    written: set[str] = set()
    for rel in producers:
        for line in (_REPO / rel).read_text(encoding="utf-8").splitlines():
            # `limitation="..."`, `limitations: str = "..."` and any other annotated default all name the same
            # kind of constant, and a pattern that required the value to follow the name immediately matched one
            # of the three -- which is how this sweep first reported the producer set as a single string.
            for match in re.finditer(
                r'limitation[s]?\s*(?::[^=]*)?=\s*"([^"]*causation[^"]*)"', line
            ):
                written.add(match.group(1))
    assert len(written) >= 3, (
        f"the producer sweep found only {sorted(written)} -- the pattern has gone blind"
    )

    missing_from_renderer = sorted(written - set(_module.PRODUCT_PROSE_ZH))
    assert not missing_from_renderer, f"report_export cannot say {missing_from_renderer} in Chinese"
    missing_from_page = sorted(written - set(_ts_map("PRODUCT_LIMITATION_TEXT")))
    assert not missing_from_page, f"the run page cannot say {missing_from_page} in Chinese"

    ts_map = _ts_map("PRODUCT_LIMITATION_TEXT")
    assert ts_map == _module.PRODUCT_PROSE_ZH, (
        f"the two tables disagree: renderer-only {set(_module.PRODUCT_PROSE_ZH) - set(ts_map)}, "
        f"page-only {set(ts_map) - set(_module.PRODUCT_PROSE_ZH)}"
    )

    severe = re.findall(
        r'"([^"]+)",',
        _web_file("app/lib/limitations.ts").split("SEVERE_LIMITATIONS = [")[1].split("];")[0],
    )
    for english, chinese in _module.PRODUCT_PROSE_ZH.items():
        assert any("\u3400" <= ch <= "\u9fff" for ch in chinese), (
            f"{english!r} was 'translated' into English"
        )
        loud_en = any(word in english.lower() for word in severe if word.isascii())
        loud_zh = any(word in chinese for word in severe if not word.isascii())
        assert loud_en == loud_zh, (
            f"{english!r} -> {chinese!r} changes how loud the caveat is "
            f"(english severe={loud_en}, chinese severe={loud_zh}); severity is keyword-matched, so the "
            "translation must not pick up or drop a defect word"
        )


def _produced_check_keys() -> set[str]:
    """Every check name the engine can put into a run's `validation_results`, read from the producers.

    The *shape* decides, not the file or the word. A key counts when it is the `check=` of a
    `ValidationResult(...)` construction or one member of a dict literal carrying all of `check`, `passed` and
    `message` -- the stored record. `assumption_check.py` also writes `{"check": "levene", "passed": ...}`, but
    that is a per-column record inside a tool's *output*, which the report prints as data, so a sweep keyed on
    the bare word `check` demanded a translation for the name of a statistic. The sweep is what found
    `reporting.py` as a fifth producer; hand-listing the modules would have kept it out.
    """
    keys: set[str] = set()
    scanned = 0
    for path in sorted((_REPO / "packages").rglob("*.py")):
        if "_vendor" in path.parts:
            continue
        scanned += 1
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "ValidationResult":
                for keyword in node.keywords:
                    if keyword.arg == "check" and isinstance(keyword.value, ast.Constant):
                        if isinstance(keyword.value.value, str):
                            keys.add(keyword.value.value)
            elif isinstance(node, ast.Dict):
                fields = {
                    key.value: value
                    for key, value in zip(node.keys, node.values, strict=False)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                if {"check", "passed", "message"} <= set(fields):
                    value = fields["check"]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        keys.add(value.value)
    assert scanned > 80, (
        f"only {scanned} package modules parsed -- the walk broke, so the set below is a guess"
    )
    return keys


def _ts_check_labels(locale: str) -> dict[str, str]:
    """The `chk.*` entries of one `UI_STRINGS` block, values included.

    The line break a long value may wrap onto is folded first, for the reason recorded in
    `test_web_locale_parity.py`: without it an entry can be silently invisible and every comparison below
    becomes vacuously true.
    """
    folded = re.sub(r":\s+", ": ", _web_file("lib/locale.ts"))
    parts = folded.split(f"{locale}: {{", 1)
    assert len(parts) == 2, f"UI_STRINGS has no {locale} block written the way this guard parses it"
    body = parts[1].split("\n  },", 1)[0]
    found = dict(re.findall(r'"chk\.([a-z_]+)": "([^"]*)",', body))
    assert found, f"no chk.* key parsed from the {locale} block -- the pattern went blind"
    return found


def test_the_validation_vocabulary_is_named_wherever_a_reviewer_reads_it() -> None:
    """A check is named by the product, on three surfaces, in the reader's language.

    What this found: `export_html` printed `<h2>Validation</h2>` straight from a literal while the markdown it
    is supposed to mirror said `## 校验`, and both listed the engine's identifier (`evidence_coverage`) where
    the same document's limitations block already said 证据覆盖率. The run page showed the identifier too. The
    heading test missed it because it enumerated the markdown headings only -- which is the same hole as every
    earlier R-13 miss: a guard that lists one rendering certifies the other by wish.
    """
    produced = _produced_check_keys()
    assert len(produced) >= 8, (
        f"the producers declare only {sorted(produced)} -- the shape rule has gone blind"
    )

    english_map = _module._CHECK_LABELS
    chinese_map = _module._CHECK_LABELS_ZH
    unnamed = sorted(produced - set(english_map))
    assert not unnamed, f"a run can report {unnamed} and the document has no words for it"
    assert set(english_map) == set(chinese_map), (
        f"the two columns disagree on which checks exist: {sorted(set(english_map) ^ set(chinese_map))}"
    )
    for key in english_map:
        assert any("\u3400" <= ch <= "\u9fff" for ch in chinese_map[key]), (
            f"{key} was 'translated' into English"
        )
        assert chinese_map[key] != english_map[key], f"{key} says the same thing in Chinese"

    # The page and the document must not call the same check by two names, in either language.
    for locale, table in (("en", english_map), ("zh", chinese_map)):
        web = _ts_check_labels(locale)
        assert set(web) == set(table), (
            f"the run page and the report name different checks in {locale}: "
            f"page-only {sorted(set(web) - set(table))}, report-only {sorted(set(table) - set(web))}"
        )
        differ = sorted(k for k in table if web[k] != table[k])
        assert not differ, (
            f"{differ} are worded differently on the page than in the downloaded report ({locale})"
        )

    # Wired, not merely available: an unmapped key would still render as the identifier.
    zh_md, en_md = export_markdown(_run(ZH_QUERY)), export_markdown(_run(EN_QUERY))
    assert "**证据覆盖率**" in zh_md and "**Evidence coverage**" not in zh_md
    assert "**Evidence coverage**" in en_md
    zh_html, en_html = export_html(_run(ZH_QUERY)), export_html(_run(EN_QUERY))
    assert "<h2>校验</h2>" in zh_html and "<h2>Validation</h2>" not in zh_html
    assert "<h2>Validation</h2>" in en_html
    assert (
        "<strong>证据覆盖率</strong>" in zh_html and "<strong>Evidence coverage</strong>" in en_html
    )
    for document in (zh_md, en_md, zh_html, en_html):
        assert "evidence_coverage" not in document, (
            "the internal identifier is still on the page as a label"
        )
    # and the sentence the engine wrote about the check is untouched, in either language
    assert "Insight I-c9de6a2f ok" in zh_md and "Insight I-c9de6a2f ok" in zh_html

    inspector = _web_file("app/analysis/[runId]/RunInspector.tsx")
    assert "checkLabel(locale, v.check)" in inspector, (
        "the validation list stopped naming the check in the visitor's language"
    )
    assert "<strong>{v.check}" not in inspector
