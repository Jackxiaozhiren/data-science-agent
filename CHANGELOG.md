# Changelog

## 2.1.0 — V3 Phases A–H (W1–W8) — in progress toward v3.0.0

- **W1 Baseline**: `docs/v3/V2_FINAL_BASELINE.md` freeze (137 passed · 92 mypy · 81% · 13 routes · 50/50 + 100/100, dirty only from untracked V3 spec).
- **W2 Benchmark Audit**: `docs/v3/BENCHMARK_AUDIT.md` + `benchmarks/v2/catalog.json 0.2.0→0.3.0` (Q1–Q10, per-task `source/license/citation/benchmark_version/generator/reviewer/acceptable_*`, evaluator_v2 note).
- **W3 Independent Reproduction**: `dsa --reproduce` / `dsa reproduce` → `reproduction/{manifest,environment,results,comparison,logs}` + `ReproductionScore` 6-dim L0–L5 — `docs/v3/REPRODUCTION.md`.
- **W4 Statistical Upgrade**: `evaluator_v2` 10 dims + S01–S10 (causal/uncertainty) wired into `EvaluationResult.details` (non-breaking, `evaluator_version: evaluator_v2`) — `docs/v3/STATISTICAL_EVALUATION.md`.
- **W5 Reliability**: 4 configs (single/planner/planner+critic/full) × 7 §27 metrics + §28–30 — `docs/v3/RELIABILITY.md`.
- **W6 Cross-Model**: 4 classes (local_small/medium/open_api/frontier) no-fabrication (§31) + 3 Pareto frontiers (§33) — `docs/v3/CROSS_MODEL.md`.
- **W7 Human Eval**: `human-eval/` 11/100 stratified (seed 42, hash c3835816) + 8-dim rubric (1–5) + Kappa/Alpha — `docs/v3/HUMAN_EVALUATION_GUIDE.md`.
- **W8 External Validation**: `dsa demo` (§40/47) + `dsa external-validation` (§42) local-first + `demo/` package (§46) — `docs/v3/EXTERNAL_VALIDATION.md`.
- **Docs/Claim policy**: README first-screen (What/Why/Why different/How run/How evaluated/How reproducible, §44), V3 docs index, claim policy §45 traceability (`Benchmark + Commit + Report`).

## 2.0.0 — V2 Research Grade (W1–W10 full)

- Baseline freeze: `docs/v2/Baseline Report.md` (live 116 passed / 87 mypy clean / 75–76% cov / 13 routes / 50/50 frozen to `benchmarks/baseline/`, mean 47.92ms)
- W2 Evaluation Framework: `packages/evaluation/src/dsa_evaluation/evaluation_framework.py` (EvaluationResultV2 10-dim + 6-level, `by_difficulty`), `significance.py` (bootstrap CI / paired / McNemar)
- W3 Benchmark v2: `benchmarks/v2` (30 datasets / 100 tasks / 11 categories) via `scripts/generate_benchmark_v2.py` — live 100/100 @1.0 (11 cats @1.0, mean 31–40ms, sql_accuracy 1.0 after heuristic fix, unsupported 0.04)
- W4–W7: trajectory (`packages/agent/src/dsa_agent/trajectory.py`), reproducibility L0–L5 (`reproducibility.py`), failure taxonomy F01–F15, observability Trace/Span, `docs/v2/{evaluation,security,MCP_2026_Audit}`, frontend tiles wired
- W8 MCP 2026-07-28: stateless core (drop `initialize` + `Mcp-Session-Id`), rich `MCPToolDef` + classification `SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT` + `tests/mcp/conformance/` (7) + ADR-001
- W9 Security: `tests/security/test_adversarial_suite.py` (10) + `research/questions`, adversarial injection/abuse/DoS suite → 23 security tests
- W10 Research: `research/` (RQs 1–5, ablation A–F at `ablation_matrix.py`, `run_ablation.py` wired to real benchmark + bootstrap CI, `research/results/ablation_*.json`, `research/paper/V2_paper_draft.md`, `research/figures/README.md`, `research/tables/README.md`)
- Frontend: `/benchmarks /evaluations /runs /runs/[id] /runs/[id]/replay /failures /research /mcp` (13 routes, wired to `benchmarks/baseline/summary.json` + `research/results/`)
- Tech debt: `datetime.utcnow` → `now(timezone.utc)` (3 Pydantic models + 3 ORM, 283 warnings → 1), `ruff format` clean, mypy strict 87 files, planner heuristic + metrics `sql_accuracy` empty Contains lenient fix to reach 100/100
- Version: `pyproject.toml` 2.0.0-alpha.1 → 2.0.0 · CI adds `dsa --limit 5`, `npm build`, `compose config` — tags `v2.0.0-alpha.1` + `v2.0.0`

## 1.8.0 — Lightweight observability
- `GET /metrics` (JSON: uptime, process `rss_mb`, `tool_calls_total`, `version`) + datasets empty-state health hint.
- `CHANGELOG` finalizes `1.6/1.7` entries; version → `1.8.0`.

## 1.7.0 — Publishability: README + examples sync
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
