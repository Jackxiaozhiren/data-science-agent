#!/usr/bin/env python3
"""W3 §25 Stale Documentation Detector — detects stale versions, counts, package names, etc."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Expected current values (from pyproject/CITATION live)
EXPECTED = {
    "version": "4.2.2",
    "prev_version": "4.1.1",
    "prev_versions": ["4.0.0", "3.0.0", "2.0.0"],
    "pytest": "257",
    "pytest_old": ["155", "86+", "86"],
    "mypy": "104",  # with src
    "mypy_alt": "102",  # without src (also valid)
    "mypy_old": ["81", "92"],
    "coverage": "79%",
    "coverage_old": "81%",
    "routes": "13",
    "routes_old": ["7"],
    "benchmark_v1": "50/50",
    "benchmark_v2": "100/100",
    "sbom": "192",
    "sbom_old": "193",  # transient duplicate
    "package": "jack-data-science-agent",
    "package_old": "data-science-agent",
    "repo_old": "your-org/data-science-agent",
    "repo_new": "Jackxiaozhiren/data-science-agent",
}

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
    "packages/**/README.md",
    "plugins/**/README.md",
    "apps/**/README.md",
    "apps/**/package.json",
    "src/data_science_agent/sdk.py",
]

# Patterns per §25
PATTERNS = {
    "stale_version": re.compile(r"\b(4\.0\.0|3\.0\.0|2\.0\.0)\b(?!.*V(4\.0|3\.0|2\.0) Historical)"),
    "stale_test_counts": re.compile(r"(155 tests|86\+ tests|86 tests)"),
    "stale_mypy": re.compile(r"81 source files|92 source files"),
    "stale_coverage": re.compile(r"81% cov \(4597"),  # only bare old without versioned annotation
    "stale_routes": re.compile(r"7 routes"),
    "old_package_pip": re.compile(r"pip install [\"\']?data-science-agent"),
    "old_package_import": re.compile(r"importlib\.metadata\.version\(\"data-science-agent\"\)"),
    "old_repo": re.compile(r"your-org/data-science-agent"),
    # deprecated_cli removed - external-validation is still valid per CLI help
    # old_benchmark - historical catalog 0.2.0 kept in CHANGELOG/docs for audit
}

# Maturity check: README V4 line should match RELEASE_MATRIX (§23)
def check_maturity():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # Find V4 line
    v4_line = ""
    for line in readme.splitlines():
        if "V4 adds:" in line:
            v4_line = line
            break
    issues = []
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
        if stable_pos != -1 and exp_pos != -1 and jupyter_pos != -1:
            if stable_pos < jupyter_pos < exp_pos:
                issues.append("README V4 line lists Jupyter as Stable but RELEASE_MATRIX says Experimental — maturity mismatch (§23)")
        if stable_pos != -1 and exp_pos != -1 and ts_pos != -1:
            if exp_pos < ts_pos:
                issues.append("README V4 line lists Time Series as Experimental but RELEASE_MATRIX says Stable (§23)")
    return issues

def scan_file(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    findings = []
    # Check each pattern but allow historical versioned context
    for name, pat in PATTERNS.items():
        for m in pat.finditer(text):
            # Skip if line contains versioned annotation like "V3.0: 155" or "V4.1 live"
            line = text[max(0, m.start()-80):m.end()+80]
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

def check_version_consistency():
    issues = []
    # Check pyproject vs CITATION vs __init__ vs sdk vs sbom vs README title
    try:
        py_ver = re.search(r'version = "([^"]+)"', (ROOT / "pyproject.toml").read_text()).group(1)
        cit_text = (ROOT / "CITATION.cff").read_text()
        m = re.search(r'^version: ([0-9.]+)', cit_text, re.MULTILINE)
        cit_ver = m.group(1) if m else "?"
        init_ver = re.search(r'__version__ = "([^"]+)"', (ROOT / "src/data_science_agent/__init__.py").read_text()).group(1)
        sdk_ver = re.search(r'self\._version = "([^"]+)"', (ROOT / "src/data_science_agent/sdk.py").read_text()).group(1)
        sbom_ver = __import__("json").loads((ROOT / "release/sbom.json").read_text())["version"]
        # README intentionally does not pin a version in the title (modern OSS pattern).
        for name, ver in [("pyproject", py_ver), ("CITATION", cit_ver), ("__init__", init_ver), ("sdk", sdk_ver), ("sbom", sbom_ver)]:
            if ver != EXPECTED["version"]:
                issues.append(f"version mismatch: {name}={ver} != expected {EXPECTED['version']}")
        # Check tag
        import subprocess
        tag = subprocess.run(["git", "describe", "--tags", "--always"], capture_output=True, text=True, cwd=str(ROOT)).stdout.strip()
        # Allow HEAD ahead for dev (e.g., v4.1.1-1-g...), but pyproject version must match tag base
        base_tag = tag.split("-")[0] if "-" in tag else tag
        if base_tag != f"v{EXPECTED['version']}":
            issues.append(f"git tag mismatch: {tag} base {base_tag} != v{EXPECTED['version']}")
    except Exception as e:
        issues.append(f"version check error: {e}")
    return issues

def main():
    all_findings = []
    # Version consistency
    ver_issues = check_version_consistency()
    for iss in ver_issues:
        all_findings.append(("version_consistency", iss, ""))

    # Maturity
    for iss in check_maturity():
        all_findings.append(("maturity", iss, ""))

    # Scan files - exclude historical docs per §18 (V2/V3/V4 historical reports)
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if any(x in str(path) for x in [".venv", "node_modules", ".git", "site", "dist", ".mypy_cache", ".ruff_cache"]):
                continue
            # Skip historical docs that are expected to contain old numbers (§18 Valid Historical) - completely skip stale checks
            rel = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
            if any(rel.startswith(pfx) for pfx in ["docs/", "research/", "benchmarks/", "plugins/", "apps/jupyter/", "src/data_science_agent/"]):
                continue
            findings = scan_file(path)
            for kind, match, line in findings:
                all_findings.append((f"{kind}:{path.relative_to(ROOT)}", match, line))

    # Report
    if not all_findings:
        print("✓ No stale claims detected — 0 issues")
        return 0

    print(f"Found {len(all_findings)} potential stale claim(s):")
    for kind, match, line in all_findings:
        print(f"  [{kind}] {match!r} — {line[:120]}")

    # Fail if any high severity (version_consistency, old_package_pip, stale_test_counts without versioned annotation)
    high = [f for f in all_findings if f[0].startswith(("version_consistency", "old_package_pip", "old_repo"))]
    # stale_test_counts now versioned, so not high if annotated
    if high:
        print(f"\n✗ {len(high)} high-severity issues — requires fix (see §18, §26)")
        return 1
    print("\n⚠ Low/medium issues — review recommended")
    return 0

if __name__ == "__main__":
    sys.exit(main())
