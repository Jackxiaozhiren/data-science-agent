"""Which audit records declare a version, and whether anything holds them to it -- ADR-003 S2, item 4.

The ADR names this item as a "contract-version policy" without defining the term. Two readings of the
phrase are available: the ``/version`` payload a deployed API discloses, which is already the
``api_version_contract`` check in S1's served-artifact probe, and the version token on the audit
records a consumer derives numbers from. This instrument takes the second, because the first already
has a reading and because a record is what a later reader meets first.

For each record it asks three questions that a reader can answer without trusting prose: does the
record name its own shape, is that name compared with anything outside the record, and does the record
say what a change to the name would mean. The first two are read from files. The third is a field that
no record in this tree carries, which is the gap the policy in ``docs/audit/contract-versions.json``
exists to close.

Every path is a repository constant and the CLI takes flags only; ``--record`` and ``--verify`` write
JSON to stdout and the caller redirects it, so this module has no file-content-to-file-write edge.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/audit"
RECORD_PATH = AUDIT / "contract-versions.json"
SCHEMA = "contract-versions/v1"
#: The tree this reading describes: the main commit the change that retook it was based on, so a
#: register regenerated before its own merge still names a commit that exists.
REVIEWED_COMMIT = "5cbee4de0906"

#: The policy decides nothing about records written before it, and is not back-dated onto them.
IN_FORCE_FROM = "2026-11-12"

#: A subject in kebab case, a slash, a decimal major that starts at one. ``/v0`` is reserved for
#: pre-policy records and is therefore never written in a file.
TOKEN_FORM = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*/v[1-9][0-9]*$")

#: The field whose presence would mean a record states what a bump means. None does; see ``summary``.
BUMP_RULE_FIELD = "version_policy"

CHECK_KINDS = ("record-vs-constant", "record-vs-rebuild", "input-vs-record", "none")

#: What compares each token with something that is not the record itself.
#:
#: Read by hand from the four files named here and pinned by the contract test: the record cannot
#: promote a token to "checked" by asserting it, and cannot demote one either. The token strings
#: themselves are never typed here -- they are read from the file the token lives in.
CHECKS: dict[str, tuple[str, str | None, str]] = {
    "docs/audit/attribution.json": (
        "record-vs-constant",
        "tests/contract/test_attribution_record.py",
        "the test types both tokens and compares the reading and its frame with them",
    ),
    "docs/audit/execution-boundary.json": (
        "record-vs-rebuild",
        "tests/contract/test_execution_boundary_record.py",
        "the test re-runs the instrument and compares the rebuilt token with the recorded one",
    ),
    "docs/audit/export-lifecycle-first.json": (
        "record-vs-constant",
        "tests/contract/test_export_lifecycle_record.py",
        "the test types the superseded pass's token and asserts the kept file still declares it",
    ),
    "docs/audit/export-lifecycle.json": (
        "record-vs-constant",
        "tests/contract/test_export_lifecycle_record.py",
        "the test compares the record with the instrument's own SCHEMA constant",
    ),
    "docs/audit/independent-rerun.json": (
        "none",
        None,
        "the instrument writes the token and the test reads the record without touching it",
    ),
    "docs/audit/served-artifacts.json": (
        "none",
        None,
        "the probe writes verdicts and the test reads them; the record carries no token to check",
    ),
    "docs/audit/authorization-coverage.json": (
        "none",
        None,
        "the first coverage reading carries no token and the test reads only its action classes",
    ),
    "docs/audit/authorization-coverage-second.json": (
        "none",
        None,
        "the second coverage reading repeats the first's shape, token included",
    ),
    "docs/audit/evidence-alignment.json": (
        "input-vs-record",
        "tests/contract/test_evidence_alignment_record.py",
        "the test compares the frame's token with the record's frame_schema; the record has no token of its own",
    ),
}


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _effective(declared: str | None) -> str:
    """The version a reader should assume: the token's own suffix, or v0 when there is no token."""
    if declared is None:
        return "v0"
    return declared.rpartition("/")[2]


def _predates_policy(payload: dict[str, Any]) -> bool:
    """The policy is not back-dated: a record taken before it is exempt whatever it declares.

    ISO dates compare correctly as strings, so no parsing is needed for the one comparison here.
    """
    return str(payload.get("recorded_at", ""))[:10] < IN_FORCE_FROM


