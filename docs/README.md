# Documentation Index

- [Architecture Freeze](../ARCHITECTURE_FREEZE_V0.1.md) — System architecture, component diagram, ERD, tool contracts, security boundary, TDR (Phase 0)
- [MCP Design](./MCP_DESIGN.md) — Stateless 2026-07-28 adapter over Tool Layer (13 tools)
- [Frontend IA](./FRONTEND_IA.md) — Routes, data flow, UI principles (Phase 7)
- [Benchmark README](../benchmarks/ds-agent-benchmark/README.md) — 20 datasets / 50 tasks / metrics + `dsa benchmark` CLI (Phase 9)
- [README](../README.md) — Quick start, API, frontend, evidence, benchmark, security, testing, Docker

## MkDocs (Phase 11 placeholder)

Full MkDocs site deferred to next iteration — current docs are Markdown in `docs/` + `README.md`.
Future sections: Getting Started, Architecture, Agent System, Tools, Statistics, ML, Evidence, MCP, Security, Benchmarks, Research, Contributing.

## API Quick Reference

```
POST /api/v1/datasets/ | GET /api/v1/datasets/{id}
POST /api/v1/analysis/ | GET /api/v1/analysis/{id} | GET /.../events (SSE) | GET /.../progress
GET  /.../report?format=markdown | GET /.../artifacts | GET /.../evidence/{id} | POST /.../approve
GET  /mcp/tools  POST /mcp/call  POST /mcp (JSON-RPC)
```

## Testing & Quality

```
uv run pytest -q         # 75 tests
uv run mypy packages     # strict
uv run ruff check .
npm run build --workspace=dsa-web  # 7 routes
```
