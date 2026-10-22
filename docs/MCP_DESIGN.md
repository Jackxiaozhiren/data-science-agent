# MCP Design — Stateless Adapter (2026-07-28)

## Principle
MCP is an **adapter** over the Tool Layer. Core domain (dsa_agent / dsa_datasets / dsa_tools) does NOT import dsa_mcp.

```
Core Domain (dsa_tools, dsa_agent, dsa_datasets)
      ↑
   MCP Adapter (dsa_mcp) — stateless, tool discovery, call dispatch
      ↑
   MCP Clients (Claude / Cursor / VS Code / etc) via stdio / HTTP+SSE
```
`dsa mcp` prints the surface as JSON; `dsa mcp --stdio` serves the same `tools/list` / `tools/call` / `resources/*`
methods over line-delimited stdin/stdout, which is what a client config that launches a command needs.

## Protocol (2026-07-28 stateless core)
- No server-side session. Each `tools/call` is self-contained.
- Tool discovery via `tools/list`; calls via `tools/call` with JSON args.
- Auth: **none on this surface.** `AuthMiddleware` covers `/api/*` only -- it returns early for any path that does
  not start with `/api/` -- so `/mcp` and `/mcp-app` are reachable without a credential even when `DSA_AUTH_TOKEN`
  is set, and there is no `DSA_MCP_TOKEN` anywhere in the code. Run the MCP endpoint only where you would run an
  unauthenticated shell: `run_python` and `run_sql` are among its tools.
- MCP surface mirrors the Tool Layer with friendly names.

## Tools Exposed
The table is the surface; `dsa mcp` prints what `tools/list` publishes, and a client reads the parameters from each
tool's `inputSchema`, which is derived from the backend's own pydantic input model rather than typed here. So this
table names the backend and the argument subset, and the schema on the wire is the authority on types and required
fields.

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
| export_artifact | export_artifact | source, filename, format, workspace |
| forecast | forecast | dataset_path, date_col, value_col, periods, method |
| assumption_check | assumption_check | dataset_path, column/columns, check, group_col |
| causal_check | causal_check | dataset_path, treatment, outcome, confounders, method |
| feature_importance | feature_importance | dataset_path, target, task, top_k |
| analyze | dsa_agent graph (§36 full loop) | dataset/dataset_path, task (alias question), run_id (alias analysis_id) |

## Implementation
- `dsa_mcp/adapter.py` — stateless registry bridging MCP JSON → BaseTool.run
- `dsa_mcp/server.py` — FastMCP-like HTTP server on /mcp (JSON-RPC 2.0), plus STDIO mode for Claude Desktop
- No global mutation of core; bootstrap idempotent.

## Out of Scope (V0.1)
- OAuth / remote registry
- Streaming tool outputs (deferred to SSE in analysis router)
- Client SDK generation
