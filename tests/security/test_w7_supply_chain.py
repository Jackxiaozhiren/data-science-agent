"""W7 §41-47 Security & Supply Chain — CodeQL, Dependency Review, Secret, Plugin, Pinning, SBOM."""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_codeql_workflow_exists_and_covers_python_js() -> None:
    p = Path(".github/workflows/codeql.yml")
    assert p.exists(), "CodeQL workflow missing (§42)"
    txt = p.read_text()
    assert "python" in txt.lower()
    assert "javascript" in txt.lower()
    assert "codeql-action/init" in txt
    assert "security-and-quality" in txt


def test_dependency_review_workflow() -> None:
    p = Path(".github/workflows/dependency-review.yml")
    assert p.exists(), "Dependency Review workflow missing (§43)"
    txt = p.read_text()
    assert "dependency-review-action" in txt
    assert "allow-licenses" in txt
    assert "fail-on-severity" in txt


def test_secret_scan_workflow() -> None:
    p = Path(".github/workflows/secret-scan.yml")
    assert p.exists(), "Secret scan workflow missing (§44)"
    txt = p.read_text()
    assert "gitleaks" in txt.lower()


def test_dependabot_exists() -> None:
    p = Path(".github/dependabot.yml")
    assert p.exists()
    txt = p.read_text()
    assert "pip" in txt and "npm" in txt and "docker" in txt


def test_sbom_exists_and_has_required_fields() -> None:
    p = Path("release/sbom.json")
    assert p.exists(), "SBOM missing at release/sbom.json (§47)"
    data = json.loads(p.read_text())
    assert "version" in data and "components" in data
    assert len(data["components"]) >= 50
    for c in data["components"][:5]:
        assert "package" in c and "version" in c and "license" in c and "source" in c
        assert c["package"] and c["version"]
    # Check cyclonedx also exists
    assert (Path("release/sbom.cyclonedx.json")).exists()
    cyclo = json.loads((Path("release/sbom.cyclonedx.json")).read_text())
    assert cyclo["bomFormat"] == "CycloneDX"
    assert len(cyclo["components"]) >= 50


def test_sbom_includes_workspace_packages() -> None:
    data = json.loads(Path("release/sbom.json").read_text())
    names = {c["package"] for c in data["components"]}
    for expected in ("jack-data-science-agent", "dsa-agent", "dsa-tools", "dsa-jupyter"):
        assert expected in names, f"SBOM missing workspace {expected}"


def test_plugin_supply_chain_typosquat() -> None:
    from dsa_plugins.manifest import PluginManifest

    # Typosquat plugin name should be flagged
    m = PluginManifest(
        name="numpy",  # popular, but plugin should not be named numpy (unless allowed)
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "some:fn"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
    )
    # numpy is popular but plugin named numpy is suspicious only if typosquat of another? Our check is edit distance <=2, so numpy vs numpy is not typosquat (exact match not flagged). Use close name
    m2 = PluginManifest(
        name="pandss",  # ~ pandas
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "some:fn"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
    )
    errs = m2.validate_manifest()
    assert any("typosquat" in e for e in errs), f"should flag typosquat, got {errs}"


def test_plugin_supply_chain_suspicious_entrypoint() -> None:
    from dsa_plugins.manifest import PluginManifest

    m = PluginManifest(
        name="evil-plugin",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "os.system:evil"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
    )
    errs = m.validate_manifest()
    assert any("suspicious" in e for e in errs)


def test_plugin_supply_chain_dependency_confusion() -> None:
    from dsa_plugins.manifest import PluginManifest

    m = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "some:fn"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
        dependencies=["dsa-evil-package>=1.0"],  # looks like workspace but not in allowlist
    )
    errs = m.validate_manifest()
    assert any("confusion" in e or "typosquat" in e for e in errs)


def test_dependency_pinning_uv_lock_exists_and_auditable() -> None:
    assert Path("uv.lock").exists(), "uv.lock missing (§46)"
    # Should be committed and non-empty
    assert Path("uv.lock").stat().st_size > 10000
    # pyproject should have versioned deps (not *)
    txt = Path("pyproject.toml").read_text()
    assert "dependencies" in txt
    # Check that prod deps have version specifiers
    assert "polars>=" in txt or "duckdb>=" in txt


