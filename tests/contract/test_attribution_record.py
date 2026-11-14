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
from dsa_evaluation.failure_codes import CODED_STAGES, FailureCode

ROOT = Path(__file__).resolve().parents[2]
FRAME_PATH = ROOT / "tests/fixtures/attribution/frame.json"
RECORD_PATH = ROOT / "docs/audit/attribution.json"
BASIS_PAGE = ROOT / "docs/measurement-basis.md"
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"
FRAME = json.loads(FRAME_PATH.read_text(encoding="utf-8"))
RECORD = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
#: The closed set a failure code must belong to. ADR-004 D2: a code is a location, never a
#: diagnosis, and a string outside this set is not a location the tree can point at.
VOCABULARY = {
    "stages": sorted(CODED_STAGES),
    "codes": sorted(member.value for member in FailureCode),
}
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
    assert RECORD["schema"] == "attribution-reading/v2"
    assert FRAME["schema"] == RECORD["frame_schema"] == "attribution-frame/v2"
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
        # ADR-004 D2: the record now carries an interval per stage. The key alone would not count;
        # ``_stages_recorded`` only returns a field whose value is a non-empty list.
        assert row["stage_keys"] == ["stage_timings"], row["task_id"]


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
    # ADR-004 D2 asks for a boundary on every task, not on some: the number is the denominator.
    assert expected["tasks_with_stage_boundaries"] == len(rows)
    assert expected["tasks_with_residual_ms"] == len(rows)


def test_every_failure_row_is_internally_consistent() -> None:
    rows = FRAME["failure_rows"]
    assert len(rows) == RECORD["failures"]["external_bundle"]["non_passing"]
    assert len({row["task_id"] for row in rows}) == len(rows)
    for row in rows:
        assert row["outcome"] in {"failed", "execution_error", "unsupported"}, row["task_id"]
        # Both members of the pair, and both from the closed vocabulary. One alone would let a
        # record say "evaluation" and never say what decided it.
        assert len(row["cause_keys"]) == 2, (row["task_id"], row["cause_keys"])
        labels = {entry.split(": ", 1)[0] for entry in row["cause_keys"]}
        assert labels == {"failure_stage", "failure_code"}, row["task_id"]
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
        "stage_level": sum(1 for row in rows if row["cause_keys"]),
        "unplaced": len(rows) - placed,
        "partial_credit": sum(
            1 for row in rows if row["score"] is not None and 0 < row["score"] < FRAME["pass_mark"]
        ),
        "free_text_errors": sum(1 for row in rows if row["has_error_text"]),
        # A row the reading counts separately: the graph refused the run and the evaluator scored it
        # above the mark anyway, so `status` and `outcome` disagree by design here.
        "failed_status_but_scored_passing": ext["failed_status_but_scored_passing"],
    }
    assert RECORD["failures"]["external_bundle"] == expected
    # ADR-004 D2's own predicate: every non-passing run carries a location, and the vocabulary it
    # was drawn from is listed in the reading rather than left in the code.
    assert expected["stage_level"] == len(rows)
    assert RECORD["failure_vocabulary"] == FRAME["failure_vocabulary"] == VOCABULARY
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
    # is that the status line names this reading; the arithmetic against the page's sections and
    # the stage's state word are checked in the page-consistency and exit-review tests.
    assert "latency/failure attribution" in status, status
    assert re.search(r"S2 (in progress|complete)", status), status


def test_the_page_quotes_the_aggregates_the_record_carries() -> None:
    """Every latency number the page states is built from the record, not remembered from a capture.

    This is not hypothetical: the page once quoted the *first* recording's median, mean, zero-duration
    count and window excursion next to a record that had been re-captured, and nothing failed because
    no test read the two side by side. Pinning the sentences to the fields makes a re-capture fail
    here rather than leaving prose that describes a frame the tree no longer holds.
    """
    latency = RECORD["latency"]
    share = latency["per_task_tool_share"]
    basis = re.sub(r"\s+", " ", BASIS_PAGE.read_text(encoding="utf-8"))
    for sentence in (
        f"{latency['tool_calls']} tool calls across {latency['tasks']} tasks",
        f"a median of {share['median']} and a mean of {share['mean']}",
        f"ranging from {share['min']} to {share['max']}",
        f"{latency['outside_window_ms_total']} ms outside",
        f"The {latency['zero_duration_calls']} calls whose `duration_ms` is zero",
    ):
        assert sentence in basis, sentence
    # The two counts are the ones a re-capture moves hardest, so they are compared as numbers rather
    # than only as substrings: a page that quotes a bigger zero count than the record has no such call.
    assert latency["zero_duration_calls"] <= latency["tool_calls"]
    assert latency["tasks_with_stage_boundaries"] == latency["tasks"]
    assert latency["tasks_with_residual_ms"] == latency["tasks"]
