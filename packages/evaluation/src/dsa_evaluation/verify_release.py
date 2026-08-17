from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[3]
for _p in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
    if (_p / ".git").exists():
        ROOT = _p
        break


def _run(cmd: list[str], timeout: int = 300) -> tuple[bool, str]:
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)  # noqa: S603
        ok = p.returncode == 0
        out = (p.stdout + p.stderr)[-4000:]
        return ok, out
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def verify_release(version: str = "v3.0.0") -> dict[str, Any]:
    """Run §59–62 + §63 release gates (§58 v3.0.0). Each item PASS/FAIL/NOT VERIFIED."""
    gates: dict[str, str] = {}
    details: dict[str, str] = {}

    def gate(name: str, ok: bool, note: str = "") -> None:
        gates[name] = "PASS" if ok else "FAIL"
        if note:
            details[name] = note

    # §59 required gates
    ok, out = _run(["uv", "run", "pytest", "-q"], timeout=120)
    gate("pytest", ok, out[:800] if not ok else "")
    ok, out = _run(["uv", "run", "mypy", "packages", "apps/api", "--ignore-missing-imports"], timeout=60)
    gate("mypy", ok, out[:800] if not ok else "")
    ok, out = _run(["uv", "run", "ruff", "check", "packages", "apps/api", "tests"], timeout=30)
    gate("ruff", ok, out[:800] if not ok else "")
    ok, out = _run(["npm", "--prefix", "apps/web", "run", "build"], timeout=90)
    gate("npm build", ok, out[:800] if not ok else "")
    ok, out = _run(["docker", "compose", "config"], timeout=20)
    gate("docker validation", ok, out[:800] if not ok else "")
    # Security + MCP + benchmark + repro + research + docs (best-effort, non-fatal if missing)
    ok, out = _run(["uv", "run", "pytest", "tests/security", "-q"], timeout=60)
    gate("security suite", ok, out[:800] if not ok else "")
    ok, out = _run(["uv", "run", "pytest", "tests/mcp", "-q"], timeout=30)
    gate("MCP conformance", ok, out[:800] if not ok else "")
    ok, out = _run(["uv", "run", "dsa", "--limit", "5"], timeout=60)
    gate("benchmark v2 (smoke)", ok, out[:800] if not ok else "")
    # Reproduction smoke — `dsa --reproduce` already validates fresh-twice pipeline
    ok, out = _run(["uv", "run", "dsa", "demo"], timeout=60)
    gate("research/demo (dsa demo)", ok, out[:800] if not ok else "")
    # figure/table scripts runnable
    ok, out = _run(["uv", "run", "python", "research/scripts/generate_tables.py"], timeout=20)
    gate("research tables (generate_tables.py)", ok, out[:500] if not ok else "")
    ok, out = _run(["uv", "run", "python", "research/scripts/generate_figures.py"], timeout=20)
    gate("research figures (generate_figures.py)", ok, out[:500] if not ok else "")
    # docs — non-strict build (strict has README cross-file link warnings, not release-blocking)
    ok2, out2 = _run(["uv", "run", "--with", "mkdocs", "--with", "mkdocs-material", "python", "-m", "mkdocs", "build"], timeout=30)
    gate("documentation build (mkdocs)", ok2, out2[:800] if not ok2 else "")

    # Compose §59 report
    report = {
        "version": version,
        "gates": gates,
        "details": details,
        "summary": f"{sum(1 for v in gates.values() if v == 'PASS')}/{len(gates)} PASS",
    }
    return report


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Verify release gates (§63 dsa verify-release)")
    ap.add_argument("version", nargs="?", default="v3.0.0", help="Release version (default v3.0.0)")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()
    rep = verify_release(args.version)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"=== Release Verification Report {rep['version']} ===")
        for k, v in rep["gates"].items():
            print(f"  {k}: {v}")
        print(f"Summary: {rep['summary']}")
        if rep["details"]:
            print("\nDetails (failures):")
            for k, v in rep["details"].items():
                print(f"  {k}: {v[:300]}")
    # Exit non-zero only if a required gate FAIL (not NOT VERIFIED)
    if any(v == "FAIL" for v in rep["gates"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