def _payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_reading(payload: dict[str, Any]) -> bool:
    """A record is a reading when it states when it was taken; gate inputs and registers do not."""
    return "recorded_at" in payload


def _row(path: Path) -> dict[str, Any]:
    key = f"docs/audit/{path.name}"
    payload = _payload(path)
    declared = payload.get("schema")
    if key not in CHECKS:
        raise LookupError(f"{key} is new: add it to CHECKS with the check that holds its token")
    kind, consumer, detail = CHECKS[key]
    return {
        "path": key,
        "recorded_at": payload.get("recorded_at"),
        "declared_schema": declared,
        "declared_frame_schema": payload.get("frame_schema"),
        "effective_version": _effective(declared),
        "pre_policy": _predates_policy(payload),
        "check_kind": kind,
        "checked_by": consumer,
        "states_bump_rule": BUMP_RULE_FIELD in payload,
        "detail": detail,
    }


def rows() -> list[dict[str, Any]]:
    """One row per reading, in path order. The register itself is not a reading."""
    found = []
    for path in sorted(AUDIT.glob("*.json")):
        if path == RECORD_PATH:
            continue
        if _is_reading(_payload(path)):
            found.append(_row(path))
    return found


def scope() -> dict[str, int]:
    """How the directory partitions: readings, this register, and gate inputs that state no date.

    The register counts as one whether or not it exists yet, because the record is generated before
    the file it will become does; the contract test asserts the partition against the directory.
    """
    readings, gate_inputs = 0, 0
    for path in sorted(AUDIT.glob("*.json")):
        if path == RECORD_PATH:
            continue
        if _is_reading(_payload(path)):
            readings += 1
        else:
            gate_inputs += 1
    return {"readings": readings, "registers": 1, "gate_inputs": gate_inputs}


def problems(candidates: list[dict[str, Any]]) -> list[str]:
    """Every way a row can break a clause. Reported by ``--verify`` and exercised by the test."""
    found: list[str] = []
    seen: set[str] = set()
    for row in candidates:
        path = row["path"]
        if path in seen:
            found.append(f"{path}: registered twice")
        seen.add(path)
        for field in ("declared_schema", "declared_frame_schema"):
            token = row[field]
            if token is not None and not TOKEN_FORM.match(token):
                found.append(f"{path}: {field} is not <subject>/vN: {token!r}")
        if row["effective_version"] != _effective(row["declared_schema"]):
            found.append(
                f"{path}: effective_version {row['effective_version']!r} does not follow from "
                f"{row['declared_schema']!r}"
            )
        if row["pre_policy"] != _predates_policy({"recorded_at": row["recorded_at"]}):
            found.append(f"{path}: pre_policy disagrees with the date the record states")
        if row["check_kind"] not in CHECK_KINDS:
            found.append(f"{path}: check_kind {row['check_kind']!r} is not one of {CHECK_KINDS}")
        if row["check_kind"] == "none" and row["checked_by"] is not None:
            found.append(f"{path}: check_kind is none but names a consumer")
        if row["check_kind"] != "none" and row["checked_by"] is None:
            found.append(f"{path}: check_kind {row['check_kind']!r} names no consumer")
        if not row["pre_policy"] and row["check_kind"] == "none":
            found.append(f"{path}: written after {IN_FORCE_FROM} and no consumer checks its token")
    return found


def summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(candidates),
        "declaring_own_schema": sum(1 for row in candidates if row["declared_schema"]),
        "declaring_only_input_schema": sum(
            1 for row in candidates if not row["declared_schema"] and row["declared_frame_schema"]
        ),
        "declaring_none": sum(
            1
            for row in candidates
            if not row["declared_schema"] and not row["declared_frame_schema"]
        ),
        "pre_policy": sum(1 for row in candidates if row["pre_policy"]),
        "own_tokens_checked": sum(
            1 for row in candidates if row["declared_schema"] and row["check_kind"] != "none"
        ),
        "own_tokens_unchecked": sum(
            1 for row in candidates if row["declared_schema"] and row["check_kind"] == "none"
        ),
        "records_carrying_a_bump_rule": sum(1 for row in candidates if row["states_bump_rule"]),
        "policy_violations": len(problems(candidates)),
    }


