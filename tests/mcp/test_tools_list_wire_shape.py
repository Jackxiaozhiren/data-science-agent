"""`tools/list` has to say what a tool takes, under the name the protocol uses.

The schemas were built all along: `_tool_input_schema` derives each one from the backend tool's pydantic input model,
and `list_mcp_tools` puts it on ``MCPToolDef.input_schema``. What left the process was the Python attribute name --
every boundary serialized with the default aliases, so a client parsing MCP's ``inputSchema`` found nothing and read
every tool as taking no arguments at all. Measured before the fix: all 19 advertised tools returned
``{"inputSchema": {}}`` from `/mcp` while `/mcp/tools` and the object model itself carried real properties. Nothing
noticed because the two existing tests assert on the Python object (`t.input_schema is not None`) rather than on the
bytes a client receives.

These guards read the wire shape at each boundary and compare advertised properties against the backend model that
owns them, so the check is a relation between two owners, not a typed list.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from typing import Any

from fastapi.testclient import TestClient
from dsa_tools import bootstrap, get as get_tool, list_tools as registered_backends

from dsa_mcp.adapter import MCP_TOOL_MAP
from dsa_mcp.server import app as mcp_app


def _tool_names(payload: list[dict[str, Any]]) -> set[str]:
    return {str(t["name"]) for t in payload}


def _rest_http() -> list[dict[str, Any]]:
    client = TestClient(mcp_app)
    body = client.get("/mcp/tools").json()
    return list(body["tools"])


def _jsonrpc_http() -> list[dict[str, Any]]:
    client = TestClient(mcp_app)
    res = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    return list(res.json()["result"]["tools"])


def _cli() -> list[dict[str, Any]]:
    import pytest

    from data_science_agent.cli import main

    buf = io.StringIO()
    monkey = pytest.MonkeyPatch()
    monkey.setattr("sys.argv", ["dsa", "mcp"])
    try:
        with redirect_stdout(buf):
            try:
                main()
            except SystemExit:
                pass
    finally:
        monkey.undo()
    parsed = json.loads(buf.getvalue().strip())
    return list(parsed)


def _backends_by_tool() -> dict[str, str]:
    bootstrap()
    return {
        name: backend for name, backend in MCP_TOOL_MAP.items() if backend in registered_backends()
    }


def test_every_boundary_publishes_the_protocol_field_name() -> None:
    """The shape is checked at each boundary; the *sets* differ there on purpose, and the difference is named.

    HTTP withholds the two execution tools -- see `tests/security/test_mcp_http_surface.py` and `MCP_DESIGN.md` --
    so asserting "every boundary carries the whole registry" would either fail or tempt someone to widen the
    filter back out. What must hold at every boundary is that nothing is invented and the protocol field name is
    used, and what must hold across them is exactly the documented asymmetry.
    """
    from dsa_mcp.adapter import HTTP_WITHHELD_TOOLS

    boundaries = (
        ("GET /mcp/tools", _rest_http()),
        ("POST /mcp tools/list", _jsonrpc_http()),
        ("dsa mcp", _cli()),
    )
    for label, tools in boundaries:
        assert tools, f"{label} published no tools at all"
        for t in tools:
            assert "inputSchema" in t, (
                f"{label}: a tool without the protocol field name: {sorted(t)}"
            )
            assert t["inputSchema"], f"{label}: {t['name']} advertises an empty inputSchema"
        assert _tool_names(tools) <= set(MCP_TOOL_MAP), (
            f"{label} invented names: {sorted(_tool_names(tools) - set(MCP_TOOL_MAP))}"
        )
    stdio = _tool_names(dict(boundaries)["dsa mcp"])
    assert stdio == set(MCP_TOOL_MAP), (
        f"stdio no longer publishes the whole registry: {sorted(stdio ^ set(MCP_TOOL_MAP))}"
    )
    for label in ("GET /mcp/tools", "POST /mcp tools/list"):
        served = _tool_names(dict(boundaries)[label])
        assert served == stdio - HTTP_WITHHELD_TOOLS, (
            f"{label} differs from stdio by more than the withheld pair: "
            f"extra={sorted(served - stdio)} missing={sorted(stdio - served)}"
        )


def test_the_documented_table_is_the_served_surface() -> None:
    """`docs/MCP_DESIGN.md` claims its table is the tool surface, so every served name has to have a row.

    The table had drifted to 13 of 19 -- `analyze` among the missing -- while the heading's own numeral made it look
    deliberate. A name added to ``MCP_TOOL_MAP`` without a row is what this catches.
    """
    from pathlib import Path

    doc = Path(__file__).resolve().parents[2] / "docs" / "MCP_DESIGN.md"
    rows = {
        line.split("|")[1].strip()
        for line in doc.read_text(encoding="utf-8").splitlines()
        if line.startswith("| ") and "|" in line[2:]
    }
    missing = sorted(set(MCP_TOOL_MAP) - rows)
    assert not missing, f"tools published but not documented in docs/MCP_DESIGN.md: {missing}"
    assert "(13)" not in doc.read_text(encoding="utf-8"), (
        "the heading counts the surface again; the table and tools/list are the owners"
    )


def test_advertised_parameters_are_the_ones_the_backend_declares() -> None:
    """The advertised property set equals the backend model's own, for every registry-backed tool.

    Read from the complete published shape (`tools_for_wire`, what stdio serves) rather than from one HTTP
    boundary, so the two withheld tools are still checked: the property names a client must see are a property of
    the registry, not of the transport that happens to withhold them.
    """
    from dsa_mcp.adapter import tools_for_wire

    tools = {t["name"]: t for t in tools_for_wire()}
    covered = 0
    for mcp_name, backend in _backends_by_tool().items():
        declared = set(
            (get_tool(backend).input_model.model_json_schema().get("properties") or {}).keys()
        )
        advertised = set((tools[mcp_name]["inputSchema"].get("properties") or {}).keys())
        assert advertised == declared, (
            f"{mcp_name} advertises {sorted(advertised)} but {backend} declares {sorted(declared)}"
        )
        covered += 1
    assert covered >= 15, f"only {covered} tools could be cross-checked against a backend model"


def test_analyze_advertises_the_argument_it_refuses_to_run_without() -> None:
    """`analyze` is hand-written rather than registry-backed, so pin it to its documented requirement."""
    tools = {t["name"]: t for t in _jsonrpc_http()}
    props = set((tools["analyze"]["inputSchema"].get("properties") or {}).keys())
    assert {"task", "dataset"} <= props, (
        f"analyze's schema omits what the dispatcher demands: {sorted(props)}"
    )
    client = TestClient(mcp_app)
    res = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "analyze", "arguments": {}},
        },
    )
    result = res.json()["result"]
    assert result["isError"] is True and result["content"][0]["text"].startswith(
        "task/question required"
    ), f"the dispatcher no longer names the required field: {res.json()}"
