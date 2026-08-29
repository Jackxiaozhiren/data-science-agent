from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized_section(data: dict[str, Any], section: str) -> dict[str, Any]:
    value = data.get(section, {})
    return value if isinstance(value, dict) else {}


def _compare_manifest(
    manifest_path: Path,
    lock_entry: dict[str, Any] | None,
    lock_key: str,
) -> list[str]:
    errors: list[str] = []
    manifest = _load_json(manifest_path)
    if lock_entry is None:
        return [f"{lock_key or '<root>'}: missing from package-lock.json packages"]

    for section in MANIFEST_SECTIONS:
        expected = _normalized_section(manifest, section)
        actual = _normalized_section(lock_entry, section)
        if expected == actual:
            continue
        keys = sorted(set(expected) | set(actual))
        for name in keys:
            expected_value = expected.get(name)
            actual_value = actual.get(name)
            if expected_value != actual_value:
                errors.append(
                    f"{lock_key or '<root>'} {section}.{name}: "
                    f"manifest={expected_value!r}, lock={actual_value!r}"
                )
    return errors


def main() -> int:
    root_manifest = _load_json(ROOT / "package.json")
    lock = _load_json(ROOT / "package-lock.json")
    packages = lock.get("packages")
    if not isinstance(packages, dict):
        print("package-lock.json is missing a packages mapping")
        return 1

    errors = _compare_manifest(ROOT / "package.json", packages.get(""), "")

    workspace_patterns = root_manifest.get("workspaces", [])
    if not isinstance(workspace_patterns, list):
        print("package.json workspaces must be a list")
        return 1

    for pattern in workspace_patterns:
        if not isinstance(pattern, str):
            continue
        for workspace_dir in sorted(ROOT.glob(pattern)):
            manifest_path = workspace_dir / "package.json"
            if not manifest_path.is_file():
                continue
            lock_key = workspace_dir.relative_to(ROOT).as_posix()
            errors.extend(_compare_manifest(manifest_path, packages.get(lock_key), lock_key))

    if errors:
        print("Root npm workspace lockfile is out of sync:")
        for error in errors:
            print(f"- {error}")
        print(
            "Regenerate package-lock.json from the repository root with the "
            "project's supported npm/Node setup."
        )
        return 1

    print("Root npm workspace lockfile matches all workspace manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
