"""Read ADR-003's S2 exit condition clause by clause against the four readings.

Four readings do not by themselves say whether the stage is exited: the ADR's migration row names an
exit condition with four clauses, and the work column names four items, but the two lists are not the
same list. This file derives the clause anchors from the ADR, the numbers from the records, and the
verdict from the gaps those records still carry. Nothing here is typed as a literal count, so a
record that changes makes the page stale and this test fail rather than quietly agreeing with it.

No new audit record is added by the review. It is a judgement about records that already exist, and
`docs/audit/contract-versions.json` keeps its own count of them.
"""

from __future__ import annotations

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
    assert external["stage_level"] == 0
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


def test_the_verdict_is_not_exited_and_the_records_support_it() -> None:
    review = _review().lower()
    status = _text(ADR).splitlines()[2]
    assert "not exited" in review
    assert "exit not declared" in status, status
    assert "S2 in progress" in status, status
    assert "S2 complete" not in status, status
    assert "product decision" in review

    boundary = _record(BOUNDARY)["summary"]
    attribution = _record(ATTRIBUTION)
    export = _record(EXPORT)["summary"]
    gaps = (
        boundary["undecidable"] > 0,
        attribution["failures"]["external_bundle"]["stage_level"] == 0,
        export["export_side_events_with_a_digest"] == 0,
    )
    assert any(gaps), (boundary, attribution["failures"], export)
