"""Where a content hash survives a run artifact's life -- ADR-003 S2, third item.

ADR-003's persistence decision replaces "data survives a restart" with "artifacts stay parseable
across lifecycle events", and its chosen alternative describes a bundle that carries "manifest,
environment, pinned dependencies, ordered execution trace and artifact hashes". This instrument asks
the narrow half of that: at each event an artifact passes through, does the record carry a digest of
it, and does any shipped code parse it and fail loudly if it cannot?

Six events, in the order an artifact meets them: the export tool writes it, the save tool writes it,
the run record lists it, the bundle exports it, the plain report export renders it, and a consumer
reads it back. For each one the record states whether a digest is recorded, whether a parse decides
readability, and whether that answer was obtained by running the code (``ran``) or by reading it
(``read``) -- a static claim and an executed one are never added together.

Not a claim that a hash would be checked by anyone, that the bundle is tamper-evident, or that absent
classes are broken. Three artifact classes have no committed export in this tree and are recorded
``not_measured`` rather than zero.

Every path is a repository constant and the CLI takes flags only; ``--record`` and ``--verify`` write
JSON to stdout and the caller redirects it, so this module has no file-content-to-file-write edge.
"""

from __future__ import annotations

import ast
import asyncio
import csv
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "export-lifecycle/v1"
#: The tree this reading describes. Measured against the merge commit of the previous section.
REVIEWED_COMMIT = "aea6ef17d647"

EXPORT_TOOL = ROOT / "packages/tools/src/dsa_tools/tools/export_artifact.py"
SAVE_TOOL = ROOT / "packages/tools/src/dsa_tools/tools/save_artifact.py"
BUNDLE_ROUTE = ROOT / "src/data_science_agent/_vendor/dsa_api/routers/bundles.py"
REPORT_EXPORT = ROOT / "packages/agent/src/dsa_agent/report_export.py"
CASE_STUDIES = ROOT / "case-studies"
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"

RECORD_PATH = ROOT / "docs/audit/export-lifecycle.json"

#: The words the ADR uses for the bundle's contents; the divergence check quotes them back to it.
ADR_CLAIM = (
    "manifest, environment, pinned dependencies, ordered execution trace and artifact hashes"
)

#: A 64-hex token, chosen so the strip rule has something to remove.
SAMPLE_DIGEST = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

HASH_FIELD = re.compile(r"sha|hash|digest", re.IGNORECASE)


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _export_artifact_event() -> dict[str, Any]:
    """Run the export tool, then compare the digest it returns with the bytes that landed."""
    from dsa_tools.tools.export_artifact import ExportArtifactInput, ExportArtifactTool

    workspace = tempfile.mkdtemp(prefix="dsa-export-lifecycle-")
    payload = {"columns": ["region", "units"], "rows": [["north", 3], ["south", 5]]}
    result = asyncio.run(
        ExportArtifactTool().execute(
            ExportArtifactInput(
                source=payload,
                filename="predictions.csv",
                format="csv",
                workspace=workspace,
            )
        )
    )
    written = Path(result.path)
    recomputed = hashlib.sha256(written.read_bytes()).hexdigest()
    rows = list(csv.reader(io.StringIO(written.read_text(encoding="utf-8"))))
    return {
        "id": "write:export_artifact",
        "surface": "packages/tools/src/dsa_tools/tools/export_artifact.py",
        "integrity_hash": "recorded",
        "parse_check": "absent",
        "evidence": "ran",
        "detail": (
            f"returns sha256 equal to the written bytes ({recomputed == result.sha256}); "
            f"the file is never re-opened, so the digest is a number nobody checks -- the "
            f"instrument read back {len(rows)} lines including the header on its own account"
        ),
    }


def _save_artifact_event() -> dict[str, Any]:
    """Run the other writer into a throwaway artifact root and look at what it returns."""
    from dsa_tools.tools.save_artifact import SaveArtifactInput, SaveArtifactTool

    root = tempfile.mkdtemp(prefix="dsa-save-lifecycle-")
    os.environ["DSA_ARTIFACT_ROOT"] = root
    result = asyncio.run(
        SaveArtifactTool().execute(
            SaveArtifactInput(
                run_id="run-probe", type="report", filename="report.md", content="# probe\n"
            )
        )
    )
    fields = sorted(result.model_dump())
    return {
        "id": "write:save_artifact",
        "surface": "packages/tools/src/dsa_tools/tools/save_artifact.py",
        "integrity_hash": "absent",
        "parse_check": "absent",
        "evidence": "ran",
        "detail": f"returns {fields} and writes the text without reading it back",
    }


