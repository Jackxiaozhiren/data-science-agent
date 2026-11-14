"""Recompute the S2 attribution reading from a pinned, version-controlled frame.

ADR-003 asks S2 for "deterministic-path latency and failure attribution". The question is not how
fast the path is: ``benchmarks/baseline/README.md`` has already shown that a stored mean latency is
not comparable with a fresh one on the same commit. The question is what a recorded run lets a reader
point at. Two facts are measured:

* **Latency.** ``raw_runs.json`` reports one ``elapsed_ms`` per task and one ``duration_ms`` per tool
  call. The sum of the latter is the only time that can be named to an execution unit; the rest of
  the clock has no stage boundary in the record. ``created_at`` / ``updated_at`` bound the window the
  run object itself covers, so time outside that window is separately visible.
* **Failure.** Two deterministic recordings ship in the tree. The frozen baseline has no failure to
  attribute (an empty denominator, recorded as not measured rather than as a perfect score). The
  external bundle records outcomes, artifact counts and one free-text error, but no stage or cause
  code.

The instrument follows the S1 evidence-alignment shape: the frame is the measured object, every path
is a repository constant, there is no exception handling (a malformed frame is a fact to surface),
and the CLI takes flags only. ``--capture`` regenerates the frame from a local 50-task run plus the
two committed recordings; ``--record`` builds the dated reading; ``--verify`` rebuilds the reading
from the frame and compares it field by field.

Capture and record emit JSON on stdout and the caller redirects it to the pinned path. Nothing read
from a file is ever passed back into a file-writing call in this module: content read from a JSON
file and then written to another file is exactly the "path traversal via file content" shape, and
keeping the write on the caller's side makes that impossible here rather than merely unsuspected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from dsa_evaluation.failure_codes import CODED_STAGES, FailureCode

ROOT = Path(__file__).resolve().parents[1]
RUN_RAW = ROOT / "artifacts" / "bench-attribution" / "raw_runs.json"
RUN_MANIFEST = ROOT / "artifacts" / "bench-attribution" / "run_manifest.json"
FROZEN_RESULTS = ROOT / "benchmarks" / "baseline" / "results.json"
EXTERNAL_RUNS = ROOT / "benchmarks" / "external" / "datascibench" / "results" / "raw_runs.json"
FRAME_PATH = ROOT / "tests" / "fixtures" / "attribution" / "frame.json"
RECORD_PATH = ROOT / "docs" / "audit" / "attribution.json"
#: The first pass stays where it was recorded and gains a pointer, so a reader can tell a
#: moved count from a moved question without reconciling two addresses.
SUPERSEDES = "docs/audit/attribution-first.json"

RUN_REL = "artifacts/bench-attribution/raw_runs.json"
MANIFEST_REL = "artifacts/bench-attribution/run_manifest.json"
FROZEN_REL = "benchmarks/baseline/results.json"
EXTERNAL_REL = "benchmarks/external/datascibench/results/raw_runs.json"

SCHEMA = "attribution-frame/v2"
RECORD_SCHEMA = "attribution-reading/v2"
#: The commit the recorded run was taken on, not the commit this file happens to be read at: the
#: procedure below checks that commit out, runs the benchmark there and derives the reading from the
#: frame it produced. Re-deriving the record on a later tree does not move it, because the numbers
#: describe that run. `--verify` holds the two together: `reviewed_commit == run_manifest_commit`.
REVIEWED_COMMIT = "5cbee4de0906"
#: The pass mark is the external adapter's own threshold, not one chosen for this reading.
PASS_MARK = 0.5
#: Whole-millisecond timestamps are rounded to 1 ms; ten times that is a resolution band, not a test.
WINDOW_RESOLUTION_MS = 10
STAGE_KEYS = ("stage_timings", "phase_timings", "stage_ms", "spans", "stages")
CAPTURE_RULE = (
    "one local 50-task deterministic run plus a census of both deterministic recordings already "
    "committed to the tree; no random draw, no exclusion by outcome, no cross-run averaging"
)
NOT_CLAIMED = [
    "No causality: a zero-evidence or OOM-killed run is placed at the artifact level from recorded "
    + "counts, not diagnosed as to why it failed.",
    "A failure code names a place in the tree that decided the outcome, never a reason for it: "
    + "`score_below_threshold` says the evaluator scored the run under its own threshold and says "
    + "nothing about why the score was low.",
    "Absolute milliseconds are not comparable with the frozen baseline or with another machine: "
    + "the baseline README records three different means for the same commit minutes apart.",
    "The tool-time share is a lower bound, not a measurement of tool cost: duration_ms is an "
    + "integer millisecond, so a sub-millisecond call contributes zero.",
    "Neither recording is a random sample. Both are convenience censuses of what this tree ships.",
    "Outcome is the evaluator's verdict on artifacts, not the run's status: a run the graph refused "
    + "can still score above the mark. The two columns are counted separately, never added together.",
    "Nothing here is a penetration result, a latency target, an S2 exit, or a statement about "
    + "publication_ready, which keeps its own gate.",
]

PROCEDURE = [
    "Check out the reviewed commit into a clean tree and export its package src roots on PYTHONPATH.",
    "Run `dsa --limit 50 --out <repo>/artifacts/bench-attribution`; `--out` is a top-level flag, "
    + "and the manifest must report llm_mode=stub and call_count=0.",
    "Run `python benchmarks/external/datascibench/run_eval.py` to re-record the external bundle; it "
    + "is the deterministic local lane and reads the gitignored `.workspace/` in place.",
    "Run `python scripts/measure_attribution.py --capture > tests/fixtures/attribution/frame.json` "
    + "in the repository root to project the run and the two committed recordings.",
    "Run `python scripts/measure_attribution.py --record > docs/audit/attribution.json` to build "
    + "the dated reading, then `--verify` to rebuild it from the frame alone. Both commands emit "
    + "JSON on stdout; the module never writes a file it has read.",
]


def read_json(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(path: Path, relative: str, committed: bool) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": relative,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "committed": committed,
    }


def _window_ms(run: dict[str, Any]) -> int:
    start = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
    return round((end - start) / timedelta(milliseconds=1))


def _stages_recorded(run: dict[str, Any]) -> list[str]:
    """Stage fields that carry at least one interval.

    A key whose value is an empty list records that this run has no stage boundary; counting the key
    alone would let a field exist and say nothing, which is the failure mode this reading exists to
    catch rather than to reproduce.
    """
    return [name for name in STAGE_KEYS if isinstance(run.get(name), list) and run[name]]


def _codes_present(row: dict[str, Any], vocabulary: dict[str, list[str]]) -> list[str]:
    """Failure fields whose value is a member of the closed vocabulary.

    Presence is not enough and neither is truthiness: a null, or a string nobody enumerated, records
    no location. Only a value the vocabulary owns counts as having placed the failure.
    """
    found: list[str] = []
    stage = row.get("failure_stage")
    if isinstance(stage, str) and stage in vocabulary["stages"]:
        found.append(f"failure_stage: {stage}")
    code = row.get("failure_code")
    if isinstance(code, str) and code in vocabulary["codes"]:
        found.append(f"failure_code: {code}")
    return found


def capture() -> dict[str, Any]:
    """Project the local run and the two committed recordings into the pinned frame."""
    raw_runs = read_json(RUN_RAW)
    manifest = read_json(RUN_MANIFEST)
    frozen = read_json(FROZEN_RESULTS)
    external = read_json(EXTERNAL_RUNS)
    assert isinstance(raw_runs, list)
    assert isinstance(manifest, dict)
    assert isinstance(frozen, dict)
    assert isinstance(external, dict)
    execution = manifest["execution"]

    latency_rows: list[dict[str, Any]] = []
    for row in raw_runs:
        run = row["run_result"]
        calls = run.get("tool_calls") or []
        elapsed = row["elapsed_ms"]
        window = _window_ms(run)
        latency_rows.append(
            {
                "task_id": row["task_id"],
                "elapsed_ms": elapsed,
                "window_ms": window,
                "outside_window_ms": max(0, elapsed - window),
                "tool_ms": sum(call.get("duration_ms") or 0 for call in calls),
                "n_tool_calls": len(calls),
                "zero_duration_calls": sum(1 for call in calls if not call.get("duration_ms")),
                "tool_failures": sum(1 for call in calls if call.get("status") != "ok"),
                "stage_keys": _stages_recorded(run),
            }
        )

    vocabulary = {
        "stages": sorted(CODED_STAGES),
        "codes": sorted(member.value for member in FailureCode),
    }
    frozen_rows = frozen["results"]
    external_rows = external["runs"]
    failure_rows: list[dict[str, Any]] = []
    for row in external_rows:
        if row["outcome"] == "passed":
            continue
        failure_rows.append(
            {
                "task_id": row["task_id"],
                "status": row["status"],
                "outcome": row["outcome"],
                "score": row["score"],
                "n_tool_calls": row["n_tool_calls"] or 0,
                "n_evidence": row["n_evidence"] or 0,
                "report_chars": row["report_chars"] or 0,
                "has_error_text": bool(row["error"]),
                "cause_keys": _codes_present(row, vocabulary),
            }
        )

    return {
        "schema": SCHEMA,
        "capture_rule": CAPTURE_RULE,
        "sources": {
            "deterministic_run": _source(RUN_RAW, RUN_REL, False),
            "run_manifest": _source(RUN_MANIFEST, MANIFEST_REL, False),
            "frozen_baseline": _source(FROZEN_RESULTS, FROZEN_REL, True),
            "external_bundle": _source(EXTERNAL_RUNS, EXTERNAL_REL, True),
        },
        "environment": raw_runs[0]["environment"],
        "run_manifest_commit": execution["git_commit"],
        "run_manifest_llm_mode": execution["llm_mode"],
        "run_manifest_call_count": execution["call_count"],
        "frozen_baseline": {
            "n_tasks": len(frozen_rows),
            "n_non_passing": sum(
                1 for row in frozen_rows if not row["metrics"].get("task_success")
            ),
            "stage_keys": _stages_recorded(frozen_rows[0]),
        },
        "external_bundle": {
            "n_runs": len(external_rows),
            "n_non_passing": len(failure_rows),
            "per_task_latency_present": sum(
                1 for row in external_rows if row["latency_s"] is not None
            ),
            "wall_s": external["wall_s"],
            "stage_keys": _stages_recorded(external_rows[0]),
            "runs_with_stage_count": sum(1 for row in external_rows if row.get("n_stages")),
            # A run the graph refused can still be scored above the mark, because the evaluator reads
            # artifacts and not the run's status. Counting it without saying so would let a reader
            # add the two columns and get a number that is neither.
            "failed_status_but_scored_passing": sum(
                1
                for row in external_rows
                if row["status"] != "COMPLETED" and row["outcome"] == "passed"
            ),
        },
        "failure_vocabulary": vocabulary,
        "pass_mark": PASS_MARK,
        "pass_mark_source": "benchmarks/external/datascibench/adapter.py (score >= 0.5)",
        "window_resolution_ms": WINDOW_RESOLUTION_MS,
        "latency_rows": latency_rows,
        "failure_rows": failure_rows,
    }


def _artifact_signal(row: dict[str, Any]) -> str | None:
    """Place a failure at the artifact level from counts alone; never infer a cause."""
    if row["status"] != "COMPLETED":
        return "run_did_not_complete"
    if row["report_chars"] == 0:
        return "no_report"
    if row["n_tool_calls"] == 0:
        return "no_tool_calls"
    if row["n_evidence"] == 0:
        return "no_evidence"
    return None


def measure(frame: dict[str, Any]) -> dict[str, Any]:
    """Arithmetic over the frame. No filesystem access and no input beyond the pinned projection."""
    latency = frame["latency_rows"]
    shares = [row["tool_ms"] / row["elapsed_ms"] for row in latency]
    failures = frame["failure_rows"]
    signals = [_artifact_signal(row) for row in failures]
    signal_counts: dict[str, int] = {}
    for signal in signals:
        if signal is not None:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
    artifact_level = sum(signal_counts.values())
    frozen = frame["frozen_baseline"]
    external = frame["external_bundle"]

    return {
        "latency": {
            "tasks": len(latency),
            "tool_calls": sum(row["n_tool_calls"] for row in latency),
            "tool_failures": sum(row["tool_failures"] for row in latency),
            "zero_duration_calls": sum(row["zero_duration_calls"] for row in latency),
            "elapsed_ms_total": sum(row["elapsed_ms"] for row in latency),
            "tool_ms_total": sum(row["tool_ms"] for row in latency),
            "outside_window_ms_total": sum(row["outside_window_ms"] for row in latency),
            "per_task_tool_share": {
                "min": round(min(shares), 4),
                "median": round(statistics.median(shares), 4),
                "mean": round(statistics.mean(shares), 4),
                "max": round(max(shares), 4),
            },
            "tasks_with_residual_ms": sum(
                1 for row in latency if row["elapsed_ms"] > row["tool_ms"]
            ),
            "tasks_over_tool_budget": sum(
                1 for row in latency if row["tool_ms"] > row["elapsed_ms"]
            ),
            "tasks_with_stage_boundaries": sum(1 for row in latency if row["stage_keys"]),
            "tasks_outside_run_window": sum(
                1 for row in latency if row["outside_window_ms"] > frame["window_resolution_ms"]
            ),
        },
        "failures": {
            "frozen_baseline": {
                "tasks": frozen["n_tasks"],
                "non_passing": frozen["n_non_passing"],
                "status": "measured" if frozen["n_non_passing"] else "not_measured",
                "reason": (
                    "empty denominator: no failure in this recording can be attributed"
                    if not frozen["n_non_passing"]
                    else "failures present"
                ),
            },
            "external_bundle": {
                "n_runs": external["n_runs"],
                "non_passing": len(failures),
                "per_task_latency_present": external["per_task_latency_present"],
                "wall_s": external["wall_s"],
                "outcome_level": len(failures),
                "artifact_level": artifact_level,
                "artifact_signals": dict(sorted(signal_counts.items())),
                "stage_level": sum(1 for row in failures if row["cause_keys"]),
                "unplaced": len(failures) - artifact_level,
                "partial_credit": sum(
                    1
                    for row in failures
                    if row["score"] is not None and 0 < row["score"] < frame["pass_mark"]
                ),
                "free_text_errors": sum(1 for row in failures if row["has_error_text"]),
                "failed_status_but_scored_passing": external["failed_status_but_scored_passing"],
            },
        },
        # Listed here rather than only in the adapter, because a reader of the record has to be able
        # to see which values counted as a location without opening the code that wrote them.
        "failure_vocabulary": frame["failure_vocabulary"],
    }


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build(frame: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    """The dated reading: metadata plus the whole of ``measure`` over the pinned frame."""
    reading = {
        "schema": RECORD_SCHEMA,
        "recorded_at": recorded_at,
        "reviewed_commit": REVIEWED_COMMIT,
        "question": (
            "in a deterministic run, what fraction of the clock and which of the failures can be "
            "pointed at a named part of the record?"
        ),
        "basis": "docs/measurement-basis.md#s2--latency-and-failure-attribution",
        "supersedes": SUPERSEDES,
        "frame_path": "tests/fixtures/attribution/frame.json",
        "frame_schema": frame["schema"],
        "frame_sha256": file_sha256(FRAME_PATH),
        "capture_rule": frame["capture_rule"],
        "run_manifest_commit": frame["run_manifest_commit"],
        "run_manifest_llm_mode": frame["run_manifest_llm_mode"],
        "run_manifest_call_count": frame["run_manifest_call_count"],
        "environment": frame["environment"],
        "pass_mark": frame["pass_mark"],
        "pass_mark_source": frame["pass_mark_source"],
        "window_resolution_ms": frame["window_resolution_ms"],
        "procedure": PROCEDURE,
        "not_claimed": NOT_CLAIMED,
        #: What changed between the first reading and this one, stated in the record rather than
        #: left to a diff. Two of these move the ruler, one moves the denominator, and a reader who
        #: adds them up as "the number improved" would be reading the wrong change.
        "basis_change": [
            "A cause field used to count when its key was present. This reading counts a value that "
            + "belongs to the closed vocabulary, so a null, an empty string or an invented name "
            + "records no location and is not counted.",
            "The latency rows now carry the run's own stage intervals (ADR-004 D2). The first "
            + "reading had no such field to find, which is why it recorded 0 of 50.",
            "The external bundle was re-recorded on the reviewed commit: 38 supported tasks and 33 "
            + "non-passing runs, where the first recording held 45 and 40. The denominator moved with "
            + "the recording, not with the code, and this line is the only place that says so.",
        ],
    }
    reading.update(measure(frame))
    return reading


def verify() -> tuple[bool, dict[str, bool]]:
    """Rebuild the reading from the frame and compare it field by field with the dated record."""
    frame = read_json(FRAME_PATH)
    record = read_json(RECORD_PATH)
    assert isinstance(frame, dict)
    assert isinstance(record, dict)
    expected = build(frame, str(record["recorded_at"]))
    checks = {key: record.get(key) == value for key, value in expected.items()}
    checks["no_extra_fields"] = set(record) == set(expected)
    return all(checks.values()), checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--capture", action="store_true", help="regenerate the pinned frame from the local run"
    )
    mode.add_argument(
        "--record", action="store_true", help="write the dated reading from the pinned frame"
    )
    mode.add_argument(
        "--verify", action="store_true", help="compare the reading with the pinned frame"
    )
    args = parser.parse_args(argv)

    if args.capture:
        if not RUN_RAW.is_file():
            print(f"capture refused: {RUN_REL} is absent", file=sys.stderr)
            return 2
        sys.stdout.write(_render(capture()) + "\n")
        return 0

    if args.record:
        frame = read_json(FRAME_PATH)
        assert isinstance(frame, dict)
        sys.stdout.write(_render(build(frame, _timestamp())) + "\n")
        return 0

    if args.verify:
        ok, checks = verify()
        for name, passed in sorted(checks.items()):
            print(f"{'ok' if passed else 'mismatch'} {name}")
        return 0 if ok else 1

    frame = read_json(FRAME_PATH)
    assert isinstance(frame, dict)
    print(_render(measure(frame)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
