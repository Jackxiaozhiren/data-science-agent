"""The independent re-run reading must be recomputable, and its exclusions must stay exclusions."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from scripts import compare_baseline_run as rerun

ROOT = Path(__file__).resolve().parents[2]
RECORDING_PATH = ROOT / "benchmarks/baseline/results.json"
RECORD_PATH = ROOT / "docs/audit/independent-rerun.json"
BASIS_PATH = ROOT / "docs/measurement-basis.md"


def _recording() -> dict:
    import json

    return json.loads(RECORDING_PATH.read_text(encoding="utf-8"))


def _record() -> dict:
    import json

    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def _mutated(**changes: object) -> dict:
    payload = copy.deepcopy(_recording())
    for key, value in changes.items():
        payload[key] = value
    return payload


def test_recording_digest_is_an_invariant() -> None:
    """The reading names the exact bytes it compared against; editing the freeze breaks it."""
    record = _record()
    digest = hashlib.sha256(RECORDING_PATH.read_bytes()).hexdigest()
    assert record["comparison"]["recording_sha256"] == digest
    assert record["sample"]["recording_sha256"] == digest


def test_the_recording_did_not_move_under_the_reading() -> None:
    record = _record()
    assert record["comparison"]["tasks_in_recording"] == record["sample"]["tasks"]
    assert (
        record["sample"]["recording_commit"]
        == record["comparison"]["execution"]["recording_commit"]
    )


def test_recorded_reading_is_internally_consistent() -> None:
    record = _record()
    comparison = record["comparison"]
    assert record["verdict"] == "measured"
    assert record["sampled"] == record["denominator"] == 1
    layers = comparison["layers"]
    assert set(layers) == {"task_roster", "task_verdicts", "aggregate", "execution"}
    everything_agrees = all(value == rerun.VERDICT_OK for value in layers.values())
    assert everything_agrees is (comparison["verdict"] == rerun.VERDICT_OK)
    assert record["numerator"] == (record["denominator"] if everything_agrees else 0)
    assert set(comparison["task_field_counts"]) == set(rerun.TASK_FIELDS)
    assert comparison["roster_differences"] == []
    assert comparison["task_disagreements"] == {}


def test_an_unchanged_recording_scores_as_reproduced() -> None:
    """A bundle compared with itself must pass every layer -- the instrument's own control."""
    result = rerun.compare_payloads(_recording(), _recording())
    assert result["verdict"] == rerun.VERDICT_OK
    assert all(value == rerun.VERDICT_OK for value in result["layers"].values())
    assert set(result["task_field_counts"].values()) == {0}


def test_one_broken_verdict_is_reported_at_its_own_layer_only() -> None:
    payload = copy.deepcopy(_recording())
    payload["results"][0]["metrics"]["task_success"] = False
    result = rerun.compare_payloads(_recording(), payload)
    assert result["verdict"] == rerun.VERDICT_MISMATCH
    assert result["layers"]["task_verdicts"] == rerun.VERDICT_MISMATCH
    assert result["layers"]["task_roster"] == rerun.VERDICT_OK
    assert result["task_field_counts"]["task_success"] == 1
    assert result["task_disagreements"]["task_success"] == [payload["results"][0]["task_id"]]


def test_a_dropped_task_is_a_roster_mismatch() -> None:
    payload = copy.deepcopy(_recording())
    dropped = payload["results"].pop(0)["task_id"]
    result = rerun.compare_payloads(_recording(), payload)
    assert result["layers"]["task_roster"] == rerun.VERDICT_MISMATCH
    assert result["roster_differences"] == [f"only_in_recording:{dropped}"]


def test_a_latency_difference_is_not_a_mismatch() -> None:
    """Wall-clock time is the machine's property. The verdict must not depend on it."""
    payload = copy.deepcopy(_recording())
    for row in payload["results"]:
        row["metrics"]["latency_ms"] = 999_999
    payload["aggregate"]["mean_latency_ms"] = 999_999.0
    result = rerun.compare_payloads(_recording(), payload)
    assert result["verdict"] == rerun.VERDICT_OK
    assert result["aggregate"]["differing_keys"] == []
    assert result["aggregate"]["excluded_keys"] == ["mean_latency_ms"]
    assert "mean_latency_ms" not in result["aggregate"]["differing_keys"]


def test_a_different_commit_is_not_a_mismatch() -> None:
    """The recording names the commit it froze at; a re-run at another commit names its own."""
    payload = copy.deepcopy(_recording())
    payload["execution"]["git_commit"] = "000000000000"
    result = rerun.compare_payloads(_recording(), payload)
    assert result["verdict"] == rerun.VERDICT_OK
    assert result["execution"]["git_commit_compared"] is False
    assert result["execution"]["fresh_commit"] == "000000000000"


def test_a_changed_model_lane_is_a_mismatch() -> None:
    """If the fresh side ran a different provider, the comparison is between unlike runs."""
    payload = copy.deepcopy(_recording())
    payload["execution"]["call_count"] = 42
    result = rerun.compare_payloads(_recording(), payload)
    assert result["verdict"] == rerun.VERDICT_MISMATCH
    assert result["execution"]["differing_keys"] == ["call_count"]


def test_an_absent_fresh_side_reads_as_unmeasured_never_as_a_pass() -> None:
    """No fresh run means no measurement. A missing file must not be scored as agreement."""
    assert rerun.compare()["verdict"] in {
        rerun.VERDICT_OK,
        rerun.VERDICT_MISMATCH,
        rerun.VERDICT_UNMEASURED,
    }
    original = rerun.FRESH
    try:
        rerun.FRESH = Path("/nonexistent/rerun/results.json")
        result = rerun.compare()
    finally:
        rerun.FRESH = original
    assert result["verdict"] == rerun.VERDICT_UNMEASURED
    assert "absent" in result["reason"]


def test_measurement_basis_points_at_this_reading() -> None:
    basis = BASIS_PATH.read_text(encoding="utf-8")
    assert "docs/audit/independent-rerun.json" in basis
    assert "scripts/compare_baseline_run.py" in basis


def test_record_does_not_claim_publication_readiness() -> None:
    record = _record()
    joined = " ".join(record["not_claimed"])
    assert "publication_ready" in joined
    assert "stub" in joined
