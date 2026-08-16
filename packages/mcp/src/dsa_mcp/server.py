from __future__ import annotations

import json
import sys
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from dsa_mcp.adapter import call_mcp_tool, list_mcp_tools

app = FastAPI(title="Data Science MCP Server", version="0.1.0")


@app.get("/mcp/tools")
async def mcp_tools_list() -> dict[str, Any]:
    tools = list_mcp_tools()
    return {"tools": [t.model_dump(mode="json") for t in tools], "count": len(tools)}


@app.post("/mcp/call")
async def mcp_call(body: dict[str, Any]) -> JSONResponse:
    name = body.get("name") or body.get("tool")
    arguments = body.get("arguments") or body.get("input") or {}
    if not name:
        return JSONResponse({"isError": True, "error": "Missing tool name"}, status_code=400)
    result = await call_mcp_tool(name, arguments if isinstance(arguments, dict) else {})
    status = 200 if not result.get("isError") else 400
    return JSONResponse(result, status_code=status)


@app.post("/mcp")
async def mcp_jsonrpc(request: Request) -> JSONResponse:
    body = await request.json()
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    if method == "tools/list":
        tools = list_mcp_tools()
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [t.model_dump(mode="json") for t in tools]},
            }
        )

    if method == "tools/call":
        raw_name = params.get("name")
        name: str = raw_name if isinstance(raw_name, str) and raw_name else ""
        if not name:
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing tool name"},
                },
                status_code=200,
            )
        arguments = params.get("arguments") or {}
        result = await call_mcp_tool(name, arguments if isinstance(arguments, dict) else {})
        if result.get("isError"):
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": result.get("error")},
                },
                status_code=200,
            )
        return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        },
        status_code=200,
    )


async def stdio_main() -> None:
    import asyncio

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            sys.stdout.write(
                json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}})
                + "\n"
            )
            sys.stdout.flush()
            continue
        method = msg.get("method")
        params = msg.get("params") or {}
        req_id = msg.get("id")
        if method == "tools/list":
            tools = list_mcp_tools()
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": [t.model_dump(mode="json") for t in tools]},
            }
        elif method == "tools/call":
            raw_name2 = params.get("name")
            name2: str = raw_name2 if isinstance(raw_name2, str) and raw_name2 else ""
            if not name2:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing tool name"},
                }
            else:
                arguments = params.get("arguments") or {}
                result = await call_mcp_tool(
                    name2, arguments if isinstance(arguments, dict) else {}
                )
                if result.get("isError"):
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32602, "message": result.get("error")},
                    }
                else:
                    resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
