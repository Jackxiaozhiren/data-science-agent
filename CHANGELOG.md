# Changelog

## 1.2.0 — Docs closeout (upcoming)
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
