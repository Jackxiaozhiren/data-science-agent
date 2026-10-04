"""§102: the orphan-read detector and its bounded external list.

`scripts/find_orphan_reads.py` answers one question mechanically, because it is the question §101 had
to be answered by hand: does this ``record.get("key", default)`` read a key anything in the repository
writes? A read with a default is the dangerous shape -- a renamed or never-written key returns the
default and no test notices.

The controls below are the falsification half: each asserts the detector *can* fail.
"""

from __future__ import annotations

import ast
import json
import re
import textwrap
from pathlib import Path

import pytest

import scripts.find_orphan_reads as probe


def test_the_shipped_tree_matches_the_declared_list() -> None:
    assert probe.evaluate(probe.measure(), probe.load_list()) == []


def test_every_declared_entry_carries_a_real_reason_and_a_date() -> None:
    entries = probe.load_list()
    assert entries, "the list must exist and be populated"
    for entry in entries:
        for field in probe.REQUIRED_FIELDS:
            assert str(entry[field]).strip(), f"{entry['key']}: {field} is empty"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry["reviewed_on"]), (
            f"{entry['key']}: reviewed_on must be a date, not {entry['reviewed_on']!r}"
        )


def test_a_new_orphan_read_fails_the_gate() -> None:
    """The gate can go red: an unlisted key read with a default is a problem, not a shrug."""
    problems = probe.evaluate(
        {"brand_new_key": ["packages/agent/src/dsa_agent/graph.py:1"]},
        [
            {
                "key": "DSA_MAX_COST_USD",
                "external_source": "env",
                "why_no_producer": "x",
                "reviewed_on": "d",
            }
        ],
    )

    assert any("brand_new_key" in line for line in problems)


def test_an_entry_that_stops_being_an_orphan_fails_the_gate() -> None:
    """The list cannot rot: a declared key that now has a producer must be pruned."""
    problems = probe.evaluate(
        {},
        [
            {
                "key": "gone_away",
                "external_source": "env",
                "why_no_producer": "x",
                "reviewed_on": "d",
            }
        ],
    )

    assert any("gone_away" in line for line in problems)
    assert any("no longer an orphan" in line for line in problems)


def test_the_producer_scan_sees_every_shape_a_key_can_be_written_in() -> None:
    tree = ast.parse(
        textwrap.dedent(
            """
            class State:
                field_key: str

            def build():
                record = {"literal_key": 1}
                record["assigned_key"] = 2
                record.setdefault("defaulted_key", {})
                call(any_key=3)
                return record
            """
        )
    )
    produced = probe._produced_names(tree)

    assert {"literal_key", "assigned_key", "defaulted_key", "any_key", "field_key"} <= produced


def test_defaulted_reads_are_found_with_their_sites() -> None:
    tree = ast.parse('value = record.get("literal_key", 0)\nother = record.get("nobody_writes", 0)')

    reads = probe._defaulted_reads(tree)

    assert ("literal_key", 1) in reads
    assert ("nobody_writes", 2) in reads


def test_the_detector_would_have_caught_the_101_defect() -> None:
    """§101 by machine instead of by hand: reading `trajectory` where the writer says `semantic`."""
    consumer = ast.parse('trajectory = float(rs.get("trajectory", 0))')
    producer = ast.parse('score = {"semantic": trajectory_rate, "overall": overall}')

    assert ("trajectory", 1) in probe._defaulted_reads(consumer)
    assert "trajectory" not in probe._produced_names(producer)
    assert "semantic" in probe._produced_names(producer)


def test_a_seeded_list_is_refused_until_it_is_reviewed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``--seed`` output cannot ship: its required fields are empty, and the loader refuses them."""
    list_file = tmp_path / "orphan-reads.json"
    monkeypatch.setattr(probe, "LIST_PATH", list_file)
    probe.write_list({"SOMETHING": ["packages/agent/src/dsa_agent/graph.py:1"]})

    with pytest.raises(SystemExit, match="missing"):
        probe.load_list()


def test_a_missing_field_is_refused(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    list_file = tmp_path / "orphan-reads.json"
    list_file.write_text(
        json.dumps({"entries": [{"key": "X", "reviewed_on": "2026-10-04"}]}), "utf-8"
    )
    monkeypatch.setattr(probe, "LIST_PATH", list_file)

    with pytest.raises(SystemExit, match="missing"):
        probe.load_list()
