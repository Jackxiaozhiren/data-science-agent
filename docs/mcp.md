# MCP — V3 W10 §48

> `docs/MCP_DESIGN.md` (design) + `docs/ADR/ADR-001-mcp-2026-07-28-stateless-core.md` + `packages/mcp/src/dsa_mcp/` — Stateless 2026-07-28.

## Protocol

- Stateless core (§79): no `Mcp-Session-Id` as protocol state; no `initialize/initialized` state (stateless `tools/list` + `tools/call` via `MCP_TOOL_MAP`).
- Endpoints: `GET /mcp/tools` + `POST /mcp/call` + stateless JSON-RPC `POST /mcp` (`tools/list`, `tools/call`), mounted at `app.mount("/mcp", mcp_app)`.

## Tool Discovery / Schemas / Calls / Errors

- 18 tools, per-tool `outputSchema/permissions/idempotency/timeout/cost_class/cache_hint/tool_class` (`SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT`), see `MCP_DESIGN.md`.
- Error handling + Authorization + Cache Hints + Tasks: see `MCP_DESIGN.md` and conformance tests `tests/mcp/conformance/` (7) + `tests/unit/test_mcp.py`.

## Final audit (§79–80)

The MCP compatibility matrix (§80: Protocol Version / tools/list / tools/call / Stateless / Authorization / Error Handling / Tasks / Cache Hints) has been verified live: `tools/list`, `tools/call`, stateless, headers all pass.

## Contributing

No old `Mcp-Session-Id` state. Architecture changes require ADR (`docs/ADR/ADR-XXX-*.md`).
