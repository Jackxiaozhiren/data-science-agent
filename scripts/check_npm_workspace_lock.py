from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIVERGENCE_LEDGER = Path("docs") / "audit" / "npm-lock-divergences.json"
MANIFEST_SECTIONS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "peerDependencies",
)


def _load_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


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


def _member_root_specifiers(packages: dict[str, Any]) -> dict[str, str]:
    """Bare specifiers this member's own install resolves at its top level, with their versions.

    Nested entries (`node_modules/next/node_modules/postcss`) are left out on purpose: matching them
    by name across two independent resolutions conflates npm's layout choice with the version a
    member's imports actually see, and the version that matters is the top-level one.
    """
    found: dict[str, str] = {}
    for path, entry in packages.items():
        if not path.startswith("node_modules/") or path.count("node_modules/") != 1:
            continue
        version = entry.get("version")
        if isinstance(version, str):
            found[path.removeprefix("node_modules/")] = version
    return found


def _root_resolution(
    root_packages: dict[str, Any], member: str, name: str
) -> tuple[str | None, str]:
    """The version the root workspace lock installs for `member`, and where it came from."""
    nested = f"{member}/node_modules/{name}"
    hoisted = f"node_modules/{name}"
    for key in (nested, hoisted):
        entry = root_packages.get(key)
        if isinstance(entry, dict) and isinstance(entry.get("version"), str):
            return entry["version"], key
    return None, ""


def _cross_lock_divergences(
    root_packages: dict[str, Any],
    member: str,
    member_packages: dict[str, Any],
) -> list[dict[str, str]]:
    """Where the member lock and the root lock resolve the same specifier to different versions.

    Every pair here satisfies the manifest's own range -- that is why the range comparison above
    cannot see them, and why CI (which installs members from the member lock) can verify a tree a
    root `npm ci` would not reproduce. `kind` separates the two shapes: `version` and `absent` are
    gated through the ledger; `placement` is npm hoisting the same package to a different depth and
    is reported without failing, because no import in the tree changes.
    """
    findings: list[dict[str, str]] = []
    for name, member_version in sorted(_member_root_specifiers(member_packages).items()):
        root_version, root_path = _root_resolution(root_packages, member, name)
        if root_version is None:
            elsewhere = next(
                (key for key in root_packages if key.endswith(f"/node_modules/{name}")),
                "",
            )
            findings.append(
                {
                    "member": member,
                    "package": name,
                    "kind": "placement" if elsewhere else "absent",
                    "member_version": member_version,
                    "root_version": "",
                    "root_path": elsewhere,
                }
            )
            continue
        if root_version != member_version:
            findings.append(
                {
                    "member": member,
                    "package": name,
                    "kind": "version",
                    "member_version": member_version,
                    "root_version": root_version,
                    "root_path": root_path,
                }
            )
    return findings


def _ledger_keys() -> set[str]:
    path = ROOT / DIVERGENCE_LEDGER
    if not path.is_file():
        return set()
    entries = _load_json(path).get("divergences")
    if not isinstance(entries, list):
        return set()
    return {
        f"{entry.get('member')}:{entry.get('package')}"
        for entry in entries
        if isinstance(entry, dict)
    }


def _reconcile_divergence_ledger(findings: list[dict[str, str]]) -> list[str]:
    """Fail on a divergence the ledger does not name, and on a ledger entry reality has moved past.

    The second direction is what keeps the file from becoming a pile of permissions: reconcile one
    of these and the gate asks you to delete its entry, so the next divergence at that path is
    caught instead of covered.
    """
    gated = [found for found in findings if found["kind"] != "placement"]
    allowed = _ledger_keys()
    seen = {f"{found['member']}:{found['package']}" for found in gated}
    errors: list[str] = []
    for found in gated:
        key = f"{found['member']}:{found['package']}"
        if key in allowed:
            continue
        errors.append(
            f"{key} resolves to {found['member_version']} in the member lock but "
            f"{found['root_version'] or 'not at all'} in the root lock ({found['kind']}) -- "
            f"regenerate one lock from the other, or name it in {DIVERGENCE_LEDGER.as_posix()}"
        )
    for key in sorted(allowed - seen):
        errors.append(
            f"{DIVERGENCE_LEDGER.as_posix()} lists {key}, which no longer diverges -- prune the entry"
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
    divergences: list[dict[str, str]] = []

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

            # The Web and VS Code workspaces also commit their own lockfiles,
            # consumed by `npm --prefix <workspace> ci`. The root lock may
            # be valid while a member lock silently points to old versions.
            member_lock_path = workspace_dir / "package-lock.json"
            if member_lock_path.is_file():
                member_packages = _load_json(member_lock_path).get("packages")
                member_key = f"{lock_key}/package-lock.json"
                if not isinstance(member_packages, dict):
                    errors.append(f"{member_key}: missing packages mapping")
                else:
                    errors.extend(
                        _compare_manifest(manifest_path, member_packages.get(""), member_key)
                    )
                    divergences.extend(_cross_lock_divergences(packages, lock_key, member_packages))

    errors.extend(_reconcile_divergence_ledger(divergences))
    placement = [found for found in divergences if found["kind"] == "placement"]
    if placement:
        print(
            f"placement-only differences between the locks, deliberately not gated: {len(placement)}"
        )
        for found in placement:
            print(
                f"- {found['member']}:{found['package']} {found['member_version']} sits at that "
                f"member's top level while the root lock resolves it at {found['root_path']}"
            )

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
    print(
        f"Resolved versions across the member locks agree, apart from "
        f"{len(_ledger_keys())} divergence(s) named in {DIVERGENCE_LEDGER.as_posix()}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
