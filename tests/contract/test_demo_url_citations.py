"""Which document names which demo hostname is a fact a file can lose.

`docs/hosted-demo.md` has a section explaining that two `*.vercel.app` hostnames both serve the demo. The owner
chose one of them as canonical on 2026-10-24 (ledger §291): `data-science-agent-web.vercel.app`, the host
`README.md` has always linked, is now the one the deployment list, the CORS examples and `render.yaml` name, while
`…-rr93.vercel.app` survives only in the section that says it exists.

That choice is the kind of arrangement that rots quietly. Put the second host back in a copy-paste block, or move
the README link, or let a third Vercel project appear, and every document still parses, still builds, and now
describes a deployment shape a reader cannot reach by following it. The assertions are about *which document says
what*; the live hosts are measured in the section itself, with a command. A hostname outside the described pair
reddens the census assertion rather than being ignored, because a fourth project silently joining the set is the
failure mode worth catching.
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


def test_the_canonical_host_is_the_one_every_config_example_carries() -> None:
    """One host per question, or the documents disagree about where the demo is.

    The owner chose the plain host on 2026-10-24 (ledger §291), so the deployment list, `README.md`, the CORS
    example in `docs/production-hardening.md` and the blueprint's explicit origin have to say the same thing. The
    suffixed hostname survives only in the section that explains it is a second live deployment, which is why the
    config files are asserted never to mention it -- a second origin in a copy-paste block is how the ambiguity
    came back.
    """
    for doc in (HOSTED_DOC, HARDENING_DOC):
        assert PLAIN in _hosts_in(doc), f"{doc.name} no longer carries the canonical host"
    assert _hosts_in(HARDENING_DOC) == {PLAIN}, (
        f"{HARDENING_DOC.name} cites {sorted(_hosts_in(HARDENING_DOC))}"
    )
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert PLAIN in blueprint, "render.yaml's explicit origin moved off the canonical host"
    assert SUFFIXED not in blueprint, (
        "render.yaml names the second host explicitly again; the regex is what admits it, not the list"
    )


def test_the_deployment_list_leads_with_the_canonical_host() -> None:
    text = HOSTED_DOC.read_text(encoding="utf-8")
    start = text.index("## Current public deployment")
    block = text[start : text.index("### ", start)]
    assert PLAIN in block, (
        "the deployment list no longer names the host the section says it leads with"
    )
    assert SUFFIXED not in block, (
        "the suffixed host is back in the list, which is the ambiguity §291 closed"
    )


def test_no_third_vercel_project_joined_without_a_word_about_it() -> None:
    found = _hosts_in(README) | _hosts_in(HOSTED_DOC) | _hosts_in(HARDENING_DOC)
    assert found == {PLAIN, SUFFIXED}, (
        f"the hostname section describes exactly two projects; these documents now cite {sorted(found)}"
    )
