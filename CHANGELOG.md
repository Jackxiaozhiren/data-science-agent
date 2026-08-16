# Changelog

## 1.7.0 — Publishability: README + examples sync (upcoming)
- `README` resynced: `~86 tests / 81 mypy / 17 tools / 50/50 @1.0` + `dv/health` details + `ready` + benchmark/seven-routes.
- `examples/README` expanded with reproducibility (`artifacts/reports/<run_id>`) and health map + full `curl` smoke.

## 1.6.0 — Hardening: compose + web build + cov gate
- `docker compose config` + `healthcheck (interval/timeout/retries/start_period)` + `depends_on: healthy` verified.
- Web `npm run build --workspace=dsa-web` → 7 routes green (dashboard/datasets/detail/analysis/trace/reports).
- `pytest --cov 74%` · `mypy 81` clean · `ruff` gated; benchmark 50/50 @1.0 retained.

## 1.5.0 — Reproducibility: executable notebook + chart-embedded report
- `analysis.ipynb` from skeleton → executable cells (profile + per-tool `run_sql/correlation/hypothesis/.../chart` + full `run_analysis`) via `build_notebook(run_id, dataset_path, query, plan, tool_calls)`.
- `report.md` embeds `![chart](artifact.png)` for `create_chart` outputs.
- `pyproject` + `config.version` → 1.5.0.

## 1.4.0 — Performance: cache + parallel
- `CachedLLMProvider` (LRU 128, TTL 600s) · tool output memoization `_TOOL_CACHE` in `graph.py`.
- Independent tool batch via `asyncio.gather` (`correlation/hypothesis/assumption/chart/run_sql`) — mean_latency 73ms → 39.8ms.
- `pyproject` + `config.version` → 1.4.0.

## 1.3.0 — Release readiness + benchmark 50/50
- Benchmark drift scan: `uv run dsa --limit 50` → 50/50 (task 1.0 / sql 1.0 / statistical 1.0 / code 1.0 / evidence 1.0) · 8 categories @ 1.0.
- `docker compose config` + healthcheck validated (`/health`→`/ready`).
- Release notes polished; `README` links verified.

## 1.2.0 — Docs closeout
- MkDocs nav hardened (tabs/sections), `docs/` fleshed out: `getting-started / agent / tools / statistics / evidence / api / security / research`.
- `THIRD_PARTY_LICENSES.md` final CC0 note; versioned via `pyproject.toml`.

## 1.1.0 — Observability & frontend polish
- `/health` + `/ready` now probe `db / duckdb / polars / llm:{active, status}` with `version`.
- Frontend `datasets` loading/empty states + error handling.

## 1.0.0 — Evidence-Grounded v1 (freeze)
- Phases 0-11, 75+ tests, `uv run dsa --limit 50` 50/50 (1.0/1.0/1.0), compose healthcheck, 7 frontend routes.

## 0.5.0 — Benchmark 100%
- Fix date-JSON evidence serialization + SQL-aware planner + honest statistical metric; sql 0.0 → 1.0.

## 0.4.x — LangGraph StateGraph
- Checkpointed `understand → plan → exec_step* → critic → report` (MemorySaver).

## 0.3.0 — Causal stub + experiments
- `causal_check` (never passes bar) + `/api/v1/experiments` compare.

## 0.2.0 — Forecast
- `forecast / assumption_check / feature_importance`; acceptance: decline + 30-day forecast.

## 0.1.0 — Phase 1 scaffold
- Monorepo, datasets/evidence/tool/benchmark/mcp/docs.
