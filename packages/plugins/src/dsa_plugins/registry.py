from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from dsa_plugins.manifest import PluginManifest

REGISTRY_DIR = Path("plugins")


def discover_plugins(root: Path | str = REGISTRY_DIR) -> list[PluginManifest]:
    root_p = Path(root)
    if not root_p.exists():
        return []
    manifests: list[PluginManifest] = []
    for p in root_p.rglob("manifest.yaml"):
        try:
            manifests.append(PluginManifest.from_yaml(p))
        except Exception:  # noqa: S112
            continue
    for p in root_p.rglob("plugin.yaml"):
        try:
            manifests.append(PluginManifest.from_yaml(p))
        except Exception:  # noqa: S112
            continue
    return manifests


def list_plugins(root: Path | str = REGISTRY_DIR) -> list[PluginManifest]:
    return discover_plugins(root)


def load_plugin(manifest: PluginManifest) -> Any:
    ep = manifest.entrypoint.get("python")
    if not ep or ":" not in ep:
        raise ValueError(f"Invalid entrypoint: {ep}")
    mod, attr = ep.split(":", 1)
    m = importlib.import_module(mod)
    fn = getattr(m, attr)
    return fn() if callable(fn) else fn
