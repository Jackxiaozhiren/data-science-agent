import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent
for p in [
    ROOT / "apps/api/src",
    ROOT / "packages/agent/src",
    ROOT / "packages/llm/src",
    ROOT / "packages/datasets/src",
    ROOT / "packages/evaluation/src",
    ROOT / "packages/tools/src",
    ROOT / "packages/execution/src",
    ROOT / "packages/statistics/src",
    ROOT / "packages/ml/src",
    ROOT / "packages/visualization/src",
    ROOT / "packages/evidence/src",
    ROOT / "packages/reports/src",
    ROOT / "packages/mcp/src",
    ROOT / "src",
]:
    if p.exists():
        sys.path.insert(0, str(p))

# Dev truth is workspace source: importing data_science_agent inserts its
# _vendor dir at sys.path[0] (needed for the published wheel), which would
# shadow packages/*/src in tests and split coverage onto the vendored copies.
# Demote _vendor to a fallback so `import dsa_*` resolves to workspace source.
try:
    import data_science_agent  # noqa: F401

    _vendor_dir = str(ROOT / "src" / "data_science_agent" / "_vendor")
    while _vendor_dir in sys.path:
        sys.path.remove(_vendor_dir)
    sys.path.append(_vendor_dir)
except Exception:  # noqa: S110 - best-effort test-only path demotion
    pass

# --- per-test isolation of process-global mutable state (audit §87 / Phase 4 target 4) -----------
#
# Derived by AST scan of the shipped trees, not by guesswork: these are the only module-level
# containers whose value is written after import. Before this existed the suite shared them across
# every test -- `tests/unit/test_tool_cache_failure_not_stored.py` hand-rolled its own
# `_TOOL_CACHE.pop()` cleanup, `reset_call_log()` was called by no test at all, and 37 files each
# called `bootstrap()` as if to defend against somebody else clearing the registry. With no ordering
# plugin installed, that coupling is latent rather than absent, and a tool served from another test's
# cache is exactly the green-but-never-ran result audit §76 caught once already.
#
# `tests/test_process_global_isolation.py` reads this tuple back out of the AST, asserts every entry
# still resolves to a real container, and asserts the set is *complete* against the same scan -- so a
# fifth cache added to shipped code turns that test red instead of quietly going unisolated.
_ISOLATED_GLOBALS = (
    ("dsa_agent.graph", "_TOOL_CACHE"),
    ("dsa_llm.providers", "_CALL_LOG"),
    ("dsa_mcp.adapter", "_ANALYSIS_STORE"),
    ("dsa_tools.registry", "_REGISTRY"),
)


def _snapshot(obj: object) -> object:
    if isinstance(obj, dict):
        return dict(obj)
    if isinstance(obj, list):
        return list(obj)
    if isinstance(obj, set):
        return set(obj)
    raise TypeError(
        f"unsupported container type {type(obj).__name__}; register a dict/list/set only"
    )


def _restore(obj: object, saved: object) -> None:
    # In place, so that `from dsa_agent.graph import _TOOL_CACHE` aliases still point at the restored
    # object; rebinding the module attribute would leave those aliases holding the stale value.
    if isinstance(obj, dict) and isinstance(saved, dict):
        obj.clear()
        obj.update(saved)
    elif isinstance(obj, list) and isinstance(saved, list):
        obj[:] = saved
    elif isinstance(obj, set) and isinstance(saved, set):
        obj.clear()
        obj.update(saved)
    else:
        raise TypeError(f"snapshot/type mismatch: {type(obj).__name__} vs {type(saved).__name__}")


@pytest.fixture(autouse=True)
def isolate_process_global_state():
    """Reset every writable module-level container after each test, whatever the test did to it."""
    live = []
    for module_name, attr in _ISOLATED_GLOBALS:
        obj = getattr(importlib.import_module(module_name), attr)
        live.append((obj, _snapshot(obj)))
    yield
    for obj, saved in live:
        _restore(obj, saved)
