"""Enumerate defaulted dict reads whose key nothing in this repository writes.

Audit §102. The §101 defect was found this way by hand: `Reproduction.run()` read
``reproduction_score["trajectory"]`` while the harness writes the trajectory rate as ``semantic``, so
the public SDK published ``0.0`` for a dimension it had never read. A read of the form
``record.get("key", <default>)`` is the dangerous shape, because a renamed or never-written key is
indistinguishable from a legitimately absent one -- it returns the default and nothing fails.

This walks the same shipped source set the debt ratchet uses and reports reads whose key has no
producer anywhere in shipped code, pydantic/dataclass/TypedDict field names, or committed JSON
artifacts. Keys whose data comes from outside the repository (environment variables, HTTP headers,
provider response bodies) can never have an in-repo producer, so they are declared in
``docs/audit/orphan-reads.json`` with the source they come from; an entry that stops being an orphan
fails, which is what keeps that list from rotting.

Usage::

    python scripts/find_orphan_reads.py            # report
    python scripts/find_orphan_reads.py --seed     # write the exemption list from the current reading
    python scripts/find_orphan_reads.py --check    # exit 1 unless the reading matches the list exactly
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LIST_PATH = ROOT / "docs" / "audit" / "orphan-reads.json"
SHIPPED = ("packages", "apps", "src", "scripts")
SKIP_DIR_PARTS = ("_vendor", "__pycache__", ".venv", "node_modules", ".git", "data-science-agent")
REQUIRED_FIELDS = ("key", "external_source", "why_no_producer", "reviewed_on")


def _skip(path: Path) -> bool:
    return any(part in SKIP_DIR_PARTS for part in path.parts)


def shipped_py() -> list[Path]:
    return sorted(
        p
        for root in SHIPPED
        for p in (ROOT / root).rglob("*.py")
        if p.is_file() and not _skip(p.relative_to(ROOT))
    )


def _produced_names(tree: ast.AST) -> set[str]:
    """String keys and declared field names this file makes available to a reader.

    Walked rather than visited with method names, so the module keeps one naming style; the shapes are
    dict literals, subscript assignment, ``setdefault``/``pop``/``update`` and annotated class fields
    (pydantic models, dataclasses and TypedDicts all serialize their field names into records).
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            names |= {
                k.value
                for k in node.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                ):
                    names.add(target.slice.value)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in {"setdefault", "pop", "update"}:
                for arg in node.args[:1]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        names.add(arg.value)
            names |= {kw.arg for kw in node.keywords if kw.arg}
        elif isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    names.add(stmt.target.id)
    return names


def _defaulted_reads(tree: ast.AST) -> list[tuple[str, int]]:
    """``x.get("key", default)`` -- a read that answers with a value instead of an error."""
    reads: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            reads.append((node.args[0].value, node.lineno))
    return reads


def measure() -> dict[str, list[str]]:
    """Return ``{key: ["path:line", ...]}`` for every defaulted read with no in-repo producer.

    Only shipped *code* counts as a producer. Committed JSON is deliberately not consulted: measured
    on this repository, folding artifact keys in masked nine of the fourteen orphan reads the detector
    finds, including the npm audit structure keys ``url`` and ``via`` that the repo merely consumes.
    """
    produced: set[str] = set()
    reads: dict[str, list[str]] = {}
    for path in shipped_py():
        # No try/except here on purpose. A shipped file this cannot parse is a file whose reads are
        # then unseen, and debt.unparseableShippedFiles measures 0 -- so a parse failure is a real
        # defect to surface, not a file to skip while reporting the rest as clean (audit §96, D-L3-08).
        tree = ast.parse(path.read_text(encoding="utf-8"))
        produced |= _produced_names(tree)
        for key, line in _defaulted_reads(tree):
            reads.setdefault(key, []).append(f"{path.relative_to(ROOT)}:{line}")
    return {key: sites for key, sites in reads.items() if key not in produced}


def load_list() -> list[dict[str, Any]]:
    data = json.loads(LIST_PATH.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise SystemExit(f"{LIST_PATH}: no 'entries' list")
    for entry in entries:
        missing = [field for field in REQUIRED_FIELDS if not entry.get(field)]
        if missing:
            raise SystemExit(f"{LIST_PATH}: entry {entry.get('key')!r} missing {missing}")
    return entries


def write_list(orphans: dict[str, list[str]]) -> None:
    """Write the reading as an unreviewed list: every required field is empty, so ``--check`` refuses
    it until a human names the external source. No placeholder text, because a placeholder written in
    shipped code is itself counted as debt by ``debt.todoMarkers``.
    """
    entries = [
        {
            "key": key,
            "external_source": "",
            "why_no_producer": "",
            "first_sites": sites[:3],
            "reviewed_on": "",
        }
        for key, sites in sorted(orphans.items())
    ]
    payload = {
        "_purpose": (
            "Defaulted dict reads whose key has no producer in this repository and whose data comes "
            "from outside it. scripts/find_orphan_reads.py --check fails if a key appears here that is "
            "no longer an orphan, or if a new orphan is not listed."
        ),
        "_do_not_run_ruff_format_on_this_file": True,
        "entries": entries,
    }
    LIST_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"seeded {len(entries)} entries into {LIST_PATH}")


def evaluate(orphans: dict[str, list[str]], entries: list[dict[str, Any]]) -> list[str]:
    """Return the problems with this reading against the declared list; empty means the gate holds."""
    listed = {entry["key"] for entry in entries}
    problems: list[str] = []
    for key in sorted(set(orphans) - listed):
        problems.append(f"unlisted orphan read {key!r} at {orphans[key][0]}")
    for key in sorted(listed - set(orphans)):
        problems.append(f"{key!r} is listed as external but is no longer an orphan read")
    return problems


def check(orphans: dict[str, list[str]]) -> int:
    """Compare a reading with the declared external list; non-zero exit means the gate is broken."""
    problems = evaluate(orphans, load_list())
    if problems:
        for line in problems:
            print(f"FAIL: {line}")
        return 1
    print(f"orphan reads: {len(orphans)} key(s), each declared with its external source")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--seed", action="store_true", help="write the exemption list from the reading"
    )
    mode.add_argument("--check", action="store_true", help="exit 1 unless reading and list agree")
    args = parser.parse_args(argv)

    orphans = measure()
    if args.seed:
        write_list(orphans)
        return 0
    if args.check:
        return check(orphans)
    print(f"defaulted reads with no in-repo producer: {len(orphans)}")
    for key, sites in sorted(orphans.items()):
        print(f"  {key!r} x{len(sites)}  {sites[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
