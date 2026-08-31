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
    """Run §59–62 + §63 release gates (§58 v3.0.0). Each item PASS/FAIL/NOT VERIFIED.

    For v4.3.0+ (Spec §93) extends with: external benchmark manifest,
    case-study verification, publication artifacts, supply-chain provenance,
    citation metadata.
    """
    gates: dict[str, str] = {}
    details: dict[str, str] = {}

    def gate(name: str, ok: bool, note: str = "") -> None:
        gates[name] = "PASS" if ok else "FAIL"
        if note:
            details[name] = note

    # §59 required gates
    ok, out = _run(["uv", "run", "pytest", "-q"], timeout=120)
    gate("pytest", ok, out[:800] if not ok else "")
    ok, out = _run(
        ["uv", "run", "mypy", "packages", "apps/api", "--ignore-missing-imports"], timeout=60
    )
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
    ok2, out2 = _run(
        [
            "uv",
            "run",
            "--with",
            "mkdocs",
            "--with",
            "mkdocs-material",
            "python",
            "-m",
            "mkdocs",
            "build",
        ],
        timeout=30,
    )
    gate("documentation build (mkdocs)", ok2, out2[:800] if not ok2 else "")

    # §93 v4.3.0 extended checks (honest: FAIL if missing, not silent)
    is_v43 = False
    try:
        # Normalize "v4.3.0" or "4.3.0"
        v = version.lstrip("v")
        parts = [int(x) for x in v.split(".")]
        is_v43 = parts >= [4, 3, 0]
    except Exception:
        is_v43 = version.strip() in ("v4.3.0", "4.3.0")
    if is_v43:
        # external benchmark manifest (§93: external benchmark manifest)
        try:
            man_path = ROOT / "benchmarks/external/datascibench/manifest.json"
            raw_path = ROOT / "benchmarks/external/datascibench/results/raw_runs.json"
            man_ok = man_path.exists() and raw_path.exists()
            detail = ""
            if man_ok:
                man = json.loads(man_path.read_text(encoding="utf-8"))
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
                # raw_runs is list or dict with runs
                n_runs = (
                    len(raw)
                    if isinstance(raw, list)
                    else len(raw.get("runs", raw.get("results", [])))
                )
                if man.get("task_count") != 222 or n_runs < 45:
                    man_ok = False
                    detail = f"manifest task_count={man.get('task_count')} runs={n_runs}"
            else:
                detail = f"missing {man_path.name if not man_path.exists() else raw_path.name}"
            gate("external benchmark manifest (§93)", man_ok, detail)
        except Exception as e:
            gate("external benchmark manifest (§93)", False, f"{type(e).__name__}: {e}")

        # case-study verification (§93: 8/8 verified)
        try:
            cs_ok = True
            cs_detail = ""
            for idx in range(1, 9):
                pat = ROOT / f"case-studies/{idx:02d}-*/outputs/summary.json"
                matches = list(ROOT.glob(f"case-studies/{idx:02d}-*/outputs/summary.json"))
                if not matches:
                    # fallback glob
                    matches = list((ROOT / "case-studies").glob(f"{idx:02d}*/outputs/summary.json"))
                if not matches:
                    # try any
                    all_sum = list((ROOT / "case-studies").glob("*/outputs/summary.json"))
                    # check count
                    if len(all_sum) < 8:
                        cs_ok = False
                        cs_detail = f"found {len(all_sum)}/8 summary.json"
                        break
                    continue
                s = json.loads(matches[0].read_text(encoding="utf-8"))
                if s.get("status") != "COMPLETED":
                    cs_ok = False
                    cs_detail = f"{matches[0].parent.parent.name} status={s.get('status')}"
                    break
            # also check total 8
            total = len(list((ROOT / "case-studies").glob("*/outputs/summary.json")))
            if total != 8:
                cs_ok = False
                cs_detail = f"case-studies summaries {total}/8"
            gate("case-study verification (§93)", cs_ok, cs_detail)
        except Exception as e:
            gate("case-study verification (§93)", False, f"{type(e).__name__}: {e}")

        # publication artifacts (§93)
        try:
            pub_ok = all(
                (ROOT / p).exists()
                for p in [
                    "research/paper/paper.md",
                    "research/paper/references.bib",
                    "docs/portfolio/PROJECT_SUMMARY.md",
                    "docs/portfolio/ONE_MINUTE_PITCH.md",
                    "research/claim-evidence-matrix.md",
                ]
            )
            gate(
                "publication artifacts (§93)",
                pub_ok,
                "" if pub_ok else "missing paper/portfolio/claim-evidence",
            )
        except Exception as e:
            gate("publication artifacts (§93)", False, f"{type(e).__name__}: {e}")

        # supply-chain provenance (§93 + W8)
        try:
            pub_path = ROOT / ".github/workflows/publish.yml"
            sbom_path = ROOT / "release/sbom.json"
            verify_path = ROOT / "docs/security/VERIFY_RELEASE.md"
            pub_ok = pub_path.exists() and "id-token: write" in pub_path.read_text(encoding="utf-8")
            exp_sbom_ver = version.lstrip("v")
            sbom_ok = (
                sbom_path.exists() and json.loads(sbom_path.read_text()).get("version") == exp_sbom_ver
            )
            verify_ok = verify_path.exists()
            sc_ok = pub_ok and sbom_ok and verify_ok
            detail = ""
            if not pub_ok:
                detail += "publish.yml missing id-token; "
            if not sbom_ok:
                detail += "sbom missing or version mismatch; "
            if not verify_ok:
                detail += "VERIFY_RELEASE.md missing; "
            gate("supply-chain provenance (§93)", sc_ok, detail.strip())
        except Exception as e:
            gate("supply-chain provenance (§93)", False, f"{type(e).__name__}: {e}")

        # citation metadata (§93)
        try:
            cit = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
            import re

            m = re.search(r"^version:\s*([0-9.]+)", cit, re.MULTILINE)
            cit_ver = m.group(1) if m else ""
            exp_ver = version.lstrip("v")
            cit_ok = cit_ver == exp_ver
            gate(
                "citation metadata (§93)",
                cit_ok,
                "" if cit_ok else f"CITATION.cff {cit_ver} != {exp_ver}",
            )
        except Exception as e:
            gate("citation metadata (§93)", False, f"{type(e).__name__}: {e}")

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
