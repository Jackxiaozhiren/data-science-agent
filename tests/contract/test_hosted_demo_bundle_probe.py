"""The bundle probe in `docs/hosted-demo.md` has to answer in both directions, and its marker has an owner.

Which web bundle the demo serves is decided by reading the deployed JavaScript chunks, because `/version` on the
API says `4.6.0` whether the image is current or a month old. The check is a loop that greps each chunk for a
phrase from the cold-start copy. Two ways it was not an instrument:

* it printed nothing unless a chunk matched. A reworded sentence and a stale deployment produced the same silence,
  which is the same class of hole as the report probe in `tests/contract/test_report_currency_probe.py` -- an
  answer the reader cannot distinguish from no answer.
* the phrase it searched for lived only in the prose. `apps/web/lib/locale.ts` owns that sentence, and the day it
  changes the loop stops matching for everyone, forever, with no check to say so.

Both are pinned here, and the marker is read out of the document rather than restated, so a writer who edits one
side has to be told about the other by a failing test instead of by this comment.
"""

from __future__ import annotations

import re
from pathlib import Path

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
