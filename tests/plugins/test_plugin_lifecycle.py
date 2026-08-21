"""W3 §21 Lifecycle + §22 manifest + §23 permissions + §24 validation."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from dsa_plugins.manifest import ALLOWED_PERMISSIONS, PluginManifest
from dsa_plugins.registry import (
    disable_plugin,
    enable_plugin,
    get_plugin_status,
    list_plugins,
    load_plugin,
    validate_plugin,
)


def test_manifest_mandatory_fields() -> None:
    m = PluginManifest.from_yaml("plugins/dsa-time-series/manifest.yaml")
    assert m.name == "dsa-time-series"
    assert m.version == "1.0.0"
    assert m.license == "MIT"
    assert m.entrypoint["python"] == "dsa_time_series.plugin:register"
    assert "dataset.read" in m.permissions
    assert "process" in m.permissions
    assert "artifact.write" in m.permissions
    assert len(m.capabilities) >= 5
    assert m.dsa is not None
    assert m.dsa["min_version"] == "4.0.0"


def test_manifest_deny_default() -> None:
    # missing permissions should fail validation
    m = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "some.mod:fn"},
        permissions=[],  # DENY
        capabilities=["forecast"],
    )
    errs = m.validate_manifest()
    assert any("permissions" in e for e in errs)
    assert not m.is_valid()


def test_manifest_permission_allowlist() -> None:
    m = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "some.mod:fn"},
        permissions=["filesystem.read", "evil.perm"],  # evil not allowed
        capabilities=["forecast"],
    )
    errs = m.validate_manifest()
    assert any("evil.perm" in e for e in errs)


def test_manifest_license_allowlist() -> None:
    m = PluginManifest(
        name="test-plugin",
        version="1.0.0",
        license="GPL-3.0",  # not in allowed
        entrypoint={"python": "some.mod:fn"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
    )
    errs = m.validate_manifest()
    assert any("license" in e for e in errs)


def test_flagship_manifest_valid() -> None:
    errs = validate_plugin("plugins/dsa-time-series/manifest.yaml")
    assert errs == [], f"flagship should be valid: {errs}"


def test_discover_lists_flagship() -> None:
    pls = list_plugins()
    names = [p.name for p in pls]
    assert "dsa-time-series" in names


def test_lifecycle_disable_enable_isolation() -> None:
    # ensure enabled
    enable_plugin("dsa-time-series")
    assert get_plugin_status("dsa-time-series") == "enabled"
    assert any(p.name == "dsa-time-series" for p in list_plugins())
    # disable hides from discover
    disable_plugin("dsa-time-series")
    assert get_plugin_status("dsa-time-series") == "disabled"
    assert not any(p.name == "dsa-time-series" for p in list_plugins())
    # re-enable
    enable_plugin("dsa-time-series")
    assert get_plugin_status("dsa-time-series") == "enabled"
    assert any(p.name == "dsa-time-series" for p in list_plugins())


def test_load_plugin_after_enable() -> None:
    enable_plugin("dsa-time-series")
    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    inst = load_plugin(m)
    assert inst.name == "dsa-time-series"
    assert "forecast" in inst.register_tools()


def test_install_validate_rejects_bad_manifest() -> None:
    with tempfile.TemporaryDirectory() as td:
        bad_dir = Path(td) / "bad-plugin"
        bad_dir.mkdir()
        (bad_dir / "manifest.yaml").write_text(
            "name: bad\nversion: 1.0.0\nlicense: MIT\nentrypoint: {python: bad:fn}\npermissions: []\ncapabilities: []\n",
            encoding="utf-8",
        )
        errs = validate_plugin(bad_dir / "manifest.yaml")
        assert len(errs) > 0
        assert not PluginManifest.from_yaml(bad_dir / "manifest.yaml").is_valid()
