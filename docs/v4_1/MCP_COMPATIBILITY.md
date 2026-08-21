# MCP Compatibility — W6 §40 (MCP 2026-07-28)

> Do not reimplement protocol for testing (§40). All checks are via `dsa_mcp` adapter + FastAPI `TestClient` + `mcp/conformance` suite.

| Feature | Spec (2026-07-28) | Implementation | Status | Evidence |
|---------|-------------------|----------------|--------|----------|
| **Stateless core** | No `initialize`, no `Mcp-Session-Id`, no protocol session; app state via explicit handles (§38) | `adapter.py` stateless, `server.py` returns `32601` for `initialize`, `ANALYSIS_STORE` keyed by `run_id` | ✅ PASS | `test_no_initialize_handshake` (32601), `test_stateless_repeated_calls_and_caching` (same output), `test_explicit_handles_stateless` (different run_id → different resources) |
| **tools/list** | `tools/list` returns tool definitions with `name/description/inputSchema/outputSchema` | `server.py` `POST /mcp` `tools/list` + `GET /mcp/tools` + `GET /tools` alias; `adapter.list_mcp_tools()` 18 tools with `tool_class/permissions/timeout/cost/cache_hint` | ✅ PASS | `test_tool_discovery_and_metadata` (18, metadata), `test_tools_list_endpoint` (`/mcp/tools` 18, `/mcp` RPC) |
| **tools/call** | `tools/call` with `name` + `arguments`, returns `output` or `isError`, stateless | `server.py` `POST /mcp` `tools/call` + `POST /mcp/call` + `POST /` alias; `adapter.call_mcp_tool` validates, dispatches to `dsa_tools` or `analyze` (§36), explicit `run_id` handle | ✅ PASS | `test_tools_call_and_errors` (valid, missing sql, unknown tool, missing name), `call_mcp_tool` analyze integration |
| **resources** | `resources/list` + `resources/read` with URI templates, mimeType, cache hints (§37) | `adapter.list_resources()` 5 schemes (`dataset://`, `evidence://`, `report://`, `artifact://`, `analysis://`) concrete + templates, `read_resource(uri)`; `server.py` `GET /mcp/resources` + `POST /mcp` `resources/list/read` + stdio | ✅ PASS | `test_mcp_resource_model_five_schemes` (5 schemes), `test_mcp_resources_read_dataset_and_analysis` (`dataset://sales` CSV, `analysis://run` JSON) |
| **authorization** | No built-in auth; transport may add, but tools must handle permission denial (§23) | MCP tools declare `permissions: ["read"/"compute"/"write"]`; `adapter.check_permission` enforced in `execute_plugin_tool` (W3), MCP `analyze` stores via explicit `run_id` (no auth needed local-first) | ✅ PASS (local-first) | `test_plugin_isolation` permission denied, `mcp/conformance` no auth required |
| **errors** | Structured `isError` + `error.code/message`, not HTTP 500 for tool errors | `call_mcp_tool` returns `isError True + error`, server maps to `JSON-RPC error code -32602` (invalid params) or `200` with `isError`; unknown method `-32601` | ✅ PASS | `test_tools_call_and_errors` (invalid params → `isError`/`-32602`, unknown tool → `-32602`, unknown method → `-32601`) |
| **cache hints** | `cacheHint` for idempotent SAFE_READ (§37) | `MCPToolDef.cache_hint="max-age=60"` for `profile_dataset`, `run_sql` etc.; `MCP_IDEMPOTENT` set | ✅ PASS | `test_mcp_tools_get_sets_cache_hint` (idempotent → cache_hint), `test_tool_discovery_and_metadata` (safe read has hint) |
| **Tasks** | Long-running Tasks (MCP 2026 extension, optional) | Not implemented — `analyze` is synchronous (30s timeout) with explicit `run_id` handle that can be polled via `analysis://`; no `tasks/*` methods (returns `32601` if called) | ⚠️ NOT IMPLEMENTED (deferred) | `server.py` `tools/call` for `analyze` returns immediately with `run_id`; no `tasks/list` — intentional for MVP, §40 “do not reimplement protocol” |
| **MCP Apps** | Apps are HTML/JS at `/mcp-app` with `Dataset→Question→Analysis→Evidence→Viz→Report` (§36, §39) and explicit handles (§38) | `dsa_mcp.app` serves HTML at `GET /mcp-app/` (via `dsa_api.main` mount `/mcp-app`) with JS that `jrpc('tools/list')` → select `dataset://` → `tools/call analyze` (explicit `run_id`) → `resources/read evidence://` + `report://` → render; stateless via `?run_id=` (§38) | ✅ PASS | `test_mcp_app_acceptance_via_server` + `via_main_app` (Discover→Call→Receive→Open Resource→Render App→Inspect Evidence), `TestClient(mcp_app).get('/')` HTML contains `Dataset`+`Evidence`+`run_id` |

## Stateless Verification (§38)

- No `Mcp-Session-Id` header in any response (`test_stateless_no_session`).
- Repeated `run_sql` same args → same output, no session (`test_stateless_repeated_calls_and_caching`).
- Different `run_id` handles → different `evidence://`/`report://` resources (`test_explicit_handles_stateless`).

## App Acceptance (§39)

```
Client (TestClient)
↓ Connect (GET /mcp/tools, POST /mcp tools/list)
↓ Discover (tools/list 18, resources/list 30)
↓ Call Tool (tools/call analyze dataset://sales + task → run_id)
↓ Receive Result (output with report/evidence)
↓ Open Resource (resources/read evidence://run_id, report://run_id)
↓ Render App (GET /mcp-app/ → HTML with Dataset→Question→Analysis→Evidence→Viz→Report)
↓ Inspect Evidence (evidence:// contains claim)
```

Executed in `tests/mcp/test_mcp_app_acceptance.py` (6 tests, all pass).

## Notes

- Do not reimplement protocol for testing — all checks use `dsa_mcp` adapter + `TestClient`, no mock MCP client.
- `Tasks` are intentionally stub for W6 MVP; full async Tasks can be added in W9/W10 without breaking stateless core.
- Authorization is local-first (no token); production would add via `Authorization` header at `apps/api` layer (W7).
