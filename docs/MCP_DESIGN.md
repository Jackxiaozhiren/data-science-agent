# MCP Design — Phase 10 (Adapter, Stateless 2026-07-28)

## Principle
MCP is an **adapter** over the Tool Layer. Core domain (dsa_agent / dsa_datasets / dsa_tools) does NOT import dsa_mcp.

```
Core Domain (dsa_tools, dsa_agent, dsa_datasets)
      ↑
   MCP Adapter (dsa_mcp) — stateless, tool discovery, call dispatch
      ↑
   MCP Clients (Claude / Cursor / VS Code / etc) via stdio / HTTP+SSE
```

## Protocol (2026-07-28 stateless core)
- No server-side session. Each `tools/call` is self-contained.
- Tool discovery via `tools/list`; calls via `tools/call` with JSON args.
- Auth: bearer token optional (env `DSA_MCP_TOKEN`), otherwise local-only.
- MCP surface is ~13 tools mirroring Tool Layer with friendly names.

## Tools Exposed (13)
| MCP name | Backend | Input subset |
|---|---|---|
| profile_dataset | dsa_tools/profile_dataset | path/dataset_id |
| inspect_dataset | wrapper around profile_dataset (schema view) | path |
| query_dataset | run_sql convenience (SELECT) | sql, dataset_path |
| run_sql | run_sql | sql, dataset_path, max_rows |
| run_python | run_python | code, dataset_path |
| run_statistical_test | hypothesis_test | dataset_path, test, group_col... |
| correlation_analysis | correlation_analysis | dataset_path, x, y, method |
| train_model | train_model | dataset_path, target, task... |
| evaluate_model | evaluate_model | dataset_path, target... |
| create_visualization | create_chart | dataset_path, chart_type, x, y... |
| get_evidence | create_evidence + validate_result (read) | evidence_id / claim |
| generate_report | generate_report | run_id, markdown... |
| save_artifact | save_artifact | run_id, type, filename, content |

## Implementation
- `dsa_mcp/adapter.py` — stateless registry bridging MCP JSON → BaseTool.run
- `dsa_mcp/server.py` — FastMCP-like HTTP server on /mcp (JSON-RPC 2.0), plus STDIO mode for Claude Desktop
- No global mutation of core; bootstrap idempotent.

## Out of Scope (V0.1)
- OAuth / remote registry
- Streaming tool outputs (deferred to SSE in analysis router)
- Client SDK generation
