"""§133: the claims gate must read the files the repository ships, not whatever a build left behind.

Found while confirming §132 against the runner. CI's own log says `0 issues (scanned 46 file(s); 54
skipped as historical)`; the same command in this working tree said **50** scanned. The four extra
matches are `apps/web/.next/**/package.json` -- Next.js build output, caught by the `apps/**/package.json`
pattern, present locally because a `next build` ran here and absent in CI because the checkout has no
`.next/` (and the gate runs before any build step). Today they carry only `{"type": "module"}`, so no
finding came from them, but the gate's denominator was already a function of whether someone had built
the web app on this machine: a generated manifest that ever carries a `version` would move the verdict
between two vantages of the same commit.

This is the same class §113 and §130 dealt with for `HISTORICAL_PREFIXES`: a scope list whose reach is
assumed rather than measured. The invariant that closes it is checkable from either vantage -- every file
the gate opens must be a file `git` tracks.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_public_claims.py"


def _checker(root: Path):
    spec = importlib.util.spec_from_file_location(
        "check_public_claims_under_test", str(root / "scripts" / "check_public_claims.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tracked(root: Path) -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return {line for line in out.stdout.splitlines() if line}


def test_the_gates_surface_is_a_subset_of_the_tracked_tree() -> None:
    """Every file the gate opens has to be one the repository ships.

    This is what makes local and CI read the same surface: CI checks out tracked files, so anything
    untracked is a vantage-dependent extra.
    """
    scanned, _skipped = _checker(ROOT).scan_scope(ROOT)

    tracked = _tracked(ROOT)
    extra = sorted(
        str(p.relative_to(ROOT)) for p in scanned if str(p.relative_to(ROOT)) not in tracked
    )
    assert extra == [], f"the gate reads files no commit contains: {extra}"


def test_a_generated_build_manifest_is_not_part_of_the_surface(tmp_path: Path) -> None:
    """The `.next/` tree is build output, so a version in it must not reach the version rule.

    Built from a scratch tree rather than the live one: CI has no `.next/`, so a case that read this
    machine's build directory would be green in one vantage and unrunnable in the other.
    """
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    (script_dir / "check_public_claims.py").write_bytes(SCRIPT.read_bytes())
    shipped = tmp_path / "apps" / "web"
    shipped.mkdir(parents=True)
    (shipped / "package.json").write_text(
        json.dumps({"name": "dsa-web", "version": "4.4.0"}), "utf-8"
    )
    generated = shipped / ".next" / "dev"
    generated.mkdir(parents=True)
    (generated / "package.json").write_text(
        json.dumps({"type": "module", "version": "0.0.1"}), "utf-8"
    )

    scanned, _skipped = _checker(tmp_path).scan_scope(tmp_path)
    names = {str(p.relative_to(tmp_path)) for p in scanned}

    assert "apps/web/package.json" in names, names
    assert "apps/web/.next/dev/package.json" not in names, (
        "build output is inside the gate's surface, so its file count depends on whether a build ran"
    )
