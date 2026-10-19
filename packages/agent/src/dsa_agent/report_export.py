"""The one export owner for a finished run (web product plan R-06).

The product's argument is a pair: "here is the conclusion" and "here is the evidence". Study 2 of plan §12
blind-compares the two renderings of the *same* run, so they must not be two documents written by two
hands -- a pair that disagrees about a number is worse than either one alone, because it destroys the
reason to show both. So this module assembles a run once and serialises it twice:

``audited``
    What the graph stores: plan, tool calls, evidence records, validation results, identifiers.
``findings``
    Conclusions, their numbers, and the limitations. No evidence ids, no tool trace, no hashes, no paths.

Both modes read :func:`dsa_agent.run_summary.run_summary`, the run-level contract every interface already
shares, and the plain mode is produced by *dropping* material from the same assembly rather than by
re-deriving anything -- which is what makes the numbers agree by construction instead of by hope.

Two rules live here that each caller would otherwise invent:

:func:`identifier_tokens` -- what counts as trace material. It is here because this is the code that has to
obey it; a test carrying its own regex would certify only the test's opinion of what "plain" means.

:func:`derived_limitations` -- the limitations section, built from validation results, per-insight
limitations, the critic's causal-rewrite marker and the run's own error. Plan R-06.4 forbids the
hand-written-per-case form, and ``report.py`` shipped exactly that: two fixed sentences. The section is
never absent, even when the run found nothing to qualify.
"""

from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from dsa_agent.run_summary import run_summary

#: The two renderings. Anything else is a caller guessing at a mode.
EXPORT_MODES: tuple[str, ...] = ("findings", "audited")

#: The critic's own words (``critic.rewrite_unsupported_claim``). A claim carrying it was rewritten, and
#: that is a limitation of the result, not a note about formatting.
CAUSAL_REWRITE_MARKER = "(Causal inference is not established.)"

#: The floor: a property of the method, true of every observational run, so it stays when nothing else does.
#: Its text lives in ``REPORT_LABELS`` below, because a Chinese run's report should say it in Chinese; the
#: constant stays as the English form so importers and the export tests keep one name to compare against.

#: Identifier shapes that mean "go and look at the trace". Each is named so a violation says which rule it
#: broke rather than only that one did.
_IDENTIFIER_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("run_id", re.compile(r"\brun-[0-9a-f]{4,}\b")),
    ("evidence_id", re.compile(r"\bE-[0-9a-f]{4,}\b")),
    ("insight_id", re.compile(r"\bI-[0-9a-f]{4,}\b")),
    ("artifact_id", re.compile(r"\bA-[0-9a-f]{4,}\b")),
    ("tool_call_id", re.compile(r"\bTC-[0-9a-f]{4,}\b", re.IGNORECASE)),
    ("dataset_id", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")),
    ("sha256", re.compile(r"\b[0-9a-f]{64}\b")),
    # Interior segments may contain spaces (this very repository lives at "/Users/.../Data agent"), but the
    # final segment may not, and the match must land on a dotted extension. Without those two limits the
    # pattern eats the rest of the sentence around a path -- measured on 2026-10-12, where
    # "…/9bdfe7ad_sales.csv with <uuid> and report the r value behind E-…" matched as one "path". Stripping
    # a sentence out of the plain export is worse than leaking an id: the mode promises to drop trace
    # material, not to lose the finding. A directory without an extension is deliberately not matched --
    # every path this product renders is a dataset or artifact file, and a looser rule would eat prose.
    (
        "absolute_path",
        re.compile(r"(?<![\w.])/(?:[\w.\- ]+/)+[\w.\-]+\.[A-Za-z0-9]{1,8}(?![\w])"),
    ),
)

#: Validation check keys, in the words a person who did not write them would use.
_CHECK_LABELS = {
    "evidence_coverage": "Evidence coverage",
    "unsupported_claim": "Causal language",
    "tool_errors": "Tool execution",
    "budget": "Run budget",
    "insight_evidence": "Insight grounding",
    "evidence_traceability": "Evidence traceability",
    "statistical_power": "Statistical power",
}

