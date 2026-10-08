#!/usr/bin/env python3
"""W3 §25 Stale Documentation Detector — detects stale versions, counts, package names, etc."""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Only `version` is read, by check_version_consistency(). The test-count, mypy,
# coverage, route and SBOM figures that used to sit here were never referenced --
# the patterns below hard-code their own literals instead -- so listing them read
# as live expectations while nothing compared against them.
EXPECTED = {
    "version": "4.4.0",
}

# Build/dependency trees that never carry a public claim. `.workspace` is the vendored DataSciBench
# clone (with its own venv and MetaGPT checkout: 6,590 files under benchmarks/ alone, of which 16
# are upstream READMEs), so it belongs with node_modules rather than with this repository's prose.
# `.next/` joined in §133 for the reason the others should have been read: the gate counted 50 files
# here and 46 in CI, the difference being four `apps/web/.next/**/package.json` build artefacts that
# `apps/**/package.json` matches and `git ls-files` does not contain. A test now requires the whole
# surface to be tracked, so a generated tree cannot re-enter it unnoticed.
NOISE_SUBSTRINGS = [
    ".venv",
    "node_modules",
    ".git",
    "site",
    "dist",
    ".mypy_cache",
    ".ruff_cache",
    ".workspace",
    ".next/",
]

# Paths whose whole purpose is to quote superseded numbers: migration guides, release-integrity
# reports, and SDK docstrings labelling maturity as "Stable since 4.0.0". They cannot simply be
# scanned -- PATTERNS has no notion of negation, and every match it produces across them is a
# reference to a superseded release rather than a false claim. Skipping them is the lesser error,
# but it also means "0 issues" describes a smaller surface than SCAN_GLOBS advertises, so the
# skipped set is counted and printed by scan_scope() rather than left invisible. No figure for that
# surface is typed here: the first version of this comment asserted "34 matches, 0 of them real",
# measured against a rule set §76 later retired, and nothing recomputed the number since.
#
# §113 removed `benchmarks/` from this list. The freeze document under it is current-tense product
# prose -- it tells a reader what a PR must not regress today -- and tests/test_automation_scripts.py
# now fails if an entry here names a tree no SCAN_GLOBS pattern can reach, which is exactly how
# `benchmarks/` and `research/` sat here while the checker never opened either.
#
# §130 applied that same reasoning to `docs/`, which was the list's biggest entry by reach: 47
# markdown files under `docs/` matched SCAN_GLOBS and every one was classified as a historical record,
# including `getting-started.md`, `api.md`, `security.md` and `security/VERIFY_RELEASE.md` -- the pages
# a user follows to install, reproduce and verify a release today. Exempting the whole tree is the
# lesser error only if the checker says so: "0 issues" described 19 files while SCAN_GLOBS advertised
# 66. What is genuinely a dated record is now exempted by name -- the v4.3 evidence archive, the
# generated release announcements, and the ADRs, each superseded-by-design rather than stale -- and
# each of those three is asserted to still match a file the checker can reach. `docs/audit/` was the
# tempting fourth exemption and is deliberately absent: it matches no markdown at all, so declaring it
# would have recreated the dead-prefix defect §113 found. The widened net cost no suppression: 50
# files scanned, 54 skipped, and all four rules still report zero findings.
HISTORICAL_PREFIXES = [
    "docs/v4_3/",
    "docs/announcements/",
    "docs/ADR/",
    "research/",
    "plugins/",
    "apps/jupyter/",
    "src/data_science_agent/",
]

# Files to scan (public surfaces §24)
SCAN_GLOBS = [
    "README.md",
    "pyproject.toml",
    "CITATION.cff",
    "CHANGELOG.md",
    "ROADMAP.md",
    "mkdocs.yml",
    "SECURITY.md",
    "docs/**/*.md",
    "research/**/*.md",
    "benchmarks/**/README.md",
    "packages/**/README.md",
    "plugins/**/README.md",
    "apps/**/README.md",
    "apps/**/package.json",
    "src/data_science_agent/sdk.py",
]


