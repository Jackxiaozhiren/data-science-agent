"""Target 4.1 -- process-global mutable state must be isolated per test, and *completely*.

Measured before this file existed (same AST criterion, run against the shipped tree): exactly four
module-level containers are written after import --

    dsa_agent.graph._TOOL_CACHE      dsa_llm.providers._CALL_LOG
    dsa_mcp.adapter._ANALYSIS_STORE  dsa_tools.registry._REGISTRY

(`dsa_mcp.adapter._ANALYSIS_STORE` is where §87 found it; §114 moved the MCP resource surface to
`dsa_mcp.resources`, and `dsa_llm.providers._CALL_LOG` moved to `dsa_llm.cost` at §116.
`conftest.py`'s entries follow the file that now owns each container.)

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

# The same criterion used to enumerate the hazard: a container bound at module scope whose
# value is written after import (mutating method call or subscript assignment).
#
# Comprehension-bound containers count too (audit §213). The literal-only version missed
# `dsa_api.core.security._limiters`, which is `[RateLimiter(n) for ... in _DEFAULT_RULES]`, and that miss is
# how the suite came to share one 30-uploads-per-minute window across every test in the process. Measured
# against the shipped tree, widening costs exactly one entry (6 -> 7); `ast.Call` would add none.
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
                if not isinstance(
                    value,
                    (ast.List, ast.Set, ast.Dict, ast.ListComp, ast.DictComp, ast.SetComp),
                ):
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


def _conftest_pairs(binding: str) -> list[tuple[str, str]]:
    """Read a `(module, name)` tuple out of conftest.py's AST -- the fixture owns the lists.

    Both registrations are read the same way for one reason: restating either in this file would make the
    check pass against a copy of a fact instead of the fact, which is how §82's rule is written.
    """
    tree = ast.parse(CONFTEST.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == binding for t in targets):
            continue
        out: list[tuple[str, str]] = []
        for elt in getattr(node.value, "elts", []):
            if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                vals = [getattr(e, "value", None) for e in elt.elts]
                if all(isinstance(v, str) for v in vals):
                    out.append((vals[0], vals[1]))  # type: ignore[arg-type]
        return out
    return []


def _conftest_registry() -> list[tuple[str, str]]:
    return _conftest_pairs("_ISOLATED_GLOBALS")


def _conftest_resets() -> list[tuple[str, str]]:
    """The containers isolated by reset rather than snapshot/restore (see §213)."""
    return _conftest_pairs("_ISOLATED_RESETS")


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
    isolated = set(_conftest_registry()) | set(_conftest_resets())
    assert isolated, "no registry to compare"
    mutated = _mutated_module_globals()
    assert mutated, "the scan found no writable module-level containers -- the criterion broke"
    missing = sorted(mutated - isolated)
    assert not missing, (
        f"process-global state written at runtime but not isolated per test: {missing}"
    )


def test_reset_members_really_hold_a_window() -> None:
    """A reset entry whose objects carry no `_hits` would clear nothing and still look registered."""
    resets = _conftest_resets()
    assert resets, "conftest.py declares no _ISOLATED_RESETS"
    registry = set(_conftest_registry())
    overlap = sorted(set(resets) & registry)
    assert not overlap, f"{overlap} is isolated twice, by snapshot and by reset"
    for module_name, attr in resets:
        holders = getattr(importlib.import_module(module_name), attr)
        assert isinstance(holders, list), (
            f"{module_name}.{attr} is {type(holders).__name__}, but the reset fixture walks it "
            "expecting one windowed object per element"
        )
        for holder in holders:
            assert isinstance(getattr(holder, "_hits", None), dict), (
                f"{module_name}.{attr} holds a {type(holder).__name__} with no `_hits` dict; "
                "the reset fixture would raise, not isolate"
            )
        assert holders, f"{module_name}.{attr} is empty, so the reset isolates nothing"


_SENTINEL = "__isolation_probe__"


def test_a1_fill_the_rate_limit_window() -> None:
    """Saturate one shared window on purpose; `test_b1` proves it did not reach the next test.

    Written as a pair because that is the only way to show a *per-test* reset fires: the budget is a
    module-level object and the suite's other tests touch it through HTTP, so the assertion has to be made
    from a different test than the one that filled it.
    """
    from dsa_api.core import security

    limiter = security._limiters[0]
    hits = limiter._hits.setdefault("isolation-probe:/api/v1/analysis", [])
    hits.extend([0.0] * limiter.max_requests)
    assert len(hits) == limiter.max_requests, (
        "the probe window was never filled, so test_b1 would pass without any reset having run"
    )


def test_b1_the_rate_limit_window_is_empty_in_a_later_test() -> None:
    resets = _conftest_resets()
    assert resets, (
        "conftest.py declares no _ISOLATED_RESETS -- with nothing named, the loop below would check "
        "nothing and this test would pass while the window still crossed the boundary"
    )
    for module_name, attr in resets:
        for holder in getattr(importlib.import_module(module_name), attr):
            survivors = sorted(key for key, window in holder._hits.items() if window)
            assert not survivors, (
                f"{module_name}.{attr} carried a rate-limit window across the test boundary: {survivors}"
            )


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