#: The same seven checks, in the language the run was asked in.
_CHECK_LABELS_ZH = {
    "evidence_coverage": "证据覆盖率",
    "unsupported_claim": "因果表述",
    "tool_errors": "工具执行",
    "budget": "运行预算",
    "insight_evidence": "洞察的依据",
    "evidence_traceability": "证据可追溯性",
    "statistical_power": "统计功效",
}

#: Every word this file says *about* a run. A report keeps the language the run was asked in
#: (`docs/FRONTEND_IA.md`), and the headings, field names and fallback sentences are the product's own words,
#: not the analyst's -- so they are chosen here by ``report_language`` from the run's question. The run's
#: findings, claims, messages and evidence text are never translated: a machine translation of a statistician's
#: sentence is how a number gets lost.
REPORT_LABELS: dict[str, dict[str, str]] = {
    "reportTitle": {"en": "Analysis Report", "zh": "分析报告"},
    "documentTitle": {"en": "Analysis report", "zh": "分析报告"},
    "objective": {"en": "Objective:", "zh": "目标："},
    "status": {"en": "Status:", "zh": "状态："},
    "generated": {"en": "Generated:", "zh": "生成时间："},
    "dataset": {"en": "Dataset:", "zh": "数据集："},
    "datasetSha256": {"en": "Dataset sha256:", "zh": "数据集 sha256："},
    "plan": {"en": "Plan", "zh": "计划"},
    "toolCalls": {"en": "Tool Calls", "zh": "工具调用"},
    "evidence": {"en": "Evidence", "zh": "证据"},
    "evidenceInline": {"en": "Evidence:", "zh": "证据："},
    "insights": {"en": "Insights", "zh": "洞察"},
    "validation": {"en": "Validation", "zh": "校验"},
    "limitations": {"en": "Limitations", "zh": "局限"},
    "limitationsLead": {"en": "Limitations.", "zh": "局限："},
    "charts": {"en": "Charts", "zh": "图表"},
    "noInsights": {
        "en": "_No insights yet — analysis may be incomplete or blocked by validation._",
        "zh": "暂无洞察——分析可能尚未完成，或被校验阻断。",
    },
    "noInsightsPlain": {
        "en": "No insights yet — analysis may be incomplete or blocked by validation.",
        "zh": "暂无洞察——分析可能尚未完成，或被校验阻断。",
    },
    "didNotPass": {"en": "the check did not pass", "zh": "该校验未通过"},
    "error": {"en": "error:", "zh": "错误："},
    "artifact": {"en": "artifact:", "zh": "产物："},
    "result": {"en": "result:", "zh": "结果："},
    "confidence": {"en": "confidence", "zh": "置信度"},
    "limitation": {"en": "limitation:", "zh": "局限："},
    # Separators belong to the sentence, so these carry their own trailing space in English and their own
    # full-width colon in Chinese; a template that added " " for both would put a space after 「：」.
    "causalRewritten": {
        "en": "One claim was rewritten because causal evidence is absent: ",
        "zh": "一条结论被改写了，因为缺少因果证据：",
    },
    "recordedError": {"en": "The run recorded an error: ", "zh": "本次运行记录了错误："},
    "standingLimitation": {
        "en": "Correlation does not imply causation unless causal evidence is established.",
        "zh": "在建立因果证据之前，相关不等于因果。",
    },
}

#: A report is Chinese when the question that produced it is mostly Chinese. Counting *words* rather than
#: characters is what keeps that honest in both directions: an English column reference inside a Chinese
#: question must not flip the document, and one Chinese file name inside an English sentence must not either.
_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z0-9_.\-/]+")


def report_language(source: Any) -> str:
    """The language the run was asked in, which is the language its report keeps.

    The decision reads the run's own objective/question, never a visitor setting: the artifact a reviewer opens
    offline ten minutes later is not a page, and it must not change language between readers.
    """
    text = str(_field(source, "objective") or _field(source, "user_query") or "")
    cjk = len(_CJK_RE.findall(text))
    tokens = cjk + len(_LATIN_WORD_RE.findall(text))
    if not tokens:
        return "en"
    return "zh" if cjk * 2 > tokens else "en"


STANDING_LIMITATION = REPORT_LABELS["standingLimitation"]["en"]


