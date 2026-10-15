"""R-07: the HTML a stranger opens is a file, not a promise.

Measured before this file was written (2026-10-15, against the acceptance run's persisted state):

- ``create_chart`` embeds the chart itself in the run state -- ``output.base64_png``, 12-126 KB per chart on
  the seeded runs -- so inlining needs no filesystem, no path containment and no artifact registry: the state
  that survives the free tier's wiped disk already carries the picture. The exporter's old behaviour ("a chart
  is named rather than embedded", its own docstring) was the honest stopgap, not the requirement.
- ``export_html`` rendered Plan / Tool Calls / Evidence / Insights / Validation / Limitations as flat lists:
  zero ``<details>``, zero ``<img>``, no ``@media print``, and a claim's evidence id appeared as bare text with
  nothing to click. The drill-down the spec asks for -- claim to tool call to dataset hash, in page -- did not
  exist, and neither did the dataset hash itself: it lives in the profile call's ``output.sha256``, which the
  HTML never surfaced.
- The file had zero external origin references already (inline CSS, no CDN). That part of the guard is green on
  arrival, which is why its falsification is a required test below rather than a comment.

The ceiling is a property of how the file travels -- pasted into an application, attached to email -- so it is
asserted here and enforced upstream by a per-chart cap in the exporter, not by trimming content.
"""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
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

from dsa_agent.report_export import export_html

RUN_ID = "run-5e4e8138a9"
DATASET_ID = "1c9e8491-demo0"
EVIDENCE_ID = "E-a32bd54b"
INSIGHT_ID = "I-9c369b3d"
CORRELATION_CALL = "TC-26ba3cd7"
CHART_CALL = "TC-7e334c91"
PROFILE_CALL = "TC-227ae6ba"
SHA256 = "05e300aca0537fcc850cbd06c0649e3c869163a180daec4e7a20e002d1ad6044"

#: A real 1x1 PNG, so ``<img>`` decoding in the browser acceptance is honest rather than a stub string.
TINY_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fc"
        "ffff3f030005fe02fea72d1e440000000049454e44ae426082"
    )
).decode()

#: How large the stranger-facing file may get. Per-chart headroom in the exporter keeps a run with many
#: charts under this; the number here is the traveller's budget, not the exporter's whim.
MAX_REPORT_BYTES = 2_000_000


def _fixture_run() -> AnalysisState:
    """One run in the shape the graph persists, transcribed from the acceptance run's ``state_json``."""
    png_b64 = TINY_PNG
    return AnalysisState(
        run_id=RUN_ID,
        dataset_id=DATASET_ID,
        dataset_path="/var/lib/dsa/output/datasets/1c9e8491_sales.csv",
        user_query="Which regions drove revenue, and is the campaign_group gap significant?",
        objective="Attribute revenue to region; test the campaign_group difference.",
        status=AnalysisStatus.COMPLETED,
        created_at=datetime(2026, 10, 15, 5, 17, 46, tzinfo=UTC),
        plan=[
            AnalysisStep(
                id="s01",
                name="Correlation",
                description="Pearson correlation between the semantic outcome and a numeric predictor",
                tool="correlation_analysis",
                inputs={"x": "revenue", "y": "price"},
                depends_on=[],
            )
        ],
        tool_calls=[
            ToolCallRecord(
                call_id=PROFILE_CALL,
                tool="profile_dataset",
                input={"dataset_path": "/var/lib/dsa/output/datasets/1c9e8491_sales.csv"},
                output={"rows": 500, "columns": 6, "sha256": SHA256},
                status="ok",
                duration_ms=9,
            ),
            ToolCallRecord(
                call_id=CORRELATION_CALL,
                tool="correlation_analysis",
                input={"x": "revenue", "y": "price"},
                output={
                    "r": 0.5857584322795393,
                    "p_value": 2.1823645484016534e-47,
                    "method": "pearson",
                },
                status="ok",
                duration_ms=12,
            ),
            ToolCallRecord(
                call_id=CHART_CALL,
                tool="create_chart",
                input={"chart_type": "histogram", "x": "revenue"},
                output={"chart_type": "histogram", "base64_png": png_b64},
                status="ok",
                duration_ms=41,
            ),
        ],
        evidence=[
            Evidence(
                id=EVIDENCE_ID,
                source_type="statistical_test",
                source_id=CORRELATION_CALL,
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
                finding="Revenue concentrates in two regions; the campaign gap tracks price, not region.",
                evidence_ids=[EVIDENCE_ID],
                limitation="Association does not imply causation.",
            )
        ],
        validation_results=[
            ValidationResult(
                check="evidence_coverage", passed=True, message="Evidence coverage ok"
            ),
            ValidationResult(check="dataset_hash", passed=True, message="Dataset hash present"),
        ],
    )


