"""The first evidence-alignment reading must be recomputable from the pinned frame alone."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import measure_evidence_alignment as alignment

ROOT = Path(__file__).resolve().parents[2]
FRAME_PATH = ROOT / "tests/fixtures/evidence-alignment/frame.json"
RECORD_PATH = ROOT / "docs/audit/evidence-alignment.json"
BASIS_PATH = ROOT / "docs/measurement-basis.md"


def _frame() -> dict:
    return json.loads(FRAME_PATH.read_text(encoding="utf-8"))


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_frame_digest_matches_the_record() -> None:
    record = _record()
    assert record["frame_path"] == "tests/fixtures/evidence-alignment/frame.json"
    assert hashlib.sha256(FRAME_PATH.read_bytes()).hexdigest() == record["frame_sha256"]


def test_frame_key_does_not_claim_a_registered_orphan_read() -> None:
    """A top-level 'runs' key would make find_orphan_reads.py --check fail on verify_release.py."""
    frame = _frame()
    assert "reports" in frame
    assert "runs" not in frame


def test_verify_agrees_with_the_record() -> None:
    ok, checks = alignment.verify()
    assert ok
    assert all(checks.values())


def test_source_hash_manifest_is_complete_and_anchored() -> None:
    frame, record = _frame(), _record()
    hashes = [report["source_sha256"] for report in frame["reports"]]
    assert len(hashes) == record["frame_runs"] == 95
    assert all(len(value) == 64 and all(c in "0123456789abcdef" for c in value) for value in hashes)
    digest = hashlib.sha256(alignment.canonical_bytes(hashes)).hexdigest()
    assert digest == record["source_sha256_manifest_sha256"]
    assert frame["schema"] == record["frame_schema"]
    assert frame["capture_rule"] == record["capture"]["capture_rule"]


def test_reading_is_recomputed_from_the_frame() -> None:
    measured = alignment.measure(_frame())
    record = _record()
    for key in (
        "frame_schema",
        "frame_runs",
        "numerator",
        "denominator",
        "stages",
        "gaps",
        "diagnostics",
    ):
        assert measured[key] == record[key], key
    assert record["numerator"] == record["stages"]["L4_data_hash"]
    assert record["denominator"] == record["stages"]["L1_evidence_node"]


def test_every_hop_is_scored_separately_and_no_gap_is_hidden() -> None:
    record = _record()
    stages = record["stages"]
    assert list(stages) == list(alignment.STAGES)
    assert all(isinstance(value, int) for value in stages.values())
    order = [stages[name] for name in alignment.STAGES]
    assert order == sorted(order, reverse=True)
    assert len(record["gaps"]) == record["denominator"] - record["numerator"]


def test_measurement_basis_points_at_this_reading() -> None:
    basis = BASIS_PATH.read_text(encoding="utf-8")
    row = next(line for line in basis.splitlines() if line.startswith("| Evidence alignment |"))
    assert "docs/audit/evidence-alignment.json" in row
    assert "measured" in row
    assert "defined, not measured" not in row
    assert record_basis_fragment() in basis


def record_basis_fragment() -> str:
    return "Sampling is by conclusion, not by run"


def test_a_broken_reference_is_reported_as_a_gap_at_its_hop() -> None:
    frame = {
        "schema": alignment.SCHEMA,
        "reports": [
            {
                "run_id": "synthetic-a",
                "source_sha256": "a" * 64,
                "dataset_sha256": "b" * 64,
                "dataset_path_present": True,
                "tool_calls": [
                    {"call_id": "call-1", "input_is_object": True, "input_keys": ["path"]}
                ],
                "evidence": [{"id": "ev-1", "source_id": "call-1"}],
                "insights": [
                    {"id": "in-1", "evidence_ids": ["ev-1"]},
                    {"id": "in-2", "evidence_ids": ["ev-missing"]},
                ],
            },
            {
                "run_id": "synthetic-b",
                "source_sha256": "c" * 64,
                "dataset_sha256": "d" * 64,
                "dataset_path_present": True,
                "tool_calls": [
                    {"call_id": "call-2", "input_is_object": True, "input_keys": ["path"]}
                ],
                "evidence": [{"id": "ev-2", "source_id": "call-missing"}],
                "insights": [{"id": "in-3", "evidence_ids": ["ev-2"]}],
            },
            {
                "run_id": "synthetic-c",
                "source_sha256": "e" * 64,
                "dataset_sha256": "",
                "dataset_path_present": False,
                "tool_calls": [
                    {"call_id": "call-3", "input_is_object": True, "input_keys": ["path"]}
                ],
                "evidence": [{"id": "ev-3", "source_id": "call-3"}],
                "insights": [{"id": "in-4", "evidence_ids": ["ev-3"]}],
            },
        ],
    }
    result = alignment.measure(frame)
    assert result["denominator"] == 4
    assert result["numerator"] == 1
    assert result["diagnostics"]["runs_without_conclusions"] == 0
    assert [(gap["conclusion_id"], gap["gap_at"]) for gap in result["gaps"]] == [
        ("in-2", "L1_evidence_node"),
        ("in-3", "L2_computation"),
        ("in-4", "L4_data_hash"),
    ]


def test_runs_without_conclusions_do_not_inflate_the_denominator() -> None:
    empty = {
        "run_id": "empty",
        "source_sha256": "f" * 64,
        "dataset_sha256": "0" * 64,
        "dataset_path_present": True,
        "tool_calls": [],
        "evidence": [],
        "insights": [],
    }
    result = alignment.measure({"schema": alignment.SCHEMA, "reports": [empty]})
    assert result["denominator"] == 0
    assert result["numerator"] == 0
    assert result["diagnostics"]["runs_without_conclusions"] == 1
