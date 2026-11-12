"""The S2 attribution reading must be arithmetic over a pinned frame, not a typed verdict.

Two failure modes are worth guarding, because both already happened elsewhere in this repository:

* A latency number copied from one machine into a document that reads like a property of the code.
  The frozen baseline README records three different means on the same commit minutes apart, so the
  test pins the reading to the frame's own rows and pins the disclaimer that says absolute
  milliseconds do not travel.
* A zero that came from an empty denominator. The frozen baseline has no failing task at all; that
  is ``not_measured``, not a perfect attribution score. S1's first rule says a zero is a reading,
  and a zero nobody looked at is not one.

The derivation below is written out again rather than imported from the instrument, so a change to
``measure_attribution.py`` cannot quietly redefine what "attributable" meant when the reading was
taken.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from pathlib import Path

from scripts import measure_attribution as attribution

ROOT = Path(__file__).resolve().parents[2]
FRAME_PATH = ROOT / "tests/fixtures/attribution/frame.json"
RECORD_PATH = ROOT / "docs/audit/attribution.json"
BASIS_PAGE = ROOT / "docs/measurement-basis.md"
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"
FRAME = json.loads(FRAME_PATH.read_text(encoding="utf-8"))
RECORD = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
#: Only a closed cause-code field counts as a stage-level attribution. Nothing here scores a guess
#: made from prose, a score, or the absence of evidence as "attributed".
CAUSE_KEYS = ("error_code", "failure_stage", "stage", "cause")
#: Closed set of committed sources. A path resolved from the record would turn a citation into a
#: filesystem probe of caller-chosen content, so the paths live here and the frame's strings are
#: only ever compared as strings.
COMMITTED_SOURCES = {
    "frozen_baseline": ROOT / "benchmarks" / "baseline" / "results.json",
    "external_bundle": ROOT
    / "benchmarks"
    / "external"
    / "datascibench"
    / "results"
    / "raw_runs.json",
}


def _signal(row: dict) -> str | None:
    if row["status"] != "COMPLETED":
        return "run_did_not_complete"
    if row["report_chars"] == 0:
        return "no_report"
    if row["n_tool_calls"] == 0:
        return "no_tool_calls"
    if row["n_evidence"] == 0:
        return "no_evidence"
    return None


def test_verify_rebuilds_the_reading_from_the_frame() -> None:
    ok, checks = attribution.verify()
    assert ok, [name for name, passed in checks.items() if not passed]


def test_frame_hash_and_committed_sources_are_the_ones_in_the_tree() -> None:
    assert hashlib.sha256(FRAME_PATH.read_bytes()).hexdigest() == RECORD["frame_sha256"]
    sources = FRAME["sources"]
    assert set(sources) == set(COMMITTED_SOURCES) | {"deterministic_run", "run_manifest"}
    for name, path in COMMITTED_SOURCES.items():
        entry = sources[name]
        assert entry["committed"] is True, name
        assert entry["path"] == path.relative_to(ROOT).as_posix(), name
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], name
        assert len(raw) == entry["bytes"], name
    for name, expected_path in (
        ("deterministic_run", "artifacts/bench-attribution/raw_runs.json"),
        ("run_manifest", "artifacts/bench-attribution/run_manifest.json"),
    ):
        local = sources[name]
        assert local["committed"] is False, name
        assert local["path"] == expected_path, name
        assert re.fullmatch(r"[0-9a-f]{64}", local["sha256"]), name


def test_provenance_names_the_commit_the_run_was_taken_on() -> None:
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", RECORD["recorded_at"])
    assert RECORD["schema"] == "attribution-reading/v1"
    assert FRAME["schema"] == RECORD["frame_schema"] == "attribution-frame/v1"
    assert RECORD["reviewed_commit"] == RECORD["run_manifest_commit"] == attribution.REVIEWED_COMMIT
    assert RECORD["run_manifest_llm_mode"] == "stub"
    assert RECORD["run_manifest_call_count"] == 0
    assert RECORD["environment"] == FRAME["environment"]
    manifest = ROOT / "artifacts" / "bench-attribution" / "run_manifest.json"
    if manifest.is_file():
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        assert recorded["execution"]["git_commit"] == RECORD["reviewed_commit"]
        assert recorded["execution"]["llm_mode"] == "stub"
        assert recorded["execution"]["call_count"] == 0


def test_every_latency_row_is_internally_consistent() -> None:
    rows = FRAME["latency_rows"]
    assert len(rows) == RECORD["latency"]["tasks"] == FRAME["frozen_baseline"]["n_tasks"]
    assert len({row["task_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["elapsed_ms"] > 0, row["task_id"]
        assert 0 <= row["tool_ms"] <= row["elapsed_ms"], row["task_id"]
        assert row["outside_window_ms"] == max(0, row["elapsed_ms"] - row["window_ms"])
        assert 0 <= row["zero_duration_calls"] <= row["n_tool_calls"], row["task_id"]
        assert 0 <= row["tool_failures"] <= row["n_tool_calls"], row["task_id"]
        assert row["stage_keys"] == [], row["task_id"]


def test_latency_numbers_are_recomputed_from_the_rows() -> None:
    rows = FRAME["latency_rows"]
    shares = [row["tool_ms"] / row["elapsed_ms"] for row in rows]
    expected = {
        "tasks": len(rows),
        "tool_calls": sum(row["n_tool_calls"] for row in rows),
        "tool_failures": sum(row["tool_failures"] for row in rows),
        "zero_duration_calls": sum(row["zero_duration_calls"] for row in rows),
        "elapsed_ms_total": sum(row["elapsed_ms"] for row in rows),
        "tool_ms_total": sum(row["tool_ms"] for row in rows),
        "outside_window_ms_total": sum(row["outside_window_ms"] for row in rows),
        "per_task_tool_share": {
            "min": round(min(shares), 4),
            "median": round(statistics.median(shares), 4),
            "mean": round(statistics.mean(shares), 4),
            "max": round(max(shares), 4),
        },
        "tasks_with_residual_ms": sum(1 for row in rows if row["elapsed_ms"] > row["tool_ms"]),
        "tasks_over_tool_budget": sum(1 for row in rows if row["tool_ms"] > row["elapsed_ms"]),
        "tasks_with_stage_boundaries": sum(1 for row in rows if row["stage_keys"]),
        "tasks_outside_run_window": sum(
            1 for row in rows if row["outside_window_ms"] > FRAME["window_resolution_ms"]
        ),
    }
    assert RECORD["latency"] == expected
    # A share is a lower bound while sub-millisecond calls read zero. That is why the record is
    # about what the clock can be pointed at, not about how long a tool took.
    assert expected["zero_duration_calls"] > 0
    assert expected["tasks_with_stage_boundaries"] == 0
    assert expected["tasks_with_residual_ms"] == len(rows)


def test_every_failure_row_is_internally_consistent() -> None:
    rows = FRAME["failure_rows"]
    assert len(rows) == RECORD["failures"]["external_bundle"]["non_passing"]
    assert len({row["task_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["outcome"] in {"failed", "execution_error", "unsupported"}, row["task_id"]
        assert row["cause_keys"] == [], row["task_id"]
        assert row["score"] is None or 0 <= row["score"] < FRAME["pass_mark"]
        for key in ("n_tool_calls", "n_evidence", "report_chars"):
            assert row[key] >= 0, (row["task_id"], key)


def test_failure_numbers_are_recomputed_from_the_rows() -> None:
    rows = FRAME["failure_rows"]
    counts: dict[str, int] = {}
    for row in rows:
        signal = _signal(row)
        if signal is not None:
            counts[signal] = counts.get(signal, 0) + 1
    placed = sum(counts.values())
    ext = FRAME["external_bundle"]
    expected = {
        "n_runs": ext["n_runs"],
        "non_passing": len(rows),
        "per_task_latency_present": ext["per_task_latency_present"],
        "wall_s": ext["wall_s"],
        "outcome_level": len(rows),
        "artifact_level": placed,
        "artifact_signals": dict(sorted(counts.items())),
        "stage_level": sum(
            1 for row in rows if any(key in CAUSE_KEYS for key in row["cause_keys"])
        ),
        "unplaced": len(rows) - placed,
        "partial_credit": sum(
            1 for row in rows if row["score"] is not None and 0 < row["score"] < FRAME["pass_mark"]
        ),
        "free_text_errors": sum(1 for row in rows if row["has_error_text"]),
    }
    assert RECORD["failures"]["external_bundle"] == expected
    assert expected["stage_level"] == 0
    assert expected["unplaced"] > 0
    assert expected["per_task_latency_present"] == 0


def test_an_empty_denominator_is_not_a_perfect_score() -> None:
    frozen = RECORD["failures"]["frozen_baseline"]
    assert frozen["non_passing"] == 0
    assert frozen["status"] == "not_measured"
    assert "empty denominator" in frozen["reason"]
    assert FRAME["frozen_baseline"]["n_non_passing"] == 0
    assert "stage_level" not in frozen


def test_the_pass_mark_is_the_adapters_own_threshold() -> None:
    assert RECORD["pass_mark"] == FRAME["pass_mark"] == 0.5
    adapter = (ROOT / "benchmarks" / "external" / "datascibench" / "adapter.py").read_text(
        encoding="utf-8"
    )
    assert "score >= 0.5" in adapter


def test_disclaimers_stay_in_the_record_and_the_basis_page_points_at_it() -> None:
    joined = " ".join(RECORD["not_claimed"]).lower()
    for phrase in (
        "no causality",
        "lower bound",
        "random sample",
        "publication_ready",
        "not comparable",
    ):
        assert phrase in joined, phrase
    assert RECORD["basis"].endswith("#s2--latency-and-failure-attribution")
    basis = BASIS_PAGE.read_text(encoding="utf-8")
    assert "## S2 — latency and failure attribution" in basis
    assert "docs/audit/attribution.json" in basis
    assert "scripts/measure_attribution.py" in basis
    assert "S2 has one reading of four" not in basis
    status = ADR.read_text(encoding="utf-8").splitlines()[2]
    # Not a count: the number of S2 readings changes every time one lands, and pinning it here
    # made this test fail on the next stage item rather than on a regression. What must stay true
    # is that the status line names this reading and still calls the stage in progress; the
    # arithmetic against the page's sections is checked in the page-consistency test.
    assert "latency/failure attribution" in status, status
    assert "S2 in progress" in status, status