def _lbl(lang: str, key: str) -> str:
    return REPORT_LABELS[key][lang]


def final_report_status(status: Any) -> str:
    """The terminal state a report should name.

    Reports are rendered during the ``REPORTING`` phase and the graph moves to ``COMPLETED`` immediately
    afterwards, so stamping the raw value would make a successful run look stuck in the artifact a reviewer
    reads. ``report.py`` did this inline; it lives here so both serialisations agree.
    """
    value = str(status or "")
    return "COMPLETED" if value == "REPORTING" else value


def _field(source: Any, name: str, default: Any = None) -> Any:
    """One scalar from a state model or its serialized dict, the way ``run_summary`` already must."""
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def identifier_tokens(text: str) -> list[str]:
    """Every trace-material token in ``text``, as ``"<rule>: <token>"``.

    Empty means the text can be handed to someone who is not being asked to audit anything.
    """
    found: list[str] = []
    for rule, pattern in _IDENTIFIER_RULES:
        found.extend(f"{rule}: {token}" for token in pattern.findall(text))
    return found


def strip_identifiers(text: str) -> str:
    """Remove identifier tokens and tidy the gap each leaves.

    Numbers are never touched: the plain export has to agree with the audited one about every figure, and
    an identifier is the only thing this function may lose.
    """
    cleaned = text
    for _, pattern in _IDENTIFIER_RULES:
        cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).replace(" )", ")").strip()


def _label(check: Any, lang: str = "en") -> str:
    key = str(check or "")
    if lang == "zh":
        return _CHECK_LABELS_ZH.get(key, key.replace("_", " ").strip() or "校验项")
    return _CHECK_LABELS.get(key, key.replace("_", " ").strip() or "Check")


def derived_limitations(source: Any, lang: str | None = None) -> list[str]:
    """What this run says is weak about itself, assembled only from records that already exist.

    The wording of the three sentences this function writes is the product's, so it follows the language
    the run was asked in -- decided from the run itself when a caller does not pass one, which is what lets
    an API or CLI caller get the right document without learning about languages at all. The insights'
    own `limitation` text and the recorded error are copied verbatim: they are the run's bytes.
    """
    summary = run_summary(source)
    if lang is None:
        lang = report_language(source)
    collected: list[str] = []

    for result in summary.get("validation_results") or []:
        if result.get("passed"):
            continue
        message = str(result.get("message") or "").strip() or _lbl(lang, "didNotPass")
        collected.append(f"{_label(result.get('check'), lang)}: {message}")

    for insight in summary.get("insights") or []:
        limitation = str(insight.get("limitation") or "").strip()
        if limitation:
            collected.append(limitation)

    for record in summary.get("evidence") or []:
        claim = str(record.get("claim") or "")
        if CAUSAL_REWRITE_MARKER in claim:
            collected.append(f"{_lbl(lang, 'causalRewritten')}{claim}")

    error = str(summary.get("error") or "").strip()
    if error:
        collected.append(f"{_lbl(lang, 'recordedError')}{error}")

    collected.append(_lbl(lang, "standingLimitation"))

    seen: set[str] = set()
    unique: list[str] = []
    for line in collected:
        if line not in seen:
            seen.add(line)
            unique.append(line)
    return unique


def _generated(source: Any) -> str:
    """When the run happened, read only from immutable run state.

    Two things are wrong with the stamp ``report.py`` wrote. ``datetime.now(UTC)`` made rendering the same
    run twice produce different bytes, which is a defect in a repository whose reviewer task (kit T5) is to
    compare two runs of one question. And deriving it from ``updated_at`` is not stable either: the measured
    capture showed the stored ``audited`` report and an on-demand ``findings`` render of the *same* run
    disagreeing by microseconds, because the row's status write touches that field after the report is
    composed. ``created_at`` is the one timestamp a finished run cannot change, so both renderings agree.
    """
    for key in ("created_at", "updated_at"):
        value = _field(source, key)
        if value:
            return str(value)
    return datetime.now(UTC).isoformat()


def _step_text(step: Any) -> str:
    get = (
        step.get
        if isinstance(step, Mapping)
        else (lambda key, fallback="": getattr(step, key, fallback))
    )
    return f"- **{get('name', '')}** (`{get('tool', '')}`): {get('description', '')}"


