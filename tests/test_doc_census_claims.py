"""No shipped document may carry a census number nothing recomputes.

A hand-typed count is born stale. §63 settled the policy for this repository -- "counts removed,
not corrected" -- after three live documents disagreed with each other about the same thing (17
tools, 18 tools, ~13 tools, "Next.js 15 / 13 routes"), and the measurement that year showed the
surface was `next 16.3.4` with 16 pages. §76 then retired the checker's four typed number rules
because they could only ever certify transcription, and replaced the one class with an owner with a
derived comparison. This guard applies the same rule to the reader-facing documents: either the
number is derived by a check that runs, or the sentence does not carry one.

Scope, stated rather than implied:
- Scanned: ``README.md``, ``docs/**/*.md``, ``apps/**/*.md`` and ``benchmarks/**/README.md`` -- what
  a user or reviewer reads as the current product. The benchmarks entry arrived with §113, after the
  freeze document turned out to sit outside both prose checks; it guards the census shape there,
  while the dated gate counts §113 removed are guarded per file.
- Exempt, as era-bound records rather than present-tense claims: ``research/**`` (papers, drafts,
  claim matrices), ``docs/v3`` and ``docs/v4_3``, ``CHANGELOG.md``, and this repository's own audit
  documents. A paper describing release N is allowed to cite release N's counts; a portfolio page
  offering the product today is not.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A count attached to a noun whose value changes whenever the *product surface* changes -- the class
# §63 measured and found already contradictory (17 / 18 / ~13 tools, "Next.js 15 / 13 routes").
# Deliberately narrow. The first cut of this pattern also matched `tests`, `tasks`, `metrics`,
# `modules`, `datasets` and `pages`, and its red list then included McNemar 6:2 and a Wilson interval
# from docs/real-model-evaluation.md, a verified run's "1.33 s, 6 evidence items" from
# docs/product-tour.md, and catalog sizes from docs/benchmark.md -- i.e. it was a ban on numbers,
# not a rule about ownership. Experiment readings and catalog facts keep their numbers.
_CENSUS = re.compile(
    r"\b\d+\s+(?:routes?|subcommands?|commands|endpoints?|views|resources|tools?(?! calls))\b",
    re.IGNORECASE,
)

SCAN_GLOBS = ("README.md", "docs/**/*.md", "apps/**/*.md", "benchmarks/**/README.md")

EXEMPT_PREFIXES = (
    "docs/v3/",
    "docs/v4_3/",
    "docs/ADR/",  # Architectural Decision Records are dated by design
    "research/",  # papers and drafts describe the release they were written against
    "site/",  # generated
    "data-science-agent/",  # a second local clone, not this repository
)

EXEMPT_NAMES = (
    "CHANGELOG.md",
    "AUDIT_LEDGER.md",
    "AUDIT_REPORT_PHASE5.md",
    "REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md",
)

# A number with a live owner is allowed to be cited, because a check recomputes it. The two keys are
# the phrases a writer uses when pointing at a derived figure, and each must appear next to a
# number for the exemption to apply.
DERIVATION_CUE = re.compile(
    r"(as (?:measured|reported)|measured:|derived|the collector|generated|see `scripts/"
    r"|recomput)",
    re.IGNORECASE,
)

# Anything the reader is told to go do, rather than a property of the product.
COMMAND_LINE = re.compile(r"^\s*(?:\$|uv run|npm |python3? |git |docker |dsa |gh )")

# Dependency and build trees are not this repository's prose. The first run of this guard reached
# `apps/web/node_modules/next/dist/docs/**` through the `apps/**/*.md` glob and reported ~40
# "offences" in third-party documentation -- the same mistake as counting generated output, which
# is why the exclusion is a path-segment test and not a file-name list.
SKIP_SEGMENTS = frozenset(
    {
        "node_modules",
        ".next",
        ".venv",
        "site",
        "_vendor",
        "dist",
        "build",
        # The vendored DataSciBench clone under benchmarks/external/ brings its own venv and a
        # MetaGPT checkout: sixteen upstream READMEs that are not this repository's prose.
        ".workspace",
    }
)


def _candidate_files() -> list[Path]:
    out: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if SKIP_SEGMENTS.intersection(path.parts):
                continue
            if rel.startswith(EXEMPT_PREFIXES) or path.name in EXEMPT_NAMES:
                continue
            out.append(path)
    return sorted(set(out))


def _line_offends(line: str) -> bool:
    if not _CENSUS.search(line):
        return False
    if COMMAND_LINE.search(line):
        return False  # an instruction the reader runs, not a product property
    if DERIVATION_CUE.search(line):
        return False  # a cited derived figure
    return True


def _offenders() -> list[str]:
    found: list[str] = []
    for path in _candidate_files():
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            if _line_offends(line):
                found.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:100]}")
    return found


def test_live_documents_cite_no_unowned_census() -> None:
    files = _candidate_files()
    assert len(files) >= 15, f"only {len(files)} files scanned -- the glob broke"
    offenders = _offenders()
    assert not offenders, (
        "hand-typed counts in reader-facing documents; drop the number or give it a check that "
        "recomputes it:\n" + "\n".join(offenders)
    )


def test_the_census_guard_fires_in_both_directions() -> None:
    """Negative control: the shape matches, and the two legitimate forms do not.

    Without the second half this becomes a rule that bans numbers rather than one that requires an
    owner, and the next author works around it by writing 'several'.
    """
    assert _line_offends("`dsa` CLI (11 subcommands), MCP (18 tools)"), "census shape not caught"
    assert _line_offends("The stack ships 16 routes today."), "route count shape not caught"
    assert not _line_offends(
        "Test count as measured by `scripts/audit_facts.py`: see the collector report."
    ), "a cited derived figure must be allowed"
    assert not _line_offends("$ dsa --help  # 12 subcommands"), "an instruction line is not a claim"
    assert not _line_offends("This release adds three tools."), "spelled-out numbers are prose"


def test_exempt_surfaces_are_what_they_claim() -> None:
    """The exemption list is a claim too: if `research/` stops existing the carve-out is vacuous."""
    assert (ROOT / "research").is_dir(), "research/ gone -- drop the exemption, do not leave it"
    assert (ROOT / "CHANGELOG.md").is_file(), "CHANGELOG gone -- drop the exemption"
    scanned = {p.relative_to(ROOT).as_posix() for p in _candidate_files()}
    assert not any(rel.startswith("research/") for rel in scanned), sorted(scanned)[:5]
    assert any(rel.startswith("docs/") for rel in scanned), "no docs/ file scanned -- glob broken"
    # §113: `benchmarks/baseline/README.md` is the regression contract and speaks in the present
    # tense, so it belongs here. What this guard buys for that file is protection against the census
    # shape it does not currently take -- replayed against the pre-§113 revision it reports zero
    # offences there, because "86 tests / 74% coverage" is not a route-or-tool count. The counts that
    # were actually wrong are guarded by tests/test_baseline_readme_integrity.py.
    assert "benchmarks/baseline/README.md" in scanned, sorted(
        r for r in scanned if "benchmark" in r
    )
    assert not any(".workspace" in rel for rel in scanned), (
        "vendored upstream prose reached the guard"
    )
