# API

Base: `/api/v1` (served from `apps/api/src/dsa_api`).

Conventions:

- Creates return **201 + `Location`** (`/api/v1/<resource>/<id>`). The one exception is an analysis run:
  it answers **202** once the row exists and is executing, because the graph is not finished by then (see
  `POST /api/v1/analysis/` below).
- The three paginated lists -- `/api/v1/datasets/`, `/api/v1/analysis/`, `/api/v1/experiments/` -- accept
  `?limit=` (1–1000, default 100) + `?offset=` (default 0) and return `{..., "total": n}` alongside the array
  (additive; old clients keep working). Any other route ignores `?limit=` rather than honouring it: the research
  list further down is capped by a constant, not by a query parameter.
- Errors keep the `{detail: string}` envelope (the web UI renders `detail`).
- Expensive `POST`s are IP rate-limited on a sliding 60-second window, `429` + `Retry-After` on breach:
  `/api/v1/analysis` 60/min (`DSA_RATE_LIMIT_ANALYSIS_PER_MIN`), `/api/v1/datasets` 30/min
  (`DSA_RATE_LIMIT_UPLOAD_PER_MIN`), `/api/v1/events` 120/min (`DSA_RATE_LIMIT_EVENTS_PER_MIN`), and
  `/api/v1/experiments` 60/min, which owns no knob of its own and follows
  `DSA_RATE_LIMIT_ANALYSIS_PER_MIN`. Reads stay unlimited; `DSA_RATE_LIMIT_ENABLED=false` turns the whole thing off.
- Opt-in auth: set `DSA_AUTH_TOKEN` to require
  `Authorization: Bearer <token>` on all `/api/*` routes
  (`/health`, `/ready`, `/version` stay public). Empty = public demo mode.
- **Visitor scoping (R-08):** every stored row carries an `owner`, and a read returns that owner's rows plus the
  published sample. Send `X-DSA-Owner: <id>` on the dataset, analysis, experiment, report and bundle routes -- or
  `?owner=<id>` on a link the browser opens itself, where no header is possible. A request with no id acts as the
  `local` owner. Someone else's id answers `404` with the same detail an id that never existed would get, so the
  API does not confirm that a run or upload is real. `shared` names the demo's own published content and is
  reserved: a client cannot be given it. Threat model, in the operator's words, is in
  [hosted-demo.md](hosted-demo.md).
