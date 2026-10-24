"""The probes `docs/hosted-demo.md` hands a reader answer in every direction, and their literals have owners.

Which web bundle the demo serves is decided by reading the deployed JavaScript chunks, because `/version` on the
API says `4.6.0` whether the image is current or a month old. The check is a loop that greps each chunk for a
phrase from the cold-start copy. Two ways it was not an instrument:

* it printed nothing unless a chunk matched. A reworded sentence and a stale deployment produced the same silence,
  which is the same class of hole as the report probe in `tests/contract/test_report_currency_probe.py` -- an
  answer the reader cannot distinguish from no answer.
* the phrase it searched for lived only in the prose. `apps/web/lib/locale.ts` owns that sentence, and the day it
  changes the loop stops matching for everyone, forever, with no check to say so.

The page probe in the same document had the first hole in a three-way form: it grepped the response headers for
`^content-security-policy` and printed nothing otherwise, which collapsed a per-document policy, an API-wide
policy on an HTML page, and no header because the request never arrived into one absence. The middle one is the
case the section exists to catch, and it looked like a clean check.

Every literal either probe searches for now has an owner in the code -- the cold-start phrase in the locale file,
the CSP discriminator in `document_security_headers()` -- and both are read out of the document rather than
restated here, so a writer who edits one side is told about the other by a failing test instead of by this comment.
"""

from __future__ import annotations

import re
from pathlib import Path

from dsa_agent.report_export import document_security_headers

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "hosted-demo.md"
LOCALE = ROOT / "apps" / "web" / "lib" / "locale.ts"


def _bundle_probe_block() -> str:
    """The one fenced bash block in the document that greps the deployed chunks."""
    blocks = re.findall(r"```bash\n(.*?)```", DOC.read_text(encoding="utf-8"), re.DOTALL)
    hits = [b for b in blocks if "MARK=" in b]
    assert len(hits) == 1, f"expected exactly one chunk-grepping block, found {len(hits)}"
    return hits[0]


def test_the_marker_the_document_searches_for_is_live_copy() -> None:
    """Reword the cold-start sentence without updating the probe and this reddens."""
    marker = re.search(r'MARK="([^"]+)"', _bundle_probe_block())
    assert marker, "the block must quote the phrase it searches for in one place"
    phrase = marker.group(1)
    assert phrase in LOCALE.read_text(encoding="utf-8"), (
        f"docs/hosted-demo.md greps the deployed bundle for {phrase!r}, which no shipped locale string contains"
    )


def test_the_probe_answers_when_it_finds_nothing() -> None:
    block = _bundle_probe_block()
    assert 'echo "chunks scanned:' in block, "the loop must state its own denominator"
    assert re.search(r'\[ "\$HIT" -gt 0 \] \|\| echo', block), (
        "the negative branch must print its own verdict"
    )


def test_the_loop_keeps_its_counters_in_the_printing_shell() -> None:
    """`curl ... | while read -r s` runs the body in a subshell, so totals cannot reach the echo."""
    block = _bundle_probe_block()
    assert "| while read -r" not in block
    assert re.search(r"for s in \$\(", block), (
        "the loop must iterate in the shell that prints the counts"
    )


def _csp_probe_blocks() -> list[str]:
    """Every block in the document that inspects the MCP App page's Content-Security-Policy."""
    blocks = re.findall(r"```bash\n(.*?)```", DOC.read_text(encoding="utf-8"), re.DOTALL)
    hits = [b for b in blocks if "content-security-policy:" in b]
    assert len(hits) == 2, (
        f"expected the page probe and its copy in the four-answer block, found {len(hits)}"
    )
    return hits


def test_every_csp_probe_names_all_three_outcomes() -> None:
    """A header that is present and wrong, and one that is absent, are different facts.

    The bare `grep -i '^content-security-policy'` this replaced printed a line only in the middle case, so "the
    container predates the per-document fix" and "this request never reached the service" both read as no output --
    and the first of those is the case the section exists to catch.
    """
    for block in _csp_probe_blocks():
        assert '[ -z "$H" ]' in block, "the probe must say what a missing header means"
        assert "elif" in block and "else" in block, (
            "each outcome needs its own branch and its own words"
        )


def test_the_csp_discriminator_is_what_the_producer_actually_emits() -> None:
    """The string the document branches on is owned by `document_security_headers`, not by the document."""
    needles = {
        m.group(1)
        for block in _csp_probe_blocks()
        for m in re.finditer(r'grep -q "([^"]+)"', block)
    }
    assert needles == {"script-src 'sha256-"}, needles
    emitted = document_security_headers(
        "<!DOCTYPE html><html><body><script>const a = 1;</script></body></html>"
    )["Content-Security-Policy"]
    (needle,) = needles
    assert needle in emitted, (
        f"docs/hosted-demo.md branches on {needle!r}, which document_security_headers no longer emits: {emitted}"
    )
