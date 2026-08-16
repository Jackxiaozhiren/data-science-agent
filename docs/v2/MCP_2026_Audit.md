# MCP 2026-07-28 Audit (W8)

- Date: 2026-08-16 · Branch: `main` · Verified live: `uv run pytest tests/mcp/conformance -v` 7 passed

| Item | Before (v1.8.0) | After (W8) |
|---|---|---|
| `Mcp-Session-Id` usage | none (stateless already) | unchanged — no session |
| `initialize` handshake | returned `2024-11-05` | removed (`32601 Method not found`) per stateless core |
| `MCPToolDef` fields | `name/description/input_schema` | + `output_schema/permissions/idempotency/timeout_ms/cost_class/tool_class/cache_hint` |
| Tool classes | undocumented | `MCP_TOOL_CLASS`: SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT per V2 §43 |
| State handling | implicit | explicit app handles `analysis_id/run_id/dataset_id` — no protocol session |
| Conformance | `tests/unit/test_mcp.py` 7 tests | + `tests/mcp/conformance/test_mcp_conformance.py` 7 tests (discovery, list, call, invalid params/schema, timeout shape, errors, stateless, repeated, caching) |

Basis: V2 spec §39–44; `docs/MCP_DESIGN.md` updated by behavior (adapter stateless over `dsa_tools` → `FastMCP-like HTTP /mcp + STDIO`).