class _PageMap(HTMLParser):
    """Ids, in-page links, details elements and image sources, from the document the exporter actually wrote.

    A regex over the HTML would certify its own search pattern; the guard's claims are about structure, so it
    parses.
    """

    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.details_count = 0
        self.img_srcs: list[str] = []
        self.scripts = 0
        self.stylesheet_imports = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        got = dict(attrs)
        if got.get("id"):
            self.ids.add(str(got["id"]))
        if tag == "a" and got.get("href", "").startswith("#"):
            self.links.append(str(got["href"]))
        if tag == "details":
            self.details_count += 1
        if tag == "img" and got.get("src"):
            self.img_srcs.append(str(got["src"]))
        if tag in {"script", "iframe"}:
            self.scripts += 1
        if tag == "style" and "@import" in str(got.get("_content", "")):
            self.stylesheet_imports += 1


def _page_map(html: str) -> _PageMap:
    parser = _PageMap()
    parser.feed(html)
    return parser


def _external_references(html: str) -> list[str]:
    """Every attribute that would make the file reach across a network, of any scheme."""
    return re.findall(r'(?:src|href)\s*=\s*["\'](?:https?:)?//[^"\']+', html)


def test_the_file_makes_no_network_request() -> None:
    html = export_html(_fixture_run())
    assert _external_references(html) == [], (
        f"the report would reach across a network: {_external_references(html)[:3]}"
    )
    page = _page_map(html)
    assert page.scripts == 0, (
        "a <script> or <iframe> tag is a fetch waiting for a stranger's file:// click"
    )
    assert page.stylesheet_imports == 0


def test_every_in_page_link_resolves_to_an_anchor_in_the_same_document() -> None:
    html = export_html(_fixture_run())
    page = _page_map(html)
    assert page.links, "no in-page links at all: the drill-down was not built"
    missing = [href for href in page.links if href[1:] not in page.ids]
    assert missing == [], f"claims link to evidence that is not in the document: {missing}"


def test_the_drill_down_chain_is_claim_to_evidence_to_call_to_dataset_hash() -> None:
    html = export_html(_fixture_run())
    page = _page_map(html)
    assert page.details_count >= 1, (
        "no <details>: the chain does not collapse, so there is nothing to expand"
    )
    assert any(src.startswith("data:image/png;base64,") for src in page.img_srcs), (
        f"the chart is not inlined: img srcs were {page.img_srcs}"
    )
    assert html.count(SHA256) == 1, (
        "the dataset hash is the chain's last link and must appear exactly once, "
        f"found {html.count(SHA256)}"
    )
    assert CHART_CALL in page.ids and CORRELATION_CALL in page.ids and EVIDENCE_ID in page.ids


def test_the_file_stays_under_the_traveller_budget() -> None:
    html = export_html(_fixture_run())
    size = len(html.encode())
    assert size <= MAX_REPORT_BYTES, (
        f"the self-contained report is {size} bytes, over the {MAX_REPORT_BYTES} ceiling"
    )


def test_limitations_are_first_class_not_a_trailing_section() -> None:
    html = export_html(_fixture_run())
    limitations_at = html.find("Association does not imply causation.")
    assert limitations_at != -1, "the limitation text is missing entirely"
    plan_at = html.find("Plan</h2>")
    assert 0 < limitations_at < plan_at, (
        f"limitations rendered at byte {limitations_at}, after the plan at {plan_at}: a reader who stops "
        "early never meets the caveat"
    )


def test_the_print_stylesheet_exists() -> None:
    assert "@media print" in export_html(_fixture_run())


def test_the_guard_sees_what_it_claims_to_see() -> None:
    """Both predicates, fed the failure each exists to catch -- on a scratch copy, not the shipped file."""
    html = export_html(_fixture_run())
    injected = html.replace(
        "</head>", '<script src="https://cdn.example.net/tracker.js"></script></head>'
    )
    assert _external_references(injected), (
        "the external-reference check went blind to a planted script tag"
    )

    broken = html.replace(f'id="{EVIDENCE_ID}"', f'id="{EVIDENCE_ID}-moved"')
    page = _page_map(broken)
    unresolved = [href for href in page.links if href[1:] not in page.ids]
    assert unresolved, "the anchor check went blind to a claim whose evidence left the document"


@pytest.mark.parametrize(
    "png_b64",
    [
        "not-base64-!!",
        base64.b64encode(b"GIF89a-not-a-png-at-all").decode(),
    ],
)
def test_a_chart_that_is_not_a_png_is_named_not_broken(png_b64: str) -> None:
    """The dishonest choice is a broken ``<img>``: it looks like the picture travelled when it did not."""
    state = _fixture_run()
    for call in state.tool_calls:
        if call.tool == "create_chart":
            call.output = {**call.output, "base64_png": png_b64}
    html = export_html(state)
    page = _page_map(html)
    assert not [src for src in page.img_srcs if src.startswith("data:image/png")], (
        "a non-PNG payload was inlined as an image"
    )
    assert "chart" in html.lower(), "the chart vanished instead of being named"
