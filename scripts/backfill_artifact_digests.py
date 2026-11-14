"""Put a digest on the committed artifact records -- ADR-004 D3, applied once to what already exists.

D3 asks four export surfaces to carry a per-file digest. Three of them are code that writes as it
runs, so the digest appears the next time the surface runs. This one is not: the eight committed
``case-studies/*/outputs/artifacts.json`` records were assembled before the field existed and no
writer in this tree emits them, so the 40 entries have to be brought forward once.

The script reads each file an entry names and prints the record with ``metadata.sha256`` added. It
prints; it does not write. The caller redirects into the record, which keeps this module free of a
read-into-write path and makes the diff reviewable before anything lands:

    python scripts/backfill_artifact_digests.py 01-sales > case-studies/01-sales/outputs/artifacts.json

A file the record names but this machine does not hold stops the run instead of being skipped: a
digest invented for an absent file would describe nothing, and the 40 entries are exactly the place
where a plausible number is worst. ``--verify`` prints nothing and exits non-zero if any committed
record disagrees with the bytes it names, so the same script is the way a reader checks the numbers.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_STUDIES = ROOT / "case-studies"

#: The eight studies, closed: a name that is not here is a typo, not a path to glob.
STUDIES: tuple[str, ...] = (
    "01-sales",
    "02-churn",
    "03-time-series",
    "04-marketing",
    "05-financial",
    "06-public-statistics",
    "07-data-quality",
    "08-classification",
)


def record_path(study: str) -> Path:
    if study not in STUDIES:
        raise SystemExit(f"unknown study {study!r}; expected one of {list(STUDIES)}")
    return CASE_STUDIES / study / "outputs/artifacts.json"


def rebuild(study: str) -> list[dict[str, Any]]:
    """The committed record with each entry's digest recomputed from the file it names."""
    entries = json.loads(record_path(study).read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    missing: list[str] = []
    for entry in entries:
        path = Path(str(entry.get("path") or ""))
        if not path.is_file():
            missing.append(f"{entry.get('id')} -> {path}")
            out.append(entry)
            continue
        metadata = dict(entry.get("metadata") or {})
        metadata["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append({**entry, "metadata": metadata})
    if missing:
        raise SystemExit(
            "refusing to write a digest for a file this machine does not hold:\n  "
            + "\n  ".join(missing)
        )
    return out


def verify() -> int:
    """Compare every committed record with the bytes it names; a mismatch is the whole answer."""
    failures = 0
    for study in STUDIES:
        recorded = json.loads(record_path(study).read_text(encoding="utf-8"))
        rebuilt = rebuild(study)
        if recorded != rebuilt:
            failures += 1
            print(f"differs: {study}", file=sys.stderr)
    print(f"verify: {len(STUDIES)} records compared, {failures} differ")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--verify"]:
        return verify()
    if len(argv) != 1:
        raise SystemExit(
            f"usage: backfill_artifact_digests.py <study> | --verify\nstudies: {', '.join(STUDIES)}"
        )
    entries = rebuild(argv[0])
    json.dump(entries, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