def _record_event() -> dict[str, Any]:
    """The run record the case studies ship: what each entry says about its file."""
    records = sorted(CASE_STUDIES.glob("*/outputs/artifacts.json"))
    entries: list[dict[str, Any]] = []
    for path in records:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        entries.extend(loaded)
    fields = sorted({name for entry in entries for name in entry})
    hash_fields = [name for name in fields if HASH_FIELD.search(name)]
    return {
        "id": "record:artifacts_json",
        "surface": "case-studies/*/outputs/artifacts.json",
        "integrity_hash": "recorded" if hash_fields else "absent",
        "parse_check": "absent",
        "evidence": "ran",
        "detail": (
            f"{len(entries)} entries across {len(records)} committed records; fields {fields}; "
            f"{len(hash_fields)} of them name a digest"
        ),
    }


def _manifest_keys() -> list[str]:
    """The keys the bundle route writes into `manifest`, read from its source rather than executed."""
    tree = ast.parse(BUNDLE_ROUTE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        named = [t for t in node.targets if isinstance(t, ast.Name) and t.id == "manifest"]
        if named and isinstance(node.value, ast.Dict):
            return sorted(
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )
    return []


def _bundle_event() -> dict[str, Any]:
    """Read the route: what the manifest carries, and whether the zip path computes anything."""
    keys = _manifest_keys()
    source = BUNDLE_ROUTE.read_text(encoding="utf-8")
    digest_mentions = len(re.findall(r"hashlib|sha256|digest", source, re.IGNORECASE))
    return {
        "id": "export:bundle",
        "surface": "src/data_science_agent/_vendor/dsa_api/routers/bundles.py",
        "integrity_hash": "absent",
        "parse_check": "absent",
        "evidence": "read",
        "detail": (
            f"manifest keys {keys}; {digest_mentions} digest references in the module, so two "
            f"bundles of different bytes are indistinguishable from their manifests"
        ),
    }


def _report_event() -> dict[str, Any]:
    """Run the plain export's strip rule against a digest and see whether it survives."""
    from dsa_agent.report_export import strip_identifiers

    text = f"The correlation is 0.81 and the dataset hash is {SAMPLE_DIGEST}."
    cleaned = strip_identifiers(text)
    return {
        "id": "read:report_export",
        "surface": "packages/agent/src/dsa_agent/report_export.py",
        "integrity_hash": "stripped",
        "parse_check": "absent",
        "evidence": "ran",
        "detail": (
            f"a 64-hex token is removed on purpose: digest gone = {SAMPLE_DIGEST not in cleaned}; "
            f"the figure 0.81 survives, which is the rule the module states"
        ),
    }


def _committed_exports() -> list[Path]:
    return sorted(
        path
        for path in CASE_STUDIES.glob("*/outputs/*")
        if path.suffix in {".json", ".md"} and path.is_file()
    )


def _consumer_event(files: list[Path]) -> dict[str, Any]:
    """Read every committed export with the reader its class implies; a failure is a crash, not a row."""
    counts: dict[str, int] = {}
    for path in files:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        else:
            path.read_text(encoding="utf-8")
        counts[path.suffix.lstrip(".")] = counts.get(path.suffix.lstrip("."), 0) + 1
    return {
        "id": "read:consumer",
        "surface": "case-studies/*/outputs/*",
        "integrity_hash": "absent",
        "parse_check": "present",
        "evidence": "ran",
        "detail": (
            f"{sum(counts.values())} committed exports parsed by class {sorted(counts.items())}; "
            f"the parser decides readability, nothing compares it with a stored digest"
        ),
    }


def _parseability(files: list[Path]) -> dict[str, Any]:
    """Per class: how many committed exports exist and how many read back."""
    by_class: dict[str, int] = {}
    for path in files:
        name = path.suffix.lstrip(".")
        by_class[name] = by_class.get(name, 0) + 1
    measured = {
        name: {"committed": count, "parsed": count} for name, count in sorted(by_class.items())
    }
    absent = {
        name: {
            "committed": 0,
            "parsed": None,
            "status": "not_measured",
            "reason": (
                "no committed export of this class; run artifacts live under a gitignored root, "
                "so a reading here would describe one machine rather than the tree"
            ),
        }
        for name in ("csv", "png", "xlsx")
    }
    return {**measured, **absent}


def _divergence(manifest_keys: list[str]) -> dict[str, Any]:
    return {
        "document": "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md",
        "claim": ADR_CLAIM,
        "claim_in_document": ADR_CLAIM in ADR.read_text(encoding="utf-8"),
        "manifest_keys": manifest_keys,
        "hash_keys_in_manifest": [key for key in manifest_keys if HASH_FIELD.search(key)],
        "reading": (
            "the ADR's bundle description names artifact hashes among five elements; the shipped "
            "manifest names files and exclusion reasons and carries no per-file digest, so the "
            "element is planned in the ADR and absent from the export a visitor keeps"
        ),
    }


def build() -> dict[str, Any]:
    files = _committed_exports()
    events = [
        _export_artifact_event(),
        _save_artifact_event(),
        _record_event(),
        _bundle_event(),
        _report_event(),
        _consumer_event(files),
    ]
    export_side = {"record:artifacts_json", "export:bundle", "read:report_export"}
    hashes = [event for event in events if event["integrity_hash"] == "recorded"]
    return {
        "schema": SCHEMA,
        "recorded_at": _timestamp(),
        "reviewed_commit": REVIEWED_COMMIT,
        "events": events,
        "summary": {
            "events": len(events),
            "events_recording_a_digest": len(hashes),
            "export_side_events": len(export_side),
            "export_side_events_with_a_digest": sum(
                1
                for event in events
                if event["id"] in export_side and event["integrity_hash"] == "recorded"
            ),
            "events_with_a_parse_check": sum(
                1 for event in events if event["parse_check"] == "present"
            ),
            "events_measured_by_running": sum(1 for event in events if event["evidence"] == "ran"),
            "committed_exports": len(files),
            "committed_exports_parsed": sum(
                entry["parsed"] or 0 for entry in _parseability(files).values()
            ),
            "classes_not_measured": sorted(
                name
                for name, entry in _parseability(files).items()
                if entry.get("status") == "not_measured"
            ),
        },
        "parseability": _parseability(files),
        "adr_divergence": _divergence(_manifest_keys()),
        "not_claimed": [
            "no containment and no tamper resistance: a digest nobody compares is a number, not a control",
            "no claim about the bundle's environment, pinned dependencies or execution trace; this reading examines digests and parse results only",
            "no claim that an absent digest means a corrupt file, and no claim that a parsed file is correct",
            "not_measured is not zero: csv, png and xlsx have no committed export to read",
            "publication_ready is untouched here and keeps its own gate",
        ],
        "procedure": [
            "Run `python scripts/measure_export_lifecycle.py --record > docs/audit/export-lifecycle.json` in the repository root.",
            "Run `python scripts/measure_export_lifecycle.py --verify` to rebuild every field from the tree and compare it with the record.",
            "The instrument writes into throwaway temporary directories only; nothing under the repository is written by it.",
        ],
    }


def measure() -> dict[str, Any]:
    return build()


def verify() -> int:
    """Rebuild the reading and compare it field by field, excluding the timestamp it was taken at."""
    recorded = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    rebuilt = build()
    failures = 0
    for key in sorted(set(recorded) | set(rebuilt)):
        if key == "recorded_at":
            continue
        if recorded.get(key) != rebuilt.get(key):
            print(f"differs: {key}", file=sys.stderr)
            print(f"  recorded: {json.dumps(recorded.get(key), sort_keys=True)}", file=sys.stderr)
            print(f"  rebuilt : {json.dumps(rebuilt.get(key), sort_keys=True)}", file=sys.stderr)
            failures += 1
    print(f"verify: {len(recorded) - 1} fields compared, {failures} differ")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Record where an artifact's digest survives")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="print the reading as JSON")
    mode.add_argument("--verify", action="store_true", help="compare the record with the tree")
    args = parser.parse_args(argv)

    if args.record:
        json.dump(measure(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