def scan_scope(root: Path = ROOT) -> tuple[list[Path], list[Path]]:
    """Split SCAN_GLOBS matches into (scanned, skipped-as-historical)."""
    scanned: list[Path] = []
    skipped: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in root.glob(pattern):
            if any(x in str(path) for x in NOISE_SUBSTRINGS):
                continue
            if any(str(path.relative_to(root)).startswith(p) for p in HISTORICAL_PREFIXES):
                skipped.append(path)
            else:
                scanned.append(path)
    return scanned, skipped


# --- currency claims (§16 drift class) -------------------------------------------
#
# `stale_version` used to be `\b(4\.0\.0|3\.0\.0|2\.0\.0)\b`: a hand-maintained blacklist of
# three retired releases, blind to every later one -- including the `v4.3.0` still advertised as
# the current release. Broadening it to "any released version that is not current" was measured
# and rejected: over the scanned surface that rule fires 160 times, 150 of them CHANGELOG release
# records, plus `cff-version: 1.2.0` (a metadata format number colliding with a tag), a
# `references:` entry citing 4.2.0, and the sub-apps' own `0.1.0`.
#
# So the rule is structural instead: a table of places where a document *asserts* which release
# is current or upcoming. A new currency surface has to be added here to be checked at all,
# which is the honest cost of having no false positives.


def released_versions(root: Path = ROOT) -> set[str]:
    """Release-line versions from git refs, normalised and without peeled duplicates.

    Read from the ref files directly: `scripts/` is under bandit's S rules, so shelling out to
    git is not available here.
    """
    git = root / ".git"
    packed = git / "packed-refs"
    refs: set[str] = set()
    if packed.is_file():
        refs.update(re.findall(r"refs/tags/([^\s^]+)", packed.read_text(encoding="utf-8")))
    loose = git / "refs" / "tags"
    if loose.is_dir():
        refs.update(p.name for p in loose.iterdir() if p.is_file())
    return {r[1:] if r.startswith("v") else r for r in refs}


def current_version(root: Path = ROOT) -> str:
    match = re.search(
        r'__version__ = "([^"]+)"',
        (root / "src/data_science_agent/__init__.py").read_text(encoding="utf-8"),
    )
    return match.group(1) if match else ""


# file, pattern with a `version` group, the claim it makes, and whether answering it needs the
# tag set (an "already released?" question does; "is this the current one?" does not).
CURRENCY_ASSERTIONS = [
    (
        "README.md",
        re.compile(r"\[\*\*v(?P<version>\d+\.\d+\.\d+)\*\*\]"),
        "advertised as the current release",
        False,
    ),
    (
        "ROADMAP.md",
        re.compile(r"next (?:minor |major )?release through \[v(?P<version>\d+\.\d+\.\d+)"),
        "named as the next release",
        True,
    ),
]


def currency_degradations(root: Path = ROOT) -> list[str]:
    """Name any currency assertion the checker could not evaluate, so silence is never a pass."""
    if not current_version(root):
        return []
    if not released_versions(root):
        skipped = [
            f"{rel} ({claim})" for rel, _p, claim, needs_tags in CURRENCY_ASSERTIONS if needs_tags
        ]
        return [f"no tags in this checkout: cannot test {', '.join(skipped)}"]
    return []


def require_released_tags(root: Path = ROOT) -> str | None:
    """Refuse a degraded run: with no refs, half the currency rules have no verdict at all.

    `currency_degradations()` exists so a shallow local checkout still yields the badge verdict
    plus an honest caveat. In CI a caveat nobody reads is the D-L1-05 failure mode again -- a gate
    that prints a pass while its strongest assertion never ran -- so the flag turns the caveat
    into a non-zero exit.
    """
    if not current_version(root):
        return "no declared version readable in this checkout: the version rules cannot run"
    released = released_versions(root)
    if not released:
        return " ".join(currency_degradations(root)) or "no release tags readable"
    return None


