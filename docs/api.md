# API

Base: `/api/v1` (served from `apps/api/src/dsa_api`).

Conventions:

- Creates return **201 + `Location`** (`/api/v1/<resource>/<id>`).
- Lists accept `?limit=` (1–1000, default 100) + `?offset=` (default 0) and
  return `{..., "total": n}` alongside the array (additive; old clients keep working).
- Errors keep the `{detail: string}` envelope (the web UI renders `detail`).
- Expensive `POST`s are IP rate-limited (analysis 60/min, upload 30/min;
  429 + `Retry-After`; disable with `DSA_RATE_LIMIT_ENABLED=false`).
- Opt-in auth: set `DSA_AUTH_TOKEN` to require
  `Authorization: Bearer <token>` on all `/api/*` routes
  (`/health`, `/ready`, `/version` stay public). Empty = public demo mode.
- Responses carry `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, and a minimal `Content-Security-Policy`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/datasets/` | upload (multipart, 100MB, MIME sniff, archive bomb guard) → 201 |
| GET | `/api/v1/datasets/` | list + `total` (paginated) |
| GET | `/api/v1/datasets/{id}` | profile + metadata |
| POST | `/api/v1/analysis/` | `{dataset_id, user_query}` → `run_id` (Agent graph) → 201 |
| GET | `/api/v1/analysis/` | list + `total` (paginated, optional `?dataset_id=`) |
| GET | `/api/v1/analysis/{id}` | AnalysisState (polling) |
| GET | `/api/v1/analysis/{id}/events` | SSE `agent/tool/validation/report/completed` (JSON fallback via `Accept`) |
| GET | `/api/v1/analysis/{id}/progress` | `progress_pct + counts` |
| GET | `/api/v1/analysis/{id}/report?format=json\|markdown` | report |
| GET | `/api/v1/analysis/{id}/artifacts` | artifacts + tool_calls + progress |
| GET | `/api/v1/analysis/{id}/evidence/{eid}` | evidence → tool_call → insights → dataset trace |
| POST | `/api/v1/analysis/{id}/approve` | HUMAN_REVIEW approval |
| POST | `/api/v1/experiments/` | programmatic experiment record → 201 (surfaced read-only in the web UI research page) |
| GET | `/api/v1/experiments/` | list + `total` (paginated, optional `?run_id=`) |
| GET | `/api/v1/experiments/{id}` | one record |
| POST | `/api/v1/experiments/compare` | rank records by shared metric (`{ids}`) |
| GET | `/health` | `{status, details:{db,duckdb,polars,llm}, version}` |
| GET | `/ready` | readiness (mirrors health) |
| GET | `/version` | version |
| GET | `/mcp/tools` POST `/mcp/call` POST `/mcp` | MCP (stateless 2026-07-28, see MCP Design) |
