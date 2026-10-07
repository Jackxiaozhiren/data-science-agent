#!/usr/bin/env python3
"""Sync the vendored dsa_* modules from their workspace source.

The published wheel `jack-data-science-agent` bundles the dsa_* sub-packages
under `src/data_science_agent/_vendor/` (so `pip install` works without
publishing 15 separate distributions). This script copies the current source
from `packages/*/src` and `apps/*/src` into `_vendor`, keeping the vendored
copies in sync with the source of truth.

Repair with `--package NAME` or `--file SRC_PATH` and commit the result whenever
a dsa_* module changes. A bare run is refused: `--all` copies whatever the source
tree currently holds, which in a shared worktree means another session's
uncommitted work lands in the mirror that ships inside the published wheel.
CI runs this with `--check`, which compares without writing: an auditor that
repairs what it audits cannot report what it found.
"""

from __future__ import annotations

import argparse
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


def _named(names: list[str], limit: int = 12) -> str:
    """The file names behind a count, bounded so a wide drift stays readable."""
    shown = names[:limit]
    tail = f", +{len(names) - len(shown)} more" if len(names) > len(shown) else ""
    return "[" + ", ".join(shown) + tail + "]"


def _diff(name: str, src: Path, dst: Path) -> str | None:
    """Describe why `dst` is not a faithful copy of `src`, or None if it is.

    The counts alone were not enough (§127.1): a CI line reading `dsa_agent: 1 file(s) differ` sends
    whoever reads it into a manual comparison of every file in the package, at the moment they are
    already diagnosing a red build. Each category names its files, bounded.
    """
    src_files = _package_files(src)
    dst_files = _package_files(dst)
    if src_files == dst_files:
        return None
    shared = set(src_files) & set(dst_files)
    differing = sorted(rel for rel in shared if src_files[rel] != dst_files[rel])
    missing = sorted(set(src_files) - set(dst_files))
    extra = sorted(set(dst_files) - set(src_files))
    parts = []
    if differing:
        parts.append(f"{len(differing)} file(s) differ {_named(differing)}")
    if missing:
        parts.append(f"{len(missing)} file(s) absent from _vendor {_named(missing)}")
    if extra:
        parts.append(f"{len(extra)} file(s) only in _vendor {_named(extra)}")
    return f"{name}: " + ", ".join(parts)


def _repair_package(name: str, src: Path) -> list[str]:
    """Make `_vendor/<name>` a byte-exact copy of its source, one file at a time.

    Deliberately not `rmtree` + `copytree`: replacing a whole directory is what made an
    unscoped repair able to swallow another session's uncommitted source, and a directory
    wipe also destroys the evidence of which file actually changed.
    """
    dst = VENDOR / name
    src_files = _package_files(src)
    dst_files = _package_files(dst)
    actions: list[str] = []
    for rel in sorted(
        set(src_files) - set(dst_files)
        | {r for r in set(src_files) & set(dst_files) if src_files[r] != dst_files[r]}
    ):
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(src_files[rel])
        actions.append(f"{name}/{rel}")
    for rel in sorted(set(dst_files) - set(src_files)):
        (dst / rel).unlink()
        actions.append(f"{name}/{rel} (removed: gone from source)")
    return actions


def _owning_package(rel_path: str) -> tuple[str, Path, Path] | None:
    """Resolve a source path to (package, package dir, path inside it), or None.

    Resolved and containment-checked rather than string-prefixed, so `../../` escapes cannot
    name a file inside a package.
    """
    candidate = Path(rel_path)
    target = (ROOT / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    for name, base in SOURCES.items():
        root = base.resolve()
        if root == target.parent or root in target.parents:
            return name, root, target.relative_to(root)
    return None


def _repair_file(rel_path: str) -> list[str]:
    owner = _owning_package(rel_path)
    if owner is None:
        raise ValueError(f"not inside any workspace source package: {rel_path}")
    name, base, inner = owner
    if not (base / inner).is_file():
        raise ValueError(f"no such source file: {rel_path}")
    dst = VENDOR / name / inner
    data = (base / inner).read_bytes()
    if dst.is_file() and dst.read_bytes() == data:
        return []
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return [f"{name}/{inner.as_posix()}"]


def sync() -> list[str]:
    VENDOR.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []
    for name, src in sorted(SOURCES.items()):
        if not src.is_dir():
            print(f"WARN: missing source {src}", file=sys.stderr)
            continue
        if _diff(name, src, VENDOR / name) is None:
            continue
        changed.extend(_repair_package(name, src))
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
    ap.add_argument(
        "--package",
        action="append",
        default=[],
        metavar="NAME",
        help="Repair only this package (repeatable). The intended mode: an unscoped repair "
        "copies whatever the source tree holds, including another session's uncommitted work.",
    )
    ap.add_argument(
        "--file",
        action="append",
        default=[],
        metavar="SRC_PATH",
        dest="files",
        help="Repair exactly this source file (repeatable), e.g. "
        "packages/agent/src/dsa_agent/graph.py",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="Repair every drifted package. Bulk write; use only on a tree you own entirely.",
    )
    args = ap.parse_args()

    if args.check:
        problems = check()
        if problems:
            drifted = sorted({p.split(":", 1)[0].strip() for p in problems})
            scoped = " ".join(f"--package {name}" for name in drifted) or "--package NAME"
            print(
                "DRIFT: vendored dsa_* differs from its sources (nothing was written).\n"
                f"Repair only what you changed: `python scripts/sync_vendor.py {scoped}`\n"
                "`--all` repairs every drifted package and will copy another session's "
                "uncommitted source into _vendor; a bare run is refused for that reason.",
                file=sys.stderr,
            )
            for reason in problems:
                print(f"  - {reason}", file=sys.stderr)
            sys.exit(1)
        print("OK: vendored dsa_* is in sync")
        return

    if args.all:
        VENDOR.mkdir(parents=True, exist_ok=True)
        actions = sync()
    elif args.package or args.files:
        VENDOR.mkdir(parents=True, exist_ok=True)
        actions = []
        try:
            for name in args.package:
                src = SOURCES.get(name)
                if src is None or not src.is_dir():
                    raise ValueError(f"unknown or source-less package: {name}")
                actions.extend(_repair_package(name, src))
            for rel_path in args.files:
                actions.extend(_repair_file(rel_path))
        except ValueError as exc:
            print(f"REFUSED: {exc} (nothing was written)", file=sys.stderr)
            sys.exit(2)
    else:
        print(
            "REFUSED: a bare run repairs every drifted package, which silently adopts work that "
            "is not yours -- the mirror ships in the published wheel.\n"
            "Name what you changed: --package NAME (repeatable) or --file SRC_PATH "
            "(repeatable); use --all only on a tree you own entirely. --check audits.",
            file=sys.stderr,
        )
        sys.exit(2)

    if actions:
        print("Wrote: " + ", ".join(actions))
    else:
        print("Already in sync")


if __name__ == "__main__":
    main()
