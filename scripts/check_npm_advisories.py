"""Adjudicate ``npm audit --json`` output against a bounded exception list.

Why this exists as a separate gate rather than the raw ``npm audit`` exit code: a
scanner cannot tell an *unactionable* finding from an ignored one. ``braces``
(GHSA-vfj7-8cjw-p6xm) has no release outside its affected range, so "keep main green"
and "pretend high severities are fine" were the only two answers available -- and a
security gate should not have those as its only two answers.

npm's own ``fixAvailable`` field is deliberately not consulted: for this advisory it
reports ``{"name": "tailwindcss", "version": "4.3.3", "isSemVerMajor": true}``, which
counts a breaking dependency *replacement* as the fix. That is the decision this
script must not make for a human.

The audit document is passed in as a file: ``scripts/`` owns no subprocess (bandit
S603/S607), and every other checker in this directory is a pure reader too, so the
scan stays in ``.github/workflows/ci.yml`` and only the verdict moves here.

Exit codes: ``0`` clean or fully accounted for, ``1`` a real violation, ``2`` the
input itself is unusable -- an unreadable or truncated audit file must never read as
green.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXCEPTIONS = ROOT / "docs" / "audit" / "npm-advisory-exceptions.json"

#: What ``npm audit --audit-level=high`` policed before this script existed. Lower
#: severities are still reported by npm and still ignored here, on purpose: this
#: change is about *high and critical* findings being unactionable, not about
#: widening or narrowing what the pipeline looks at.
POLICY_SEVERITIES = ("high", "critical")

#: An exception without one of these is an unbounded exception, which is the thing
#: this gate is meant to prevent.
REQUIRED_EXCEPTION_FIELDS = (
    "id",
    "package",
    "severity",
    "advisory_url",
    "affected_range",
    "why_unactionable",
    "exposure",
    "advised",
    "review_by",
)

EXIT_CLEAN = 0
EXIT_VIOLATION = 1
EXIT_INPUT_ERROR = 2


class InputError(Exception):
    """The audit document or the exception list cannot be used as given."""


def _ghsa_from_url(url: str) -> str:
    marker = "/advisories/"
    if marker not in url:
        return ""
    tail = url.rsplit(marker, 1)[1].strip("/#")
    return tail.split("?")[0] if tail.startswith("GHSA-") else ""


def _advisories_of(
    vulns: dict[str, dict], name: str, seen: frozenset[str] = frozenset()
) -> list[tuple[str, str, str]]:
    """Reach ``(advisory id, advisory package, severity)`` through npm's ``via`` graph.

    npm lists a vulnerable package once per node in the tree and expresses the chain as
    strings for the downstream nodes, so ``tailwindcss -> micromatch -> braces`` carries
    the GHSA id only at the ``braces`` entry. Without this walk, exempting the advisory
    that actually has no fix would leave the four packages it infects failing.
    """
    entry = vulns.get(name)
    if entry is None or name in seen:
        return []
    found: list[tuple[str, str, str]] = []
    for via in entry.get("via", []):
        if isinstance(via, dict):
            ghsa = _ghsa_from_url(str(via.get("url", "")))
            severity = str(via.get("severity") or entry.get("severity", ""))
            found.append((ghsa or "<unidentified>", str(via.get("name") or name), severity))
        elif isinstance(via, str):
            found.extend(_advisories_of(vulns, via, seen | {name}))
    return found


def _load_audit(path: Path) -> dict[str, dict]:
    """Return npm's ``vulnerabilities`` map, rejecting anything not shaped like it."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{path}: cannot read the audit document ({exc})") from exc
    if not text.strip():
        raise InputError(
            f"{path}: empty. `npm audit --json` did not produce a report; "
            "a gate that passes on an absent scan is a gate that was never run."
        )
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: not valid JSON ({exc}). Truncated npm output?") from exc
    if not isinstance(doc, dict):
        raise InputError(f"{path}: expected a JSON object, got {type(doc).__name__}")
    if doc.get("auditReportVersion") != 2:
        raise InputError(
            f"{path}: auditReportVersion is {doc.get('auditReportVersion')!r}, this reader "
            "implements schema 2. npm changed format; re-read its docs before trusting counts."
        )
    vulns = doc.get("vulnerabilities")
    if not isinstance(vulns, dict):
        raise InputError(f"{path}: no `vulnerabilities` object to adjudicate")
    return vulns