def _insight_lines(insights: list[dict[str, Any]], *, plain: bool, lang: str = "en") -> list[str]:
    lines: list[str] = []
    for insight in insights:
        raw = str(insight.get("finding") or "").strip()
        # The finding is model prose, and a run that cites its own evidence inside a sentence would
        # otherwise carry that citation into the document whose promise is that it does not.
        finding = strip_identifiers(raw) if plain else raw
        lines.append(f"- {finding}" if plain else f"- **{insight.get('id')}**: {finding}")
        for key in ("magnitude", "significance", "limitation"):
            value = insight.get(key)
            if value:
                detail = strip_identifiers(f"{value}") if plain else f"{value}"
                lines.append(f"  - {key}: {detail}")
        refs = insight.get("evidence_ids") or []
        if refs and not plain:
            lines.append(f"  - evidence: {', '.join(str(ref) for ref in refs)}")
    return lines


def _evidence_lines(records: list[dict[str, Any]], lang: str = "en") -> list[str]:
    lines: list[str] = []
    for record in records:
        confidence = record.get("confidence")
        confidence_text = (
            f"{float(confidence):.2f}" if isinstance(confidence, (int, float)) else "?"
        )
        lines.append(
            f"- **{record.get('id')}** ({record.get('source_type')} → {record.get('source_id')}) "
            f"— {record.get('claim')} — {_lbl(lang, 'confidence')} {confidence_text} "
            f"— {record.get('validation_status')}"
        )
        if record.get("result"):
            snippet = json.dumps(record["result"], ensure_ascii=False, default=str, sort_keys=True)[
                :600
            ]
            lines.append(f"  - {_lbl(lang, 'result')} `{snippet}`")
    return lines


def _tool_call_lines(calls: list[dict[str, Any]], lang: str = "en") -> list[str]:
    lines: list[str] = []
    for call in calls:
        mark = "✓" if call.get("status") == "ok" else "✗"
        lines.append(
            f"- {mark} **{call.get('tool')}** ({call.get('call_id')}) — {call.get('duration_ms')}ms"
        )
        if call.get("error"):
            lines.append(f"  - {_lbl(lang, 'error')} {call['error']}")
        output = call.get("output") or {}
        artifact = output.get("artifact_path") if isinstance(output, Mapping) else None
        if call.get("tool") == "create_chart" and artifact:
            lines.append(f"  - ![chart]({str(artifact).rsplit('/', 1)[-1]})")
            lines.append(f"  - {_lbl(lang, 'artifact')} `{artifact}`")
    return lines


def _validation_lines(results: list[dict[str, Any]]) -> list[str]:
    return [
        f"- {'✓' if result.get('passed') else '✗'} **{result.get('check')}**: {result.get('message')}"
        for result in results
    ]


def build_sections(source: Any, *, plain: bool) -> list[tuple[str, list[str]]]:
    """The one assembly: front matter then named blocks, empty blocks dropped.

    ``plain`` removes whole sections and every identifier column. It never adds, rephrases or recomputes a
    figure -- that asymmetry is what lets the two documents be compared at all.
    """
    summary = run_summary(source)
    lang = report_language(source)
    raw_objective = str(_field(source, "objective") or _field(source, "user_query") or "").strip()
    # The objective is the user's own sentence, and people paste the file they mean into it.
    objective = strip_identifiers(raw_objective) if plain else raw_objective
    status = final_report_status(summary.get("status"))

    report_title = _lbl(lang, "reportTitle")
    title = f"# {report_title}" if plain else f"# {report_title} — {summary.get('run_id')}"
    front = [title, f"**{_lbl(lang, 'objective')}** {objective}"]
    if plain:
        front.append(
            f"**{_lbl(lang, 'status')}** {status}  |  **{_lbl(lang, 'generated')}** {_generated(source)}"
        )
    else:
        front.append(
            f"**{_lbl(lang, 'dataset')}** `{_field(source, 'dataset_id', '')}`  |  **{_lbl(lang, 'status')}** {status}"
            f"  |  **{_lbl(lang, 'generated')}** {_generated(source)}"
        )

    blocks: list[tuple[str, list[str]]] = [("", front)]

    plan = list(_field(source, "plan", []) or [])
    if plan and not plain:
        blocks.append((_lbl(lang, "plan"), [_step_text(step) for step in plan]))

    if not plain:
        calls = _tool_call_lines(summary.get("tool_calls") or [], lang)
        if calls:
            blocks.append((_lbl(lang, "toolCalls"), calls))
        evidence = _evidence_lines(summary.get("evidence") or [], lang)
        if evidence:
            blocks.append((_lbl(lang, "evidence"), evidence))

    insights = _insight_lines(summary.get("insights") or [], plain=plain, lang=lang)
    blocks.append(
        (
            _lbl(lang, "insights"),
            insights or [_lbl(lang, "noInsights")],
        )
    )

    if not plain:
        validation = _validation_lines(summary.get("validation_results") or [])
        if validation:
            blocks.append((_lbl(lang, "validation"), validation))

    blocks.append(
        (
            _lbl(lang, "limitations"),
            [
                f"- {strip_identifiers(line) if plain else line}"
                for line in derived_limitations(source, lang)
            ],
        )
    )
    return blocks


