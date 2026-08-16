# API

Base: `/api/v1` (served from `apps/api/src/dsa_api`).

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/datasets/` | upload (multipart, 100MB, MIME sniff, archive bomb guard) |
| GET | `/api/v1/datasets/{id}` | profile + metadata |
| POST | `/api/v1/analysis/` | `{dataset_id, user_query}` → `run_id` (Agent graph) |
| GET | `/api/v1/analysis/{id}` | AnalysisState (polling) |
| GET | `/api/v1/analysis/{id}/events` | SSE `agent/tool/validation/report/completed` (JSON fallback via `Accept`) |
| GET | `/api/v1/analysis/{id}/progress` | `progress_pct + counts` |
| GET | `/api/v1/analysis/{id}/report?format=json\|markdown` | report |
| GET | `/api/v1/analysis/{id}/artifacts` | artifacts + tool_calls + progress |
| GET | `/api/v1/analysis/{id}/evidence/{eid}` | evidence → tool_call → insights → dataset trace |
| POST | `/api/v1/analysis/{id}/approve` | HUMAN_REVIEW approval |
| GET | `/health` | `{status, details:{db,duckdb,polars,llm}, version}` |
| GET | `/ready` | readiness (mirrors health) |
| GET | `/version` | version |
| GET | `/mcp/tools` POST `/mcp/call` POST `/mcp` | MCP (stateless 2026-07-28, see MCP Design) |
