"""docs/api.md declares the shape of the health endpoints; the handlers say otherwise.

The table row for ``GET /health`` advertises ``details:{db,duckdb,polars,llm}``. The handler
returns ``details:{"process":...}`` only; ``db`` is added on ``/ready``, and the
``{duckdb,polars,llm}`` probe is a third route (``/health/dependencies``) that the table does
not list at all. ``ci.yml`` asserts the *code* (``set(body["details"]) == {"process"}``), so
the documented contract and the enforced one disagree.

Compared by parsing the handlers, not by calling them: a TestClient request runs ``init_db()``
and would write SQLite into the working tree.
"""

from __future__ import annotations

import ast
import pathlib
import re

_API_DOC = pathlib.Path("docs/api.md")
_HEALTH_SRC = pathlib.Path("apps/api/src/dsa_api/routers/health.py")


def _documented_paths() -> dict[str, set[str]]:
    """Map ``/health``-family paths to the ``details:{...}`` key set the table claims."""
    rows: dict[str, set[str]] = {}
    for line in _API_DOC.read_text(encoding="utf-8").splitlines():
        cell = line.strip()
        if not cell.startswith("| GET |"):
            continue
        path_match = re.search(r"`(/health[a-z/]*|/ready)`", cell)
        if not path_match:
            continue
        detail_keys = re.search(r"details:\{([^}]*)\}", cell)
        rows[path_match.group(1)] = (
            {k.strip() for k in detail_keys.group(1).split(",")} if detail_keys else set()
        )
    return rows


def _route_of(node: ast.AsyncFunctionDef) -> str | None:
    for dec in node.decorator_list:
        if (
            isinstance(dec, ast.Call)
            and dec.args
            and isinstance(dec.args[0], ast.Constant)
            and isinstance(dec.args[0].value, str)
            and (dec.args[0].value.startswith("/health") or dec.args[0].value == "/ready")
        ):
            return dec.args[0].value
    return None


def _returned_detail_keys() -> dict[str, set[str]]:
    """The ``details`` keys each health handler actually builds, read from its return dict."""
    tree = ast.parse(_HEALTH_SRC.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        route = _route_of(node)
        if route is None:
            continue
        keys: set[str] = set()
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Dict):
                for k, v in zip(stmt.keys, stmt.values, strict=False):
                    if (
                        isinstance(k, ast.Constant)
                        and k.value == "details"
                        and isinstance(v, ast.Dict)
                    ):
                        keys |= {kk.value for kk in v.keys if isinstance(kk, ast.Constant)}
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and stmt.target.id == "details"
                and isinstance(stmt.value, ast.Dict)
            ):
                keys |= {kk.value for kk in stmt.value.keys if isinstance(kk, ast.Constant)}
        out[route] = keys
    return out


def test_health_family_endpoints_are_all_documented() -> None:
    documented = set(_documented_paths())
    shipped = set(_returned_detail_keys())
    assert shipped, "no health handler parsed, so this test checks nothing"
    missing = sorted(shipped - documented)
    assert not missing, f"routes shipped but absent from docs/api.md: {missing}"


def test_documented_details_match_returned_details() -> None:
    doc = _documented_paths()
    code = _returned_detail_keys()
    mismatched = {
        path: {"doc": sorted(keys), "code": sorted(code[path])}
        for path, keys in doc.items()
        if path in code and code[path] and keys != code[path]
    }
    assert not mismatched, (
        f"docs/api.md promises a different shape than the handler builds: {mismatched}"
    )
