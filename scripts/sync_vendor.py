#!/usr/bin/env python3
"""Sync the vendored dsa_* modules from their workspace source.

The published wheel `jack-data-science-agent` bundles the dsa_* sub-packages
under `src/data_science_agent/_vendor/` (so `pip install` works without
publishing 15 separate distributions). This script copies the current source
from `packages/*/src` and `apps/*/src` into `_vendor`, keeping the vendored
copies in sync with the source of truth.

Run `python scripts/sync_vendor.py` and commit the result whenever a dsa_*
module changes. CI runs this with `--check`, which compares without writing:
an auditor that repairs what it audits cannot report what it found.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "src/data_science_agent/_vendor"

# name -> source dir (must match the top-level import name)
SOURCES: dict[str, Path] = {
    "dsa_agent": ROOT / "packages/agent/src/dsa_agent",
    "dsa_datasets": ROOT / "packages/datasets/src/dsa_datasets",
    "dsa_evaluation": ROOT / "packages/evaluation/src/dsa_evaluation",
    "dsa_evidence": ROOT / "packages/evidence/src/dsa_evidence",
    "dsa_execution": ROOT / "packages/execution/src/dsa_execution",
    "dsa_llm": ROOT / "packages/llm/src/dsa_llm",
    "dsa_mcp": ROOT / "packages/mcp/src/dsa_mcp",
    "dsa_ml": ROOT / "packages/ml/src/dsa_ml",
    "dsa_plugins": ROOT / "packages/plugins/src/dsa_plugins",
    "dsa_reports": ROOT / "packages/reports/src/dsa_reports",
    "dsa_statistics": ROOT / "packages/statistics/src/dsa_statistics",
    "dsa_tools": ROOT / "packages/tools/src/dsa_tools",
    "dsa_viz": ROOT / "packages/visualization/src/dsa_viz",
    "dsa_api": ROOT / "apps/api/src/dsa_api",
    "dsa_jupyter": ROOT / "apps/jupyter/src/dsa_jupyter",
}


def _package_files(base: Path) -> dict[str, bytes]:
    """Map every vendorable file under `base` to its bytes.

    A missing `base` yields an empty map, so comparing a source against a
    vendored copy that was never made is the same comparison as a partial one.
    """
    return {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def _diff(name: str, src: Path, dst: Path) -> str | None:
    """Describe why `dst` is not a faithful copy of `src`, or None if it is."""
    src_files = _package_files(src)
    dst_files = _package_files(dst)
    if src_files == dst_files:
        return None
    shared = set(src_files) & set(dst_files)
    differs = sum(1 for rel in shared if src_files[rel] != dst_files[rel])
    missing = len(set(src_files) - set(dst_files))
    extra = len(set(dst_files) - set(src_files))
    parts = []
    if differs:
        parts.append(f"{differs} file(s) differ")
    if missing:
        parts.append(f"{missing} file(s) absent from _vendor")
    if extra:
        parts.append(f"{extra} file(s) only in _vendor")
    return f"{name}: " + ", ".join(parts)


def sync() -> list[str]:
    VENDOR.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for name, src in sorted(SOURCES.items()):
        if not src.is_dir():
            print(f"WARN: missing source {src}", file=sys.stderr)
            continue
        dst = VENDOR / name
        reason = _diff(name, src, dst)
        if reason is None:
            continue
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        changed.append(name)
    return changed


def check() -> list[str]:
    """Report why `_vendor` is stale. Writes nothing, creates nothing."""
    problems: list[str] = []
    for name, src in sorted(SOURCES.items()):
        dst = VENDOR / name
        if not src.is_dir():
            # sync() cannot repair this, so without a verdict here a module whose
            # source was deleted keeps shipping while --check reports OK.
            if dst.is_dir():
                problems.append(f"{name}: vendored copy has no source to rebuild it from")
            print(f"WARN: missing source {src}", file=sys.stderr)
            continue
        reason = _diff(name, src, dst)
        if reason is not None:
            problems.append(reason)
    vendored: set[str] = set()
    if VENDOR.is_dir():
        vendored = {p.name for p in VENDOR.iterdir() if p.is_dir() and p.name != "__pycache__"}
    orphans = sorted(vendored - set(SOURCES))
    if orphans:
        problems.append(f"no workspace source backs: {', '.join(orphans)}")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync vendored dsa_* modules")
    ap.add_argument(
        "--check",
        action="store_true",
        help="Verify _vendor is in sync without writing (exit 1 if not)",
    )
    args = ap.parse_args()

    if args.check:
        problems = check()
        if problems:
            print(
                "DRIFT: vendored dsa_* differs from its sources (nothing was written).\n"
                "Fix with `python scripts/sync_vendor.py`, then commit the result:",
                file=sys.stderr,
            )
            for reason in problems:
                print(f"  - {reason}", file=sys.stderr)
            sys.exit(1)
        print("OK: vendored dsa_* is in sync")
    else:
        changed = sync()
        if changed:
            print(f"Synced: {', '.join(changed)}")
        else:
            print("Already in sync")


if __name__ == "__main__":
    main()
