# MCP — V4 W6 Real Integration (§36–40, 2026-07-28 Stateless)

## Levels (§30, W6)

- **Tools (L1)** ✅ 18 tools (`profile_dataset`, `inspect_dataset`, `query_dataset`, `run_sql`, `run_python`, `run_statistical_test`, `correlation_analysis`, `forecast`, `assumption_check`, `causal_check`, `train_model`, `evaluate_model`, `feature_importance`, `create_visualization`, `get_evidence`, `generate_report`, `save_artifact`, `analyze` (§36)) — `adapter.py` + `server.py` `tools/list`/`tools/call` (§40)
- **Resources (L2)** ✅ 5 schemes (`dataset://`, `evidence://`, `report://`, `artifact://`, `analysis://`) with `mimeType` + `cacheHint` — `adapter.list_resources()`/`read_resource()` (§37) + `resources/list`/`resources/read` JSON-RPC + `GET /mcp/resources` (§40)
- **Apps (L3)** ✅ Real HTML at `/mcp-app/` — `Dataset→Question→Analysis→Evidence→Viz→Report` (§36) with explicit handles `run_id`/`analysis_id` (§38) — `app.py` + `docs/v4_1/MCP_COMPATIBILITY.md`
- **Tasks (L4)** ⏳ Stub — `analyze` is sync with explicit `run_id` polling via `analysis://`; no `tasks/*` yet (W9/W10)

## Stateless Core (§38, 2026-07-28)

No `initialize` handshake (returns `32601`), no `Mcp-Session-Id`, no protocol session. App state via explicit `run_id` in `?run_id=` and resource URIs (`evidence://{run_id}`). Verified in `test_stateless_no_session` + `test_explicit_handles_stateless`.

## Adapter (§32, §37-38)

```
Core (dsa_agent, dsa_tools)
  ↓ Adapter (dsa_mcp.adapter — 18 tools, 5 resources, _ANALYSIS_STORE)
  ↓ App (dsa_mcp.app — HTML/JS at /mcp-app)
  ↓ Server (dsa_mcp.server — FastAPI at /mcp, aliases for mount)
```

- `MCP_TOOL_MAP` 18, `MCP_TOOL_CLASS` (SAFE_READ/ANALYSIS/COMPUTE/WRITE), `MCP_IDEMPOTENT` + `cache_hint`
- `analyze` tool (§36) wraps `Agent.analyze` with explicit `run_id`, stores in `_ANALYSIS_STORE` for resource reads (§38)
- `list_resources()` discovers `benchmarks/v2/datasets/*.csv` (50 max) + stored analyses → `dataset://sales` etc.; `read_resource(uri)` returns `text`/`blob` with `mimeType`

## Server (§40)

- `POST /mcp` JSON-RPC `tools/list` / `tools/call` / `resources/list` / `resources/read` + `GET /mcp/tools` / `/mcp/resources` / `/mcp/resources/read?uri=` + `POST /mcp/call`
- Aliases for mount: `/tools`, `/resources`, `/`, `""` so `app.mount("/mcp", mcp_app)` works via `TestClient(main_app).get("/mcp/tools")` and `TestClient(mcp_app).get("/mcp/tools")`
- `POST /mcp` with `initialize` → `32601` per 2026-07-28 (no handshake)

## App (§36, §39)

`packages/mcp/src/dsa_mcp/app.py` → `GET /mcp-app/` returns HTML/JS:

```js
jrpc('tools/list') → select dataset:// → fetchProfile → jrpc('tools/call',{name:'analyze',arguments:{dataset,task,run_id}}) → display evidence/report → jrpc('resources/read',{uri:'evidence://run_id'}) → render
```

Handles explicit via `?run_id=` (§38), no session. Acceptance in `tests/mcp/test_mcp_app_acceptance.py` (Discover→Call→Receive→Open Resource→Render App→Inspect Evidence).

## Compatibility (§40)

See `docs/v4_1/MCP_COMPATIBILITY.md` — 9-row matrix (stateless, tools, resources, auth, errors, cache, Tasks, Apps) with evidence.

## Tests

- `tests/mcp/conformance/test_mcp_conformance.py` — 7 tests (tools 18, metadata, errors, stateless, 32601)
- `tests/mcp/test_mcp_app_acceptance.py` — 6 tests (5 schemes, explicit handles, App via server/main, dataset/analysis resources, stateless)
