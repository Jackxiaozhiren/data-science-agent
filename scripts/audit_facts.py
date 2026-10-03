"""Measure repository debt and reconciliation facts from the working tree, at runtime.

The exit code is the product. Nothing here renders prose or issues verdicts: a
capability probe reports only a contradiction between two measured facts, and the
reader decides what it means.

Modes, in ascending order of consequence:

    audit_facts.py              print the derived snapshot
    audit_facts.py --write      snapshot to the gitignored path
    audit_facts.py --seed       write current readings as ceilings (deliberate)
    audit_facts.py --check      exit 1 and name every violated key
    audit_facts.py --ratchet-from <path>   swap the limits file (testing only)

Constraints, each because breaking one caused a real failure here:

* stdlib only, no network, sub-second, and **no writes outside ``docs/audit/``**.
* **No subprocess.** ``scripts/`` sits inside the ``S`` (bandit) ruleset with no
  per-file-ignore, so a ``git`` call here is an S603/S607 finding waiting to be
  filed. Git position therefore comes from the plumbing files, and worktree
  staleness is mtime-derived: informational, never a ceiling.
* **The instrument never measures itself** (``SELF``). On first authoring this
  file's own regex literals scored as the repository's entire debt-marker count,
  and it listed itself as an unwired checker. A device that indicts its own
  source seeds ceilings out of noise.
* Installed versions come from distribution metadata, never a declared range: a
  range is intent, and the intent/fact gap is its own bug class.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
import sys
import time
from importlib import metadata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "audit" / "facts.snapshot.json"
LIMITS = ROOT / "docs" / "audit" / "facts.limits.json"
SELF = Path(__file__).name

#: Trees the scanner walks. Deliberately narrow: the working tree also holds
#: generated output and third-party bulk that must never be attributed to this
#: project, and walking it from the root would read gigabytes.
SCANNED = ("packages", "apps", "src", "tests", "scripts", "docs", ".github")
#: Shipped code only -- debt counters must not charge tests or docs for markers.
SHIPPED = ("packages", "apps", "src", "scripts")
SKIP_DIRS = frozenset(
    {
        "_vendor",
        "__pycache__",
        "node_modules",
        ".venv",
        "dist",
        "site",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".workspace",
    }
)
PY_SUFFIX = (".py",)
TEXT_SUFFIX = (".py", ".md", ".yml", ".yaml", ".json", ".ts", ".tsx")

TODO_RE = re.compile(r"\b(?:TODO|FIXME|HACK|XXX)\b")
SKIP_MARK_RE = re.compile(r"pytest\.mark\.(?:skip|xfail)")
SUPPRESSION_RE = re.compile(r"#\s*(?:noqa|type:\s*ignore)")
DOC_LINK_RE = re.compile(r":\s*([A-Za-z0-9_./-]+\.md)")
PROMPT_DOC_RE = re.compile(r"^[A-Z][A-Z_]*_(?:PROMPT|SPEC)\.md$")
LEDGER_DOC_RE = re.compile(r"^AUDIT_LEDGER\.md$")
TEST_DEF_RE = re.compile(r"^\s*(?:async\s+)?def test_", re.M)

#: Keys that may carry a ceiling or floor, with the debt each one guards. Never
#: auto-collect by prefix: a key that rises with legitimate work reddens the gate
#: within a week, and the gate gets disabled instead.
CEILING_KEYS: dict[str, str] = {
    "debt.todoMarkers": "debt comments left in shipped code",
    "debt.pytestSkipXfail": "tests silenced instead of fixed",
    "debt.suppressionDirectives": "lint and type suppressions in shipped code",
    "debt.swallowedExceptionSites": "handlers whose whole body is pass/continue/an ellipsis",
    "debt.exceptHandlers": "exception handlers in shipped code, any shape",
    "debt.unwiredCheckers": "checker scripts that no workflow invokes",
    "debt.auditApparatusLines": "prompt/spec documents an audit series keeps rewriting",
    "debt.governanceFilesMissing": "required policy files absent",
    "capabilities.packagesWithoutManifest": "package dirs that are not workspace members",
    "capabilities.memberWithoutArtifactCopy": "source packages shipped by no installed wheel",
    "capabilities.artifactCopyWithoutMember": "vendored copies whose source is gone",
    "capabilities.navDanglingEntries": "nav entries naming a file that is absent",
    "capabilities.navOrphanPages": "docs pages referenced by no nav entry",
    "capabilities.entrypointsWithoutTarget": "console scripts whose module cannot resolve",
}
FLOOR_KEYS: dict[str, str] = {
    "debt.testFunctions": "tests may only be added, never quietly deleted",
}

#: Measured and printed, but deliberately NOT ceilings. A key that can never fire
#: in the pipeline it appears to protect produces only local false reds --
#: including from the act of writing this file -- so its cost is carried by the
#: audit process instead of a gate. Recorded here so nobody re-adds them.
EXCLUDED_KEYS: dict[str, str] = {
    "git.filesTouchedSinceLastCommit": "always 0 on a clean checkout; can never fire in CI",
    "git.head": "not a quantity",
    "runtime.*": "versions legitimately rise on upgrade; guarding them blocks upgrading",
    "capabilities.sourceFiles": "grows whenever anyone writes code",
    "capabilities.largestSourceFiles": "array length is constant by construction",
    "debt.coveragePercent": "already machine-checked by pytest's fail_under -- no second source",
    "debt.lintFindings": "already machine-checked by ruff -- no second source",
    "debt.typeErrors": "already machine-checked by mypy -- no second source",
    "debt.unparseableShippedFiles": (
        "measured so a skipped file is never silent, within the pass that can skip one: a "
        "file is parsed only if its text contains `except`, so this counts handler-shaped "
        "files that could not be read or parsed. A shipped .py that does not parse is "
        "already a red pytest, ruff and mypy -- all three parse every file -- and gating a "
        "duplicate here would crash the collector where it should report"
    ),
    "debt.ledgerLines": (
        "the ledger is append-only session record that §N10 mandates; gating it makes honest "
        "bookkeeping illegal -- measured for the ratio check, reviewed, never auto-failed"
    ),
    "warnings.contradictions": (
        "a composite counter: adding any new probe would trip it with no debt change, so the "
        "individual contradiction keys are gated and this total is only reviewed"
    ),
    "capabilities.untestedCallbacks": (
        "L8's candidate key: 'shapes a test names' needs a semantic judgement the collector "
        "cannot make from syntax alone, so a count here would be a proxy that can be satisfied "
        "without guarding anything -- adjudicated per dependency instead"
    ),
    "debt.markdownPercentClaims": (
        "counts ordinary prose percentages too, so it is too coarse to guard; L5 adjudicates"
    ),
    "debt.yieldSites": (
        "a bare yield count is not a cleanup defect; that class needs the finally block read"
        " per site, which a generic probe cannot assert honestly"
    ),
}

_WALK_CACHE: dict[tuple[tuple[str, ...], tuple[str, ...]], list[Path]] = {}


def _read(path: Path) -> str:
    """Return a file's text, or empty when it is absent or unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _walk(*roots: str, suffixes: tuple[str, ...]) -> list[Path]:
    """Collect files under the named roots, skipping generated and vendored bulk.

    Prunes during traversal rather than filtering after: ``rglob`` would first
    descend into ``node_modules`` and the vendored mirror, and that is what
    pushed the first implementation past the sub-second promise in this file's
    own docstring. Memoised, because several groups need the same trees.
    """
    key = (roots, suffixes)
    if key not in _WALK_CACHE:
        found: list[Path] = []
        for rel in roots:
            base = ROOT / rel
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for name in sorted(filenames):
                    path = Path(dirpath) / name
                    if path.suffix in suffixes and path.name != SELF:
                        found.append(path)
        _WALK_CACHE[key] = found
    return _WALK_CACHE[key]