def check_currency_claims(root: Path = ROOT) -> list[str]:
    """Flag documents that assert a superseded release as current, or a shipped one as upcoming."""
    issues: list[str] = []
    current = current_version(root)
    released = released_versions(root)
    if not current:
        # With no current version there is nothing to compare against at all: report that rather
        # than returning an empty list, which a caller cannot tell apart from "found nothing".
        return [f"currency check disabled: no current version resolved under {root}"]
    for rel_path, pattern, claim, needs_tags in CURRENCY_ASSERTIONS:
        if needs_tags and not released:
            continue
        path = root / rel_path
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in pattern.finditer(line):
                version = match.group("version")
                if version == current:
                    continue
                if needs_tags:
                    if version not in released:
                        continue  # an unreleased version is exactly what "the next release" means
                    problem = "that release already exists"
                else:
                    problem = "which it is not"
                issues.append(
                    f"{rel_path}:{lineno} cites {version!r}, {claim}, {problem} (current {current})"
                )
    return issues


# --- measurement claims ----------------------------------------------------------
#
# Four rules used to sit in PATTERNS as hand-typed numbers -- `155 tests|86+ tests|86 tests`,
# `81 source files|92 source files`, `81% cov (4597`, `7 routes`. Measured over the scanned
# surface they carry no live coverage: their only remaining hits are inside `CHANGELOG.md`, where
# quoting a superseded figure is the file's purpose, so every one of them is a false positive.
# Meanwhile the repository's single real claim of this shape -- `apps/vscode/README.md:83`,
# "uv run pytest tests/vscode -v  # 6 tests" against seven `def test_` in that directory -- was
# invisible to them. A measurement in prose is now checked by re-measuring.

MEASURE_CLAIM = re.compile(r"pytest\s+(?P<target>[\w./-]+)[^#\n]*#\s*(?P<count>\d+)\s+tests\b")
_COLLECTOR = Path(__file__).with_name("audit_facts.py")
_TEST_DEF_RE: re.Pattern[str] | None = None


def _test_def_re() -> re.Pattern[str]:
    """The collector's own definition of a test function, so one rule owns the number."""
    global _TEST_DEF_RE
    if _TEST_DEF_RE is None:
        spec = importlib.util.spec_from_file_location("audit_facts_for_measure", _COLLECTOR)
        if spec is None or spec.loader is None:  # pragma: no cover - packaging guard
            raise RuntimeError(f"cannot load the shared rule from {_COLLECTOR}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _TEST_DEF_RE = module.TEST_DEF_RE
    return _TEST_DEF_RE


def _count_test_defs(root: Path, target: str) -> int | None:
    base = (root / target).resolve()
    root_resolved = root.resolve()
    if root_resolved != base and root_resolved not in base.parents:
        return None  # the named target escapes the tree; nothing to compare
    if base.is_file():
        files = [base]
    elif base.is_dir():
        files = sorted(base.rglob("*.py"))
    else:
        return None
    rule = _test_def_re()
    total = 0
    for path in files:
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        total += sum(1 for line in text.splitlines() if rule.match(line))
    return total


def measurement_claims(root: Path = ROOT) -> list[tuple[str, int, str, int]]:
    """Locate every scanned line that names a pytest target and asserts a test count."""
    found: list[tuple[str, int, str, int]] = []
    for path in scan_scope(root)[0]:
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
        ):
            match = MEASURE_CLAIM.search(line)
            if match:
                found.append(
                    (
                        str(path.relative_to(root)),
                        lineno,
                        match.group("target"),
                        int(match.group("count")),
                    )
                )
    return found


def measurement_claims_evaluated(root: Path = ROOT) -> int:
    return len(measurement_claims(root))


