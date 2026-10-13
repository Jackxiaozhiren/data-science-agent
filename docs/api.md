# API

Base: `/api/v1` (served from `apps/api/src/dsa_api`).

Conventions:

- Creates return **201 + `Location`** (`/api/v1/<resource>/<id>`). The one exception is an analysis run:
  it answers **202** once the row exists and is executing, because the graph is not finished by then (see
  `POST /api/v1/analysis/` below).
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
| POST | `/api/v1/analysis/` | `{dataset_id, user_query}` → **202** + `Location`, with the row already persisted and the run executing in this process. Poll `GET /api/v1/analysis/{id}` or follow `/events`; a run that crashes lands on the row as `status: FAILED` with a generic `error`, never as a 500 on a later read. Re-submitting the same question while a run is in flight returns **200** with that run's id rather than starting a second one |
| GET | `/api/v1/analysis/` | list + `total` (paginated, optional `?dataset_id=`) |
| GET | `/api/v1/analysis/{id}` | AnalysisState (polling) |
| GET | `/api/v1/analysis/{id}/events` | SSE `agent/tool/validation/report/completed`, following the stored row while the run is still going and closing once it is terminal (JSON fallback via `Accept`) |
| GET | `/api/v1/analysis/{id}/progress` | `progress_pct + counts` |
| GET | `/api/v1/analysis/{id}/report?format=json\|markdown\|html&mode=findings\|audited` | the export pair (R-06). `audited` (default) is the stored report with evidence ids, tool trace and artifact paths; `findings` is the plain document — conclusions, numbers and limitations, with every identifier stripped by the same rule the guard tests. `mode` is checked against `dsa_agent.report_export.EXPORT_MODES`; an unknown value is a 400. `format=html` renders the audited document as one self-contained file and is refused for `findings` |
| GET | `/api/v1/analysis/{id}/artifacts` | artifacts + tool_calls + progress |
| GET | `/api/v1/analysis/{id}/evidence/{eid}` | evidence → tool_call → insights → dataset trace |
| POST | `/api/v1/analysis/{id}/approve` | HUMAN_REVIEW approval |
| POST | `/api/v1/experiments/` | programmatic experiment record → 201 (surfaced read-only in the web UI research page) |
| GET | `/api/v1/experiments/` | list + `total` (paginated, optional `?run_id=`) |
| GET | `/api/v1/experiments/{id}` | one record |
| POST | `/api/v1/experiments/compare` | rank records by shared metric (`{ids}`) |
| GET | `/api/v1/benchmarks/baseline` | the frozen aggregate, verbatim from `benchmarks/baseline/summary.json` (read-only) |
| GET | `/api/v1/benchmarks/catalog` | `{tasks, by_category, datasets, source}` computed from `benchmarks/v2/catalog.json` |
| GET | `/api/v1/research/experiments` | `{experiments, total}` -- `ablation_*` files under `research/results`, first 10 by name |
| GET | `/health` | `{status, details:{process}, version}` — liveness only: no database I/O and no optional scientific/LLM imports, so a small instance can answer probes immediately |
| GET | `/ready` | `{status, details:{process,db}, version}` — database readiness; `status` degrades to `degraded` when the DB check fails |
| GET | `/health/dependencies` | `{status, details:{duckdb,polars,llm}, version}` — deeper optional-dependency diagnostic |
| GET | `/version` | `{version, distribution, reasoning_mode}` — which build answers and what would plan a run: `version` is read from the installed distribution's metadata (`unknown` when there is none), `reasoning_mode` is `{mode, stub, provider, model, error}` resolved the same way `EnvLLMProvider` resolves it, so a UI copying it cannot claim a model ran where the runtime would refuse |
| GET | `/mcp/tools` POST `/mcp/call` POST `/mcp` | MCP (stateless 2026-07-28, see MCP Design) |