def _lines_of(paths: list[Path]) -> list[str]:
    """Every line of every file, reading each file exactly once."""
    lines: list[str] = []
    for path in paths:
        lines.extend(_read(path).splitlines())
    return lines


#: Memoised on the file list, because `_collect_debt` needs three views of one parse and
#: the sub-second promise in this file's docstring is load-bearing: it is why the ratchet
#: can sit before the test suite instead of after it.
_SHAPES_CACHE: dict[tuple[Path, ...], tuple[int, int, list[Path]]] = {}


def _hides_failure(body: list[ast.stmt]) -> bool:
    """True when a handler's whole body is something that cannot report anything.

    `pass`, `continue`, and a bare expression (an ellipsis or a lone docstring) are the
    shapes that end a failure with no trace. A re-raise is deliberately not one of them:
    the line-shaped counter this replaced charged a handler that raises the same as one
    that swallows, and charged a comment or a variable name containing the substring
    "except" as well (audit §90, and `tests/unit/test_debt_ratchet.py` pins the ratio).
    """
    if not body:
        return True
    if all(isinstance(node, ast.Pass) for node in body):
        return True
    if all(isinstance(node, ast.Continue) for node in body):
        return True
    return all(isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) for node in body)


def _except_shapes(paths: list[Path]) -> tuple[int, int, list[Path]]:
    """Parse `paths` once and return (handlers, handlers that hide, files not parsed).

    The third element exists because a counter that quietly skips a file it cannot read
    or parse reports less debt rather than fewer files, which is the hole §90 was written
    to close. The skip stays visible as `debt.unparseableShippedFiles`.
    """
    key = tuple(paths)
    if key in _SHAPES_CACHE:
        return _SHAPES_CACHE[key]
    handlers = 0
    hidden = 0
    unparsed: list[Path] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            unparsed.append(path)
            continue
        if "except" not in text:
            # Conservative prefilter, and it cannot lose a handler: every ast.ExceptHandler
            # needs the `except` token in its own source. Parsing all 128 shipped files cost
            # +0.195s, which pushed this collector past the sub-second promise its module
            # docstring makes -- and that promise is why the ratchet runs before the tests.
            continue
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError):
            unparsed.append(path)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                handlers += 1
                if _hides_failure(node.body):
                    hidden += 1
    result = (handlers, hidden, unparsed)
    _SHAPES_CACHE[key] = result
    return result


