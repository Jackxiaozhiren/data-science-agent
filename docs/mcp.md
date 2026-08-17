# MCP — V3 W10 §48

> `docs/MCP_DESIGN.md` (design) + `docs/v2/MCP_2026_Audit.md` + `docs/ADR/ADR-001-mcp-2026-07-28-stateless-core.md` + `docs/v3/V2_FINAL_BASELINE.md` §10 + `packages/mcp/src/dsa_mcp/` — Stateless 2026-07-28.

## Protocol

- Stateless core (§79): no `Mcp-Session-Id` as protocol state; no `initialize/initialized` state (stateless `tools/list` + `tools/call` via `MCP_TOOL_MAP`).
- Endpoints: `GET /mcp/tools` + `POST /mcp/call` + stateless JSON-RPC `POST /mcp` (`tools/list`, `tools/call`), mounted at `app.mount("/mcp", mcp_app)`.

## Tool Discovery / Schemas / Calls / Errors

- 17 tools, per-tool `outputSchema/permissions/idempotency/timeout/cost_class/cache_hint/tool_class` (`SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT`), see `MCP_DESIGN.md`.
- Error handling + Authorization + Cache Hints + Tasks: see `MCP_2026_Audit.md` §79 and conformance tests `tests/mcp/conformance/` (7) + `tests/unit/test_mcp.py`.

## Final audit (§79–80)

`docs/v3/MCP_COMPATIBILITY.md` (V3.1) tracks compatibility matrix (§80: Protocol Version / tools/list / tools/call / Stateless / Authorization / Error Handling / Tasks / Cache Hints). Current live: `tools/list`, `tools/call`, stateless, headers all pass.

## Contributing

No old `Mcp-Session-Id` state. Architecture changes require ADR (`docs/ADR/ADR-XXX-*.md`).
