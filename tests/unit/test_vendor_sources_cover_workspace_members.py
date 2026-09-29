"""`sync_vendor.SOURCES` must cover the workspace members exactly, in both directions.

Nothing cross-checked the hand-maintained list: `grep -rln "uv.workspace" tests/ scripts/ .github/`
returned no hits, and `tests/unit/test_vendor_parity.py` parametrises over the same list, so a
package added to `[tool.uv.workspace] members` would simply never be vendored -- it would still
build, still test green, and still be absent from the published wheel. Recorded as L7-AR-07.

The join key is each member's own ``[tool.hatch.build.targets.wheel] packages`` entry, not its
directory name or its distribution name: `dsa-visualization` ships the import package `dsa_viz`,
so normalising `-`/`_` is necessary but not sufficient.

This is not the invariant ``capabilities.memberWithoutArtifactCopy`` already holds. That key
compares members against whatever directories exist under `_vendor` on disk, so a package copied
in by hand passes it while remaining invisible to the repair tool -- which is exactly how a
vendored copy can go stale forever with every gate green.
"""

from __future__ import annotations

import importlib.util
import tomllib
from glob import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _collector():
    spec = importlib.util.spec_from_file_location(
        "sync_vendor_probe", ROOT / "scripts/sync_vendor.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _member_import_names() -> set[str]:
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["uv"][
        "workspace"
    ]["members"]
    names: set[str] = set()
    seen_dirs = 0
    for pattern in declared:
        for member in sorted(glob(pattern)):
            manifest = Path(member) / "pyproject.toml"
            if not manifest.is_file():
                continue
            seen_dirs += 1
            targets = (
                tomllib.loads(manifest.read_text(encoding="utf-8"))
                .get("tool", {})
                .get("hatch", {})
                .get("build", {})
                .get("targets", {})
                .get("wheel", {})
                .get("packages", [])
            )
            assert targets, f"member {member} declares no wheel packages, so the join key is absent"
            for entry in targets:
                names.add(Path(str(entry)).name)
    assert seen_dirs == len(declared), (
        f"a member glob matched nothing: resolved {seen_dirs} of {len(declared)} declared patterns"
    )
    return names


def _diff(sources: set[str], members: set[str]) -> tuple[list[str], list[str]]:
    return sorted(members - sources), sorted(sources - members)


def test_sources_and_members_agree_in_both_directions() -> None:
    sources = set(_collector().SOURCES)
    members = _member_import_names()
    assert members and sources, "one side resolved empty, so equality below proves nothing"
    only_members, only_sources = _diff(sources, members)
    assert not only_members, f"workspace members vendored by nobody: {only_members}"
    assert not only_sources, f"_vendor copies with no workspace member behind them: {only_sources}"


def test_the_comparison_can_fail() -> None:
    """Green-on-arrival guard, so the mechanism is proven here rather than assumed.

    Removing one entry from the SOURCES set must surface exactly that package as a member nobody
    vendors; if the diff comes back empty, the main assertion is comparing nothing.
    """
    sources = set(_collector().SOURCES)
    members = _member_import_names()
    victim = sorted(sources & members)[0]
    shrunk = set(sources)
    shrunk.discard(victim)
    only_members, only_sources = _diff(shrunk, members)
    assert only_members == [victim], (
        f"dropping {victim} from SOURCES was not detected; diff reported {only_members}"
    )
    assert only_sources == [], "the synthetic removal created a phantom in the other direction"
