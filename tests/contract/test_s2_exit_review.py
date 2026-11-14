"""Read ADR-003's S2 exit condition clause by clause against the four readings.

Four readings do not by themselves say whether the stage is exited: the ADR's migration row names an
exit condition with four clauses, and the work column names four items, but the two lists are not the
same list. This file derives the clause anchors from the ADR, the numbers from the records, and the
verdict from the predicates those records satisfy. Nothing here is typed as a literal count, so a
record that changes makes the page stale and this test fail rather than quietly agreeing with it.

The verdict used to be the one thing the records could not supply: with three producer gaps open,
"not exited" was a declaration nobody had made, and this file pinned its absence. ADR-004 closed those
gaps, so the verdict is derived now — four predicates, one set of readings — and the declaration is
held to the derivation rather than to a sentence someone wrote first.

No new audit record is added by the review. It is a judgement about records that already exist, and
`docs/audit/contract-versions.json` keeps its own count of them.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"
PAGE = ROOT / "docs/measurement-basis.md"
BOUNDARY = ROOT / "docs/audit/execution-boundary.json"
ATTRIBUTION = ROOT / "docs/audit/attribution.json"
EXPORT = ROOT / "docs/audit/export-lifecycle.json"
REGISTER = ROOT / "docs/audit/contract-versions.json"
PUBLICATION = ROOT / "packages/evaluation/src/dsa_evaluation/publication.py"

REVIEW_HEADING = "Stage exit — the four clauses against the four readings"
NEXT_HEADING = "## What this page is not"
CLAUSES = (
    "boundary decidability",
    "attribution completeness",
    "artifact parseability",
    "`matrix_valid` and `publication_ready` never conflated",
)
GATE_EXPRESSION = 'publication_ready = matrix_valid and scope == "full"'
EVIDENCE = (
    BOUNDARY,
    ATTRIBUTION,
    EXPORT,
    REGISTER,
    PUBLICATION,
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _record(path: Path) -> dict[str, Any]:
    return json.loads(_text(path))


def _s2_cells() -> list[str]:
    """The ADR's migration row: stage, entry, work, exit condition."""
    rows = [
        line
        for line in _text(ADR).splitlines()
        if line.startswith("| S2 boundary and attribution |")
    ]
    assert len(rows) == 1, rows
    return [cell.strip() for cell in rows[0].split("|")]


def _review() -> str:
    page = _text(PAGE)
    start = page.index(f"## {REVIEW_HEADING}")
    end = page.index(NEXT_HEADING, start)
    return page[start:end]


def _headings() -> list[str]:
    return re.findall(r"^## (.+)$", _text(PAGE), re.MULTILINE)


def test_the_adr_names_four_clauses_in_one_s2_exit_condition() -> None:
    cells = _s2_cells()
    assert len(cells) >= 5, cells
    condition = cells[4]
    assert all(clause in condition for clause in CLAUSES), condition
    assert condition.index(CLAUSES[0]) < condition.index(CLAUSES[1]) < condition.index(CLAUSES[2])
    assert condition.rstrip().endswith(CLAUSES[3])


def test_the_review_is_a_heading_but_not_a_fifth_item() -> None:
    headings = _headings()
    assert headings.count(REVIEW_HEADING) == 1, headings
    s2_sections = [heading for heading in headings if heading.startswith("S2 — ")]
    work_items = [item.strip() for item in _s2_cells()[3].split(",")]
    assert len(s2_sections) == len(work_items), (s2_sections, work_items)
    assert REVIEW_HEADING not in s2_sections


def test_every_clause_and_every_evidence_path_is_cited() -> None:
    review = _review().lower()
    assert all(clause.lower() in review for clause in CLAUSES), CLAUSES
    for path in EVIDENCE:
        rel = path.relative_to(ROOT).as_posix()
        assert rel in review, rel
        assert path.is_file(), rel


def test_boundary_decidability_numbers_come_from_the_record() -> None:
    summary = _record(BOUNDARY)["summary"]
    review = _review()
    assert summary["decided_by_check"] + summary["undecidable"] == summary["cells"]
    assert f"{summary['decided_by_check']} of {summary['cells']} cells" in review
    assert f"{summary['undecidable']} are undecidable" in review
    assert f"{summary['open']} open and {summary['fenced']} fenced" in review


def test_attribution_gap_numbers_come_from_the_record() -> None:
    record = _record(ATTRIBUTION)
    external = record["failures"]["external_bundle"]
    latency = record["latency"]
    frozen = record["failures"]["frozen_baseline"]
    review = _review()
    # ADR-004 D2 moved this number from 0. What the review must keep doing is quoting the record;
    # pinning the gap open would make the page fail at the moment the gap closed, which is the
    # opposite of what an exit review is for. Whether the number counts as closed is D4's judgement.
    assert external["stage_level"] <= external["non_passing"]
    assert frozen["non_passing"] == 0
    assert f"{external['stage_level']} of {external['non_passing']}" in review
    assert f"{latency['tasks_with_stage_boundaries']} of {latency['tasks']}" in review
    assert frozen["status"] in review


def test_parseability_numbers_come_from_the_record() -> None:
    summary = _record(EXPORT)["summary"]
    review = _review()
    assert f"{summary['committed_exports_parsed']} of {summary['committed_exports']}" in review
    assert f"{summary['events_with_a_parse_check']} of {summary['events']}" in review
    assert (
        f"{summary['export_side_events_with_a_digest']} of {summary['export_side_events']}"
        in review
    )
    assert all(f"`{name}`" in review for name in summary["classes_not_measured"])
    assert summary["committed_exports_parsed"] <= summary["committed_exports"]


