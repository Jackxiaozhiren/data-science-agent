"""§114, Phase 4 target 2 seam #6: the MCP *resources* surface lives in its own module.

`packages/mcp/src/dsa_mcp/adapter.py` carried two protocol surfaces in one file: the tool side
(schemas, classification, dispatch) and the resource side (`dataset://`, `evidence://`, `report://`,
`analysis://`, `artifact://` plus the explicit-handle store). 632 lines, the second-largest shipped
file, and the split is not cosmetic -- MCP clients list resources and call tools through different
handlers, and `server.py` already imports them as two groups.

Red on arrival as an `ImportError`, the way §112's seam was: the module does not exist yet, so the
documented import path fails at collection rather than as an assertion.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MCP_SRC = REPO / "packages" / "mcp" / "src" / "dsa_mcp"

RESOURCE_NAMES = (
    "_discover_datasets",
    "_ANALYSIS_STORE",
    "store_analysis",
    "list_resources",
    "read_resource",
)


def _top_level_defs(path: Path) -> set[str]:
    """Names a module binds at import time.

    `ast.AnnAssign` is not optional here: `_ANALYSIS_STORE: dict[str, dict[str, Any]] = {}` and
    `MCP_TOOL_MAP: dict[str, str] = {...}` are both annotated, and a helper that read only plain
    `Assign` reported the adapter as *not* defining the store -- a guard that passes for the wrong
    reason is worse than one that fails.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            found |= {str(t.id) for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.add(node.target.id)
    return found


def test_the_resource_surface_is_its_own_module() -> None:
    assert (MCP_SRC / "resources.py").is_file(), "dsa_mcp.resources does not exist"
    defined = _top_level_defs(MCP_SRC / "resources.py")
    missing = [n for n in RESOURCE_NAMES if n not in defined]
    assert not missing, f"resources.py does not define: {missing}"


def test_the_adapter_no_longer_defines_the_resource_surface() -> None:
    """The seam is a move, not a copy: a second `_ANALYSIS_STORE` would be two stores."""
    defined = _top_level_defs(MCP_SRC / "adapter.py")
    leftover = [n for n in RESOURCE_NAMES if n in defined]
    assert not leftover, f"adapter.py still defines the resource surface: {leftover}"


def test_the_tool_surface_stays_in_the_adapter() -> None:
    defined = _top_level_defs(MCP_SRC / "adapter.py")
    for name in ("call_mcp_tool", "list_tools", "list_mcp_tools", "MCP_TOOL_MAP"):
        assert name in defined, f"the tool surface moved out of the adapter: {name} gone"


def test_resources_does_not_import_the_dispatcher() -> None:
    """Dependency direction: the resource side must not reach back into the tool side.

    Without this the split is a filing cabinet -- two modules that need each other, which is the
    same coupling in two files instead of one.
    """
    tree = ast.parse((MCP_SRC / "resources.py").read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports |= {a.name for a in node.names}
    assert not [m for m in imports if m.endswith("adapter")], sorted(imports)


def test_the_server_wires_both_surfaces_from_where_they_live() -> None:
    """`server.py` must import the resources from `dsa_mcp.resources`, not through the adapter."""
    tree = ast.parse((MCP_SRC / "server.py").read_text(encoding="utf-8"))
    by_module: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            by_module[node.module] = {a.name for a in node.names}
    resources = by_module.get("dsa_mcp.resources", set())
    tools = by_module.get("dsa_mcp.adapter", set())
    assert {"list_resources", "read_resource"} <= resources, by_module
    assert {"call_mcp_tool", "list_mcp_tools"} <= tools, by_module


def test_the_analysis_store_the_isolation_fixture_clears_is_this_one() -> None:
    """The process-global handle store is still the one §87 isolates, wherever it now lives.

    Read from `conftest.py`'s AST rather than restated, the way §87's completeness guard does: a
    second copy of the container would make the fixture clear a dict nobody writes to.
    """
    conftest = REPO / "conftest.py"
    tree = ast.parse(conftest.read_text(encoding="utf-8"))
    entry = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(getattr(t, "id", "") == "_ISOLATED_GLOBALS" for t in n.targets)
    )
    pairs = {
        (ast.literal_eval(elt.elts[0]), ast.literal_eval(elt.elts[1]))
        for elt in entry.value.elts
        if isinstance(elt, ast.Tuple)
    }
    assert ("dsa_mcp.resources", "_ANALYSIS_STORE") in pairs, pairs
    assert ("dsa_mcp.adapter", "_ANALYSIS_STORE") not in pairs, pairs

    from dsa_mcp import resources
    from dsa_mcp.adapter import store_analysis
    from dsa_mcp.resources import _ANALYSIS_STORE, list_resources, read_resource

    assert store_analysis.__globals__ is resources.__dict__, (
        "store_analysis still bound to the adapter"
    )
    assert list_resources.__globals__ is resources.__dict__
    assert read_resource.__globals__ is resources.__dict__
    _ANALYSIS_STORE.clear()
    store_analysis(
        "seam-probe", {"run_id": "seam-probe", "evidence": [{"id": "e1"}], "artifacts": []}
    )
    assert _ANALYSIS_STORE.keys() == {"seam-probe"}, (
        "the store the writer reaches is not the isolated one"
    )
    uris = {r["uri"] for r in list_resources()}
    assert "evidence://seam-probe" in uris
    served = asyncio.run(read_resource("evidence://seam-probe"))
    assert served["mimeType"] == "application/json", served
    assert "e1" in served["text"], served


def test_the_adapter_still_resolves_dataset_uris_for_the_analyze_tool() -> None:
    """The dispatcher keeps needing the catalogue; that dependency is explicit, not shared state."""
    tree = ast.parse((MCP_SRC / "adapter.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if "resources" in node.module:
                imported |= {a.name for a in node.names}
    assert "_discover_datasets" in imported and "store_analysis" in imported, sorted(imported)
