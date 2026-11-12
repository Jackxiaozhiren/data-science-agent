"""The export-lifecycle reading must be arithmetic over the tree, not a typed verdict.

Three failure modes are worth guarding here, each because it already happened in this repository:

* A number copied from one machine. Nothing in this reading is a clock or a local run, so the test
  rebuilds every field from the tree and refuses a record that has drifted from it.
* An absent class scored as zero. ``csv``, ``png`` and ``xlsx`` have no committed export; the test
  requires each to stay ``not_measured`` and requires no file of that class to exist where the
  reading says there is none.
* A citation that resolves to nothing. Every surface an event names is looked up from a closed table
  in this file rather than from the record's own strings, so a record cannot turn a citation into a
  filesystem probe of caller-chosen content.

The ADR divergence is pinned from both sides: the quoted phrase must still appear in the ADR, and the
manifest key list the reading reports must still be the one the record carries.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts import measure_export_lifecycle as lifecycle

ROOT = Path(__file__).resolve().parents[2]
RECORD = json.loads((ROOT / "docs/audit/export-lifecycle.json").read_text(encoding="utf-8"))
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"
CASE_STUDIES = ROOT / "case-studies"

#: The only surfaces the reading may cite, by event id. Closed on purpose.
SURFACES = {
    "write:export_artifact": "packages/tools/src/dsa_tools/tools/export_artifact.py",
    "write:save_artifact": "packages/tools/src/dsa_tools/tools/save_artifact.py",
    "record:artifacts_json": "case-studies",
    "export:bundle": "src/data_science_agent/_vendor/dsa_api/routers/bundles.py",
    "read:report_export": "packages/agent/src/dsa_agent/report_export.py",
    "read:consumer": "case-studies",
}

EVENT_ORDER = [
    "write:export_artifact",
    "write:save_artifact",
    "record:artifacts_json",
    "export:bundle",
    "read:report_export",
    "read:consumer",
]

DISCLAIMERS = (
    "no containment",
    "tamper",
    "not_measured is not zero",
    "publication_ready",
)


def test_the_record_speaks_for_one_commit() -> None:
    assert RECORD["schema"] == lifecycle.SCHEMA
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", RECORD["recorded_at"])
    assert re.fullmatch(r"[0-9a-f]{12}", RECORD["reviewed_commit"])


def test_rebuilding_the_reading_reproduces_it() -> None:
    rebuilt = lifecycle.build()
    for key in sorted(set(RECORD) | set(rebuilt)):
        if key == "recorded_at":
            continue
        assert RECORD.get(key) == rebuilt.get(key), key


def test_the_events_are_the_lifecycle_in_order() -> None:
    assert [event["id"] for event in RECORD["events"]] == EVENT_ORDER


def test_every_event_is_answered_and_every_surface_exists() -> None:
    for event in RECORD["events"]:
        assert event["integrity_hash"] in {"recorded", "absent", "stripped"}, event["id"]
        assert event["parse_check"] in {"present", "absent"}, event["id"]
        assert event["evidence"] in {"ran", "read"}, event["id"]
        assert event["detail"].strip(), event["id"]
        assert (ROOT / SURFACES[event["id"]]).exists(), event["id"]


def test_the_summary_is_arithmetic_over_the_events() -> None:
    events = RECORD["events"]
    summary = RECORD["summary"]
    export_side = {"record:artifacts_json", "export:bundle", "read:report_export"}
    assert summary["events"] == len(events)
    assert summary["events_recording_a_digest"] == sum(
        1 for event in events if event["integrity_hash"] == "recorded"
    )
    assert summary["export_side_events"] == len(export_side)
    assert summary["export_side_events_with_a_digest"] == sum(
        1
        for event in events
        if event["id"] in export_side and event["integrity_hash"] == "recorded"
    )
    assert summary["events_with_a_parse_check"] == sum(
        1 for event in events if event["parse_check"] == "present"
    )
    assert summary["events_measured_by_running"] == sum(
        1 for event in events if event["evidence"] == "ran"
    )


def test_parseability_is_recounted_from_the_tree() -> None:
    counts: dict[str, int] = {}
    for path in CASE_STUDIES.glob("*/outputs/*"):
        if path.is_file() and path.suffix in {".json", ".md"}:
            name = path.suffix.lstrip(".")
            counts[name] = counts.get(name, 0) + 1
    measured = {
        name: entry["committed"]
        for name, entry in RECORD["parseability"].items()
        if entry.get("status") != "not_measured"
    }
    assert measured == counts
    assert RECORD["summary"]["committed_exports"] == sum(counts.values())
    assert RECORD["summary"]["committed_exports_parsed"] == sum(counts.values())


def test_an_unmeasured_class_has_no_committed_file() -> None:
    for name, entry in RECORD["parseability"].items():
        if entry.get("status") != "not_measured":
            assert entry["committed"] > 0, name
            continue
        assert entry["parsed"] is None, name
        assert entry["reason"].strip(), name
        assert list(CASE_STUDIES.glob(f"*/outputs/*.{name}")) == [], name
    assert RECORD["summary"]["classes_not_measured"] == sorted(
        name
        for name, entry in RECORD["parseability"].items()
        if entry.get("status") == "not_measured"
    )


def test_the_divergence_quotes_the_adr_it_accuses() -> None:
    divergence = RECORD["adr_divergence"]
    assert divergence["claim"] in ADR.read_text(encoding="utf-8"), divergence["claim"]
    assert divergence["claim_in_document"] is True
    assert divergence["manifest_keys"] == [
        "artifact_root",
        "excluded",
        "included",
        "run_id",
        "storage",
    ]
    assert divergence["hash_keys_in_manifest"] == []


def test_the_disclaimers_are_pinned() -> None:
    joined = " ".join(RECORD["not_claimed"]).lower()
    for phrase in DISCLAIMERS:
        assert phrase in joined, phrase
    assert RECORD["procedure"] and all(step.strip() for step in RECORD["procedure"])