def test_non_conflation_is_structural_and_stated_in_every_reading() -> None:
    assert GATE_EXPRESSION in _text(PUBLICATION)
    assert GATE_EXPRESSION in _review()
    for path in (BOUNDARY, ATTRIBUTION, EXPORT, REGISTER):
        disclaimers = _record(path)["not_claimed"]
        assert any("publication_ready" in line for line in disclaimers), path


def test_the_fourth_item_has_no_exit_clause() -> None:
    cells = _s2_cells()
    assert "contract-version policy" in cells[3]
    assert "contract-version" not in cells[4].lower()
    review = _review()
    assert "the contract-version policy" in review
    assert "no exit clause names it" in review


def _clauses(
    boundary: dict[str, Any], attribution: dict[str, Any], export: dict[str, Any]
) -> dict[str, bool]:
    """The four exit predicates as functions of the records — not of the page that quotes them.

    Each is the ADR-004 Appendix B form: an equality between the numerator the record counts and the
    denominator that makes it meaningful, so a zero denominator cannot pass as a closed gap.
    """
    external = attribution["failures"]["external_bundle"]
    latency = attribution["latency"]
    summary = export["summary"]
    return {
        "undecidable == 0": boundary["summary"]["undecidable"] == 0,
        "stage_level == non_passing": external["stage_level"] == external["non_passing"],
        "tasks_with_stage_boundaries == tasks": latency["tasks_with_stage_boundaries"]
        == latency["tasks"],
        "export_side_events_with_a_digest == export_side_events": summary[
            "export_side_events_with_a_digest"
        ]
        == summary["export_side_events"],
    }


def _records() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return _record(BOUNDARY), _record(ATTRIBUTION), _record(EXPORT)


def test_every_exit_clause_holds_on_the_records() -> None:
    clauses = _clauses(*_records())
    assert all(clauses.values()), clauses


def test_each_reading_names_the_commit_its_evidence_lives_at() -> None:
    """The four clauses are read from four records, and each names the commit it is evidence about.

    They are not all one commit, and saying they were would be the false claim: the boundary and
    export readings re-read this tree, while the attribution reading's `reviewed_commit` is the tree
    its run was taken on — its own `--verify` requires that field to equal `run_manifest_commit`, so
    re-deriving the record on a later tree cannot move it. What makes the four one set is that each
    is the latest record for its clause, none is superseded, and the two that were re-taken say which
    record they replace.
    """
    for path in (BOUNDARY, ATTRIBUTION, EXPORT, REGISTER):
        record = _record(path)
        assert re.fullmatch(r"[0-9a-f]{12}", record["reviewed_commit"]), path
        assert "superseded_by" not in record, path
    attribution = _record(ATTRIBUTION)
    assert attribution["reviewed_commit"] == attribution["run_manifest_commit"]
    for first, second in (
        (ROOT / "docs/audit/attribution-first.json", ATTRIBUTION),
        (ROOT / "docs/audit/export-lifecycle-first.json", EXPORT),
    ):
        assert _record(first)["superseded_by"] == second.relative_to(ROOT).as_posix()
        assert _record(second)["supersedes"] == first.relative_to(ROOT).as_posix()


def test_a_reopened_gap_would_flip_the_verdict() -> None:
    """Negative control: each predicate reads its own field, and none is carried by the other three."""
    boundary, attribution, export = _records()

    opened = copy.deepcopy(boundary)
    opened["summary"]["undecidable"] = 1
    assert not _clauses(opened, attribution, export)["undecidable == 0"]

    unplaced = copy.deepcopy(attribution)
    unplaced["failures"]["external_bundle"]["stage_level"] = 0
    assert not _clauses(boundary, unplaced, export)["stage_level == non_passing"]

    unbounded = copy.deepcopy(attribution)
    unbounded["latency"]["tasks_with_stage_boundaries"] = 0
    assert not _clauses(boundary, unbounded, export)["tasks_with_stage_boundaries == tasks"]

    undeclared = copy.deepcopy(export)
    undeclared["summary"]["export_side_events_with_a_digest"] = 0
    assert not _clauses(boundary, attribution, undeclared)[
        "export_side_events_with_a_digest == export_side_events"
    ]

    # Flipping one leaves exactly three true, so the conjunction is a real conjunction rather than
    # one field that happens to agree with itself.
    assert sum(_clauses(opened, attribution, export).values()) == 3
    assert sum(_clauses(boundary, unplaced, export).values()) == 3
    assert sum(_clauses(boundary, attribution, undeclared).values()) == 3


def test_the_declaration_matches_the_readings() -> None:
    """The page and the status line say what the records support, and neither says more.

    This replaces the test that pinned the *absence* of a declaration. With the three producer gaps
    closed, "not exited" stopped being derivable from a gap list, so the honest form runs the other
    way: derive the four predicates above, then hold the prose to them.
    """
    review = _review()
    status = _text(ADR).splitlines()[2]
    assert "**The stage is exited.**" in review
    assert "S2 complete" in status, status
    assert "S2 in progress" not in status, status
    assert "exit not declared" not in status, status
    # Every predicate is named as a predicate next to the field it reads, so a reader can check the
    # verdict rather than take it.
    for name in _clauses(*_records()):
        assert f"`{name}`" in review, name
    # And the page states the boundary the exit does not widen.
    lowered = review.lower()
    for phrase in ("not a trend", "not `publication_ready`", "not full export coverage", "not s3"):
        assert phrase in lowered, phrase