def _handler_shapes(paths: list[Path]) -> tuple[int, int]:
    """(every handler, the ones that can only hide a failure) over `paths`."""
    handlers, hidden, _ = _except_shapes(paths)
    return handlers, hidden


def _unparseable_shipped_files(paths: list[Path]) -> list[Path]:
    """Shipped files the shape pass could not read or parse, so the skip is on record."""
    return _except_shapes(paths)[2]


def _git_dir() -> Path:
    """Locate the git directory, following a worktree-style pointer file."""
    dot = ROOT / ".git"
    if dot.is_dir():
        return dot
    pointer = _read(dot)
    if pointer.startswith("gitdir:"):
        return (ROOT / pointer.removeprefix("gitdir:").strip()).resolve()
    return dot


def _git_position() -> dict[str, Any]:
    """Resolve HEAD and branch from plumbing files, and staleness from mtimes."""
    git = _git_dir()
    raw = _read(git / "HEAD").strip()
    head = ""
    branch = "(detached)"
    if raw.startswith("ref:"):
        ref_name = raw.removeprefix("ref:").strip()
        branch = ref_name.removeprefix("refs/heads/")
        head = _read(git / ref_name).strip() or _packed_ref(git, ref_name)
    else:
        head = raw
    stamp = 0.0
    if head:
        try:
            stamp = (git / raw.removeprefix("ref:").strip()).stat().st_mtime
        except OSError:
            stamp = 0.0
    touched = 0
    if stamp:
        for path in _walk(*SCANNED, suffixes=TEXT_SUFFIX):
            try:
                if path.stat().st_mtime > stamp:
                    touched += 1
            except OSError:
                continue
    return {
        "head": head or "(unreadable)",
        "branch": branch,
        "tagCount": len(_list_tags(git)),
        "commitStampAgeDays": round((time.time() - stamp) / 86400, 1) if stamp else None,
        "filesTouchedSinceLastCommit": touched,
    }


def _packed_ref(git: Path, ref_name: str) -> str:
    for line in _read(git / "packed-refs").splitlines():
        if line.endswith(f" {ref_name}"):
            return line.split(" ", 1)[0]
    return ""


def _list_tags(git: Path) -> list[str]:
    loose: list[str] = []
    base = git / "refs" / "tags"
    if base.is_dir():
        loose = [p.name for p in sorted(base.iterdir()) if p.is_file()]
    packed = re.findall(r"refs/tags/([^\s^]+)", _read(git / "packed-refs"))
    return sorted({*loose, *packed})


