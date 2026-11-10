"""Compare a clean-environment re-run against the frozen baseline recording, layer by layer.

Two repository-relative files are read, both named here as constants:

* ``benchmarks/baseline/results.json`` — the recording frozen at ``4259e8f101ed``.
* ``artifacts/rerun/results.json`` — what a re-run writes. It is produced by

      uv sync --frozen --no-dev
      uv run dsa --limit 50 --out artifacts/rerun

  from a clean checkout. ``artifacts/`` is git-ignored on purpose: the point of this metric is
  that the fresh side is *produced*, never shipped. A tool that accepted a path argument for it
  would also invite a comparison against a file someone else chose, which is the opposite of the
  question being asked, so there is no such argument.

What is compared, and what is deliberately not:

* Per-task verdicts — ``task_success``, ``statistical_accuracy``, ``sql_accuracy``,
  ``code_execution_success``, ``evidence_coverage``, ``unsupported_claim`` — and the per-task
  ``error`` field. These are the substance of the recording.
* The aggregate block, plus the per-category table. One key in that block, ``mean_latency_ms``, is
  the average of the per-task latency already excluded, so it is excluded with it and reported
  under ``latency`` instead. Excluding it per task and then comparing it in the aggregate was the
  first draft's contradiction: it failed every honest re-run on slower hardware.
* ``latency_ms`` is *excluded* from equality and reported as its own summary. Wall-clock time is
  a property of the machine that ran it, not of the analysis; folding it into the verdict would
  make every honest re-run look like a mismatch.
* ``execution.git_commit`` is *expected* to differ. The recording names the commit it was frozen
  at; a re-run at another commit names that one. Everything else in ``execution`` must agree, and
  a difference there is a mismatch rather than a note.

Exit codes follow the same convention as the served-artifact probe: ``0`` every layer agrees,
``1`` at least one layer disagrees, ``2`` the fresh side is absent or unreadable, so nothing was
measured.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

RECORDING = Path("benchmarks/baseline/results.json")
FRESH = Path("artifacts/rerun/results.json")
RECORD = Path("docs/audit/independent-rerun.json")

VERDICT_OK = "ok"
VERDICT_MISMATCH = "mismatch"
VERDICT_UNMEASURED = "unmeasured"

TASK_FIELDS = (
    "task_success",
    "statistical_accuracy",
    "sql_accuracy",
    "code_execution_success",
    "evidence_coverage",
    "unsupported_claim",
)

EXECUTION_FIELDS = (
    "llm_mode",
    "provider",
    "model",
    "fallback",
    "evaluation_variant",
    "evidence_critic_enabled",
    "evidence_critic_setting",
    "call_count",
)

#: Aggregate keys excluded from equality because they measure the machine, not the analysis.
AGGREGATE_EXCLUDED = ("mean_latency_ms",)


def load(path: Path) -> dict[str, Any] | None:
    """Read a JSON object, or ``None`` when the file is absent or unreadable."""
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _task_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("task_id")): row for row in payload.get("results", [])}


def _task_differences(
    recording: dict[str, Any], fresh: dict[str, Any]
) -> tuple[list[str], dict[str, list[str]]]:
    """Return (roster differences, per-field lists of tasks that disagree)."""
    left, right = _task_index(recording), _task_index(fresh)
    missing = [f"only_in_recording:{key}" for key in sorted(set(left) - set(right))]
    missing += [f"only_in_fresh:{key}" for key in sorted(set(right) - set(left))]
    disagreements: dict[str, list[str]] = {field: [] for field in (*TASK_FIELDS, "error")}
    for task_id in sorted(set(left) & set(right)):
        first, second = left[task_id], right[task_id]
        metrics_first = first.get("metrics") or {}
        metrics_second = second.get("metrics") or {}
        for field in TASK_FIELDS:
            if metrics_first.get(field) != metrics_second.get(field):
                disagreements[field].append(task_id)
        if (first.get("error") or None) != (second.get("error") or None):
            disagreements["error"].append(task_id)
    return missing, {key: value for key, value in disagreements.items() if value}


def _aggregate_differences(recording: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    left = recording.get("aggregate") or {}
    right = fresh.get("aggregate") or {}
    excluded = {"by_category", *AGGREGATE_EXCLUDED}
    differing = sorted(
        key
        for key in set(left) | set(right)
        if key not in excluded and left.get(key) != right.get(key)
    )
    by_category_differing = sorted(
        name
        for name in set(left.get("by_category") or {}) | set(right.get("by_category") or {})
        if (left.get("by_category") or {}).get(name) != (right.get("by_category") or {}).get(name)
    )
    return {
        "n_equal": left.get("n") == right.get("n"),
        "differing_keys": differing,
        "by_category_differing": by_category_differing,
        "excluded_keys": sorted(excluded - {"by_category"}),
        "recording": {key: left.get(key) for key in sorted(left) if key != "by_category"},
        "fresh": {key: right.get(key) for key in sorted(right) if key != "by_category"},
    }


def _execution_differences(recording: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    left = recording.get("execution") or {}
    right = fresh.get("execution") or {}
    return {
        "differing_keys": [
            field for field in EXECUTION_FIELDS if left.get(field) != right.get(field)
        ],
        "recording": {field: left.get(field) for field in EXECUTION_FIELDS},
        "fresh": {field: right.get(field) for field in EXECUTION_FIELDS},
        "recording_commit": left.get("git_commit"),
        "fresh_commit": right.get("git_commit"),
        "git_commit_compared": False,
    }


def _latency(fresh: dict[str, Any]) -> dict[str, Any]:
    values = [
        (row.get("metrics") or {}).get("latency_ms")
        for row in fresh.get("results", [])
        if isinstance((row.get("metrics") or {}).get("latency_ms"), (int, float))
    ]
    return {
        "samples": len(values),
        "tasks": len(fresh.get("results", [])),
        "mean_ms": round(sum(values) / len(values), 1) if values else None,
        "max_ms": max(values) if values else None,
        "excluded_from_equality": True,
        "reason": (
            "Wall-clock time is a property of the machine and the load on it, not of the analysis. "
            "It is reported here so a reader can see the run happened, and kept out of the verdict "
            "so that an honest re-run on slower hardware still reads as reproducing."
        ),
    }


def compare_payloads(recording: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Compare two result payloads. Pure: no filesystem access, so a test can feed it anything."""
    roster, task_disagreements = _task_differences(recording, fresh)
    aggregate = _aggregate_differences(recording, fresh)
    execution = _execution_differences(recording, fresh)
    layers = {
        "task_roster": VERDICT_OK if not roster else VERDICT_MISMATCH,
        "task_verdicts": VERDICT_OK if not task_disagreements else VERDICT_MISMATCH,
        "aggregate": VERDICT_OK
        if aggregate["n_equal"]
        and not aggregate["differing_keys"]
        and not aggregate["by_category_differing"]
        else VERDICT_MISMATCH,
        "execution": VERDICT_OK if not execution["differing_keys"] else VERDICT_MISMATCH,
    }
    return {
        "verdict": VERDICT_OK
        if all(value == VERDICT_OK for value in layers.values())
        else VERDICT_MISMATCH,
        "layers": layers,
        "tasks_in_recording": len(recording.get("results", [])),
        "tasks_in_fresh": len(fresh.get("results", [])),
        "roster_differences": roster,
        "task_disagreements": task_disagreements,
        "task_field_counts": {
            field: len(task_disagreements.get(field, [])) for field in TASK_FIELDS
        },
        "aggregate": aggregate,
        "execution": execution,
        "latency": _latency(fresh),
    }


