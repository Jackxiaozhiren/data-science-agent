"""Which document names which demo hostname is a fact a file can lose.

`docs/hosted-demo.md` has a section explaining that two `*.vercel.app` hostnames both serve the demo -- `…-rr93`
in its own deployment list and in `docs/production-hardening.md`, the plain one in `README.md`, which is where a
visitor arrives from. That arrangement is the kind of cross-document mirror that rots quietly: change the README
link, or add a third Vercel project, and every document still parses, still builds, and now describes a deployment
shape that is no longer the one a reader can reach.

The assertions are about *which document says what*, not about the live hosts -- those are measured in the section
itself, with a command. A hostname that appears nowhere in this list reddens the census assertion rather than
being ignored, because a fourth project silently joining the set is the failure mode worth catching.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
HOSTED_DOC = ROOT / "docs" / "hosted-demo.md"
HARDENING_DOC = ROOT / "docs" / "production-hardening.md"

PLAIN = "data-science-agent-web.vercel.app"
SUFFIXED = "data-science-agent-web-rr93.vercel.app"
_HOST = re.compile(r"data-science-agent-web[a-z0-9-]*\.vercel\.app")


def _hosts_in(path: Path) -> set[str]:
    return set(_HOST.findall(path.read_text(encoding="utf-8")))


def test_the_two_documents_name_the_two_hostnames_the_section_describes() -> None:
    readme = _hosts_in(README)
    assert PLAIN in readme, "README is the visitor's door; the section says it links the plain host"
    assert SUFFIXED not in readme, (
        "the hostname section says README links only the plain host; if it names rr93 too, the section is stale"
    )


def test_the_suffixed_host_is_the_one_the_deployment_lists_carry() -> None:
    assert SUFFIXED in _hosts_in(HOSTED_DOC)
    assert SUFFIXED in _hosts_in(HARDENING_DOC), (
        "docs/production-hardening.md sets CORS for this origin"
    )


def test_the_deployment_list_still_leads_with_the_suffixed_host() -> None:
    """The section's whole point is that the list and the README disagree, so the list must still say so."""
    text = HOSTED_DOC.read_text(encoding="utf-8")
    start = text.index("## Current public deployment")
    block = text[start : text.index("### ", start)]
    assert SUFFIXED in block, (
        "the deployment list no longer names the host the section says it names"
    )
    assert PLAIN not in block, (
        "the deployment list now cites the plain host too, which is exactly the ambiguity the next section resolves"
    )


def test_no_third_vercel_project_joined_without_a_word_about_it() -> None:
    found = _hosts_in(README) | _hosts_in(HOSTED_DOC) | _hosts_in(HARDENING_DOC)
    assert found == {PLAIN, SUFFIXED}, (
        f"the hostname section describes exactly two projects; these documents now cite {sorted(found)}"
    )
