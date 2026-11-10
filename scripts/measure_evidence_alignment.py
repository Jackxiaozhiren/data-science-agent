"""Recompute the S1 evidence-alignment reading from a pinned, version-controlled frame.

The original ``artifacts/reports/*/experiment.json`` files are gitignored and together weigh more
than the whole repository's documentation. Pinning them verbatim would make the reading depend on
artefacts a third party cannot see, so this script projects each report down to the fields the
four-hop walk in ``docs/measurement-basis.md`` actually reads, records the SHA-256 of each source
report as an anchor, and writes that projection to ``tests/fixtures/evidence-alignment/frame.json``.

Four rules are deliberate:

* **The frame is the measured object.** A clean checkout recomputes the reading from the frame alone;
  ``--capture`` only regenerates the frame where the original artefacts do exist.
* **Every path is a repository constant.** The CLI takes no path argument, so nothing caller-supplied
  reaches a file read or a file write. Capture reads ``artifacts/reports`` and writes the pinned
  frame; verify reads the pinned record. Neither is parameterised from the command line.
* **No exception handling.** A malformed frame or a broken hash is a fact to surface, not a reason to
  report a comfortable number. Raising is the intended behaviour.
* **Every recorded field is recomputable.** Observations that only exist on the capturing machine —
  whether an input file was still there, whether its hash matched — are deliberately absent from both
  the frame and the reading. The ledger records them as capture-time context instead.

The four hops, matching the definition verbatim: conclusion -> evidence node -> computation ->
computation input -> input data with a hash. A missing ID at any hop is an unaligned conclusion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRAME_PATH = ROOT / "tests/fixtures/evidence-alignment/frame.json"
RECORD_PATH = ROOT / "docs/audit/evidence-alignment.json"
REPORT_ROOT = ROOT / "artifacts/reports"
SCHEMA = "evidence-alignment-frame/v1"
STAGES = (
    "L1_evidence_node",
    "L2_computation",
    "L3_computation_input",
    "L4_data_hash",
)
CAPTURE_RULE = (
    "census of every artifacts/reports/*/experiment.json visible in the local working copy at "
    "capture time; sorted by run_id; no random draw and no exclusion by outcome"
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _dataset_fields(obj: dict[str, Any]) -> dict[str, Any]:
    """The two facts the fourth hop needs, and nothing that reaches the filesystem.

    An earlier draft followed ``dataset_path`` to the input file to record whether it still existed
    and whether its hash matched. That made the reading depend on local state a checkout cannot
    reproduce, and it turned report content into a filesystem path. Both the dependency and the
    finding go away by keeping only the recorded hash and the fact that a path was recorded.
    """
    return {
        "dataset_sha256": str(obj.get("dataset_sha256") or ""),
        "dataset_path_present": bool(obj.get("dataset_path")),
    }


def _project_tool_calls(obj: dict[str, Any]) -> list[dict[str, Any]]:
    calls = []
    for call in obj.get("tool_calls", []):
        value = call.get("input")
        is_object = isinstance(value, dict)
        calls.append(
            {
                "call_id": str(call.get("call_id") or ""),
                "input_is_object": is_object,
                "input_keys": sorted(str(k) for k in value) if is_object else [],
            }
        )
    return calls


def _project_evidence(obj: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"id": str(item.get("id") or ""), "source_id": str(item.get("source_id") or "")}
        for item in obj.get("evidence", [])
    ]


def _project_insights(obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(item.get("id") or ""),
            "evidence_ids": [str(x) for x in item.get("evidence_ids", [])],
        }
        for item in obj.get("insights", [])
    ]


def capture(report_root: Path | None = None) -> dict[str, Any]:
    """Project local reports into a deterministic, self-contained frame."""
    root = report_root or REPORT_ROOT
    reports: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/experiment.json")):
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        reports.append(
            {
                "run_id": str(obj.get("run_id") or path.parent.name),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                **_dataset_fields(obj),
                "tool_calls": _project_tool_calls(obj),
                "evidence": _project_evidence(obj),
                "insights": _project_insights(obj),
            }
        )
    return {
        "schema": SCHEMA,
        "source_root": "artifacts/reports",
        "capture_rule": CAPTURE_RULE,
        "reports": sorted(reports, key=lambda report: report["run_id"]),
    }


def _gap_stage(
    run: dict[str, Any],
    insight: dict[str, Any],
    calls: dict[str, Any],
    evidence: dict[str, Any],
) -> str | None:
    """Return the first hop that breaks, or None when all four resolve."""
    ids = insight["evidence_ids"]
    if not ids or any(x not in evidence for x in ids):
        return STAGES[0]
    if any(evidence[x]["source_id"] not in calls for x in ids):
        return STAGES[1]
    if any(
        not (
            calls[evidence[x]["source_id"]]["input_is_object"]
            and calls[evidence[x]["source_id"]]["input_keys"]
        )
        for x in ids
    ):
        return STAGES[2]
    if not (run["dataset_sha256"] and run["dataset_path_present"]):
        return STAGES[3]
    return None


def _count_passed_hops(stages: dict[str, int], gap: str | None) -> None:
    passed = STAGES if gap is None else STAGES[: STAGES.index(gap)]
    for name in passed:
        stages[name] += 1


def measure(frame: dict[str, Any]) -> dict[str, Any]:
    """Count conclusions whose four-hop walk has no gap, and where any gap appeared."""
    stages = dict.fromkeys(STAGES, 0)
    gaps: list[dict[str, str]] = []
    conclusions = 0
    for run in frame["reports"]:
        calls = {call["call_id"]: call for call in run["tool_calls"]}
        evidence = {item["id"]: item for item in run["evidence"]}
        for insight in run["insights"]:
            conclusions += 1
            gap = _gap_stage(run, insight, calls, evidence)
            _count_passed_hops(stages, gap)
            if gap is not None:
                gaps.append(
                    {"run_id": run["run_id"], "conclusion_id": insight["id"], "gap_at": gap}
                )
    reports = frame["reports"]
    return {
        "frame_schema": frame["schema"],
        "frame_runs": len(reports),
        "denominator": conclusions,
        "numerator": stages[STAGES[3]],
        "stages": stages,
        "gaps": gaps,
        "diagnostics": {
            "runs_without_conclusions": sum(1 for run in reports if not run["insights"]),
        },
    }


def verify() -> tuple[bool, dict[str, bool]]:
    """Compare the recorded reading with what the pinned frame yields today."""
    frame = read_json(FRAME_PATH)
    record = read_json(RECORD_PATH)
    result = measure(frame)
    checks = {
        "frame_sha256": file_sha256(FRAME_PATH) == record["frame_sha256"],
        "frame_schema": result["frame_schema"] == record["frame_schema"],
        "frame_runs": result["frame_runs"] == record["frame_runs"],
        "denominator": result["denominator"] == record["denominator"],
        "numerator": result["numerator"] == record["numerator"],
        "stages": result["stages"] == record["stages"],
        "gaps": result["gaps"] == record["gaps"],
        "diagnostics": result["diagnostics"] == record["diagnostics"],
        "source_sha256_manifest": hashlib.sha256(
            canonical_bytes([report["source_sha256"] for report in frame["reports"]])
        ).hexdigest()
        == record["source_sha256_manifest_sha256"],
    }
    return all(checks.values()), checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--capture", action="store_true", help="regenerate the pinned frame from artifacts/reports"
    )
    mode.add_argument(
        "--verify", action="store_true", help="compare the recorded reading with the pinned frame"
    )
    args = parser.parse_args(argv)

    if args.capture:
        paths = sorted(REPORT_ROOT.glob("*/experiment.json"))
        if not paths:
            print("capture refused: no reports under artifacts/reports", file=sys.stderr)
            return 2
        frame = capture()
        FRAME_PATH.write_text(
            json.dumps(frame, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {len(frame['reports'])} reports to {FRAME_PATH.relative_to(ROOT)}")
        return 0

    if args.verify:
        ok, checks = verify()
        for name, passed in checks.items():
            print(f"{'ok' if passed else 'mismatch'} {name}")
        return 0 if ok else 1

    print(json.dumps(measure(read_json(FRAME_PATH)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
