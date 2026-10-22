"""The policy for served HTML has to name the blocks the served bytes actually contain.

``SecurityHeadersMiddleware`` answers every request with ``default-src 'none'; frame-ancestors 'none'``, which is the
right posture for a JSON API and fatal for the two routes this product also serves as documents. Measured on a live
instance on 2026-10-21: ``/mcp-app/`` answered HTTP 200 and Chromium logged ``Executing inline script violates the
following Content Security Policy directive 'default-src 'none'''``, so the page that the MCP client opens offered
zero dataset options while its own server published thirty, and its ``fetch`` to ``/mcp`` would have been blocked by
the ``connect-src`` fallback even if the script had run. Every test of that page had used ``TestClient``, which
executes no JavaScript: the surface was "accepted" in the ledger without ever having been rendered.

These guards hold the shape of the fix. What the fix *does* -- options appearing, the report frame holding a styled
document with its drill-downs -- is asserted in the browser by ``apps/web/scripts/mcp-app-page.mjs``, which the gate
mirror already runs.
"""

from __future__ import annotations

from html.parser import HTMLParser

from dsa_agent.report_export import document_security_headers, export_html
from dsa_api.main import app as main_app
from dsa_mcp.app import HTML as APP_PAGE
from fastapi.testclient import TestClient

_REPORT_STATE = {
    "run_id": "run-csp-guard",
    "status": "COMPLETED",
    "objective": "Does the served report carry its own policy?",
    "user_query": "Does the served report carry its own policy?",
}


class _Blocks(HTMLParser):
    """Count inline blocks and style attributes with a parser, not a line scan."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.script = 0
        self.style = 0
        self.style_attributes = 0
        self._inside: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._inside = tag
        self.style_attributes += sum(1 for name, _ in attrs if name == "style")

    def handle_endtag(self, tag: str) -> None:
        if tag == self._inside:
            if tag == "script":
                self.script += 1
            else:
                self.style += 1
            self._inside = None


def _blocks(document: str) -> _Blocks:
    parser = _Blocks()
    parser.feed(document)
    return parser


def _directive(policy: str, name: str) -> str:
    for part in policy.split(";"):
        stripped = part.strip()
        if stripped.startswith(f"{name} "):
            return stripped[len(name) + 1 :].strip()
    return ""


def _sources(value: str) -> list[str]:
    return [token for token in value.split() if token.startswith("'sha256-")]


def test_the_policy_names_every_block_and_only_those() -> None:
    for name, document in (("mcp app page", APP_PAGE), ("report", export_html(_REPORT_STATE))):
        policy = document_security_headers(document)["Content-Security-Policy"]
        blocks = _blocks(document)
        assert _directive(policy, "default-src") == "'none'", f"{name} lost its baseline: {policy}"
        assert len(_sources(_directive(policy, "script-src"))) == blocks.script, (
            f"{name}: script-src names {len(_sources(_directive(policy, 'script-src')))} blocks, "
            f"the document has {blocks.script}"
        )
        assert len(_sources(_directive(policy, "style-src"))) == blocks.style, (
            f"{name}: style-src names {len(_sources(_directive(policy, 'style-src')))} blocks, "
            f"the document has {blocks.style}"
        )
        assert "'unsafe-inline'" not in policy, (
            f"{name} opened a wildcard instead of naming its blocks: {policy}"
        )
        assert "'unsafe-eval'" not in policy, f"{name} permits eval: {policy}"
        assert blocks.style_attributes == 0, (
            f"{name} gained inline style attributes, which no hash can admit -- the policy would have to relax"
        )


def test_the_report_forbids_script_and_the_app_page_allows_its_own_work() -> None:
    report = document_security_headers(export_html(_REPORT_STATE))["Content-Security-Policy"]
    assert _directive(report, "script-src") == "'none'", (
        f"the served report is meant to carry no script at all: {report}"
    )
    assert "data:" in _directive(report, "img-src"), (
        f"charts travel inside the report as data URIs, and a policy that drops data: blanks them: {report}"
    )
    assert "frame-src" not in report, (
        f"the report embeds no frame, so it should not permit one: {report}"
    )

    page = document_security_headers(APP_PAGE)["Content-Security-Policy"]
    assert _sources(_directive(page, "script-src")), (
        "the App page's own script is unnamed, so it will not run"
    )
    assert _directive(page, "connect-src") == "'self'", (
        f"the page calls /mcp on its own origin; a missing connect-src falls back to 'none': {page}"
    )
    assert _directive(page, "frame-src") == "'self'", (
        f"the report frame it embeds is not permitted: {page}"
    )


def test_one_extra_byte_inside_a_block_changes_the_policy() -> None:
    """The hash list is a function of the bytes, so a page that changes must be re-readmitted by name."""
    original = document_security_headers(APP_PAGE)["Content-Security-Policy"]
    touched = APP_PAGE.replace("let lastDataset = '';", "let lastDataset = ' ';", 1)
    assert touched != APP_PAGE, "the edit found no anchor, so this comparison proves nothing"
    changed = document_security_headers(touched)["Content-Security-Policy"]
    assert original != changed, (
        "the policy survived an edit to the page's own script: it cannot be derived from the document"
    )


def test_the_host_middleware_leaves_a_route_set_policy_alone() -> None:
    with TestClient(main_app) as client:
        page = client.get("/mcp-app/")
        assert page.status_code == 200, page.text[:200]
        served = page.headers.get("content-security-policy", "")
        assert "script-src 'sha256-" in served, (
            f"the App page arrived without a policy that admits its own script: {served!r}"
        )
        assert served != "default-src 'none'; frame-ancestors 'none'", (
            "the JSON default is still being applied to the HTML route"
        )
        assert page.headers.get("x-frame-options") == "DENY", (
            f"nothing may frame the App page: {page.headers.get('x-frame-options')}"
        )

        framed = client.get("/mcp-app/report/run-that-does-not-exist")
        assert framed.status_code == 404, framed.text[:200]
        assert (
            framed.headers.get("content-security-policy")
            == "default-src 'none'; frame-ancestors 'none'"
        ), "the strict default should still cover a JSON answer"

        # `docs/api.md` promises four hardening headers on responses, and nothing in the suite read any of them
        # before this file. The JSON answer is where the blanket policy belongs, so its companions are pinned here.
        for header, expected in (
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "same-origin"),
            ("X-Frame-Options", "DENY"),
        ):
            assert framed.headers.get(header) == expected, (
                f"{header} is documented as always set; the JSON 404 carried {framed.headers.get(header)!r}"
            )
