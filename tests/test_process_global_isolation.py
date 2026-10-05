"""Target 4.1 -- process-global mutable state must be isolated per test, and *completely*.

Measured before this file existed (same AST criterion, run against the shipped tree): exactly four
module-level containers are written after import --

    dsa_agent.graph._TOOL_CACHE      dsa_llm.providers._CALL_LOG
    dsa_mcp.adapter._ANALYSIS_STORE  dsa_tools.registry._REGISTRY

(`dsa_mcp.adapter._ANALYSIS_STORE` is where §87 found it; §114 moved the MCP resource surface to
`dsa_mcp.resources`, and `conftest.py`'s entry follows the file that now owns the container.)

and `conftest.py` isolated none of them. The consequences were visible in the suite rather than
hypothetical: `tests/unit/test_tool_cache_failure_not_stored.py` hand-rolls `_TOOL_CACHE.pop(key)`
cleanup at its own boundaries, `reset_call_log()` is called by zero tests, and 37 test files each call
`bootstrap()` as if to defend against somebody else clearing the registry. No ordering plugin is
installed, so order dependence here is latent, not absent -- and a tool served from another test's
cache produces exactly the green-but-executed-nothing result §76 caught once already.

Why the completeness test parses the source of truth instead of restating it: a list duplicated in the
test and in the fixture is two owners of one fact, and only one of them would be updated when a fifth
cache appears (§82's rule). The registry lives in `conftest.py`; this file reads it out of that file's
AST.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFTEST = ROOT / "conftest.py"

# The same criterion used to enumerate the hazard: a container literal bound at module scope whose
# value is written after import (mutating method call or subscript assignment).
_MUTATORS = frozenset(
    {
        "append",
        "extend",
        "insert",
        "update",
        "add",
        "discard",
        "pop",
        "popitem",
        "clear",
        "setdefault",
        "remove",
        "sort",
    }
)
_SCAN_ROOTS = ("packages", "apps/api/src", "apps/jupyter/src", "src/data_science_agent")
_SKIP_PARTS = frozenset({"_vendor", "__pycache__", "node_modules"})


def _mutated_module_globals() -> set[tuple[str, str]]:
    """Every (module, name) pair whose module-level container is written at runtime."""
    found: set[tuple[str, str]] = set()
    for root in _SCAN_ROOTS:
        root_path = ROOT / root
        if not root_path.is_dir():
            continue
        for path in sorted(root_path.rglob("*.py")):
            if _SKIP_PARTS.intersection(path.parts):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - a shipped file must parse
                continue
            bound: dict[str, str] = {}
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    targets, value = node.targets, node.value
                elif isinstance(node, ast.AnnAssign):
                    targets, value = [node.target], node.value
                else:
                    continue
                if not isinstance(value, (ast.List, ast.Set, ast.Dict)):
                    continue
                for target in targets:
                    if isinstance(target, ast.Name):
                        bound[target.id] = ""
            if not bound:
                continue
            module = _module_name(path)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in _MUTATORS
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in bound
                ):
                    found.add((module, node.func.value.id))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if (
                            isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Name)
                            and target.value.id in bound
                        ):
                            found.add((module, target.value.id))
    return found


def _module_name(path: Path) -> str:
    """The importable dotted name for a package source file, via its src/ layout."""
    parts = list(path.relative_to(ROOT).parts)
    if "src" in parts:
        parts = parts[parts.index("src") + 1 :]
    if parts[-1] == "__init__.py":
        parts.pop()
    else:
        parts[-1] = parts[-1][: -len(".py")]
    return ".".join(parts)


def _conftest_registry() -> list[tuple[str, str]]:
    """Read `_ISOLATED_GLOBALS` out of conftest.py's AST -- the fixture owns the list."""
    tree = ast.parse(CONFTEST.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "_ISOLATED_GLOBALS" for t in node.targets):
            continue
        out: list[tuple[str, str]] = []
        for elt in getattr(node.value, "elts", []):
            if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                vals = [getattr(e, "value", None) for e in elt.elts]
                if all(isinstance(v, str) for v in vals):
                    out.append((vals[0], vals[1]))  # type: ignore[arg-type]
        return out
    return []


def test_conftest_declares_an_isolation_registry() -> None:
    registry = _conftest_registry()
    assert registry, (
        "conftest.py declares no _ISOLATED_GLOBALS -- per-test isolation of process-global state is "
        "not installed, so these tests share caches across runs"
    )


def test_registry_names_really_exist_and_are_mutable_containers() -> None:
    """A name that no longer resolves makes the fixture isolate nothing while still passing."""
    registry = _conftest_registry()
    assert registry, "no registry to check"
    for module_name, attr in registry:
        module = importlib.import_module(module_name)
        obj = getattr(module, attr, None)
        assert isinstance(obj, (dict, list, set)), (
            f"{module_name}.{attr} is {type(obj).__name__}, not a mutable container the fixture "
            "can snapshot and restore"
        )


def test_registry_is_complete_against_the_shipped_tree() -> None:
    """The uplift only holds if it covers every process-global that gets written.

    Derived from the source rather than asserted against a constant: adding a fifth module-level cache
    to shipped code must widen this check, and the fixture must then isolate it.
    """
    registry = set(_conftest_registry())
    assert registry, "no registry to compare"
    mutated = _mutated_module_globals()
    assert mutated, "the scan found no writable module-level containers -- the criterion broke"
    missing = sorted(mutated - registry)
    assert not missing, (
        f"process-global state written at runtime but not isolated per test: {missing}"
    )


_SENTINEL = "__isolation_probe__"


def test_a_pollute_every_isolated_global() -> None:
    """Deliberately writes into each registry member; `test_b` proves the write did not survive.

    This pair is the fixture's falsification: without snapshot/restore, `test_b` sees the sentinel and
    fails -- which is how it was confirmed to bite before the fixture existed.
    """
    registry = _conftest_registry()
    assert registry, "nothing to pollute -- the registry is empty, so test_b would pass vacuously"
    for module_name, attr in registry:
        obj = getattr(importlib.import_module(module_name), attr)
        if isinstance(obj, dict):
            obj[_SENTINEL] = {}
        elif isinstance(obj, set):
            obj.add(_SENTINEL)
        else:
            obj.append(_SENTINEL)


def test_b_no_write_from_the_previous_test_survives() -> None:
    registry = _conftest_registry()
    assert registry, "nothing was isolated, so 'no leak' here would prove nothing"
    survivors: list[str] = []
    for module_name, attr in registry:
        obj = getattr(importlib.import_module(module_name), attr)
        if _SENTINEL in obj:
            survivors.append(f"{module_name}.{attr}")
    assert not survivors, f"process-global state leaked across tests: {survivors}"