def build() -> dict[str, Any]:
    candidates = rows()
    return {
        "schema": SCHEMA,
        "recorded_at": _timestamp(),
        "reviewed_commit": REVIEWED_COMMIT,
        "in_force_from": IN_FORCE_FROM,
        "question": (
            "For each audit record a consumer derives numbers from: does the record name its own "
            "shape, is that name compared with anything outside the record, and does the record say "
            "what changing the name would mean?"
        ),
        "scope": scope(),
        "policy": {
            "applies_to": (
                "every file under docs/audit/ that carries a recorded_at, written from "
                f"{IN_FORCE_FROM}; the records above that predate it are read as v0"
            ),
            "pre_policy_version": "v0",
            "clauses": [
                {
                    "id": "P1",
                    "rule": (
                        "schema is <subject>/vN: a kebab-case subject naming the record's own "
                        "artifact, then a decimal major starting at 1. A projection's token goes in "
                        "frame_schema under the same form."
                    ),
                    "enforced_by": "the token form, checked by --verify and by the contract test",
                },
                {
                    "id": "P2",
                    "rule": (
                        "N increments when a consumer's arithmetic would change -- a key it reads is "
                        "removed or renamed, or its type or meaning changes. Adding a key, reordering "
                        "keys, or re-deriving a value for the same key does not increment."
                    ),
                    "enforced_by": (
                        "nothing mechanical; a bump edits the record and this register in one change, "
                        "and the contract test fails while they disagree"
                    ),
                },
                {
                    "id": "P3",
                    "rule": (
                        "No silent readers. A consumer compares schema with a literal, with the "
                        "instrument's constant, or with a rebuild, or refuses an unknown value "
                        "explicitly. A consumer that never touches schema is registered as none."
                    ),
                    "enforced_by": "check_kind per row, plus the post-policy rule in --verify",
                },
                {
                    "id": "P4",
                    "rule": (
                        "A record that predates this policy and declares no token is read as v0 and "
                        "is not retro-tagged: the page's third rule forbids rewriting a reading that "
                        "was taken. One that declares a token keeps it, checked or not, and the "
                        "register says which."
                    ),
                    "enforced_by": "effective_version per row, derived rather than typed",
                },
                {
                    "id": "P5",
                    "rule": (
                        "The register travels with the record: every docs/audit file carrying a "
                        "recorded_at has a row in the change that adds it."
                    ),
                    "enforced_by": (
                        "the contract test compares the rows with the directory, so an unregistered "
                        "record fails it"
                    ),
                },
            ],
        },
        "records": candidates,
        "summary": summary(candidates),
        "not_claimed": [
            "not an external API guarantee: these are repository artefacts, and no consumer outside "
            "this tree is bound by the token",
            "no claim that a checked token makes a reading correct; it makes the shape a reader "
            "assumes explicit",
            "no claim that the pre-policy records are wrong; they are read as v0 rather than "
            "retro-tagged",
            "no claim about the five gate inputs under docs/audit/; versioning a ceiling or an "
            "exception list is a separate question",
            "not_measured is not zero, and publication_ready is untouched here",
        ],
        "procedure": [
            "Run `python scripts/measure_contract_versions.py --record > docs/audit/contract-versions.json` in the repository root.",
            "Run `python scripts/measure_contract_versions.py --verify` to rebuild every field from the tree and compare it with the register.",
            "The check column is read by hand and pinned by `tests/contract/test_contract_versions_record.py`; every token is read from the file it lives in.",
        ],
    }


def measure() -> dict[str, Any]:
    return build()


def verify() -> int:
    """Rebuild the register and compare it field by field, excluding the timestamp it was taken at."""
    recorded = _payload(RECORD_PATH)
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
    for problem in problems(recorded.get("records", [])):
        print(f"violates: {problem}", file=sys.stderr)
        failures += 1
    print(f"verify: {len(recorded) - 1} fields compared, {failures} differ")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record which audit records declare a version")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record", action="store_true", help="print the register as JSON")
    mode.add_argument("--verify", action="store_true", help="compare the register with the tree")
    args = parser.parse_args(argv)

    if args.record:
        json.dump(measure(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
