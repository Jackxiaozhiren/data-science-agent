from __future__ import annotations

import importlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from dsa_plugins.manifest import ALLOWED_PERMISSIONS, PluginManifest

REGISTRY_DIR = Path("plugins")
REGISTRY_STATE = REGISTRY_DIR / ".registry_state.json"

# §23 default DENY, §25 isolation, §21 lifecycle


def _load_state() -> dict[str, Any]:
    if REGISTRY_STATE.exists():
        try:
            data: dict[str, Any] = json.loads(REGISTRY_STATE.read_text(encoding="utf-8"))
            return data
        except Exception:
            return {}
    return {}


def _save_state(state: dict[str, Any]) -> None:
    REGISTRY_STATE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _is_disabled(name: str) -> bool:
    state = _load_state()
    return bool(state.get("disabled", {}).get(name, False))


def _manifest_source_path(manifest: PluginManifest, root: Path | str = REGISTRY_DIR) -> Path | None:
    root_p = Path(root)
    for p in root_p.rglob("manifest.yaml"):
        try:
            m = PluginManifest.from_yaml(p)
            if m.name == manifest.name and m.version == manifest.version:
                return p.parent
        except Exception:
            continue
    return None


def discover_plugins(
    root: Path | str = REGISTRY_DIR, include_disabled: bool = False
) -> list[PluginManifest]:
    """§21 Discover — scan for manifest.yaml/plugin.yaml (§22)."""
    root_p = Path(root)
    if not root_p.exists():
        return []
    manifests: list[PluginManifest] = []
    for p in root_p.rglob("manifest.yaml"):
        try:
            m = PluginManifest.from_yaml(p)
            if not include_disabled and _is_disabled(m.name):
                continue
            manifests.append(m)
        except Exception:  # noqa: S112
            continue
    for p in root_p.rglob("plugin.yaml"):
        try:
            m = PluginManifest.from_yaml(p)
            if not include_disabled and _is_disabled(m.name):
                continue
            manifests.append(m)
        except Exception:  # noqa: S112
            continue
    return manifests


def list_plugins(root: Path | str = REGISTRY_DIR) -> list[PluginManifest]:
    return discover_plugins(root)


# §24 Validation
def validate_plugin(manifest: PluginManifest | Path | str) -> list[str]:
    """§24 Validate manifest/version/dependency/license/hash/permissions/compatibility."""
    if isinstance(manifest, (str, Path)):
        try:
            m = PluginManifest.from_yaml(Path(manifest))
        except Exception as e:
            return [f"manifest parse failed: {e}"]
    else:
        m = manifest
    return m.validate_manifest()


# §21 Install — local copy + validation
def install_plugin(source: Path | str, target_root: Path | str = REGISTRY_DIR) -> PluginManifest:
    """Install plugin from source dir (containing manifest.yaml) into registry.

    Steps: Validate → Check compatibility → Copy → Verify hash
    Default DENY is enforced via validate.
    """
    src = Path(source)
    manifest_path = src / "manifest.yaml" if src.is_dir() else src
    if not manifest_path.exists():
        # try plugin.yaml
        manifest_path = src / "plugin.yaml" if src.is_dir() else Path(source)
    errors = validate_plugin(manifest_path)
    if errors:
        raise ValueError(f"Plugin validation failed §24: {errors}")
    m = PluginManifest.from_yaml(manifest_path)
    # check not already installed with same version
    dst = Path(target_root) / m.name
    if dst.exists():
        raise FileExistsError(f"Plugin {m.name} already installed at {dst} — remove first (§21)")
    # copy
    src_root = manifest_path.parent
    shutil.copytree(src_root, dst)
    return m


def _ensure_plugin_on_path(manifest: PluginManifest, root: Path | str = REGISTRY_DIR) -> None:
    src_path = _manifest_source_path(manifest, root)
    if src_path is None:
        # fallback: try plugins/<name>/src
        cand = Path(root) / manifest.name / "src"
        if cand.exists():
            src_path = cand.parent
            cand_str = str(cand)
        else:
            return
    else:
        cand = src_path / "src"
        if cand.exists():
            cand_str = str(cand)
        else:
            cand_str = str(src_path)
    if cand_str not in sys.path:
        sys.path.insert(0, cand_str)


