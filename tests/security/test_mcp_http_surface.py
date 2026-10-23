"""The HTTP MCP surface offers 17 tools, and the two it withholds are withheld for a measured reason.

Decided by the owner on 2026-10-23, after `AUDIT_LEDGER.md` 265 measured that `run_python`'s AST deny list is
not a boundary -- `pl.os.walk('/')`, `pl.os.remove('…')` and `pl._dependencies.subprocess.Popen('…')` all pass
`_check_ast`, because polars re-exports `os` and `subprocess` -- and that no in-process fix exists, since an
interpreter running as the API's own user holds that user's rights. `run_sql` had already needed an
engine-level switch to stop reading arbitrary files (264), and its replacement-scan bypass is the kind of hole
a name list cannot close. The surface takes no credential: `AuthMiddleware` is `/api/*`-only.

So the two execution tools are removed from the HTTP surface, in both directions -- not advertised, not
callable -- while `dsa mcp` (stdio, launched by the person who owns that machine) keeps the whole registry.
What the HTTP surface still does reach, `profile_dataset`'s arbitrary path read and its path-existence oracle,
is unchanged and still documented: withholding two tools narrows the exposure, it does not close it.

`_never_runs` is the witness that matters. A refusal that reaches the dispatcher and then gets discarded would
satisfy a status-code test, so these tests fail if the tool body is entered at all.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from dsa_mcp import server as mcp_server
from dsa_mcp.adapter import HTTP_WITHHELD_TOOLS, MCP_TOOL_MAP, tools_for_wire
from dsa_mcp.server import app

WITHHELD = frozenset({"run_python", "run_sql"})


def _names(payload: list[dict[str, Any]]) -> set[str]:
    return {str(t["name"]) for t in payload}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.parametrize("path", ["/mcp/tools", "/tools"], ids=["mcp-prefixed", "bare"])
def test_the_rest_listing_omits_the_withheld_tools(client: TestClient, path: str) -> None:
    body = client.get(path).json()
    names = _names(list(body["tools"]))
    assert names & WITHHELD == set(), f"{path} still advertises {sorted(names & WITHHELD)}"
    assert names == set(MCP_TOOL_MAP) - WITHHELD, (
        f"{path} should offer the registry minus the withheld pair: "
        f"extra={sorted(names - set(MCP_TOOL_MAP))} missing={sorted(set(MCP_TOOL_MAP) - WITHHELD - names)}"
    )
    assert body["count"] == len(names), (
        f"{path} counts {body['count']} tools but lists {len(names)}"
    )


def test_the_jsonrpc_listing_omits_them_too(client: TestClient) -> None:
    res = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    names = _names(list(res.json()["result"]["tools"]))
    assert names & WITHHELD == set(), sorted(names & WITHHELD)
    assert "profile_dataset" in names, (
        "the filter is refusing more than the withheld pair, which would read as a broken surface"
    )


@pytest.mark.parametrize("tool", sorted(WITHHELD))
def test_a_withheld_tool_is_not_executed_when_it_is_called_over_http(
    client: TestClient, tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refused before the dispatcher, not routed and then discarded.

    A control that fails to run proves nothing about where it failed, so the trap raises rather than returns:
    reaching `call_mcp_tool` at all is the failure the assertion below reports.
    """

    def _trap(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(f"{tool} reached the dispatcher over HTTP")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", _trap)
    res = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool, "arguments": {}},
        },
    )
    payload = res.json()
    assert "error" in payload, f"{tool} was not refused: {payload}"
    message = str(payload["error"].get("message", ""))
    assert tool in message and "dsa mcp" in message, (
        f"the refusal does not say which tool is unavailable and where to get it: {message!r}"
    )
    # Server-defined range, not -32601: the tool exists, this transport does not offer it.
    assert payload["error"]["code"] == -32000, payload["error"]


@pytest.mark.parametrize("tool", sorted(WITHHELD))
def test_the_rest_call_endpoint_refuses_them_as_well(
    client: TestClient, tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _trap(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError(f"{tool} reached the dispatcher over the REST endpoint")

    monkeypatch.setattr(mcp_server, "call_mcp_tool", _trap)
    res = client.post("/mcp/call", json={"name": tool, "arguments": {}})
    assert res.status_code == 400
    assert res.json().get("isError") is True, res.json()


def test_a_retained_tool_still_runs_so_the_filter_is_not_a_refusing_everything(
    client: TestClient,
) -> None:
    """The clean-pass direction. Without this the two refusals above pass on a surface that answers nothing."""
    res = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "inspect_dataset", "arguments": {}},
        },
    )
    payload = res.json()
    assert "error" not in payload or "not offered" not in str(payload["error"]), payload
    assert "result" in payload, f"an advertised tool was not served: {payload}"


def test_stdio_still_publishes_the_whole_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The withholding is per-transport, so the operator's own process keeps what it had.

    `tools_for_wire()` is what `stdio_main` puts on the line for `tools/list`; if it ever filtered the same
    pair, the local command would lose capability it was designed to have and the docs would be wrong twice.
    """
    names = _names(tools_for_wire())
    assert names >= WITHHELD, sorted(WITHHELD - names)
    assert names == set(MCP_TOOL_MAP), (
        f"stdio is no longer the whole registry: {sorted(names ^ set(MCP_TOOL_MAP))}"
    )


def test_the_withheld_set_is_the_pair_the_owner_decided_and_no_more() -> None:
    """Someone widening this set would be removing capability from the demo without a decision.

    The pair was chosen because each has a measured bypass and neither has an engine-level switch left to pull.
    Every other tool on the surface is read-or-compute over data the caller already supplies.
    """
    assert HTTP_WITHHELD_TOOLS == WITHHELD, sorted(HTTP_WITHHELD_TOOLS)


def test_the_boundary_the_docs_promise_is_the_boundary_the_code_keeps() -> None:
    """`docs/MCP_DESIGN.md` says which tools the HTTP surface withholds; the sentence and the set are one fact.

    Read folded, because the sentence wraps: a literal-space pattern goes blind the next time someone rewraps
    it, and a guard that misses its own sentence is the defect it exists to prevent.
    """
    from pathlib import Path

    doc = Path(__file__).resolve().parents[2] / "docs" / "MCP_DESIGN.md"
    text = " ".join(doc.read_text(encoding="utf-8").split())
    marker = "withheld from the HTTP surface"
    assert text.count(marker) == 1, (
        f"the withheld-tools sentence must appear exactly once: {text.count(marker)}"
    )
    clause = text[text.index(marker) - 260 : text.index(marker) + 260]
    for tool in sorted(WITHHELD):
        assert f"`{tool}`" in clause, f"{tool} is withheld but not named in the sentence: {clause}"
