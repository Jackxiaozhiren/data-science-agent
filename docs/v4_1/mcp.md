# MCP — V4.1 §36-40 (18 Tools, 5 Resources, App, Stateless 2026-07-28)

**Tools L1 (§36):** 18 (`profile_dataset`, `inspect_dataset`, `query_dataset`, `run_sql`, `run_python`, `run_statistical_test`, `correlation_analysis`, `forecast`, `assumption_check`, `causal_check`, `train_model`, `evaluate_model`, `feature_importance`, `create_visualization`, `get_evidence`, `generate_report`, `save_artifact`, `analyze` (§36 full loop)) — `MCP_TOOL_CLASS` etc., `MCP_COMPATIBILITY.md`.

**Resources L2 (§37):** 5 schemes `dataset://` (50), `evidence://`, `report://`, `artifact://`, `analysis://` with `mimeType`/`cacheHint` — `list_resources()`/`read_resource()` + `resources/list`/`resources/read` JSON-RPC + `GET /mcp/resources`.

**Apps L3 (§36):** Real HTML at `GET /mcp-app/` → JS `jrpc('tools/list')` → `dataset://` select → `tools/call analyze` (explicit `run_id`) → `resources/read evidence://` → render (`W6_MCP_APP.md`).

**Stateless (§38):** No `initialize`, no `Mcp-Session-Id`, explicit handles `run_id/analysis_id/dataset` in `?run_id=` and URIs, `stateless` verified (`test_explicit_handles_stateless`).

**Compatibility (§40):** `MCP_COMPATIBILITY.md` 9 rows (stateless, tools, resources, auth, errors, cache, Tasks stub, Apps).

**Tests:** `mcp/conformance` 7 + `test_mcp_app_acceptance` 6 (5 schemes, explicit handles, App via server/main).

See `packages/mcp/src/dsa_mcp/*` + `W6_MCP_APP.md` + `MCP_COMPATIBILITY.md`.