def _load_exceptions(path: Path) -> dict[tuple[str, str], date]:
    """Return ``{(advisory id, package): review-by date}``, refusing unbounded entries."""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"{path}: cannot read the exception list ({exc})") from exc
    except json.JSONDecodeError as exc:
        raise InputError(f"{path}: exception list is not valid JSON ({exc})") from exc
    entries = doc.get("advisories") if isinstance(doc, dict) else None
    if not isinstance(entries, list):
        raise InputError(f"{path}: expected an `advisories` array")
    out: dict[tuple[str, str], date] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise InputError(f"{path}: an advisory entry is not an object: {entry!r}")
        missing = [field for field in REQUIRED_EXCEPTION_FIELDS if not entry.get(field)]
        if missing:
            raise InputError(
                f"{path}: exception {entry.get('id', '<no id>')!r} is missing "
                f"{missing}; an exemption without a reason or a review date is unbounded"
            )
        try:
            review_by = date.fromisoformat(str(entry["review_by"]))
        except ValueError as exc:
            raise InputError(
                f"{path}: exception {entry['id']!r} has review_by={entry['review_by']!r}, "
                "which is not an ISO date"
            ) from exc
        out[(str(entry["id"]), str(entry["package"]))] = review_by
    return out


def _report(violations: list[str], exemptions: list[str]) -> None:
    for line in violations:
        print(f"FAIL {line}")
    for line in exemptions:
        print(f"EXEMPT {line}")
    if not violations and not exemptions:
        print("npm advisory gate: no high/critical findings.")
    elif not violations:
        print(
            f"npm advisory gate: clean, with {len(exemptions)} bounded exemption(s) carried above."
        )
    else:
        print(f"npm advisory gate: {len(violations)} violation(s).")


def main(argv: list[str] | None = None, today: date | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audit_json", type=Path, help="a `npm audit --json` capture")
    parser.add_argument(
        "--exceptions", type=Path, default=DEFAULT_EXCEPTIONS, help="bounded exception list"
    )
    args = parser.parse_args(argv)

    today = today or date.today()
    try:
        vulns = _load_audit(args.audit_json)
        allowed = _load_exceptions(args.exceptions)
    except InputError as exc:
        print(f"INPUT ERROR {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    listed_in = (
        args.exceptions.relative_to(ROOT)
        if args.exceptions.is_relative_to(ROOT)
        else args.exceptions
    )

    violations: list[str] = []
    exemptions: list[str] = []
    seen_ids: set[tuple[str, str]] = set()
    for name, entry in sorted(vulns.items()):
        if not isinstance(entry, dict):
            violations.append(f"{name}: vulnerability entry is not an object")
            continue
        if entry.get("severity") not in POLICY_SEVERITIES:
            continue
        advisories = _advisories_of(vulns, name)
        if not advisories:
            violations.append(f"{name}: {entry.get('severity')} with no advisory reachable")
            continue
        for ghsa, advisory_package, severity in sorted(set(advisories)):
            key = (ghsa, advisory_package)
            seen_ids.add(key)
            if severity not in POLICY_SEVERITIES:
                continue
            if ghsa == "<unidentified>":
                violations.append(
                    f"{name}: a {severity} finding on {advisory_package} carries no "
                    "GHSA url, so it cannot be accounted for"
                )
                continue
            if key not in allowed:
                violations.append(
                    f"{name}: {severity} advisory {ghsa} ({advisory_package}) has no "
                    "exemption -- fix it, or add a dated entry to "
                    f"{listed_in} saying why it is unactionable"
                )
                continue
            review_by = allowed[key]
            if review_by < today:
                violations.append(
                    f"{name}: exemption for {ghsa} expired {review_by.isoformat()} -- "
                    "re-review it: upstream may have shipped a fix, or the migration "
                    "that removes it is now overdue"
                )
                continue
            exemptions.append(
                f"{ghsa} on {advisory_package} ({severity}) tolerated until "
                f"{review_by.isoformat()}; reached from {name}"
            )

    for stale in sorted(set(allowed) - seen_ids):
        violations.append(
            f"exception list carries {stale[0]} on {stale[1]}, which this audit no longer "
            "reports -- delete the entry so the list keeps meaning something"
        )

    _report(violations, exemptions)
    return EXIT_VIOLATION if violations else EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