def compare() -> dict[str, Any]:
    """Compare the committed recording with the re-run on disk, or say why that cannot be done."""
    recording, fresh = load(RECORDING), load(FRESH)
    if recording is None:
        return {"verdict": VERDICT_UNMEASURED, "reason": f"{RECORDING} is not readable"}
    if fresh is None:
        return {
            "verdict": VERDICT_UNMEASURED,
            "reason": (
                f"{FRESH} is absent. Run the benchmark from a clean checkout first: "
                "`uv sync --frozen --no-dev && uv run dsa --limit 50 --out artifacts/rerun`."
            ),
        }
    result = compare_payloads(recording, fresh)
    result["recording_sha256"] = hashlib.sha256(RECORDING.read_bytes()).hexdigest()
    result["fresh_sha256"] = hashlib.sha256(FRESH.read_bytes()).hexdigest()
    return result


def verify_checks(record_path: Path = RECORD) -> tuple[bool, dict[str, bool]]:
    """Compare the committed reading against a fresh computation, field by field."""
    record = load(record_path)
    result = compare()
    if record is None or result["verdict"] == VERDICT_UNMEASURED:
        return False, {"record_readable": record is not None, "fresh_side_present": False}
    claimed = record.get("comparison") or {}
    checks = {
        "record_readable": True,
        "fresh_side_present": True,
        "verdict": claimed.get("verdict") == result["verdict"],
        "layers": claimed.get("layers") == result["layers"],
        "task_field_counts": claimed.get("task_field_counts") == result["task_field_counts"],
        "task_disagreements": claimed.get("task_disagreements") == result["task_disagreements"],
        "roster_differences": claimed.get("roster_differences") == result["roster_differences"],
        "aggregate_differing_keys": (claimed.get("aggregate") or {}).get("differing_keys")
        == result["aggregate"]["differing_keys"],
        "execution_differing_keys": (claimed.get("execution") or {}).get("differing_keys")
        == result["execution"]["differing_keys"],
        # The recording's digest is an invariant: it fails if the frozen side is edited. The fresh
        # side's digest is *not* checked, because every re-run writes its own latency measurements
        # into that file, so a reader on another machine would fail a check that proves nothing.
        "recording_sha256": claimed.get("recording_sha256") == result["recording_sha256"],
    }
    return all(checks.values()), checks


def verify(record_path: Path = RECORD) -> int:
    ok, checks = verify_checks(record_path)
    for name in sorted(checks):
        print(("ok    " if checks[name] else "FAIL  ") + name)
    if not ok:
        print("mismatch the reading does not match a fresh computation")
        return 1
    print("ok     independent re-run agrees with the recorded reading")
    return 0


def main(argv: list[str]) -> int:
    if "--verify" in argv[1:]:
        return verify()
    result = compare()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {VERDICT_OK: 0, VERDICT_MISMATCH: 1, VERDICT_UNMEASURED: 2}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main(sys.argv))