def _workspace_members() -> list[str]:
    """Declared workspace member directories, read from the members list."""
    match = re.search(r"members\s*=\s*\[([^\]]*)\]", _read(ROOT / "pyproject.toml"), re.S)
    return re.findall(r"['\"]([^'\"]+)['\"]", match.group(1)) if match else []


def _source_package_dirs(member_dir: Path) -> list[str]:
    """The import packages a member directory actually ships."""
    src = member_dir / "src"
    if not src.is_dir():
        return []
    return [p.name for p in sorted(src.iterdir()) if (p / "__init__.py").is_file()]


def _checker_scripts() -> list[Path]:
    """Scripts presenting themselves as gates: named ``check_*`` or offering ``--check``."""
    checkers = []
    for path in sorted((ROOT / "scripts").glob("*.py")):
        if path.name == SELF:
            continue
        if path.name.startswith("check_") or "--check" in _read(path):
            checkers.append(path)
    return checkers


def _wired_names() -> str:
    """Everything the pipeline or a manifest can invoke, as one haystack."""
    blob = _read(ROOT / ".pre-commit-config.yaml") + _read(ROOT / "pyproject.toml")
    blob += _read(ROOT / "package.json")
    for extra in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        blob += _read(extra)
    return blob


def _unwired_checkers() -> list[str]:
    """Gates that exist but nothing runs: a written-but-never-run checker is S1."""
    wired = _wired_names()
    return [
        f"scripts/{path.name}"
        for path in _checker_scripts()
        if path.name not in wired and path.stem not in wired
    ]


def _missing_governance_files() -> list[str]:
    required = ("SECURITY.md", "GOVERNANCE.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md")
    return [name for name in required if not (ROOT / name).is_file()]


def _volume(pattern: re.Pattern[str]) -> int:
    """Line count of root-level markdown whose name matches `pattern`."""
    return sum(
        len(_read(path).splitlines())
        for path in sorted(ROOT.glob("*.md"))
        if pattern.match(path.name)
    )


def _collect_debt() -> dict[str, Any]:
    shipped_paths = _walk(*SHIPPED, suffixes=PY_SUFFIX)
    shipped = _lines_of(shipped_paths)
    tests = _lines_of(_walk("tests", "apps", suffixes=PY_SUFFIX))
    handlers, hidden, unparsed = _except_shapes(shipped_paths)
    return {
        "todoMarkers": sum(len(TODO_RE.findall(line)) for line in shipped),
        "pytestSkipXfail": sum(len(SKIP_MARK_RE.findall(line)) for line in tests),
        "suppressionDirectives": sum(len(SUPPRESSION_RE.findall(line)) for line in shipped),
        "exceptHandlers": handlers,
        "swallowedExceptionSites": hidden,
        "unparseableShippedFiles": len(unparsed),
        "unwiredCheckers": len(_unwired_checkers()),
        "governanceFilesMissing": len(_missing_governance_files()),
        "auditApparatusLines": _volume(PROMPT_DOC_RE),
        "ledgerLines": _volume(LEDGER_DOC_RE),
        "testFunctions": sum(1 for line in tests if TEST_DEF_RE.match(line)),
    }


def _dangling_entrypoints() -> list[str]:
    """Console scripts whose target module cannot be located in their own project."""
    dangling: list[str] = []
    projects = [ROOT] + [ROOT / m for m in _workspace_members() if (ROOT / m).is_dir()]
    for project in projects:
        block = re.search(
            r"\[project\.scripts\](.*?)(?:^\[|\Z)", _read(project / "pyproject.toml"), re.S | re.M
        )
        if not block:
            continue
        for name, target in re.findall(r'^(\S+)\s*=\s*["\']([^"\']+)["\']', block.group(1), re.M):
            module = target.split(":")[0].replace(".", "/")
            resolved = any(
                (base / f"{module}.py").is_file() or (base / module / "__init__.py").is_file()
                for base in (project / "src", project)
            )
            if not resolved:
                dangling.append(f"{project.relative_to(ROOT)}:{name} -> {target}")
    return dangling