def check_measurement_claims(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    for rel, lineno, target, claimed in measurement_claims(root):
        actual = _count_test_defs(root, target)
        if actual is None:
            issues.append(
                f"{rel}:{lineno} counts tests in {target!r}, but that path is absent -- "
                "the claim cannot be verified"
            )
        elif actual != claimed:
            issues.append(
                f"{rel}:{lineno} claims {claimed} tests for {target!r}; the tree defines {actual}"
            )
    return issues


# Patterns per §25
PATTERNS = {
    "old_package_pip": re.compile(r"pip install [\"\']?data-science-agent"),
    "old_package_import": re.compile(r"importlib\.metadata\.version\(\"data-science-agent\"\)"),
    "old_repo": re.compile(r"your-org/data-science-agent"),
    # deprecated_cli removed - external-validation is still valid per CLI help
    # old_benchmark - historical catalog 0.2.0 kept in CHANGELOG/docs for audit
}


# Maturity check: README V4 line should match RELEASE_MATRIX (§23)
def check_maturity() -> list[str]:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Find V4 line
    v4_line = ""
    for line in readme.splitlines():
        if "V4 adds:" in line:
            v4_line = line
            break
    issues: list[str] = []
    if not v4_line:
        return issues
    # Check: Stable should contain Time Series, Experimental should contain Jupyter
    # Use simple: if Jupyter appears before "Experimental" marker in v4_line, it's in Stable (wrong)
    # Correct is: Stable ... Time Series ... · Experimental ... Jupyter
    if "Jupyter" in v4_line:
        # Find positions
        stable_pos = v4_line.find("Stable")
        exp_pos = v4_line.find("Experimental")
        jupyter_pos = v4_line.find("Jupyter")
        ts_pos = v4_line.find("Time Series")
        if (
            stable_pos != -1
            and exp_pos != -1
            and jupyter_pos != -1
            and stable_pos < jupyter_pos < exp_pos
        ):
            issues.append(
                "README V4 line lists Jupyter as Stable but RELEASE_MATRIX says Experimental — maturity mismatch (§23)"
            )
        if stable_pos != -1 and exp_pos != -1 and ts_pos != -1 and exp_pos < ts_pos:
            issues.append(
                "README V4 line lists Time Series as Experimental but RELEASE_MATRIX says Stable (§23)"
            )
    return issues


#: Finding prefixes that fail the run. Everything else is printed and exits 0, so a
#: rule added here is the only way to make it a gate rather than a notice (§96).
HIGH_SEVERITY_PREFIXES = (
    "version_consistency",
    "currency_claims",
    "measurement_claims",
    "old_package_pip",
    "old_repo",
    "unreadable_file",
)


def scan_file(path: Path) -> list[tuple[str, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        # D-L3-08: this returned [] before, so a scanned file that could not be read
        # subtracted itself from the gate's scope while the gate still reported clean.
        return [("unreadable_file", f"{type(exc).__name__}: {exc}", str(path))]
    findings: list[tuple[str, str, str]] = []
    # Check each pattern but allow historical versioned context
    for name, pat in PATTERNS.items():
        for m in pat.finditer(text):
            # Skip if line contains versioned annotation like "V3.0: 155" or "V4.1 live"
            line = text[max(0, m.start() - 80) : m.end() + 80]
            # Allow historical in CHANGELOG and report docs
            if path.name == "CHANGELOG.md":
                continue  # CHANGELOG historical versions are expected per §18
            if "MIGRATION" in str(path) or "migration.md" in str(path):
                continue  # Migration guides intentionally mention old versions
            if "V4_1_RELEASE_INTEGRITY_REPORT" in str(path):
                continue
            if "QUANTITATIVE_CLAIMS" in str(path):
                continue
            if "V4.1 live" in line or "V3.0:" in line or "V1:" in line or "Historical" in line:
                continue
            # For old package, allow in POPULAR_PYPI typosquat list and report
            if "POPULAR_PYPI" in line or "WORKSPACE_PACKAGES" in line:
                continue
            if "your-org" in line and "report" in str(path).lower():
                continue
            findings.append((name, m.group(0), line.strip()[:120]))
    return findings


def _is_release_candidate_ref(version: str) -> bool:
    """Allow a frozen release branch to lead the latest tag before final tagging.

    On pull_request runs GitHub exposes the source branch as GITHUB_HEAD_REF;
    on branch pushes it is GITHUB_REF_NAME. The exception is deliberately narrow:
    only release/v<expected>-rc or release/v<expected>-rcN is accepted.
    (Ported from origin/main during the 4.3.2 lineage merge.)
    """
    ref = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or ""
    return bool(re.fullmatch(rf"release/v{re.escape(version)}-rc\d*", ref))


def _first_group(pattern: str, path: Path) -> str:
    """Read `path` and return the first capture group, or "?" if the pattern is absent.

    A missing pattern is reported as `?=4.4.0` by the caller rather than raising:
    an AttributeError here used to be swallowed by the blanket handler below, which
    silently retired all five version checks instead of reporting one.
    """
    match = re.search(pattern, path.read_text(encoding="utf-8"))
    return match.group(1) if match else "?"


def check_version_consistency() -> list[str]:
    issues: list[str] = []
    # Check pyproject vs CITATION vs __init__ vs sdk vs sbom vs README title
    try:
        py_ver = _first_group(r'version = "([^"]+)"', ROOT / "pyproject.toml")
        cit_text = (ROOT / "CITATION.cff").read_text()
        m = re.search(r"^version: ([0-9.]+)", cit_text, re.MULTILINE)
        cit_ver = m.group(1) if m else "?"
        init_ver = _first_group(
            r'__version__ = "([^"]+)"', ROOT / "src/data_science_agent/__init__.py"
        )
        sdk_ver = _first_group(
            r'self\._version = "([^"]+)"', ROOT / "src/data_science_agent/sdk.py"
        )
        sbom_ver = __import__("json").loads((ROOT / "release/sbom.json").read_text())["version"]
        # README intentionally does not pin a version in the title (modern OSS pattern).
        for name, ver in [
            ("pyproject", py_ver),
            ("CITATION", cit_ver),
            ("__init__", init_ver),
            ("sdk", sdk_ver),
            ("sbom", sbom_ver),
        ]:
            if ver != EXPECTED["version"]:
                issues.append(f"version mismatch: {name}={ver} != expected {EXPECTED['version']}")
        # Check tag
        import shutil
        import subprocess

        _git = shutil.which("git") or "git"
        tag = subprocess.run(  # noqa: S603 - fixed args, no shell, no untrusted input
            [_git, "describe", "--tags", "--always"], capture_output=True, text=True, cwd=str(ROOT)
        ).stdout.strip()
        # Allow HEAD ahead for dev (e.g., v4.1.1-1-g...), but pyproject version must match tag base
        base_tag = tag.split("-")[0] if "-" in tag else tag
        if base_tag != f"v{EXPECTED['version']}" and not _is_release_candidate_ref(
            EXPECTED["version"]
        ):
            issues.append(f"git tag mismatch: {tag} base {base_tag} != v{EXPECTED['version']}")
    except Exception as e:
        issues.append(f"version check error: {e}")
    return issues


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="W3 §25 stale documentation detector")
    parser.add_argument(
        "--require-released-tags",
        action="store_true",
        help="exit non-zero when the checkout exposes no release tags, so CI cannot report a pass "
        "for a currency rule that never had a verdict",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    opts = _parse_args(argv)
    if opts.require_released_tags:
        refusal = require_released_tags()
        if refusal:
            print(f"✗ {refusal} (high severity: the rule would report a pass it never tested)")
            return 1

    all_findings = []
    # Version consistency
    ver_issues = check_version_consistency()
    for iss in ver_issues:
        all_findings.append(("version_consistency", iss, ""))

    # Maturity
    for iss in check_maturity():
        all_findings.append(("maturity", iss, ""))

    for iss in check_currency_claims():
        all_findings.append(("currency_claims", iss, ""))

    for iss in check_measurement_claims():
        all_findings.append(("measurement_claims", iss, ""))

    # Scan files, minus the historical prefixes scan_scope() documents.
    scanned, skipped = scan_scope()
    for path in scanned:
        for kind, match, line in scan_file(path):
            all_findings.append((f"{kind}:{path.relative_to(ROOT)}", match, line))

    degraded = currency_degradations()
    scope = f"scanned {len(scanned)} file(s); {len(skipped)} skipped as historical"
    if degraded:
        scope += "; " + "; ".join(degraded)
    # Report
    if not all_findings:
        print(f"✓ No stale claims detected — 0 issues ({scope})")
        return 0

    print(f"Found {len(all_findings)} potential stale claim(s) ({scope}):")
    for kind, match, line in all_findings:
        print(f"  [{kind}] {match!r} — {line[:120]}")

    # Fail if any high severity (see HIGH_SEVERITY_PREFIXES; stale_test_counts is now
    # versioned, so it is not high when annotated)
    high = [f for f in all_findings if f[0].startswith(HIGH_SEVERITY_PREFIXES)]
    if high:
        print(f"\n✗ {len(high)} high-severity issues — requires fix (see §18, §26)")
        return 1
    print("\n⚠ Low/medium issues — review recommended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
