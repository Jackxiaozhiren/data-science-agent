"""§97 Phase 4 target 2, seam #1: column inspection has one owner, bound by name.

A split that is not pinned is a split that silently re-merges: someone pastes a helper back
into the planner, the two copies drift, and the plan starts answering to whichever module
imported last. These tests are structural -- they read the ASTs of both files -- because the
claim is about where a definition lives, not about behaviour any single call can show.

The binding rule is not stylistic. `tests/test_product_hardening.py` patches
`planner._numeric_columns`; that only intercepts the planner's real call while the planner
holds the function in its own namespace. Converting the import to `columns._numeric_columns(...)`
would keep every test green and make the patch a no-op.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLANNER = REPO / "packages/agent/src/dsa_agent/planner.py"
COLUMNS = REPO / "packages/agent/src/dsa_agent/columns.py"

#: Everything the seam module owns. `normalize_text` and `mentioned_columns` are public
#: because the planner does not call them -- ruff's isort stripped them from its import
#: list, which is the correct reading: they exist to serve the other five.
SEAM = frozenset(
    {
        "_numeric_columns",
        "normalize_text",
        "mentioned_columns",
        "_pick_target_column",
        "_pick_treatment_column",
        "_pick_numeric_predictor",
        "_has_time_data",
    }
)
PLANNER_CALLS = frozenset(
    {
        "_numeric_columns",
        "_has_time_data",
        "_pick_target_column",
        "_pick_treatment_column",
        "_pick_numeric_predictor",
    }
)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _top_level_defs(tree: ast.Module) -> set[str]:
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_the_seam_functions_are_defined_in_columns_only() -> None:
    in_columns = _top_level_defs(_tree(COLUMNS))
    in_planner = _top_level_defs(_tree(PLANNER))
    assert in_columns >= SEAM, sorted(SEAM - in_columns)
    assert not (SEAM & in_planner), (
        f"a copy of the seam reappeared in planner: {sorted(SEAM & in_planner)}"
    )


def test_planner_imports_the_seam_by_name_not_by_attribute() -> None:
    tree = _tree(PLANNER)
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "dsa_agent.columns":
            imported |= {alias.name for alias in node.names}
    assert imported == set(PLANNER_CALLS), f"planner binds {sorted(imported)}"

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "columns"
        ):
            raise AssertionError(
                f"planner reaches for columns.{node.attr} -- attribute access breaks "
                "monkeypatch.setattr(planner, ...) at every such call site"
            )


def test_the_seam_is_actually_called_from_the_planner() -> None:
    """An import nobody calls is how a seam becomes dead code with a green suite."""
    called = set()
    for node in ast.walk(_tree(PLANNER)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called.add(node.func.id)
    expected = {
        "_numeric_columns",
        "_has_time_data",
        "_pick_target_column",
        "_pick_treatment_column",
    }
    assert expected <= called, sorted(expected - called)


def test_columns_depends_on_nothing_from_the_planner_side() -> None:
    """The seam must not reach back: only stdlib at module scope, dataset loaders lazily."""
    tree = _tree(COLUMNS)
    module_scope: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            module_scope += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            module_scope.append(node.module)
    assert module_scope == ["__future__", "re"], module_scope
    lazy: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and node not in tree.body:
            for alias in node.names:
                lazy.add(alias.name if isinstance(node, ast.Import) else (node.module or ""))
    needed = {"dsa_datasets.loader", "dsa_datasets.validate", "polars", "pathlib"}
    assert needed <= lazy, sorted(lazy)
