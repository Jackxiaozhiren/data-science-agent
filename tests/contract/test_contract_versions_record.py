"""The contract-version register must be read out of the tree, not typed.

Three failure modes are worth guarding, each because it already happened in this repository:

* A version string copied into a document that no check holds you to. Four records declare a token
  and one of them is written by its instrument, read by its test, and never compared with anything;
  the test proves each ``none`` by reading the consumer and finding the token absent.
* A register that drifts from the files it registers. Every token is compared with the file it lives
  in, and the rows are compared with the directory, so a new reading without a row fails here.
* A policy that describes itself as enforced when nothing enforces it. The clauses name their
  enforcement, and the validator that ``--verify`` runs is exercised here on doctored rows, one per
  clause, so a rule that stops firing reddens this file rather than a reader.

The register is not a reading of the tree's behaviour; it is the shape contract the readings rest on.
That is why its own ``recorded_at`` is the only field excluded from the rebuild comparison.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from scripts import measure_contract_versions as cv

ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "docs/audit/contract-versions.json").read_text(encoding="utf-8"))
PAGE = ROOT / "docs/measurement-basis.md"

#: Who reads each record. Closed on purpose: a row cannot nominate its own consumer.
CONSUMERS = {
    "docs/audit/attribution.json": "tests/contract/test_attribution_record.py",
    "docs/audit/authorization-coverage-second.json": (
        "tests/contract/test_authorization_coverage_record.py"
    ),
    "docs/audit/authorization-coverage.json": (
        "tests/contract/test_authorization_coverage_record.py"
    ),
    "docs/audit/evidence-alignment.json": "tests/contract/test_evidence_alignment_record.py",
    "docs/audit/execution-boundary.json": "tests/contract/test_execution_boundary_record.py",
    "docs/audit/export-lifecycle-first.json": ("tests/contract/test_export_lifecycle_record.py"),
    "docs/audit/export-lifecycle.json": "tests/contract/test_export_lifecycle_record.py",
    "docs/audit/independent-rerun.json": "tests/contract/test_independent_rerun_record.py",
    "docs/audit/served-artifacts.json": "tests/contract/test_served_artifacts_probe.py",
}

DISCLAIMERS = (
    "not an external api guarantee",
    "no claim that a checked token makes a reading correct",
    "read as v0",
    "gate inputs",
    "publication_ready",
)


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _rows() -> list[dict[str, Any]]:
    return RECORD["records"]


def _synthetic(**overrides: Any) -> dict[str, Any]:
    row = {
        "path": "docs/audit/example.json",
        "recorded_at": "2026-11-12T00:00:00Z",
        "declared_schema": "example/v1",
        "declared_frame_schema": None,
        "effective_version": "v1",
        "pre_policy": False,
        "check_kind": "record-vs-constant",
        "checked_by": "tests/contract/test_example.py",
        "states_bump_rule": False,
        "detail": "a synthetic row",
    }
    row.update(overrides)
    return row


def test_the_register_speaks_for_one_commit() -> None:
    assert RECORD["schema"] == cv.SCHEMA
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", RECORD["recorded_at"])
    assert re.fullmatch(r"[0-9a-f]{12}", RECORD["reviewed_commit"])
    assert RECORD["in_force_from"] == cv.IN_FORCE_FROM


def test_rebuilding_the_register_reproduces_it() -> None:
    rebuilt = cv.build()
    for key in sorted(set(RECORD) | set(rebuilt)):
        if key == "recorded_at":
            continue
        assert RECORD.get(key) == rebuilt.get(key), key


def test_the_rows_partition_the_directory() -> None:
    files = sorted(cv.AUDIT.glob("*.json"))
    scope = RECORD["scope"]
    assert scope["readings"] == len(_rows())
    assert scope["readings"] + scope["registers"] + scope["gate_inputs"] == len(files)
    assert (cv.AUDIT / "contract-versions.json").exists()
    registered = {row["path"] for row in _rows()}
    assert "docs/audit/contract-versions.json" not in registered


def test_every_row_resolves_to_a_file_that_agrees() -> None:
    for row in _rows():
        payload = json.loads(_text(row["path"]))
        assert payload.get("schema") == row["declared_schema"], row["path"]
        assert payload.get("frame_schema") == row["declared_frame_schema"], row["path"]
        assert payload["recorded_at"] == row["recorded_at"], row["path"]
        assert row["path"] in CONSUMERS, row["path"]


def test_every_token_matches_the_form() -> None:
    for row in _rows():
        for field in ("declared_schema", "declared_frame_schema"):
            token = row[field]
            if token is None:
                continue
            assert cv.TOKEN_FORM.match(token), (row["path"], field, token)
            assert not token.endswith("/v0"), (row["path"], field, token)


def test_effective_version_follows_from_the_token() -> None:
    for row in _rows():
        expected = row["declared_schema"].rpartition("/")[2] if row["declared_schema"] else "v0"
        assert row["effective_version"] == expected, row["path"]
        assert row["pre_policy"] is (row["recorded_at"][:10] < cv.IN_FORCE_FROM), row["path"]


def test_a_none_claim_is_proved_by_the_consumer() -> None:
    """The label 'nothing checks it' must be readable in the consumer, not asserted by the record."""
    for row in _rows():
        consumer = _text(CONSUMERS[row["path"]]).lower()
        if row["check_kind"] == "none":
            assert row["checked_by"] is None, row["path"]
            assert "schema" not in consumer, row["path"]
            continue
        assert row["checked_by"] == CONSUMERS[row["path"]], row["path"]
        assert (ROOT / row["checked_by"]).exists(), row["path"]
        assert "schema" in _text(row["checked_by"]).lower(), row["path"]


def test_the_summary_is_arithmetic_over_the_rows() -> None:
    rows = _rows()
    summary = RECORD["summary"]
    assert summary["records"] == len(rows)
    assert summary["declaring_own_schema"] == sum(1 for row in rows if row["declared_schema"])
    assert summary["declaring_only_input_schema"] == sum(
        1 for row in rows if not row["declared_schema"] and row["declared_frame_schema"]
    )
    assert summary["pre_policy"] == sum(1 for row in rows if row["pre_policy"])
    assert summary["own_tokens_unchecked"] == sum(
        1 for row in rows if row["declared_schema"] and row["check_kind"] == "none"
    )
    assert summary["records_carrying_a_bump_rule"] == sum(
        1 for row in rows if row["states_bump_rule"]
    )


def test_the_validator_fires_on_each_clause() -> None:
    assert cv.problems([_synthetic()]) == []
    assert "is not <subject>/vN" in " ".join(cv.problems([_synthetic(declared_schema="Example/1")]))
    assert "does not follow" in " ".join(cv.problems([_synthetic(effective_version="v2")]))
    assert "disagrees with the date" in " ".join(cv.problems([_synthetic(pre_policy=True)]))
    assert "is not one of" in " ".join(cv.problems([_synthetic(check_kind="checked")]))
    assert "names a consumer" in " ".join(
        cv.problems([_synthetic(check_kind="none", checked_by="tests/x.py")])
    )
    assert "names no consumer" in " ".join(cv.problems([_synthetic(checked_by=None)]))
    assert "no consumer checks its token" in " ".join(
        cv.problems([_synthetic(check_kind="none", checked_by=None)])
    )
    assert "registered twice" in " ".join(cv.problems([_synthetic(), _synthetic()]))


def test_the_policy_clauses_name_their_enforcement() -> None:
    clauses = RECORD["policy"]["clauses"]
    assert [clause["id"] for clause in clauses] == ["P1", "P2", "P3", "P4", "P5"]
    for clause in clauses:
        assert clause["rule"].strip(), clause["id"]
        assert clause["enforced_by"].strip(), clause["id"]
    assert RECORD["policy"]["pre_policy_version"] == "v0"
    assert cv.IN_FORCE_FROM in RECORD["policy"]["applies_to"]


def test_the_disclaimers_and_the_page_are_pinned() -> None:
    joined = " ".join(RECORD["not_claimed"]).lower()
    for phrase in DISCLAIMERS:
        assert phrase in joined, phrase
    assert all(step.strip() for step in RECORD["procedure"])
    page = PAGE.read_text(encoding="utf-8")
    assert "docs/audit/contract-versions.json" in page
    assert "scripts/measure_contract_versions.py" in page