def _collect_capabilities() -> dict[str, Any]:
    members = _workspace_members()
    missing_dirs = [m for m in members if not (ROOT / m).is_dir()]
    member_leaf_names = {m.split("/")[-1] for m in members}
    packages_dir = ROOT / "packages"
    # Only a directory that ships Python can be a workspace package. Without this,
    # packages/artifacts/ -- gitignored output the test suite itself writes -- was
    # counted as a package lacking a manifest, so any local `pytest` run turned the
    # ratchet red for a reason that had nothing to do with debt.
    packages_without_manifest = [
        f"packages/{path.name}"
        for path in (sorted(packages_dir.iterdir()) if packages_dir.is_dir() else [])
        if path.is_dir()
        and path.name not in member_leaf_names
        and not (path / "pyproject.toml").is_file()
        and any(path.rglob("*.py"))
    ]

    mirror = ROOT / "src" / "data_science_agent" / "_vendor"
    artifact_names = (
        {p.name for p in sorted(mirror.iterdir()) if (p / "__init__.py").is_file()}
        if mirror.is_dir()
        else set()
    )
    source_names: set[str] = set()
    for member in members:
        source_names.update(_source_package_dirs(ROOT / member))

    nav = {entry for entry in DOC_LINK_RE.findall(_read(ROOT / "mkdocs.yml"))}
    docs_dir = ROOT / "docs"
    disk = (
        {str(p.relative_to(docs_dir)) for p in docs_dir.rglob("*.md")}
        if docs_dir.is_dir()
        else set()
    )
    largest = sorted(
        (
            {"path": str(p.relative_to(ROOT)), "lines": len(_read(p).splitlines())}
            for p in _walk(*SHIPPED, suffixes=PY_SUFFIX)
        ),
        key=lambda item: item["lines"],
        reverse=True,
    )[:10]

    return {
        "membersMissingFromDisk": missing_dirs,
        "packagesWithoutManifest": packages_without_manifest,
        "memberWithoutArtifactCopy": sorted(source_names - artifact_names),
        "artifactCopyWithoutMember": sorted(artifact_names - source_names),
        "navDanglingEntries": sorted(entry for entry in nav if entry not in disk),
        "navOrphanPages": sorted(page for page in disk if page not in nav),
        "entrypointsWithoutTarget": _dangling_entrypoints(),
        "largestSourceFiles": largest,
        "sourceFiles": len(_walk(*SHIPPED, suffixes=(".py", ".ts", ".tsx"))),
    }


def _which(name: str) -> str:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def _collect_runtime() -> dict[str, Any]:
    installed: dict[str, str] = {}
    for dist in ("pydantic", "fastapi", "langgraph", "duckdb", "polars", "numpy"):
        try:
            installed[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            installed[dist] = "(not installed)"
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "uvOnPath": bool(_which("uv")),
        "nodeOnPath": bool(_which("node")),
        "installed": installed,
    }


def _contradictions(
    capabilities: dict[str, Any], debt: dict[str, Any], git: dict[str, Any]
) -> list[str]:
    """One id per measured contradiction. Never a judgement about whether it matters."""
    found: list[str] = []
    for group in (
        "membersMissingFromDisk",
        "packagesWithoutManifest",
        "memberWithoutArtifactCopy",
        "artifactCopyWithoutMember",
        "navDanglingEntries",
        "entrypointsWithoutTarget",
    ):
        if capabilities[group]:
            found.append(f"{group}:{len(capabilities[group])}")
    for group, count in (
        ("unwiredCheckers", debt["unwiredCheckers"]),
        ("governanceFilesMissing", debt["governanceFilesMissing"]),
        ("navOrphanPages", len(capabilities["navOrphanPages"])),
    ):
        if count:
            found.append(f"{group}:{count}")
    if debt["todoMarkers"] or debt["pytestSkipXfail"] or debt["suppressionDirectives"]:
        found.append("selfReportedDebt")
    if git["head"] == "(unreadable)":
        found.append("gitHeadUnreadable")
    return found


def collect_facts() -> dict[str, Any]:
    """Measure every fact. Writes nothing."""
    git = _git_position()
    runtime = _collect_runtime()
    debt = _collect_debt()
    capabilities = _collect_capabilities()
    warnings = _contradictions(capabilities, debt, git)
    return {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git": git,
        "runtime": runtime,
        "debt": debt,
        "capabilities": capabilities,
        "warnings": {"contradictions": warnings},
        "meta": {"collector": f"scripts/{SELF}", "scannedRoots": list(SCANNED)},
    }


