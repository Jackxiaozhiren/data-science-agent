"""The S1 authorization-coverage readings must be derived, not typed.

The repository's rule for a number in a shipped document is that something recomputes it
(`tests/test_doc_census_claims.py`, `scripts/check_public_claims.py`). A reading is a
human adjudication over the tree, so no collector can re-decide it -- but the arithmetic
around the adjudication can still be checked: the total, the numerator, the gap list and
the covered/not-covered verdict all follow from the same per-class fields. For the second
reading the verdicts are additionally recomputed from the governance table itself, so a
row silently going blank would fail CI rather than quietly lowering a score.

What these tests deliberately do not check: whether a class was scored correctly. That
judgement lives in each record's evidence and reason fields and is reviewed by a person.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIRST = ROOT / "docs/audit/authorization-coverage.json"
SECOND = ROOT / "docs/audit/authorization-coverage-second.json"
BASIS_PAGE = ROOT / "docs/measurement-basis.md"
GOVERNANCE = ROOT / "GOVERNANCE.md"
RECORDS = (FIRST, SECOND)


def _record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_arithmetic_follows_the_checklist() -> None:
    for path in RECORDS:
        record = _record(path)
        classes = record["action_classes"]
        ids = [item["id"] for item in classes]

        assert len(set(ids)) == len(classes), path.name
        assert set(ids) == {f"AC{i}" for i in range(1, len(classes) + 1)}, path.name
        assert len(classes) == record["denominator"], path.name
        assert sum(1 for item in classes if item["covered"]) == record["numerator"], path.name
        assert set(record["gaps"]) == {item["id"] for item in classes if not item["covered"]}
        assert record["verdict"] == "measured", path.name
        assert record["recorded_at"].endswith("Z"), path.name
        assert len(record["reviewed_commit"]) == 7, path.name


def test_covered_means_both_parts_are_named() -> None:
    for path in RECORDS:
        for item in _record(path)["action_classes"]:
            key = f"{path.name}:{item['id']}"
            authorizer = item["authorizer"]
            decision_record = item["decision_record"]
            has_authorizer = isinstance(authorizer, str) and bool(authorizer.strip())
            has_record = isinstance(decision_record, str) and bool(decision_record.strip())

            assert item["covered"] == (has_authorizer and has_record), key
            assert isinstance(item["reason"], str) and item["reason"].strip(), key
            assert isinstance(item["action"], str) and item["action"].strip(), key
            assert item["external_consequence"].strip(), key
            assert isinstance(item["authorizer_evidence"], list), key
            assert isinstance(item["decision_record_evidence"], list), key

            evidence = item["authorizer_evidence"] + item["decision_record_evidence"]
            assert all(isinstance(entry, str) and entry for entry in evidence), key

            if item["covered"]:
                assert item["authorizer_evidence"], key
                assert item["decision_record_evidence"], key
            else:
                assert isinstance(item["existing_controls"], list), key
                assert item["existing_controls"], key


def test_basis_page_links_both_records() -> None:
    rows = [
        line
        for line in BASIS_PAGE.read_text(encoding="utf-8").splitlines()
        if line.startswith("| Authorization coverage |")
    ]

    assert len(rows) == 1
    assert "docs/audit/authorization-coverage.json" in rows[0]
    assert "docs/audit/authorization-coverage-second.json" in rows[0]
    assert "measured" in rows[0]


def test_readings_share_one_basis_and_history_is_intact() -> None:
    first, second = _record(FIRST), _record(SECOND)

    for field in ("metric", "basis", "method", "denominator_basis", "denominator"):
        assert first[field] == second[field], field
    assert [(c["id"], c["action"], c["external_consequence"]) for c in first["action_classes"]] == [
        (c["id"], c["action"], c["external_consequence"]) for c in second["action_classes"]
    ]

    assert second["basis_unchanged"] is True
    assert second["previous_reading"]["path"] == "docs/audit/authorization-coverage.json"
    assert second["previous_reading"]["recorded_at"] == first["recorded_at"]
    assert second["previous_reading"]["numerator"] == first["numerator"]
    assert second["previous_reading"]["denominator"] == first["denominator"]
    assert second["recorded_at"] > first["recorded_at"]
    assert first["proposed_amendment"].startswith("NOT APPLIED")
    assert second["gaps"] == []
    assert second["numerator"] > first["numerator"]


def test_second_reading_is_recomputed_from_the_governance_table() -> None:
    rows = {}
    for line in GOVERNANCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("| AC"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            assert len(cells) == 5, line
            rows[cells[0]] = cells

    assert len(rows) == 9
    second = _record(SECOND)
    recomputed = 0

    for item in second["action_classes"]:
        cells = rows[item["id"]]
        named_authorizer = bool(cells[2]) and cells[2] not in {"-", "—", "TBD"}
        named_record = bool(cells[3]) and len(cells[3]) > 20
        derived = named_authorizer and named_record

        assert item["covered"] == derived, item["id"]
        recomputed += int(derived)

    assert recomputed == second["numerator"] == second["denominator"]
