from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[3]
for _p in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
    if (_p / ".git").exists():
        ROOT = _p
        break

_REQUIRED_EVIDENCE_GATES = (
    "ci",
    "dependency_review",
    "secret_scan",
    "codeql",
    "sonarqube",
    "wheel_sdist_build",
    "clean_wheel_install",
    "sdk_smoke",
    "cli_smoke",
)


def _candidate_sha_is_valid(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def verify_release(version: str = "v3.0.0") -> dict[str, Any]:
    """Validate retained release-candidate evidence without executing external commands.

    CI is responsible for actually running tests, builds, security checks, package-install
    smoke tests, and container checks. This verifier only checks that the frozen release
    manifest records those independently executed gates under the expected candidate
    identity, which keeps the CLI deterministic and free of process-execution capability.
    """
    release_tag = version if version.startswith("v") else f"v{version}"
    normalized_version = release_tag.removeprefix("v")
    manifest_path = ROOT / "release" / normalized_version / "manifest.json"

    gates: dict[str, str] = {}
    details: dict[str, str] = {}

    def gate(name: str, ok: bool, note: str = "") -> None:
        gates[name] = "PASS" if ok else "FAIL"
        if note and not ok:
            details[name] = note

    manifest: dict[str, Any] = {}
    manifest_exists = manifest_path.is_file()
    if manifest_exists:
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                manifest = raw
        except (OSError, json.JSONDecodeError) as exc:
            details["manifest present"] = f"Could not read manifest: {exc}"

    gate(
        "manifest present",
        bool(manifest),
        details.get("manifest present", f"Missing or invalid manifest: {manifest_path}"),
    )
    gate(
        "manifest version",
        manifest.get("version") == normalized_version,
        f"Expected version {normalized_version!r}, got {manifest.get('version')!r}",
    )
    gate(
        "release tag",
        manifest.get("release_tag") == release_tag,
        f"Expected release_tag {release_tag!r}, got {manifest.get('release_tag')!r}",
    )
    gate(
        "release-candidate status",
        manifest.get("status") == "release-candidate",
        f"Expected release-candidate status, got {manifest.get('status')!r}",
    )
    gate(
        "source candidate SHA",
        _candidate_sha_is_valid(manifest.get("source_candidate_commit")),
        "source_candidate_commit must be a full lowercase 40-character Git SHA",
    )

    evidence_gates = manifest.get("gates")
    evidence = evidence_gates if isinstance(evidence_gates, dict) else {}
    for key in _REQUIRED_EVIDENCE_GATES:
        value = evidence.get(key)
        gate(
            f"evidence:{key}",
            value == "pass",
            f"Expected retained evidence gate {key!r} to be 'pass', got {value!r}",
        )

    return {
        "version": release_tag,
        "gates": gates,
        "details": details,
        "summary": f"{sum(1 for value in gates.values() if value == 'PASS')}/{len(gates)} PASS",
        "manifest": str(manifest_path),
        "mode": "evidence-validation",
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Validate retained release-candidate evidence")
    ap.add_argument("version", nargs="?", default="v3.0.0", help="Release version")
    ap.add_argument("--json", action="store_true", help="Output JSON")
    args = ap.parse_args()
    rep = verify_release(args.version)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"=== Release Evidence Verification {rep['version']} ===")
        for key, value in rep["gates"].items():
            print(f"  {key}: {value}")
        print(f"Summary: {rep['summary']}")
        if rep["details"]:
            print("\nDetails (failures):")
            for key, value in rep["details"].items():
                print(f"  {key}: {value[:300]}")
    if any(value == "FAIL" for value in rep["gates"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
