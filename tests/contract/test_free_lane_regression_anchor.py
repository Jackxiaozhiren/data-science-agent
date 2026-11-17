"""The free-lane regression record must stay internally recomputable and non-publishable."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "docs/audit/free-lane-regression-anchor.json"
SCHEMA = "free-lane-regression-anchor/v1"


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_schema_token_is_checked_against_a_constant() -> None:
    """The record's schema token is compared with a literal outside the record."""
    assert _record()["schema"] == SCHEMA


def test_schema_and_two_lanes() -> None:
    record = _record()
    assert record["schema"] == "free-lane-regression-anchor/v1"
    assert len(record["lanes"]) == 2


def test_each_lane_names_a_real_provider_and_model() -> None:
    for lane in _record()["lanes"]:
        assert lane["provider"] in {"openai-compat", "ollama"}
        assert lane["model"] not in {"", "heuristic", "default"}


def test_aggregate_tokens_equal_sum_of_per_call_entries() -> None:
    for lane in _record()["lanes"]:
        aggregate = lane["token_usage"]
        calls = lane["per_call"]
        assert len(calls) == lane["call_count"]
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            assert aggregate[field] == sum(call[field] for call in calls)


def test_both_lanes_share_one_commit_and_stay_free() -> None:
    record = _record()
    for lane in record["lanes"]:
        assert lane["cost_usd"] == 0.0
    assert len({lane["model"] for lane in record["lanes"]}) == 2


def test_response_ids_present_and_distinct() -> None:
    for lane in _record()["lanes"]:
        ids = lane["response_ids"]
        assert len(ids) == lane["call_count"]
        assert len(set(ids)) == len(ids)


def test_record_never_claims_publication() -> None:
    text = RECORD_PATH.read_text(encoding="utf-8")
    assert "not publication evidence" in text
    assert "cost_usd>0" in text
