"""Every code path a live document cites has to be a path the reader can actually open.

Found the hard way on 2026-10-23, twice over. First reading: `docs/security.md` named four modules under
`packages/execution/`, and the real ones live one directory deeper under `src/dsa_execution/`; twelve broken
citations across five live documents in total, all repaired in the round this guard was written. Second
reading: the guard passed locally and went red in CI, because `docs/FRONTEND_IA.md` cited
`build/r13f-nav-acceptance.mjs` -- a real script, on my machine, inside a directory that is never shipped. A
citation that resolves only on the author's box is the same defect with a worse diagnosis, because everything
green at the time of writing says it is fine.

So two rules, not one: the resolved path must exist, and the spelling must not name an unshipped directory.
`output/` is deliberately excluded from the second -- it is the documented artifact root, and a sentence naming
a generated file there tells the truth about a path that is not meant to exist yet.

Resolution tries the document's own directory first and then the repository root, because that is the order a
reader tries and a root-only guard would flag prose that is correct: web documents cite `app/lib/...` and
`lib/...` from inside `apps/web`. Dated records are exempt -- `CHANGELOG.md`, `AUDIT_LEDGER.md`, `HANDOFF-*.md`
and `docs/v4_*/` -- they describe the tree as it was, and rewriting them to satisfy a present-day check would
make them lie.

Two controls on the guard itself, because a documentation check is exactly the kind of thing that can pass by
measuring nothing: the census asserts it resolved a non-trivial number of citations, and a planted path is
asserted to be reported -- both a made-up module and a made-up path under `build/`.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

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
_UNSHIPPED = {"build", "site", ".next", "dist", "node_modules", ".venv"}


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
        candidate = (doc.parent / raw).resolve()
        if not candidate.exists():
            alt = (REPO / raw).resolve()
            if alt.exists():
                candidate = alt
        found.append((raw, candidate))
    return found


def _unshipped(raw: str) -> bool:
    return any(part in _UNSHIPPED for part in PurePosixPath(raw).parts[:-1])


def test_live_documents_cite_only_paths_that_exist() -> None:
    docs = _live_docs()
    assert len(docs) >= 30, f"only {len(docs)} live documents scanned -- the file list broke"
    offenders: list[str] = []
    total = 0
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for raw, resolved in _citations(text, doc):
            total += 1
            if _unshipped(raw):
                offenders.append(f"{doc.relative_to(REPO)}: `{raw}` names an unshipped directory")
            elif not resolved.exists():
                offenders.append(f"{doc.relative_to(REPO)}: `{raw}`")
    assert total >= 80, (
        f"the census found {total} code citations across {len(docs)} live docs; a scan this quiet is blind"
    )
    assert not offenders, "documents point at files a reader cannot open:\n" + "\n".join(
        sorted(offenders)
    )


def test_the_guard_sees_a_citation_and_reports_a_fake_one() -> None:
    """A doc check that cannot fail is the defect it is supposed to prevent."""
    doc = REPO / "docs/security.md"
    real = _citations(doc.read_text(encoding="utf-8"), doc)
    assert real, "docs/security.md cites no code path, so the scanner cannot be trusted"
    assert any(raw.endswith("sql_guard.py") for raw, _ in real), [r for r, _ in real][:5]

    planted = (
        "see `packages/execution/src/dsa_execution/definitely_not_a_module.py` for the rule, "
        "and run `build/scratch-instrument.mjs` to reproduce it"
    )
    parsed = _citations(planted, doc)
    missing = [raw for raw, where in parsed if not where.exists()]
    assert missing == [
        "packages/execution/src/dsa_execution/definitely_not_a_module.py",
        "build/scratch-instrument.mjs",
    ], missing
    assert [raw for raw, _ in parsed if _unshipped(raw)] == ["build/scratch-instrument.mjs"], (
        "the unshipped rule does not fire on the spelling that broke CI"
    )