def export_markdown(source: Any, mode: str = "audited") -> str:
    """Render one run as markdown, in ``findings`` or ``audited`` form."""
    if mode not in EXPORT_MODES:
        raise ValueError(f"unknown export mode {mode!r}; expected one of {EXPORT_MODES}")
    lines: list[str] = []
    for heading, body in build_sections(source, plain=(mode == "findings")):
        if heading:
            lines.append(f"## {heading}")
        lines.extend(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_CSS = (
    "body{font:15px/1.6 system-ui,sans-serif;margin:2rem auto;max-width:46rem;color:#18181b;"
    "padding:0 1rem}h1{font-size:1.5rem;margin-bottom:.25rem}h2{font-size:1.05rem;"
    "margin-top:1.75rem;border-bottom:1px solid #e4e4e7;padding-bottom:.25rem}"
    "p.meta{color:#52525b;font-size:.85rem}ul{padding-left:1.1rem}li{margin:.2rem 0}"
    "code{background:#f4f4f5;padding:.1rem .25rem;border-radius:.25rem;font-size:.85em;"
    "overflow-wrap:anywhere}.fail{color:#b91c1c}.pass{color:#047857}"
    ".chart{max-width:100%;height:auto;border:1px solid #e4e4e7;border-radius:.5rem;margin:.4rem 0}"
    ".limitations{border:1px solid #fde68a;background:#fffbeb;color:#92400e;padding:.6rem .8rem;"
    "border-radius:.5rem;margin:.8rem 0;font-size:.9rem}"
    ".limitations ul{margin:.3rem 0 0;padding-left:1.1rem}"
    "details{border:1px solid #e4e4e7;border-radius:.5rem;padding:.4rem .6rem;margin:.35rem 0}"
    "summary{cursor:pointer;font-weight:600}"
    "@media print{body{margin:0;max-width:none}.chart{max-width:100%}details{border:none;"
    "padding-left:0}a{color:inherit;text-decoration:none}}"
)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _inline(value: Any) -> str:
    """Escape, then render the markdown emphasis this module itself emits.

    The HTML view is built from the same line strings as the markdown view, so without this the reviewer's
    offline file showed literal ``**Profile dataset**`` and backticks -- measured on the first capture, in
    the artifact a reviewer is supposed to read. A chart reference becomes a named line rather than an
    ``<img>``: the image is not embedded until R-07, and a broken image tag would claim otherwise.
    """
    text = _esc(value)
    text = re.sub(r"!\[[^\]]*\]\(([^)]*)\)", r"chart: \1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


#: Per-chart headroom. The seeded runs' charts are 12-126 KB of base64; a cap keeps a pathological run from
#: pushing the stranger-facing file past the traveller budget the offline guard asserts.
_MAX_CHART_B64 = 300_000
_PNG_MAGIC = "iVBORw0KGgo"


def _travelling_charts(source: Any) -> list[tuple[str, str]]:
    """``(alt, data-uri)`` for every chart the run state itself carries, in trace order.

    The state survives the free tier's wiped disk; the filesystem does not, so the picture is read from the
    ``create_chart`` call's own output and never from a path. A payload that is not a PNG, or one over the
    cap, is left out here and named in the trace instead -- a broken ``<img>`` would claim the picture
    travelled when it did not.
    """
    charts: list[tuple[str, str]] = []
    for call in _field(source, "tool_calls", []) or []:
        get = (
            call.get
            if isinstance(call, Mapping)
            else (lambda k, _c=call, d=None: getattr(_c, k, d))
        )
        if get("tool") != "create_chart":
            continue
        output = get("output")
        if not isinstance(output, Mapping):
            continue
        b64 = str(output.get("base64_png") or "")
        if not b64.startswith(_PNG_MAGIC) or len(b64) > _MAX_CHART_B64:
            continue
        kind = str(output.get("chart_type") or "chart")
        charts.append((f"{kind} chart", f"data:image/png;base64,{b64}"))
    return charts


def _named_chart_lines(source: Any, lang: str = "en") -> list[str]:
    """The charts that did *not* travel, named the way the markdown view names them."""
    lines: list[str] = []
    for call in _field(source, "tool_calls", []) or []:
        get = (
            call.get
            if isinstance(call, Mapping)
            else (lambda k, _c=call, d=None: getattr(_c, k, d))
        )
        if get("tool") != "create_chart":
            continue
        output = get("output")
        if not isinstance(output, Mapping):
            continue
        b64 = str(output.get("base64_png") or "")
        if b64.startswith(_PNG_MAGIC) and len(b64) <= _MAX_CHART_B64:
            continue
        artifact = str(output.get("artifact_path") or "").rsplit("/", 1)[-1]
        if artifact:
            lines.append(f"chart: {artifact} (not embedded)")
    return lines


def _dataset_sha256(source: Any) -> str | None:
    """The hash the profile call computed, read from the run's own trace -- the drill-down's last link."""
    for call in _field(source, "tool_calls", []) or []:
        get = (
            call.get
            if isinstance(call, Mapping)
            else (lambda k, _c=call, d=None: getattr(_c, k, d))
        )
        output = get("output")
        if isinstance(output, Mapping):
            value = output.get("sha256")
            if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
                return value
    return None


def export_html(source: Any) -> str:
    """The audited rendering as a single file a stranger opens with no server and no network.

    R-07. The chart travels inside the file -- read from the run state's own ``base64_png``, never from the
    filesystem, because the state is what survives a free tier's wiped disk. Every claim collapses into an
    in-page drill-down: insight to evidence to the tool call that produced it, closed by the dataset hash the
    profile call computed. Limitations lead, because the reader this file exists for brings ten minutes of
    judgement, not an audit session. No ``<script>``, no external origin of any kind; the offline guard
    (``tests/contract/test_report_html_offline.py``) asserts both and plants a script tag to prove it would
    see one.

    Values come from the same ``run_summary`` and state primitives the markdown pair reads; the order and the
    wrapping differ on purpose, because a page a stranger scrolls and a document pasted into a submission are
    read differently.
    """
    summary = run_summary(source)
    lang = report_language(source)
    objective = str(_field(source, "objective") or _field(source, "user_query") or "").strip()
    status = final_report_status(summary.get("status"))
    sha256 = _dataset_sha256(source)

    parts: list[str] = [
        "<!DOCTYPE html>",
        f'<html lang="{lang}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_lbl(lang, 'documentTitle')}</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        f"<h1>{_lbl(lang, 'reportTitle')} — {_esc(summary.get('run_id'))}</h1>",
        f'<p class="meta"><strong>{_lbl(lang, "objective")}</strong> {_inline(objective)}</p>',
        f'<p class="meta"><strong>{_lbl(lang, "dataset")}</strong> <code>{_esc(_field(source, "dataset_id", ""))}</code>'
        f"  |  <strong>{_lbl(lang, 'status')}</strong> {_esc(status)}"
        f"  |  <strong>{_lbl(lang, 'generated')}</strong> {_esc(_generated(source))}</p>",
    ]
    if sha256:
        parts.append(
            f'<p class="meta"><strong>{_lbl(lang, "datasetSha256")}</strong> <code>{_esc(sha256)}</code></p>'
        )

    limitations = derived_limitations(source, lang)
    if limitations:
        parts.append(
            f'<div class="limitations" role="note"><strong>{_lbl(lang, "limitationsLead")}</strong> <ul>'
        )
        parts.extend(f"<li>{_inline(line)}</li>" for line in limitations)
        parts.append("</ul></div>")

    charts = _travelling_charts(source)
    named = _named_chart_lines(source, lang)
    if charts or named:
        parts.append(f"<h2>{_lbl(lang, 'charts')}</h2>")
        parts.extend(f'<img class="chart" alt="{_esc(alt)}" src="{src}">' for alt, src in charts)
        parts.extend(f'<p class="meta">{_esc(line)}</p>' for line in named)

    plan = list(_field(source, "plan", []) or [])
    if plan:
        parts.append(f"<h2>{_lbl(lang, 'plan')}</h2>")
        parts.append("<ul>")
        parts.extend(f"<li>{_inline(line.lstrip('- '))}</li>" for line in map(_step_text, plan))
        parts.append("</ul>")

    parts.append(f"<h2>{_lbl(lang, 'toolCalls')}</h2>")
    parts.append("<ul>")
    for call in summary.get("tool_calls") or []:
        mark = "✓" if call.get("status") == "ok" else "✗"
        klass = ' class="pass"' if mark == "✓" else ' class="fail"'
        parts.append(
            f'<li{klass} id="{_esc(call.get("call_id"))}">{mark} <strong>{_esc(call.get("tool"))}</strong>'
            f" — {_esc(call.get('duration_ms'))}ms</li>"
        )
        if call.get("error"):
            parts.append(f'<li class="fail">{_lbl(lang, "error")} {_esc(call["error"])}</li>')
    parts.append("</ul>")

    parts.append(f"<h2>{_lbl(lang, 'evidence')}</h2>")
    parts.append("<ul>")
    for record in summary.get("evidence") or []:
        confidence = record.get("confidence")
        confidence_text = (
            f"{float(confidence):.2f}" if isinstance(confidence, (int, float)) else "?"
        )
        result = (
            f"<br><code>{_esc(json.dumps(record['result'], sort_keys=True))}</code>"
            if record.get("result")
            else ""
        )
        parts.append(
            f'<li id="{_esc(record.get("id"))}"><strong>{_esc(record.get("id"))}</strong>'
            f' ({_esc(record.get("source_type"))} → <a href="#{_esc(record.get("source_id"))}">'
            f"{_esc(record.get('source_id'))}</a>) — {_inline(record.get('claim'))}"
            f" — {_lbl(lang, 'confidence')} {confidence_text} — {_esc(record.get('validation_status'))}{result}</li>"
        )
    parts.append("</ul>")

    parts.append(f"<h2>{_lbl(lang, 'insights')}</h2>")
    insights = summary.get("insights") or []
    if not insights:
        parts.append(f'<p class="meta">{_lbl(lang, "noInsightsPlain")}</p>')
    for insight in insights:
        parts.append("<details>")
        parts.append(f"<summary>{_inline(insight.get('finding'))}</summary>")
        if insight.get("limitation"):
            parts.append(
                f'<p class="meta">{_lbl(lang, "limitation")} {_inline(insight["limitation"])}</p>'
            )
        links = " ".join(
            f'<a href="#{_esc(eid)}">{_esc(eid)}</a>' for eid in insight.get("evidence_ids") or []
        )
        if links:
            parts.append(f'<p class="meta">{_lbl(lang, "evidenceInline")} {links}</p>')
        parts.append("</details>")

    parts.append("<h2>Validation</h2>")
    parts.append("<ul>")
    for check in summary.get("validation_results") or []:
        mark = "✓" if check.get("passed") else "✗"
        klass = ' class="pass"' if check.get("passed") else ' class="fail"'
        parts.append(
            f"<li{klass}>{mark} <strong>{_esc(check.get('check'))}</strong> — {_esc(check.get('message'))}</li>"
        )
    parts.append("</ul>")

    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"
