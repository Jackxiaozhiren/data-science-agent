#!/usr/bin/env python3
"""Generate SBOM for release/sbom.json (§47) — package, version, license, source."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]
OUT = ROOT / "release" / "sbom.json"


def parse_pyproject_license(path: Path) -> str:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        lic = data.get("project", {}).get("license")
        if isinstance(lic, dict):
            text = lic.get("text", "Unknown")
            return text if isinstance(text, str) else "Unknown"
        if isinstance(lic, str):
            return lic
        return "Unknown"
    except Exception:
        return "Unknown"


def parse_uv_lock() -> list[dict[str, str]]:
    lock = ROOT / "uv.lock"
    if not lock.exists():
        return []
    text = lock.read_text(encoding="utf-8")
    # naive parse: find [[package]] blocks
    packages: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        line = line.strip()
        if line == "[[package]]":
            if current:
                packages.append(current)
            current = {}
        elif current is not None and line.startswith("name ="):
            m = re.search(r'"([^"]+)"', line)
            if m:
                current["name"] = m.group(1)
        elif (
            current is not None
            and line.startswith("version =")
            and "name" in current
            and "version" not in current
        ):
            m = re.search(r'"([^"]+)"', line)
            if m:
                current["version"] = m.group(1)
        elif current is not None and "source" in line and "registry" in line:
            m = re.search(r'"([^"]+)"', line)
            if m:
                current["source"] = m.group(1)
    if current and "name" in current:
        packages.append(current)
    # enrich source default
    for p in packages:
        p.setdefault("source", "https://pypi.org/simple")
        p.setdefault("license", "Unknown")
        p.setdefault("version", "unknown")
    return packages


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate or verify the release SBOM (§47)")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write both SBOM files into DIR instead of release/ (keeps a check run off the tracked copy)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="verify release/sbom.json still matches the dependency set, and write nothing",
    )
    args = ap.parse_args()
    sbom, sbom_simple = build_sboms()

    if args.check:
        return _verify(sbom_simple)

    out_dir = args.out or OUT.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    simple_path = out_dir / "sbom.json"
    simple_path.write_text(json.dumps(sbom_simple, indent=2, ensure_ascii=False), encoding="utf-8")
    # Also write full cyclonedx
    (out_dir / "sbom.cyclonedx.json").write_text(
        json.dumps(sbom, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"SBOM: {len(sbom_simple['components'])} components → {simple_path} (plus cyclonedx)")
    return 0


#: The fields a check compares. `generated` is a wall-clock stamp and `license` is a lookup against
#: PyPI that improves between runs, so neither is a claim about what this revision depends on;
#: (package, version) is, and that is the claim a published SBOM makes.
def _pairs(sbom: dict) -> set[tuple[str, str]]:
    return {(c["package"], c["version"]) for c in sbom["components"]}


def _verify(sbom_simple: dict) -> int:
    committed_path = ROOT / "release" / "sbom.json"
    if not committed_path.is_file():
        print(f"SBOM CHECK FAIL: {committed_path} does not exist", file=sys.stderr)
        return 1
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    derived, on_disk = _pairs(sbom_simple), _pairs(committed)
    missing = sorted(f"{p}@{v}" for p, v in derived - on_disk)
    stale = sorted(f"{p}@{v}" for p, v in on_disk - derived)
    if missing or stale:
        print(
            f"SBOM CHECK FAIL: {len(derived)} components derived from this revision, "
            f"{len(on_disk)} on disk",
            file=sys.stderr,
        )
        if missing:
            print(f"  not in the committed SBOM: {', '.join(missing)}", file=sys.stderr)
        if stale:
            print(
                f"  in the committed SBOM but not in this revision: {', '.join(stale)}",
                file=sys.stderr,
            )
        return 1
    if committed.get("version") != sbom_simple.get("version"):
        print(
            f"SBOM CHECK FAIL: committed SBOM declares release {committed.get('version')!r}, "
            f"this revision declares {sbom_simple.get('version')!r}",
            file=sys.stderr,
        )
        return 1
    print(
        f"SBOM CHECK OK: {len(derived)} components and release "
        f"{sbom_simple.get('version')!r} match this revision (license fields and the generated stamp "
        "are not compared)"
    )
    return 0


def build_sboms() -> tuple[dict, dict]:
    # collect workspace packages
    workspace_pkgs: list[dict[str, str]] = []
    # root version
    try:
        root_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        root_version = root_data.get("project", {}).get("version", "4.1.0")
    except Exception:
        root_version = "4.1.0"
    root_license = parse_pyproject_license(ROOT / "pyproject.toml")
    workspace_pkgs.append(
        {
            "name": "jack-data-science-agent",
            "version": root_version,
            "license": root_license,
            "source": "local:pyproject.toml",
        }
    )
    # workspace members
    for member in [
        "apps/api",
        "apps/jupyter",
        "packages/agent",
        "packages/datasets",
        "packages/evaluation",
        "packages/evidence",
        "packages/execution",
        "packages/llm",
        "packages/mcp",
        "packages/ml",
        "packages/plugins",
        "packages/reports",
        "packages/statistics",
        "packages/tools",
        "packages/visualization",
    ]:
        p = ROOT / member / "pyproject.toml"
        if p.exists():
            try:
                data = tomllib.loads(p.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name", member)
                version = data.get("project", {}).get("version", "0.1.0")
                lic = parse_pyproject_license(p)
                workspace_pkgs.append(
                    {"name": name, "version": version, "license": lic, "source": f"local:{member}"}
                )
            except Exception as e:
                print(f"warn: failed to parse {p}: {e}", file=sys.stderr)
    # uv.lock packages
    locked = parse_uv_lock()
    # Merge: deduplicate by name+version, prefer workspace
    seen: set[tuple[str, str]] = {(p["name"], p["version"]) for p in workspace_pkgs}
    all_pkgs = list(workspace_pkgs)
    for pkg in locked:
        key = (pkg["name"], pkg["version"])
        if key not in seen:
            # try to get license from importlib if installed
            try:
                import importlib.metadata

                meta = importlib.metadata.metadata(pkg["name"])
                lic = meta.get("License", "Unknown")
                if lic and len(lic) > 80:
                    lic = lic[:80] + "..."
                pkg["license"] = lic or "Unknown"
            except Exception:
                pkg["license"] = "Unknown"
            all_pkgs.append(pkg)
            seen.add(key)
    # Build SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "component": {
                "name": "jack-data-science-agent",
                "version": root_version,
                "type": "application",
            }
        },
        "components": [
            {
                "name": pkg["name"],
                "version": pkg["version"],
                "licenses": [{"license": {"id": pkg["license"]}}]
                if pkg["license"] != "Unknown"
                else [],
                "purl": f"pkg:pypi/{pkg['name']}@{pkg['version']}"
                if "pypi" in pkg["source"]
                else f"pkg:local/{pkg['name']}@{pkg['version']}",
                "source": pkg["source"],
            }
            for pkg in sorted(all_pkgs, key=lambda x: x["name"].lower())
        ],
    }
    # Also simple flat list per §47 spec
    sbom_simple = {
        "version": root_version,
        "generated": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
        "components": [
            {
                "package": c["name"],
                "version": c["version"],
                "license": (c["licenses"][0]["license"]["id"] if c["licenses"] else "Unknown"),
                "source": c["source"],
                "purl": c["purl"],
            }
            for c in sbom["components"]
        ],
    }
    return sbom, sbom_simple


if __name__ == "__main__":
    raise SystemExit(main())
