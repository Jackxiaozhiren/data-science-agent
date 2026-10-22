"""The stdio transport had no door: nothing in the product could reach ``stdio_main``.

``docs/MCP_DESIGN.md`` advertises clients connecting "via stdio / HTTP+SSE", and ``dsa_mcp.server.stdio_main`` is a
real line-delimited JSON-RPC loop. But the only console script the distribution installs is ``dsa``, ``dsa mcp``
printed the tool list and returned, and no test spawned the server at all -- so the function was reachable only by
importing it in-process, which no client does. Four tests were named ``*_stdio_*`` and every one of them drove the
HTTP app with ``TestClient``, which never opens a stdin pipe; one of them asserted
``status_code in (200, 404, 405)``, a claim that cannot fail for the wrong reason.

This file spawns the installed ``dsa`` script with ``mcp --stdio`` and speaks to it the way an MCP client config
does: write a request line, read a response line. The four tests are the protocol surface a client actually touches
-- discovery with real ``inputSchema``, a tool call, an argument error, and a malformed line answered with a parse
error instead of a crash.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def _dsa_script() -> str:
    sibling = Path(sys.executable).parent / "dsa"
    found = sibling if sibling.exists() else shutil.which("dsa")
    assert found, (
        f"no `dsa` console script beside {sys.executable}; the distribution installs it, so a test environment "
        "without it cannot prove the CLI surface"
    )
    return str(found)


def _exchange(lines: list[Any]) -> list[dict[str, Any]]:
    payload = "".join(
        json.dumps(line) + "\n" if not isinstance(line, str) else line + "\n" for line in lines
    )
    proc = subprocess.run(
        [_dsa_script(), "mcp", "--stdio"],
        input=payload,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(Path(__file__).resolve().parents[2]),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr[-400:]}"
    out = []
    for raw in proc.stdout.splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def test_stdio_discovery_publishes_protocol_schemas() -> None:
    replies = _exchange([{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}])
    assert len(replies) == 1, replies
    tools = replies[0]["result"]["tools"]
    assert len(tools) >= 19, f"stdio discovery offered {len(tools)} tools"
    by_name = {t["name"]: t for t in tools}
    assert "inputSchema" in by_name["run_sql"], sorted(by_name["run_sql"])
    assert {"sql", "dataset_path"} <= set(by_name["run_sql"]["inputSchema"]["properties"]), by_name[
        "run_sql"
    ]["inputSchema"]
    assert all("input_schema" not in t for t in tools), (
        "stdio still publishes the Python attribute name, which no MCP client reads"
    )


def test_stdio_calls_a_tool_and_returns_its_result() -> None:
    replies = _exchange(
        [
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "profile_dataset",
                    "arguments": {"path": "benchmarks/v2/datasets/sales.csv"},
                },
            }
        ]
    )
    result = replies[0]["result"]
    assert result.get("isError") is not True, result
    assert "rows" in json.dumps(result)[:4000] or "columns" in json.dumps(result)[:4000], (
        f"the profile result carries neither rows nor columns: {str(result)[:200]}"
    )


def test_stdio_answers_a_malformed_line_with_a_parse_error_not_a_crash() -> None:
    replies = _exchange(
        ["this is not json", {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}]
    )
    assert replies[0]["error"]["code"] == -32700, replies[0]
    assert "result" in replies[1], (
        "the loop died on the bad line instead of answering the next request"
    )


def test_stdio_reports_a_missing_required_argument() -> None:
    replies = _exchange(
        [
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "causal_check",
                    "arguments": {"dataset_path": "benchmarks/v2/datasets/sales.csv"},
                },
            }
        ]
    )
    err = replies[0].get("error") or {}
    assert err, f"an argument-less causal_check should not report success: {replies[0]}"


@pytest.mark.parametrize("flag", ["--stdio"])
def test_the_flag_is_advertised_where_a_user_would_look(flag: str) -> None:
    """``--stdio`` has to be findable from ``dsa mcp --help``, or the door exists only for whoever reads the source."""
    proc = subprocess.run(
        [_dsa_script(), "mcp", "--help"], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, proc.stderr[-300:]
    assert flag in proc.stdout, f"`dsa mcp --help` does not mention {flag}: {proc.stdout}"
