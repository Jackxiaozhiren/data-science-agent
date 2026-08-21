#!/usr/bin/env python3
"""Generate SBOM for release/sbom.json (§47) — package, version, license, source."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import tomllib  # py312
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found]

ROOT = Path(__file__).parents[1]
OUT = ROOT / "release" / "sbom.json"


def parse_pyproject_license(path: Path) -> str:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        lic = data.get("project", {}).get("license")
        if isinstance(lic, dict):
            return lic.get("text", "Unknown")
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
        elif current is not None and line.startswith("version =") and "name" in current and "version" not in current:
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


def main() -> None:
    # collect workspace packages
    workspace_pkgs: list[dict[str, str]] = []
    # root version
    try:
        root_data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        root_version = root_data.get("project", {}).get("version", "4.1.0")
    except Exception:
        root_version = "4.1.0"
    root_license = parse_pyproject_license(ROOT / "pyproject.toml")
    workspace_pkgs.append({"name": "data-science-agent", "version": root_version, "license": root_license, "source": "local:pyproject.toml"})
    # workspace members
    for member in ["apps/api", "apps/jupyter", "packages/agent", "packages/datasets", "packages/evaluation", "packages/evidence", "packages/execution", "packages/llm", "packages/mcp", "packages/ml", "packages/plugins", "packages/reports", "packages/statistics", "packages/tools", "packages/visualization"]:
        p = ROOT / member / "pyproject.toml"
        if p.exists():
            try:
                data = tomllib.loads(p.read_text(encoding="utf-8"))
                name = data.get("project", {}).get("name", member)
                version = data.get("project", {}).get("version", "0.1.0")
                lic = parse_pyproject_license(p)
                workspace_pkgs.append({"name": name, "version": version, "license": lic, "source": f"local:{member}"})
            except Exception as e:
                print(f"warn: failed to parse {p}: {e}", file=sys.stderr)
    # uv.lock packages
    locked = parse_uv_lock()
    # Merge: deduplicate by name+version, prefer workspace
    seen: set[tuple[str, str]] = {(p["name"], p["version"]) for p in workspace_pkgs}
    all_pkgs = list(workspace_pkgs)
    for p in locked:
        key = (p["name"], p["version"])
        if key not in seen:
            # try to get license from importlib if installed
            try:
                import importlib.metadata

                meta = importlib.metadata.metadata(p["name"])
                lic = meta.get("License", "Unknown")
                if lic and len(lic) > 80:
                    lic = lic[:80] + "..."
                p["license"] = lic or "Unknown"
            except Exception:
                p["license"] = "Unknown"
            all_pkgs.append(p)
            seen.add(key)
    # Build SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {"component": {"name": "data-science-agent", "version": root_version, "type": "application"}},
        "components": [
            {"name": p["name"], "version": p["version"], "licenses": [{"license": {"id": p["license"]}}] if p["license"] != "Unknown" else [], "purl": f"pkg:pypi/{p['name']}@{p['version']}" if "pypi" in p["source"] else f"pkg:local/{p['name']}@{p['version']}", "source": p["source"]}
            for p in sorted(all_pkgs, key=lambda x: x["name"].lower())
        ],
    }
    # Also simple flat list per §47 spec
    sbom_simple = {
        "version": root_version,
        "generated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "components": [{"package": c["name"], "version": c["version"], "license": (c["licenses"][0]["license"]["id"] if c["licenses"] else "Unknown"), "source": c["source"], "purl": c["purl"]} for c in sbom["components"]],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sbom_simple, indent=2, ensure_ascii=False), encoding="utf-8")
    # Also write full cyclonedx
    (ROOT / "release" / "sbom.cyclonedx.json").write_text(json.dumps(sbom, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SBOM: {len(sbom_simple['components'])} components → {OUT} (plus cyclonedx)")


if __name__ == "__main__":
    main()