def numeric_leaves(obj: Any, prefix: str = "") -> dict[str, int]:
    """Flatten to dotted integer keys; arrays count by length.

    Strings are skipped deliberately: runtime versions are not quantities, and
    comparing them numerically would seed nonsense ceilings from a version bump.
    """
    out: dict[str, int] = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            dot = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                out[dot] = int(value)
            elif isinstance(value, (list, tuple, set)):
                out[dot] = len(value)
            elif isinstance(value, dict):
                out.update(numeric_leaves(value, dot))
    return out


def evaluate_ratchet(facts: dict[str, Any], limits: dict[str, Any] | None) -> dict[str, Any]:
    """Compare readings with the ledger. A named-but-unmeasured key is a violation.

    A key the ledger guards that nothing measures any more is a silent no-op,
    which is worse than a red gate: it reports protection that has been removed.
    """
    leaves = numeric_leaves(facts)
    violations: list[dict[str, Any]] = []
    for key, maximum in (limits or {}).get("ceiling", {}).items():
        if key not in leaves:
            violations.append({"key": key, "kind": "ceiling", "problem": "key_no_longer_measured"})
        elif leaves[key] > maximum:
            violations.append(
                {
                    "key": key,
                    "kind": "ceiling",
                    "problem": "debt_grew",
                    "actual": leaves[key],
                    "limit": maximum,
                }
            )
    for key, minimum in (limits or {}).get("floor", {}).items():
        if key not in leaves:
            violations.append({"key": key, "kind": "floor", "problem": "key_no_longer_measured"})
        elif leaves[key] < minimum:
            violations.append(
                {
                    "key": key,
                    "kind": "floor",
                    "problem": "guard_shrank",
                    "actual": leaves[key],
                    "limit": minimum,
                }
            )
    return {"violations": violations, "leaves": leaves}


def _seed(facts: dict[str, Any]) -> int:
    leaves = numeric_leaves(facts)
    unmeasured = [key for key in CEILING_KEYS if key not in leaves]
    if unmeasured:
        print(f"seed: these keys are not measured: {', '.join(unmeasured)}")
        return 1
    ceiling = {key: leaves[key] for key in CEILING_KEYS}
    floor = {key: leaves[key] for key in FLOOR_KEYS if key in leaves}
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    preserved: dict[str, Any] = {}
    if LIMITS.is_file():
        previous = json.loads(_read(LIMITS) or "{}")
        preserved = {k: v for k, v in previous.items() if k.endswith("Note")}
    payload = {
        "_seededAt": facts["generatedAt"],
        "_seededAtHead": facts["git"]["head"],
        "_keys": CEILING_KEYS,
        "_floorKeys": FLOOR_KEYS,
        "_excluded": EXCLUDED_KEYS,
        **preserved,
        "ceiling": ceiling,
        "floor": floor,
    }
    LIMITS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"seeded {len(ceiling)} ceiling and {len(floor)} floor keys")
    if preserved:
        print(f"preserved human-authored fields: {', '.join(sorted(preserved))}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write the gitignored snapshot")
    mode.add_argument("--seed", action="store_true", help="write current readings as ceilings")
    mode.add_argument("--check", action="store_true", help="exit 1 if any key breaches its limit")
    parser.add_argument("--ratchet-from", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    facts = collect_facts()
    if args.seed:
        return _seed(facts)
    if args.check:
        path = args.ratchet_from or LIMITS
        try:
            limits = json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            print(f"limits file missing at {path.name} - run --seed first")
            return 1
        report = evaluate_ratchet(facts, limits)
        for violation in report["violations"]:
            actual = violation.get("actual", "absent")
            print(
                f"{violation['kind']} {violation['key']}: actual={actual} ({violation['problem']})"
            )
        if report["violations"]:
            print(f"facts ratchet: {len(report['violations'])} violation(s)")
            return 1
        print("facts ratchet: OK")
        return 0

    payload = json.dumps(facts, indent=2, sort_keys=True)
    if args.write:
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {SNAPSHOT.relative_to(ROOT)}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
