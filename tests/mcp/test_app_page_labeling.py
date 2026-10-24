"""`/mcp-app/` is labelled as a page, not as a protocol surface, and the sentence is checked against the server.

R-14 shipped a browser document at `/mcp-app/` and left open how to describe it. Two options were on the table
(ledger §265's sibling item #56): advertise it as an MCP UI resource, or say plainly that it is a page a client will
not discover. The second was taken, because publishing a UI resource is a claim about what a client does with it and
nothing here has a client to test that against -- the same round that found every tool publishing `input_schema`
where the protocol reads `inputSchema` (§250) also established that "verified live" had meant the product's own
client agreeing with the product's own server.

So the claim in `docs/mcp.md` is pinned here in both directions, the way this repository pins a document to the code
it describes rather than to a reader's patience:

* the resource list really carries no UI scheme and no UI MIME type, and the **scheme set the sentence enumerates is
  the set the server produces** -- a sixth scheme added to `resources.py` reddens the document's own words;
* the sentence exists, exactly once, and names the two things that make it a re-labelling rather than a shrug.

`docs/MCP_DESIGN.md` points at that paragraph instead of restating it, so the claim has one owner.
"""

from __future__ import annotations

import re
from pathlib import Path

from dsa_mcp.resources import list_resources

REPO = Path(__file__).resolve().parents[2]
MCP_DOC = REPO / "docs" / "mcp.md"
DESIGN_DOC = REPO / "docs" / "MCP_DESIGN.md"

#: The phrase the labelling paragraph is built around. One copy, in one document.
_MARKER = "not** an MCP UI resource"


def _folded(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_server_publishes_no_ui_resource_and_no_html_profile() -> None:
    resources = list_resources()
    assert resources, "the resource surface is empty, so this guard would prove nothing"
    for item in resources:
        uri = str(item.get("uri", ""))
        mime = str(item.get("mimeType", ""))
        assert not uri.startswith("ui://"), f"{uri!r} would make the page a advertised UI resource"
        assert "profile=mcp-app" not in mime, f"{mime!r} advertises an HTML UI profile"
        assert "_meta" not in item or "ui" not in str(item.get("_meta")).lower(), item


def test_the_document_names_exactly_the_schemes_the_server_emits() -> None:
    """The sentence enumerates a set; the set has one owner in code, and the document has to track it."""
    schemes = {str(item.get("uri", "")).split("://", 1)[0] for item in list_resources()}
    prose = _folded(MCP_DOC)
    assert _MARKER in prose, "the labelling sentence is gone from docs/mcp.md"
    clause = prose[prose.index(_MARKER) : prose.index(_MARKER) + 900]
    group = re.search(r"\((`[a-z]+://`(?:, `[a-z]+://`)*)\)", clause)
    assert group, f"the paragraph must enumerate the schemes it claims, got: {clause[:220]}"
    named = set(re.findall(r"`([a-z]+)://`", group.group(1)))
    assert named == schemes, (
        f"docs/mcp.md enumerates {sorted(named)}, the server emits {sorted(schemes)}"
    )
    assert len(named) >= 2, named
    # The negative half of the claim must stay in the same sentence, or the enumeration alone reads as a shrug.
    for negated in ("ui://", "text/html;profile=mcp-app", "_meta"):
        assert negated in clause, f"the paragraph stopped ruling out {negated!r}"
    assert "`ui://`" not in group.group(1)

    #: The set above is derived, so the paragraph must not also count it in prose: a spelled-out count is a
    #: second owner for a number that changes whenever `resources.py` gains a scheme.
    counted = re.search(
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+\w*\s*schemes\b", clause
    )
    assert counted is None, (
        f"the paragraph counts the enumeration it should derive: {counted.group(0)!r}"
    )


def test_the_relabel_is_claimed_once_and_the_design_doc_points_at_it() -> None:
    """Two owners for one claim is how documents start disagreeing."""
    assert _folded(MCP_DOC).count(_MARKER) == 1, "the claim is duplicated inside one document"
    design = _folded(DESIGN_DOC)
    assert "not a protocol surface" in design, "docs/MCP_DESIGN.md stopped describing the page"
    assert (
        "docs/mcp.md"
        in design[
            design.index("not a protocol surface") : design.index("not a protocol surface") + 400
        ]
    ), "docs/MCP_DESIGN.md must hand the claim to docs/mcp.md rather than restate it"
