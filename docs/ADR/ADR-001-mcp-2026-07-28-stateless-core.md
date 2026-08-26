# ADR-001 — MCP 2026-07-28 Stateless Core Alignment

- Status: Accepted · Date: 2026-08-16 · Applies to: `packages/mcp`
- Related: `docs/MCP_DESIGN.md` · MCP conformance status in `docs/mcp.md`

## Problem

Live MCP at `v1.8.0` exposed `initialize` (protocolVersion `2024-11-05`) and had room to add tool metadata for 2026-07-28 stateless core (no `initialize`/`initialized` handshake, no `Mcp-Session-Id`, tools list with cache hints, Tasks extension).

## Evidence

- `packages/mcp/src/dsa_mcp/server.py` handled `method == "initialize"` → 200 with `protocolVersion 2024-11-05`.
- `MCPToolDef` had only `name/description/input_schema`. No `outputSchema/permissions/idempotency/timeout/cost_class/cache_hint/tool_class`.
- Conformance coverage lived only in `tests/unit/test_mcp.py` (7 tests); no `tests/mcp/conformance/`.

## Impact

Non-compliance would break clients speaking MCP 2026-07-28; `--limit 50` still 50/50 but MCP contract not audited for production hardening.

## Alternatives

1. Keep `initialize` dual-mode forever → retains legacy incompatibility, debt.
2. Remove `initialize` now, add rich `MCPToolDef`, add conformance, keep stateless dispatch unchanged → chosen.
3. Rewrite MCP as core domain concern → violates freeze (forbidden: rewrite backend).

## Recommendation

- Drop protocol-layer `initialize`/`initialized` (return `32601 Method not found`) while keeping app-level handles `analysis_id/dataset_id/run_id`.
- Enrich `MCPToolDef` + `MCP_TOOL_CLASS/MCP_IDEMPOTENT/MCP_WRITE` maps; generate `output_schema`, `permissions`, `timeout_ms`, `cost_class`, `cache_hint` per tool.
- Add `tests/mcp/conformance/test_mcp_conformance.py` (tool discovery, tools/list, tools/call, invalid schema/params, errors, stateless, repeated calls, tool caching) per V2 §44.
- No change to core domain imports (still adapter over `dsa_tools`).

## Migration Plan

- Callers using `initialize` must stop calling it; switch to direct `tools/list` / `tools/call` (stateless).
- No header `Mcp-Session-Id` was ever used — no migration needed.

## Rollback Plan

- Restore `if method == "initialize": return protocolVersion` branch in `server.py` and revert `test_mcp.py` assertion to `assert r2.status_code == 200` if downstream MCP clients require it; metadata fields are additive so rollback is safe.