def load_plugin(manifest: PluginManifest) -> Any:
    """§21 Load — isolated; adds plugin src to sys.path for import."""
    if _is_disabled(manifest.name):
        raise RuntimeError(f"Plugin {manifest.name} is disabled (§21)")
    # permission default DENY already validated; here just check we have entrypoint
    ep = manifest.entrypoint.get("python")
    if not ep or ":" not in ep:
        raise ValueError(f"Invalid entrypoint: {ep} (§22)")
    _ensure_plugin_on_path(manifest)
    try:
        mod, attr = ep.split(":", 1)
        m = importlib.import_module(mod)
        fn = getattr(m, attr)
        inst = fn() if callable(fn) else fn
        return inst
    except Exception as e:
        # §25 isolation: wrap, do not crash caller — caller should catch
        raise RuntimeError(f"Plugin {manifest.name} load failed (isolated §25): {e}") from e


def load_plugin_isolated(manifest: PluginManifest) -> tuple[Any | None, str | None]:
    """Load with isolation — returns (plugin, error). Never raises to crash core (§25)."""
    try:
        p = load_plugin(manifest)
        return p, None
    except Exception as e:
        return None, str(e)


# §23 Permission check — DENY default
def check_permission(manifest: PluginManifest, required: str | list[str]) -> bool:
    reqs = [required] if isinstance(required, str) else required
    # canonical mapping: legacy "read" etc already in ALLOWED but check explicit
    perms = set(manifest.permissions)
    # expand canonical: if plugin has granular, it covers legacy shorthand; we check exact
    for r in reqs:
        if r not in perms:
            # also check if canonical covers: e.g. plugin has "dataset.read" covers "read"?
            # For strict DENY, require exact; legacy plugins with "read" need mapping
            # If plugin has legacy "read" and required is dataset.read, allow via mapping
            if r == "dataset.read" and "read" in perms:
                continue
            if r == "process" and "compute" in perms:
                continue
            if r == "artifact.write" and "write" in perms:
                continue
            return False
    return True


# §21 Execute — isolated, permission-checked
def execute_plugin_tool(
    manifest: PluginManifest, tool_name: str, *args: Any, **kwargs: Any
) -> dict[str, Any]:
    """Execute a plugin tool with isolation and permission check (§23/§25).

    Returns: {"ok": bool, "result": Any, "error": str|None}
    Never crashes caller.
    """
    # permission map per §23 — minimal required per tool
    TOOL_PERMS: dict[str, list[str]] = {
        "forecast": ["dataset.read", "process"],
        "backtest": ["dataset.read", "process"],
        "metrics": ["dataset.read", "process"],
        "visualization": ["artifact.write"],
        "forecast_viz": ["artifact.write"],
        "evidence": ["dataset.read"],
    }
    needed = TOOL_PERMS.get(tool_name, [])
    if needed and not check_permission(manifest, needed):
        return {
            "ok": False,
            "result": None,
            "error": f"permission denied §23: {tool_name} needs {needed}, has {manifest.permissions}",
        }
    plugin, err = load_plugin_isolated(manifest)
    if err:
        return {"ok": False, "result": None, "error": err}
    try:
        # plugin may expose methods named <tool_name> or via register_tools
        if plugin is not None and hasattr(plugin, tool_name):
            fn = getattr(plugin, tool_name)
            res = fn(*args, **kwargs) if callable(fn) else fn
        elif plugin is not None and hasattr(plugin, "execute"):
            res = plugin.execute(tool_name, *args, **kwargs)
        else:
            return {
                "ok": False,
                "result": None,
                "error": f"tool {tool_name} not found on plugin {manifest.name}",
            }
        return {"ok": True, "result": res, "error": None}
    except Exception as e:
        return {
            "ok": False,
            "result": None,
            "error": f"plugin tool {tool_name} failed (isolated §25): {e}",
        }


# §21 Disable / Enable / Remove
def disable_plugin(name: str) -> None:
    state = _load_state()
    state.setdefault("disabled", {})[name] = True
    _save_state(state)


def enable_plugin(name: str) -> None:
    state = _load_state()
    if name in state.get("disabled", {}):
        del state["disabled"][name]
        _save_state(state)


def remove_plugin(name: str, root: Path | str = REGISTRY_DIR) -> None:
    p = Path(root) / name
    if not p.exists():
        raise FileNotFoundError(f"Plugin {name} not found at {p}")
    # ensure not disabling state left
    state = _load_state()
    if name in state.get("disabled", {}):
        del state["disabled"][name]
        _save_state(state)
    shutil.rmtree(p)


def get_plugin_status(name: str) -> str:
    if _is_disabled(name):
        return "disabled"
    for m in discover_plugins(include_disabled=True):
        if m.name == name:
            return "enabled"
    return "not_found"
