"""The S1 authorization-coverage reading must be derived, not typed.

The repository's rule for a number in a shipped document is that something recomputes it
(`tests/test_doc_census_claims.py`, `scripts/check_public_claims.py`). This reading is a
human adjudication over the tree, so no collector can re-decide it -- but the arithmetic
around the adjudication can still be checked: the total, the numerator, the gap list and
the covered/not-covered verdict all follow from the same per-class fields. A later edit
that changes one without the others is a transcription error, not a new reading.

What these tests deliberately do not check: whether a class was scored correctly. That
judgement lives in the record's evidence and reason fields and is reviewed by a person.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "docs/audit/authorization-coverage.json"
BASIS_PAGE = ROOT / "docs/measurement-basis.md"


def _record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_arithmetic_follows_the_checklist() -> None:
    record = _record()
    classes = record["action_classes"]
    ids = [item["id"] for item in classes]

    assert len(set(ids)) == len(classes)
    assert set(ids) == {f"AC{i}" for i in range(1, len(classes) + 1)}
    assert len(classes) == record["denominator"]
    assert sum(1 for item in classes if item["covered"]) == record["numerator"]
    assert set(record["gaps"]) == {item["id"] for item in classes if not item["covered"]}
    assert record["verdict"] == "measured"
    assert record["recorded_at"].endswith("Z")
    assert len(record["reviewed_commit"]) == 7


def test_covered_means_both_parts_are_named() -> None:
    for item in _record()["action_classes"]:
        key = item["id"]
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


def test_basis_page_links_the_record() -> None:
    rows = [
        line
        for line in BASIS_PAGE.read_text(encoding="utf-8").splitlines()
        if line.startswith("| Authorization coverage |")
    ]

    assert len(rows) == 1
    assert "docs/audit/authorization-coverage.json" in rows[0]
    assert "measured" in rows[0]
