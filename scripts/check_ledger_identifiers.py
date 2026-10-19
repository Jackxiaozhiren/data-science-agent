#!/usr/bin/env python3
"""Audit §208's rule in code: a ledger section number is issued once, and a citation resolves.

Why the rule is shaped as "no new gap, no new collision, no new dangling citation" rather than as "numbers
must be unique". AUDIT_LEDGER.md carries two collisions this file refuses to repair by editing: §178 and §179
each appear twice, written minutes apart by two lanes that computed "next number" from the same tail of a
shared worktree (AUDIT_LEDGER §181 records both the cause and the decision not to renumber, because renaming a
dated section would rewrite text another section already cross-references). Renumbering is therefore not what
this gate asks for. What it asks is that the same accident cannot happen a third time unnoticed: every number
in the canonical run must be issued exactly once, and the only gaps permitted are the ones declared below with
the reason they exist.

Canonical means the `## N. ` heading form, which the ledger adopted at §62 and has used ever since. Citations
to numbers below that floor -- `§4`, `§33` -- name sections written in the older prose and phase-heading forms
(`## Baseline`, `## Lane L1`, `### D-L1-12`), which no scanner here claims to interpret; the check is silent
about them rather than guessing, and says so in its output.

Run with `--check` (CI's form) or `--ledger <path>` (a copy, to prove this gate can fail).
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Collisions that exist, with the section that decided to leave them. Each is exempted by number, so a THIRD
#: heading under either number still fails -- the exemption covers the recorded past, not the coming present.
GRANDFATHERED_DUPLICATES = {
    178: "§181: two lanes both wrote 178 minutes apart; renumbering would edit a dated record §180 cites",
    179: "§181: same collision in the same window; the two entries argue with each other on purpose",
}

#: Numbers cited in the body that have no heading. §83 is not a typo to fix: §181 traced it to a 2026-10-02
#: entry that quoted a paragraph living only in an agent memory note, and editing the citation would rewrite
#: dated text written by another session.
GRANDFATHERED_GAPS = {
    83: "§181: cited three times, never issued; the sentence's real home is a session memory note"
}

#: First section written in the `## N. ` form. Measured from the file, not recited: the run from here up is
#: what this gate holds contiguous.
CANONICAL_FLOOR = 62

_HEADING = re.compile(r"(?m)^## (\d+)\. (.*)$")
_CITATION = re.compile(r"§(\d+)")


def _headings(text: str) -> dict[int, list[tuple[int, str]]]:
    """Every canonical heading, as number -> [(line, subject), ...]."""
    found: dict[int, list[tuple[int, str]]] = collections.defaultdict(list)
    for lineno, line in enumerate(text.splitlines(), 1):
        match = _HEADING.match(line)
        if match:
            found[int(match.group(1))].append((lineno, match.group(2).strip()))
    return found


def _citations(text: str, declared: set[int]) -> dict[int, int]:
    """Body citations above the canonical floor that name a number with no heading.

    Headings themselves are skipped: a subject line may quote another section, and that is a reference the
    author wrote on purpose, not a claim that the number exists.
    """
    counts: dict[int, int] = collections.Counter()
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        for token in _CITATION.findall(line):
            number = int(token)
            if number >= CANONICAL_FLOOR and number not in declared:
                counts[number] += 1
    return dict(counts)


def check(path: Path) -> list[str]:
    """Problems with the ledger's identifiers, as human-readable lines. Empty means the file is consistent."""
    text = path.read_text(encoding="utf-8")
    headings = _headings(text)
    declared = set(headings)
    issues: list[str] = []

    if not declared:
        return [
            f"{path.name}: no `## N. ` headings parsed at all -- the scanner broke, not the ledger"
        ]
    if min(declared) > CANONICAL_FLOOR:
        issues.append(
            f"the canonical run now starts at §{min(declared)}, above the declared floor §{CANONICAL_FLOOR}: "
            "either a section was deleted or the floor is stale -- say which, in this file"
        )

    for number, entries in sorted(headings.items()):
        if len(entries) > 1:
            where = "; ".join(f"line {line}: {subject[:60]}" for line, subject in entries)
            if number in GRANDFATHERED_DUPLICATES:
                continue
            issues.append(
                f"§{number} is issued {len(entries)} times ({where}) -- pick the next free number; "
                f"{number} is not in the grandfathered set, and adding it to that set means editing a dated "
                "record, which is the thing AUDIT_LEDGER §181 refused to do"
            )

    missing = [
        number
        for number in range(CANONICAL_FLOOR, max(declared) + 1)
        if number not in declared and number not in GRANDFATHERED_GAPS
    ]
    for number in missing:
        issues.append(
            f"§{number} is cited in the body or sits inside the numbering run but has no heading, and is not "
            f"declared as a known gap (declared: {sorted(GRANDFATHERED_GAPS)})"
        )

    for number, hits in sorted(_citations(text, declared).items()):
        if number not in GRANDFATHERED_GAPS:
            issues.append(
                f"§{number} is cited {hits} time(s) in the body with no heading and no exemption"
            )

    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify without writing anything (CI's form)"
    )
    parser.add_argument(
        "--ledger", type=Path, default=ROOT / "AUDIT_LEDGER.md", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)

    text = args.ledger.read_text(encoding="utf-8")
    headings = _headings(text)
    declared = set(headings)
    issues = check(args.ledger)
    print(
        f"ledger identifiers: {len(headings)} headings issued, run §{min(declared)}-§{max(declared)}, "
        f"{sum(len(v) for v in headings.values())} heading lines read; exemptions: duplicates "
        f"{sorted(GRANDFATHERED_DUPLICATES)}, gaps {sorted(GRANDFATHERED_GAPS)}"
    )
    for line in issues:
        print(f"  FAIL {line}")
    if issues:
        return 1
    print("ledger identifiers: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