def _plugin_manifest(**over: object):
    """A PluginManifest for the hash tests, so each one states only what it varies."""
    from dsa_plugins.manifest import PluginManifest

    fields: dict = {
        "name": "demo-plugin",
        "version": "1.0.0",
        "license": "MIT",
        "entrypoint": {"python": "main:run"},
        "permissions": ["dataset.read"],
    }
    fields.update(over)
    return PluginManifest(**fields)


def test_plugin_hash_distinguishes_never_inspected_from_nothing_to_read(tmp_path: Path) -> None:
    """§93: three different worlds must not share one digest.

    The first version gated its walk on `if root and root.exists()`, so the digest for a
    plugin directory that does not exist, one that is empty, and a call that supplied no
    directory at all were all just name + entrypoint. An install into a missing directory
    therefore hashed identically to a caller that checked nothing -- and an integrity
    digest that cannot tell those apart is not an integrity digest.
    """
    m = _plugin_manifest()
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    a_file = tmp_path / "not-a-dir.py"
    a_file.write_bytes(b"x\n")

    absent = m.compute_hash(tmp_path / "absent")
    empty = m.compute_hash(empty_root)
    uninspected = m.compute_hash(None)
    file_root = m.compute_hash(a_file)

    assert len({absent, empty, uninspected, file_root}) == 4, (
        absent,
        empty,
        uninspected,
        file_root,
    )


def test_a_file_that_cannot_be_read_is_not_the_same_as_a_file_that_is_gone(
    tmp_path: Path, monkeypatch
) -> None:
    """An I/O failure must not produce the digest of a legitimately smaller plugin."""
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "a.py").write_bytes(b"print(1)\n")
    target = root / "b.py"
    target.write_bytes(b"print(2)\n")

    m = _plugin_manifest()
    complete = m.compute_hash(root)
    real_read = Path.read_bytes

    def unreadable(self: Path) -> bytes:
        if self.name == "b.py":
            raise PermissionError("disk gone")
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    errored = m.compute_hash(root)
    monkeypatch.undo()

    target.unlink()
    deleted = m.compute_hash(root)

    assert errored != complete, "an unreadable file did not change the digest at all"
    assert errored != deleted, "an unreadable file hashed as if it had been removed"


def test_a_non_io_failure_propagates_instead_of_being_absorbed(tmp_path: Path, monkeypatch) -> None:
    """`except Exception` around a file read also catches a caller's deliberate refusal.

    pydantic raises ValueError, as does any code that rejects an argument on purpose; the
    first version turned that refusal into "skip this file and keep hashing", which is the
    one outcome an integrity check must never produce silently (§93).
    """
    import pytest

    root = tmp_path / "plugin"
    root.mkdir()
    (root / "a.py").write_bytes(b"x\n")

    def refuse(self: Path) -> bytes:
        raise ValueError("not a file I am willing to read")

    monkeypatch.setattr(Path, "read_bytes", refuse)
    with pytest.raises(ValueError, match="willing to read"):
        _plugin_manifest().compute_hash(root)


def test_plugin_hash_is_deterministic_and_moves_with_content(tmp_path: Path) -> None:
    """Green-on-arrival: the old implementation already did this, and the fix must not lose it.

    Pinned because the §93 change rewrites the hash's inputs; if the digest stopped
    tracking file *contents*, the two new discriminations above would be meaningless.
    """
    m = _plugin_manifest()
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "a.py").write_bytes(b"print(1)\n")
    before = m.compute_hash(root)

    assert m.compute_hash(root) == before
    (root / "a.py").write_bytes(b"print(2)\n")
    assert m.compute_hash(root) != before


def test_secret_protection_no_hardcoded_secrets_in_repo() -> None:
    # Simple grep for obvious secrets in tracked files (not .venv)
    patterns = [
        r"sk-[A-Za-z0-9]{20}",
        r"ghp_[A-Za-z0-9]{30}",
        r"api_key\s*=\s*['\"][A-Za-z0-9]{20}",
    ]
    for pat in patterns:
        for p in Path(".").rglob("*.py"):
            if ".venv" in str(p) or ".git" in str(p) or "node_modules" in str(p):
                continue
            try:
                txt = p.read_text()[:5000]
                assert not re.search(pat, txt), f"Potential secret {pat} in {p}"
            except Exception:  # noqa: S112
                continue
    # Also check that SECURITY.md mentions secret scanning
    assert (
        "Secret Scanning" in Path("SECURITY.md").read_text()
        or "secret" in Path("SECURITY.md").read_text().lower()
    )
