# MCP — Conformance & Integration

> `docs/MCP_DESIGN.md` (design) + `docs/ADR/ADR-001-mcp-2026-07-28-stateless-core.md` + `packages/mcp/src/dsa_mcp/` — Stateless 2026-07-28.

## Protocol

- Stateless core: no `Mcp-Session-Id` as protocol state; no `initialize/initialized` state (stateless `tools/list` + `tools/call` via `MCP_TOOL_MAP`).
- Endpoints: `GET /mcp/tools` + `POST /mcp/call` + stateless JSON-RPC `POST /mcp` (`tools/list`, `tools/call`), mounted at `app.mount("/mcp", mcp_app)`.

## Tool Discovery / Schemas / Calls / Errors

- the typed tool surface, per-tool `outputSchema/permissions/idempotency/timeout/cost_class/cache_hint/tool_class` (`SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT`), see `MCP_DESIGN.md`.
- Error handling + Authorization + Cache Hints + Tasks: see `MCP_DESIGN.md` and conformance tests `tests/mcp/conformance/` (7) + `tests/unit/test_mcp.py`.

## Conformance

The MCP compatibility matrix was verified live for `tools/list`, `tools/call`, the stateless rule and the JSON-RPC
error codes -- see `tests/mcp/conformance/` and `tests/mcp/test_{stdio_transport,tools_list_wire_shape}.py`. Two
rows of that matrix are **not** capabilities of this server, and are listed here rather than marked pass: there is
no Authorization on `/mcp` or `/mcp-app` at any token setting (see `MCP_DESIGN.md`), and Tasks is a stub. The
result envelope was also wrong until 2026-10-22 -- `tools/call` answered with the product's own object instead of
MCP's required `content`, and `resources/read` with a bare item instead of `contents` -- so "verified live" once
meant that the product's own client agreed with the product's own server.

## Contributing

No old `Mcp-Session-Id` state. Architecture changes require ADR (`docs/ADR/ADR-XXX-*.md`).
