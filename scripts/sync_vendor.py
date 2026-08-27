#!/usr/bin/env python3
"""Sync the vendored dsa_* modules from their workspace source.

The published wheel `jack-data-science-agent` bundles the dsa_* sub-packages
under `src/data_science_agent/_vendor/` (so `pip install` works without
publishing 15 separate distributions). This script copies the current source
from `packages/*/src` and `apps/*/src` into `_vendor`, keeping the vendored
copies in sync with the source of truth.

Run `python scripts/sync_vendor.py` and commit the result whenever a dsa_*
module changes. CI runs this with `--check` to catch drift.
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


def sync() -> list[str]:
    VENDOR.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for name, src in sorted(SOURCES.items()):
        if not src.is_dir():
            print(f"WARN: missing source {src}", file=sys.stderr)
            continue
        dst = VENDOR / name
        # Compare file set (excluding __pycache__) to decide if anything changed.
        src_files = {p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        dst_files = {p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        if src_files == dst_files and not changed:
            # same file names — check content hashes
            same = True
            for rel in src_files:
                s = (src / rel).read_bytes()
                d = (dst / rel).read_bytes() if (dst / rel).is_file() else b""
                if s != d:
                    same = False
                    break
            if same:
                continue
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        changed.append(name)
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description="Sync vendored dsa_* modules")
    ap.add_argument("--check", action="store_true", help="Verify _vendor is in sync (exit 1 if not)")
    args = ap.parse_args()

    # Snapshot current state
    before: dict[str, bytes] = {}
    for name in SOURCES:
        dst = VENDOR / name
        for p in dst.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                before[(name, p.relative_to(dst).as_posix())] = p.read_bytes()

    changed = sync()

    after: dict[str, bytes] = {}
    for name in SOURCES:
        dst = VENDOR / name
        for p in dst.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                after[(name, p.relative_to(dst).as_posix())] = p.read_bytes()

    if args.check:
        if before == after:
            print("OK: vendored dsa_* is in sync")
        else:
            print("DRIFT: vendored dsa_* differs from source — run `python scripts/sync_vendor.py`", file=sys.stderr)
            sys.exit(1)
    else:
        if changed:
            print(f"Synced: {', '.join(changed)}")
        else:
            print("Already in sync")


if __name__ == "__main__":
    main()
