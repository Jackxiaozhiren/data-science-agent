"""Every code path a live document cites has to exist, because a reader follows it.

Found the hard way on 2026-10-23: `docs/security.md` named four modules under `packages/execution/`, and the
real ones live one directory deeper under `src/dsa_execution/`. The sentences beside those paths were the ones
this round had to correct anyway, so a reader trying to verify a security claim was sent to a file that is not
there. Twelve broken citations across five live documents -- `docs/security.md`, `docs/statistics.md`,
`docs/FRONTEND_IA.md`, `docs/MCP_DESIGN.md`, `docs/portfolio/PROJECT_SUMMARY.md` -- were found and repaired in
the same round this guard was written.

Twelve of the 107 citations in the 46 live documents pointed at files that are not there (measured on
2026-10-23; all twelve repaired the same round). Two shapes caused it: modules cited one directory above their
real `src/dsa_*` home, and web files cited as `app/...` or `lib/...` where the reader is not inside `apps/web`.
That second shape is why resolution is tried relative to the document first and only then to the repository
root -- a reader does the same, and a guard that only tries the root would flag prose that is correct.

Dated records are exempt -- `CHANGELOG.md`, `AUDIT_LEDGER.md`, `HANDOFF-*.md` and the `docs/v4_*/` archives
describe the tree as it was, and rewriting them to satisfy a present-day check would make them lie. The guard
also asserts it can see: a scan that found zero citations would pass on any tree, so the census itself is
checked for a non-trivial count, and a planted fake path is verified to be reported.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_CITE = re.compile(
    r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|pyi|mjs|cjs|js|ts|tsx|json|toml|sh|sql|yaml|yml))`"
)

# Live documents: the ones a reader is pointed at for how things work today.
_LIVE = ["README.md", "docs"]
for _app in sorted((REPO / "apps").glob("*/README.md")):
    _LIVE.append(str(_app.relative_to(REPO)))

_EXEMPT_PARTS = ("v4_3", "v4_4", "v4_5", "v4_6")
_EXEMPT_NAMES = ("CHANGELOG.md", "AUDIT_LEDGER.md")


def _live_docs() -> list[Path]:
    out: list[Path] = []
    for entry in _LIVE:
        p = REPO / entry
        if p.is_file():
            out.append(p)
            continue
        for md in sorted(p.rglob("*.md")):
            rel = md.relative_to(REPO)
            if any(part in _EXEMPT_PARTS for part in rel.parts):
                continue
            if rel.name in _EXEMPT_NAMES or rel.name.startswith("HANDOFF-"):
                continue
            if "node_modules" in rel.parts or ".next" in rel.parts:
                continue
            out.append(md)
    return out


def _citations(text: str, doc: Path) -> list[tuple[str, Path]]:
    """Resolve each citation the way a reader would: relative to the document, then to the repository root."""
    found = []
    for match in _CITE.finditer(text):
        raw = match.group(1)
        found.append((raw, (doc.parent / raw).resolve()))
        if not (doc.parent / raw).exists():
            alt = (REPO / raw).resolve()
            if alt.exists():
                found[-1] = (raw, alt)
    return found


def test_live_documents_cite_only_paths_that_exist() -> None:
    docs = _live_docs()
    assert len(docs) >= 30, f"only {len(docs)} live documents scanned -- the file list broke"
    offenders: list[str] = []
    total = 0
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for raw, resolved in _citations(text, doc):
            total += 1
            if not resolved.exists():
                offenders.append(f"{doc.relative_to(REPO)}: `{raw}`")
    assert total >= 80, (
        f"the census found {total} code citations across {len(docs)} live docs; a scan this quiet is blind"
    )
    assert not offenders, "documents point at files that are not there:\n" + "\n".join(
        sorted(offenders)
    )


def test_the_guard_sees_a_citation_and_reports_a_fake_one(tmp_path: Path) -> None:
    """A doc check that cannot fail is the defect it is supposed to prevent."""
    doc = REPO / "docs/security.md"
    real = _citations(doc.read_text(encoding="utf-8"), doc)
    assert real, "docs/security.md cites no code path, so the scanner cannot be trusted"
    assert any(raw.endswith("sql_guard.py") for raw, _ in real), [r for r, _ in real][:5]

    planted = "see `packages/execution/src/dsa_execution/definitely_not_a_module.py` for the rule"
    offenders = [raw for raw, where in _citations(planted, doc) if not where.exists()]
    assert offenders == ["packages/execution/src/dsa_execution/definitely_not_a_module.py"], (
        offenders
    )
