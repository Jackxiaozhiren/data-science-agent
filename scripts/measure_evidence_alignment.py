"""Recompute the S1 evidence-alignment reading from a pinned, version-controlled frame.

The original ``artifacts/reports/*/experiment.json`` files are gitignored and together weigh more
than the whole repository's documentation. Pinning them verbatim would make the reading depend on
artefacts a third party cannot see, so this script projects each report down to the fields the
four-hop walk in ``docs/measurement-basis.md`` actually reads, records the SHA-256 of each source
report as an anchor, and writes that projection to ``tests/fixtures/evidence-alignment/frame.json``.

Three rules are deliberate:

* **The frame is the measured object.** A clean checkout recomputes the reading from the frame alone;
  ``--capture`` is only for regenerating the frame where the original artefacts do exist.
* **No exception handling.** A malformed frame or a broken hash is a fact to surface, not a reason to
  report a comfortable number. Raising is the intended behaviour.
* **Capture-time observations are labelled.** Whether an input file still existed, and whether its
  SHA-256 matched, cannot be re-derived from a checkout. Those booleans live in diagnostics and never
  enter the numerator.

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


def capture(report_root: Path) -> dict[str, Any]:
    """Project local reports into a deterministic, self-contained frame."""
    reports = sorted(report_root.glob("*/experiment.json"))
    runs: list[dict[str, Any]] = []
    for path in reports:
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        data_path = str(obj.get("dataset_path") or "")
        declared_hash = str(obj.get("dataset_sha256") or "")
        data_file = Path(data_path) if data_path else None
        present = bool(data_file and data_file.is_file())
        matches = bool(
            present
            and data_file
            and hashlib.sha256(data_file.read_bytes()).hexdigest() == declared_hash
        )

        calls: list[dict[str, Any]] = []
        for call in obj.get("tool_calls", []):
            value = call.get("input")
            calls.append(
                {
                    "call_id": str(call.get("call_id") or ""),
                    "input_is_object": isinstance(value, dict),
                    "input_keys": sorted(str(k) for k in value) if isinstance(value, dict) else [],
                }
            )
        runs.append(
            {
                "run_id": str(obj.get("run_id") or path.parent.name),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "dataset_sha256": declared_hash,
                "dataset_path_present": bool(data_path),
                "dataset_file_present_at_capture": present,
                "dataset_hash_matches_at_capture": matches,
                "tool_calls": calls,
                "evidence": [
                    {
                        "id": str(item.get("id") or ""),
                        "source_id": str(item.get("source_id") or ""),
                    }
                    for item in obj.get("evidence", [])
                ],
                "insights": [
                    {
                        "id": str(item.get("id") or ""),
                        "evidence_ids": [str(x) for x in item.get("evidence_ids", [])],
                    }
                    for item in obj.get("insights", [])
                ],
            }
        )
    return {
        "schema": SCHEMA,
        "source_root": "artifacts/reports",
        "capture_rule": CAPTURE_RULE,
        "runs": sorted(runs, key=lambda run: run["run_id"]),
    }


def measure(frame: dict[str, Any]) -> dict[str, Any]:
    """Count conclusions whose four-hop walk has no gap, and where any gap appeared."""
    stages = dict.fromkeys(STAGES, 0)
    gaps: list[dict[str, str]] = []
    conclusions = 0
    for run in frame["runs"]:
        calls = {call["call_id"]: call for call in run["tool_calls"]}
        evidence = {item["id"]: item for item in run["evidence"]}
        for insight in run["insights"]:
            conclusions += 1
            ids = insight["evidence_ids"]
            label = {"run_id": run["run_id"], "conclusion_id": insight["id"]}
            if not ids or not all(x in evidence for x in ids):
                gaps.append({**label, "gap_at": STAGES[0]})
                continue
            stages[STAGES[0]] += 1

            if not all(evidence[x]["source_id"] in calls for x in ids):
                gaps.append({**label, "gap_at": STAGES[1]})
                continue
            stages[STAGES[1]] += 1

            if not all(
                calls[evidence[x]["source_id"]]["input_is_object"]
                and calls[evidence[x]["source_id"]]["input_keys"]
                for x in ids
            ):
                gaps.append({**label, "gap_at": STAGES[2]})
                continue
            stages[STAGES[2]] += 1

            if not (run["dataset_sha256"] and run["dataset_path_present"]):
                gaps.append({**label, "gap_at": STAGES[3]})
                continue
            stages[STAGES[3]] += 1

    return {
        "frame_schema": frame["schema"],
        "frame_runs": len(frame["runs"]),
        "denominator": conclusions,
        "numerator": stages[STAGES[3]],
        "stages": stages,
        "gaps": gaps,
        "diagnostics": {
            "runs_without_conclusions": sum(1 for run in frame["runs"] if not run["insights"]),
            "dataset_files_present_at_capture": sum(
                1 for run in frame["runs"] if run["dataset_file_present_at_capture"]
            ),
            "dataset_hashes_recomputable_at_capture": sum(
                1 for run in frame["runs"] if run["dataset_hash_matches_at_capture"]
            ),
        },
    }


def verify(record_path: Path) -> tuple[bool, dict[str, bool]]:
    """Compare a recorded reading with what the pinned frame yields today."""
    frame = read_json(FRAME_PATH)
    record = read_json(record_path)
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
            canonical_bytes([run["source_sha256"] for run in frame["runs"]])
        ).hexdigest()
        == record["source_sha256_manifest_sha256"],
    }
    return all(checks.values()), checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", metavar="DIR", help="project reports under DIR into a frame")
    parser.add_argument("--out", metavar="PATH", help="write the captured frame to PATH")
    parser.add_argument("--verify", metavar="RECORD", help="compare RECORD with the pinned frame")
    args = parser.parse_args(argv)

    if args.capture:
        reports = sorted(Path(args.capture).glob("*/experiment.json"))
        if not reports:
            print("capture refused: no reports found", file=sys.stderr)
            return 2
        frame = capture(Path(args.capture))
        body = json.dumps(frame, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.out:
            Path(args.out).write_text(body, encoding="utf-8")
            print(f"wrote {len(frame['runs'])} runs to {args.out}")
        else:
            print(body, end="")
        return 0

    if args.verify:
        ok, checks = verify(Path(args.verify))
        for name, passed in checks.items():
            print(f"{'ok' if passed else 'mismatch'} {name}")
        return 0 if ok else 1

    print(json.dumps(measure(read_json(FRAME_PATH)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