- Responses carry `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a minimal
  `Content-Security-Policy` -- `default-src 'none'; frame-ancestors 'none'`, which is what a JSON API should say.
  The routes that hand an HTML *document* to a browser -- `/mcp-app/`, `/mcp-app/report/{run_id}`, and
  `GET /api/v1/analysis/{run_id}/report?format=html` -- set their own instead, derived from the bytes they return:
  every `<script>` and `<style>` block in the document is named by `sha256-` hash, so no `'unsafe-inline'` appears
  anywhere and a block added later has to be re-admitted by name. The middleware leaves a header the route already
  set alone. That split exists because the blanket policy made the App page inert -- measured 2026-10-21, Chromium
  refused its inline script and the page offered zero dataset options while the same server answered `resources/list`
  with its whole catalog, and no `TestClient`-based test could see it because none of them runs JavaScript. The
  report document carries no script at all, so its policy says `script-src 'none'`; `img-src` allows `data:` because
  the charts travel inside the file.

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/datasets/` | upload (multipart, 100MB, MIME sniff, archive guard: extension blocklist plus the file's own leading bytes) → 201 |
| GET | `/api/v1/datasets/` | list + `total` (paginated) |
| GET | `/api/v1/datasets/{id}` | profile + metadata |
| POST | `/api/v1/analysis/` | `{dataset_id, user_query}` → **202** + `Location`, with the row already persisted and the run executing in this process. Poll `GET /api/v1/analysis/{id}` or follow `/events`; a run that crashes lands on the row as `status: FAILED` with a generic `error`, never as a 500 on a later read. Re-submitting the same question while a run is in flight returns **200** with that run's id rather than starting a second one |
| GET | `/api/v1/analysis/` | list + `total` (paginated, optional `?dataset_id=`) |
| GET | `/api/v1/analysis/{id}` | AnalysisState (polling) |
| GET | `/api/v1/analysis/{id}/events` | SSE `agent/tool/validation/report/completed`, following the stored row while the run is still going and closing once it is terminal (JSON fallback via `Accept`) |
| GET | `/api/v1/analysis/{id}/progress` | `progress_pct + counts` |
| GET | `/api/v1/analysis/{id}/report?format=json\|markdown\|html&mode=findings\|audited` | the export pair (R-06). `audited` (default) is the stored report with evidence ids, tool trace and artifact paths; `findings` is the plain document — conclusions, numbers and limitations, with every identifier stripped by the same rule the guard tests. `mode` is checked against `dsa_agent.report_export.EXPORT_MODES`; an unknown value is a 400. `format=html` renders the audited document as one self-contained file and is refused for `findings` |
| GET | `/api/v1/analysis/{id}/artifacts` | artifacts + tool_calls + progress |
| GET | `/api/v1/analysis/{id}/bundle` | a zip of the artifact files this run recorded, plus a `manifest.json`. Only paths that resolve under the configured artifact root are read; a recorded path outside it, or a file the host has already cleared, is named in the manifest's `excluded` with its reason instead of being silently dropped, and `storage` repeats what `/version` says about the roots. A run with nothing includable is a **404**, not an empty archive |
| GET | `/api/v1/analysis/{id}/evidence/{eid}` | evidence → tool_call → insights → dataset trace |
| POST | `/api/v1/analysis/{id}/approve` | HUMAN_REVIEW approval |
| POST | `/api/v1/experiments/` | programmatic experiment record → 201 (surfaced read-only in the web UI research page) |
| GET | `/api/v1/experiments/` | list + `total` (paginated, optional `?run_id=`) |
| GET | `/api/v1/experiments/{id}` | one record |
| POST | `/api/v1/experiments/compare` | rank records by shared metric (`{ids}`) |
| GET | `/api/v1/provider` | The instance's own model configuration: what is stored (provider, model, endpoint, and *whether* a credential is present -- never the value), what `resolve_llm_mode()` will use and which knob decided it (`source: stored / environment / default`), and whether this process accepts a credential at all. Public on purpose: it is the read half of R-02's promise that the interface shows the effective mode |
| PUT | `/api/v1/provider` | Validate and store `{mode?, provider?, model?, base_url?, api_key?}`. **Merge, not replace**: an omitted `api_key` keeps the stored one (the response never repeats it, so the form cannot resend it), and an empty string removes it. Shape-validated only -- the route never contacts the provider, because a verification call would spend the operator's credit or ship their data unsolicited. `403` when `DSA_PROVIDER_CONFIG` is unset (a hosted demo has nowhere to keep a secret) or when the request did not arrive from this machine and no `DSA_AUTH_TOKEN` is configured; `400` when the resulting configuration could not run |
| DELETE | `/api/v1/provider` | Delete the stored settings file. Same refusals as `PUT` |
| POST | `/api/v1/events` | `{event, payload}` → **202**. The relay for the one funnel link only a browser can observe (`arrival`); see `apps/api/src/dsa_api/services/product_events.json` for the vocabulary. It is a transport, not a second authority: the payload passes the same checks the in-process emitter applies — declared keys only, the prohibited classes (query text, dataset content, user-identifying values), the identifier-shaped value rule, and the choice list the vocabulary declares for each field — and an event the vocabulary says the **api** emits is refused with a 400, so a client cannot write `run_started`, `run_completed`, `export_taken` or `starter_question_used`. An invalid payload is a 400 whose `detail` is the vocabulary's own sentence. When this instance runs without `DSA_TELEMETRY=on` the answer is the same 202 and **nothing is written**, so the route is not a way to ask whether an operator is counting. The client half is gated at build time by `NEXT_PUBLIC_TELEMETRY=on`: a bundle that was not built with it sends no request at all, so the default deployment reports nothing about whoever opens it |
| GET | `/api/v1/benchmarks/baseline` | the frozen aggregate, verbatim from `benchmarks/baseline/summary.json` (read-only) |
| GET | `/api/v1/benchmarks/catalog` | `{tasks, by_category, datasets, source}` computed from `benchmarks/v2/catalog.json` |
| GET | `/api/v1/research/experiments` | `{experiments, total}` -- `ablation_*` files under `research/results`, first 10 by name. **Not paginated**: `?limit=` and `?offset=` are ignored here, and `total` counts every file the directory holds, not the ten returned |
| GET | `/health` | `{status, details:{process}, version}` — liveness only: no database I/O and no optional scientific/LLM imports, so a small instance can answer probes immediately |
| GET | `/ready` | `{status, details:{process,db}, version}` — database readiness; `status` degrades to `degraded` when the DB check fails |
| GET | `/health/dependencies` | `{status, details:{duckdb,polars,llm}, version}` — deeper optional-dependency diagnostic |
| GET | `/version` | `{version, distribution, reasoning_mode, storage}` — which build answers and what would plan a run: `version` is read from the installed distribution's metadata (`unknown` when there is none), `reasoning_mode` is `{mode, stub, provider, model, error}` resolved the same way `EnvLLMProvider` resolves it, so a UI copying it cannot claim a model ran where the runtime would refuse; `storage` is `{durable, ephemeral_roots}`, where `ephemeral_roots` names the roles (`database`, `datasets`, `artifacts`) whose configured path is one the host may clear, and `durable` is their conjunction -- no location is published because this route is unauthenticated, and `durable` claims nothing about the volume behind a mount |
| GET | `/mcp/tools` POST `/mcp/call` POST `/mcp` | MCP (stateless 2026-07-28, see MCP Design) |
