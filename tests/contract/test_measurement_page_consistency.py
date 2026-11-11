"""The measurement page must not claim an item has no reading while publishing that reading.

`docs/measurement-basis.md` says near the top which stage items have no reading yet, and then gives
each recorded item a section of its own. The page drifted exactly there: after the attribution
reading landed, the top said "two of S2's four items", the boundary-matrix section still said "three
of its four items -- latency and failure attribution, the export-first lifecycle, the contract-version
policy -- have no reading yet", and the item it named second had its own section fifty lines below.

Both sides of every check here are read out of the page and the ADR rather than typed into the test,
so adding a reading cannot leave a stale literal behind in this file.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs/measurement-basis.md"
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"

WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
}

#: The stage this file guards. Sections are written as "## S2 -- <topic>".
STAGE = "S2"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sections() -> list[str]:
    """Every S2 section title on the page, lowercased, without the heading marker."""
    pattern = re.compile(rf"^## {STAGE} — (.+)$", re.MULTILINE)
    return [match.group(1).strip().lower() for match in pattern.finditer(_text(PAGE))]


def _sentences() -> list[str]:
    """The page split into sentences, because the claim and the counter-claim share a paragraph."""
    flat = re.sub(r"\s+", " ", _text(PAGE))
    return [part.strip() for part in re.split(r"(?<=[.!?]) ", flat) if part.strip()]


def test_the_page_publishes_sections_to_check() -> None:
    """An empty list would make the two tests below pass while comparing nothing."""
    assert len(_sections()) >= 2, _sections()


def test_no_sentence_denies_a_reading_that_has_its_own_section() -> None:
    topics = _sections()
    assert topics
    offenders = []
    for sentence in _sentences():
        if "no reading" not in sentence.lower():
            continue
        for topic in topics:
            if topic in sentence.lower():
                offenders.append((topic, sentence))
    assert not offenders, offenders


def test_the_intro_counts_the_sections_it_has() -> None:
    match = re.search(r"are (\w+) of S2's four items", re.sub(r"\s+", " ", _text(PAGE)))
    assert match, "the intro no longer states how many S2 items carry a reading"
    assert WORDS[match.group(1)] == len(_sections()), (match.group(1), _sections())


def test_the_adr_status_counts_the_same_sections() -> None:
    status = _text(ADR).splitlines()[2]
    readings = re.search(r"S2 in progress \((\w+) readings?:", status)
    remaining = re.search(r"(\w+) items? remaining", status)
    assert readings and remaining, status
    assert WORDS[readings.group(1)] == len(_sections()), (status, _sections())
    assert WORDS[readings.group(1)] + WORDS[remaining.group(1)] == WORDS["four"], status
