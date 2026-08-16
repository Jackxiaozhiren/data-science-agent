# V2.0 FINAL BASELINE — V3.0 Phase A Freeze & Revalidation

> **Phase A — V2.0 Freeze & Revalidation (No code modifications)** · Generated: 2026-08-16 (Asia/Shanghai, live run)
> Commit: `9a6e410` · Describe: `v2.0.0-5-g9a6e410-dirty` (dirty = untracked `DATA_SCIENCE_AGENT_V3_0.md` + `benchmarks/ds-agent-benchmark/results` refreshes + `/tmp` outputs) · Tag: `v2.0.0` (head), `v2.0.0-alpha.1`
> Python: `3.12` (`.python-version`) / `3.9.6` system / `uv 0.11.7` · Node: `v24.15.0` · OS: Darwin ARM64 `25.6.0` · MkDocs: `1.6.1` + `material 9.0` (via `uv sync --dev`)

---

## 1. Repository State

* Root: `/Users/jackson/Data agent` · Monorepo: `apps/{api,web}` + `packages/{agent,datasets,evaluation,evidence,execution,llm,mcp,ml,reports,statistics,tools,visualization,artifacts}` · Workspaces: `uv` + `npm`
* Untracked: `DATA_SCIENCE_AGENT_V3_0.md` only (Phase A spec); Modified: `benchmarks/ds-agent-benchmark/results/{summary,results,raw_runs}.json` (parameterized run artifacts, not baseline source) · No tracked business code modifications during Phase A
* Baseline anchors (frozen): `docs/v2/Baseline Report.md` (V1.8→V2.0 freeze on `587c4bf`), `docs/v2/baseline/ARCHITECTURE.md`, `docs/v2/{evaluation.md,security.md,MCP_2026_Audit.md}`, `docs/ADR/ADR-001-*`, `benchmarks/baseline/{summary,results,raw_runs}.json`, `benchmarks/v2/catalog.json` (+ `benchmarks/v2/datasets/` 30 CSVs, `scripts/generate_benchmark_v2.py` seed 42), `research/{questions,experiments,paper,results,figures,tables}`, `tests/{regression,mcp/conformance,security/evals,unit/**}`, `apps/web/app/{benchmarks,evaluations,runs,failures,research,mcp}`
* Dependency lock: `uv.lock` (114 packages) · CI: `.github/workflows/ci.yml` gates `ruff/mypy/pytest/dsa build/mkdocs strict`

---

## 2. Git Commit

* `HEAD`: `9a6e410 chore: polish ruff + reach 80% coverage (136 tests) — scoped per-file ignores`
* Ancestors: `81131ba` (80% `generate_report`) → `2fe33d6` (ruff scoped + `utcnow→now`, 79%) → `8305832` → `777dd08 chore: release 2.0.0` → `2f8a23e` (frontend wired) → `feb31c6` (100/100 fix) → `4b1de8b feat: V2.0-alpha.1` → `587c4bf V1.8`
* Local trace: `/Users/jackson/logs/V2_Traceability.md` links each V2.0 section to commit (V2.0 lineage preserved, not re-reported here)

---

## 3. Git Tag

* `v2.0.0` at `777dd08`, `v2.0.0-alpha.1` at `4b1de8b` — V3 Phase A revalidation points to `v2.0.0`; head is `v2.0.0-5-g9a6e410-dirty` (5 commits of polish on top of `v2.0.0`, dirty only from untracked docs/artifact refresh)

---

## 4. Functional Status

* API: `apps/api` FastAPI + Pydantic + SQLAlchemy (`/.health /ready /version /metrics`, `/api/v1/datasets/{id} /analysis/{id}/{events,progress,artifacts,report,evidence,approve}`, `/experiments/compare`), async SQLite requested (falls back sync with warning if `aiosqlite` absent — current env has it)
* Agent: `Planner → DataScientist → Critic → Report` (LangGraph `langgraph_graph` w/ `MemorySaver`), budgets `max_steps 20 / max_tool_calls 40 / max_retries 3`
* Tools (17 registered via `MCP_TOOL_MAP`): `profile_dataset/run_sql/run_python/describe/correlation/hypothesis_test/regression/train_model/evaluate_model/feature_importance/forecast/create_chart/generate_report/validate_*` dispatching to `packages/tools|statistics|ml|visualization|evidence`
* Data: `dsa_datasets.loader` (CSV/Parquet/JSON/Excel, 100 MB, extension+MIME guard) + `profiler` + DuckDB read-only `SELECT/WITH/SHOW/DESCRIBE/EXPLAIN` · Python sandbox AST allowlist + 5s wall-clock · Stats `correlation/hypothesis/regression/assumption/causal_check` · Viz Plotly/Matplotlib → `artifacts/` PNGs
* Evidence/Reports: `Evidence/Insight/Artifact/ValidationResult` (`state.py` + `evidence/models.py`), graph `Insight→Evidence→ToolCall→Dataset(hash)`, `validator.validate_evidence_graph`, report `markdown/html/pdf/notebook`, reproducibility bundle (`experiment.json` + `reproduce.sh` + `analysis.ipynb`)
* Frontend: 13 routes (`/ /benchmarks /evaluations /runs /runs/[id] /runs/[id]/replay /failures /research /mcp` + `analysis/datasets/reports`) — `Next.js 15` (SSR+prerender), shadcn/ui · Backend mounts `/mcp`

---

## 5. Test Status

* **pytest (live, current tree):** `137 passed, 1 warning` — `uv run pytest -q` in `5.6s`
  * Measured as: `tests/` + `apps/api/tests` (137 collected, `testpaths` in `pyproject.toml`)
  * Suites: `regression 5 · mcp/conformance 7 · security 23 (adversarial 10 + phase8 13) · evals 2 · unit 100 (trajectory/reliability/failure/observability/significance + coverage gaps)` + `apps/api/tests/test_health 2` + `integration/e2e 10`
  * Warning count `1` only (`fastapi.testclient StarletteDeprecation`) — `filterwarnings` silences `pydantic/sqlalchemy`, and `utcnow` was migrated to `now(timezone.utc)` (9 sites: 6 source + 3 ORM), so prior `283` → `1`
  * History delta: V2.0 claim `136 passed` → live `137 passed` (+1 from `tests/unit/test_cov_mcp_server_and_llm.py` in `9a6e410`; artifact of `80%` polish, not a regression)
* **Runner config:** `pytest.ini_options` `addopts=-q --asyncio-mode=auto`, `filterwarnings` (`fastapi.testclient/pydantic/sqlalchemy ignored`)

---

## 6. Coverage

* `uv run pytest --cov --cov-report=term-missing` → **80%** (`3926 stmts / 633 miss / 926 branches / 203 partial`)
  * Up from V2.0 `75%→80%` trajectory (`2fe33d6` 79% + `81131ba` 80% via `test_generate_report_coverage.py` + `9a6e410` 80% via `test_cov_mcp_server_and_llm.py`)
  * Weak spots (post-80%): `generate_report 92%`, `create_chart 62%→92% (new)`, `mcp/server 51%`, `evidence/models` branches — `85%` would need `mcp/server+hypothesis+forecast+reports` push (spec deferred to V3 W5/W10)
  * Empty files: 5 skipped · All green under scoped gate

---

## 7. Benchmark Status

* **Catalog (v2 authoritative):** `benchmarks/v2/catalog.json` `version 0.2.0` — `30 datasets`, `100 tasks`, `11 categories` (`EDA 11 / SQL 11 / Statistics 13 / Regression 9 / Classification 9 / Time Series 8 / Visualization 8 / Data Quality 8 / Data Profiling 6 / Clustering 7 / Evidence Validation 10`, difficulties `easy 35 / medium 43 / hard 14 / expert 8`), seed `42` via `scripts/generate_benchmark_v2.py`, sha `45db0be7d65e` (12-char), each task carries `difficulty/gold_method/required_tools/gold_metrics/required_evidence/forbidden_claims`
* **Datasets on disk:** `benchmarks/v2/datasets/` `30` CSVs (on `aarch64-darwin`), `benchmarks/ds-agent-benchmark/datasets/` `20` + `benchmarks/baseline/README.md` (frozen snapshot `summary n=50 mean 47.92ms unsupported 0.06`)
* **Live runs (must-reproduce gates):**
  * `uv run dsa --limit 50` (v1 `ds-agent-benchmark`): **50/50 @1.00** `By category 8-cats @1.0`, `mean ~47ms`, `code/sql/evidence 1.0`, `unsupported 0.04–0.06` — writes `benchmarks/ds-agent-benchmark/results`
  * `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 --out /tmp/v3-phaseA-v2` (v2): **100/100 @1.00** `11 cats @1.0`, `mean 30–32ms`, `statistical_accuracy 1.0`, `sql_accuracy 1.0` (fixed `feb31c6` from `0.69`), `unsupported 0.04`, `evidence_coverage 1.0`
* **Re-run variance:** v1 mean `47.92ms` (frozen) vs live `~47–48ms`; v2 `30.78–31.66ms` — variance <2ms, `task_success_rate` stuck at `1.00` by stub evaluator design

---

## 8. Evaluation Status

* **Framework:** `packages/evaluation/src/dsa_evaluation/evaluation_framework.py` `EvaluationResultV2` (10 dims: `task_success/statistical/tool/evidence/unsupported/code/sql/reproducibility/safety/latency/token` × 6 levels `Tool→Numerical→Statistical→Interpretation→Evidence→Report`), `by_category/by_difficulty` aggregations, `bootstrap_ci/mcnemar/wilcoxon` in `significance.py`
* **Gates:** `tests/evals/test_evaluation_framework.py` (2 collected, pass) + live `dsa` aggregation uses `metrics.py` tolerant `sql_accuracy` (`empty sql_contains → any run_sql ok`) — no silent single-method gate (`acceptable_method/metrics/interpretation/evidence/forbidden_interpretation` enumerated per task)
* **Docs:** `docs/v2/evaluation.md` records `10×6` matrix + significance helpers; `benchmarks/v2/catalog.json` embedded gold fields authoritative

---

## 9. Security Status

* **Suite (live):** `23 cases` all pass — `uv run pytest tests/security tests/mcp` → `30 passed` (23 security + 7 MCP conformance)
  * `tests/security/test_adversarial_suite.py` 10 (Prompt/CSV/Markdown/Formula/Tool-Description/Report injection, traversal, SQL injection, symlink escape, oversized payload, wide table — covers W9 §46–50: file traversal `U01`, SQL/code sandbox `U02`, CSV/formula injection `U03`, DoS `U04`, report xss `U05`, prompt `U06`)
  * `tests/security/test_security_phase8.py` 13 (file validation + SQL validation + sandbox AST + `PROMPT_INJECTION_PATTERNS`)
* **Guards re-audited:** `packages/execution/src/dsa_execution/{file_validator,sql_validator,python_sandbox,guardrails,mime_sniff}.py` + `packages/tools/src/dsa_tools/tools/{run_sql,run_python}.py` read-only DuckDB, AST `deny os/subprocess/socket/requests/eval/exec/open/__import__`, `allowed imports {polars/numpy/math/statistics/json/re/datetime/collections/itertools}`, row limit `10k`, archive bomb heuristic — unchanged since V2.0
* **Docs:** `docs/v2/security.md` (hardening matrix), `SECURITY.md` (policy), `docs/security.md` — Phase A reads only, no mutation

---

## 10. MCP Status

* **Spec:** `2026-07-28 stateless core` (cancelled `initialize/initialized` + `Mcp-Session-Id` session state), `ADR-001-mcp-2026-07-28-stateless-core.md` authoritative
* **Implementation:** `packages/mcp/src/dsa_mcp/{adapter,server}.py` — stateless `tools/list` + `tools/call` dispatch via `MCP_TOOL_MAP`, per-tool metadata `outputSchema/permissions/idempotency/timeout/cost_class/cache_hint/tool_class` (`SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT`), mounted at `app.mount("/mcp", mcp_app)`
* **Live conformance:** `tests/mcp/conformance/test_mcp_conformance.py` **7/7 pass** (`tools/list`, `tools/call`, no `initialize`, stateless repeated calls, caching headers) + `tests/unit/test_mcp.py` + `tests/unit/test_cov_mcp_server_and_llm.py` (coverage)
* **Audit:** `docs/v2/MCP_2026_Audit.md` records stateless compliance + tool classification — `docs/v3/MCP_COMPATIBILITY.md` deferred to V3 Phase A W79–80

---

## 11. Reproducibility Status

* **Bundle:** per-run `artifacts/reports/<runId>/{experiment.json,reproduce.sh,analysis.ipynb,evidence_graph.json,report.md}` (`experiment.json` = `dataset hash + schema + code/SQL/params/model + python/platform/package_versions + llm/prompt/seed/timestamp`)
* **Scoring/levels:** `packages/evidence/src/dsa_evidence/{reproducibility.py L0–L5, failure_taxonomy.py F01–F15, observability.py Trace/Span}` + `packages/agent/src/dsa_agent/trajectory.py` (`Trajectory/NodeExecution/ToolExecution/RetryEvent/Checkpoint`) — `tests/unit/test_reliability_repro_failure_obs.py` (3) + `test_trajectory.py` + `test_significance.py` all pass
* **Mechanism:** `Checkpoint`: `MemorySaver` in `langgraph_graph.py`; `pause/resume/replay/fork/inspect` as spec (§28) — not exercised as CLI `dsa reproduce` yet (Phase A only audits existing bundle; `dsa reproduce --run/--benchmark` is V3 W3 §18–20)
* **Live ablation:** `uv run python research/experiments/run_ablation.py --limit 2 --out /tmp/v3-phaseA-ablation` writes `ablation_ablation-*.json` + `_tmp_*` (real `run_benchmark` + `bootstrap_ci`); Phase A sampled 20/100 (`research/results _tmp_*/ablation_*.json`), not full 100 (V3 Research Report will gate on full)

---

## 12. Research Status

* **Structure:** `research/{questions/RQs.md,experiments/{ablation_matrix.py,run_ablation.py},results/ablation_*.json,paper/{outline.md,V2_paper_draft.md},figures/README.md,tables/README.md,related-work.md (Phase A not yet),claim-evidence-matrix.md (Phase A not yet)}`
* **RQs/Ablation:** RQs 1–5 (tool, critic, evidence, statistics, model) + matrix `A–F` (`LLM→Full`) wired to real benchmark (`run_ablation.py` drives `run_benchmark` + `bootstrap_ci`/`paired_bootstrap`/`mcnemar` from `significance.py`); Phase A did **smoke 2/20** and full `100/100` via `dsa v2` (both `@1.0`)
* **Paper:** `V2_paper_draft.md` skeleton + `outline.md` reference real `benchmarks/v2` + `research/results` — figures/tables `scripts/` reproducibility deferred to V3 W10–11 (§51–57) `NOT FULLY VERIFIED` (no `research/figures/*.png` generated by script yet)
* **Failure/human:** `Failure Analysis` (§30–32 `failures` route present) and `human-eval/` (§35–38) not yet populated — explicitly `NOT IN PHASE A SCOPE`

---

## 13. Technical Debt

* **TD-01 datetime:** Clean — `utcnow` eliminated (283 warnings → 1). Sources migrated (`state/evidence/datasets` + 3 ORMs `analysis/dataset/experiment`); `pyproject.filterwarnings` ignores `pydantic/sqlalchemy/fastapi.testclient`. Residual `1` is `starlette.testclient` upstream, non-blocking.
* **TD-02–04 polish:** Ruff scoped pass, `ruff format --check packages apps/api tests` pass, `mypy packages apps/api --ignore-missing-imports` clean (102 → 87 source scope); raw `mypy . --ignore-missing-imports` = 102 errors in 23 files (tests `no-untyped-def` + `Path/str` + `research dict type-arg`) — not a V2 gate.
* **TD-05 MkDocs:** Now verified — `mkdocs 1.6.1` installed via `uv sync --dev`, but `python -m mkdocs build --strict` aborts (`ARCHITECTURE_FREEZE_V0.1.md` link + missing `CONTRIBUTING/THIRD_PARTY_LICENSES` in `docs/`), CI `|| echo skipping` masked this — V3 W10 to fix nav, not Phase A blocking.
* **TD-06 MCP spec drift:** `MCP 2026-07-28` implemented, but upstream spec may evolve post-2026-Q3 — ADR-001 covers rollback; risk R-05 carries.
* **TD-07 Sandbox:** In-process AST only (`max CPU/memory/output/file/process` not yet kernel-cgroups), fine for benchmark but not for adversarial wide-table `S311` path — V3 W9 will add limits.
* **TD-08 Low-coverage islands:** `mcp/server 51%`, `routers/analysis 45%`, `reports` — targeted `tests/unit/test_*` pushed 75%→80%, next Push to 85% is V3 W5.
* **TD-10 Tool cache:** Global `_TOOL_CACHE` dict still present (determinism risk R-03) — not yet scoped per-run.
* **TD-12 Benchmark looseness:** `_approx_equal` style check still present; `sql_accuracy` empty-set leniency added `feb31c6` to heal `100/100` — audit point for V3 W2 `scientific audit`.

---

## 14. Remaining Polish

* **Non-blocking polish (5 commits of diff on `v2.0.0`):** `benchmarks/ds-agent-benchmark/results` refresh churn (3 files), `research/results` tmp churn, `docs/v3/` empty pre-Phase A — all excluded from `9a6e410` scope except polish tests.
* **Intentional ignores (scoped 15):** `pyproject.per-file-ignores` masks `F841/S110/S608/B008/SIM/*` by design (FastAPI Depends, empty SQL cat, controlled `duckdb` string view); global `ignore ["S101","E501"]` only — `ruff check packages apps/api tests` = `All checks passed`.
* **Docs strict:** `mkdocs build --strict` needs `nav` fix (3 missing files) — follow-up in V3 W10, explicitly not fixed in Phase A per `§98 STOP CONDITION`.
* **Track-workspace gate:** `docker build api/web` not run Phase A (only `docker compose config` valid + `npm build` 13/13); full `dsa verify-release` is V3 W63/W12.

---

## 15. V3 Priority Recommendations

**Recommended workstream order (Phase A → L, per DATA_SCIENCE_AGENT_V3_0.md §89):**

* **W2 Benchmark Scientific Audit (next, Phase B):** Answer §12 ten questions, then enumerate per-task `source/license/citation/benchmark_version/generator/reviewer` (§13–17), normalize `acceptable_method/metrics/interpretation/evidence` and `forbidden_*`; `version 0.2.0 → 0.3.0` or `v2.1`.
* **W3 Independent Reproduction:** Implement `dsa reproduce --run/--benchmark` → `reproduction/{manifest,environment,results,comparison,logs}` + `ReproductionScore` (§17–21) before any new metric work.
* **W4 Statistical Evaluation Upgrade:** Add `S01–S10` taxonomy + `causal language audit` + `uncertainty evaluation` (§22–25) and wire to `EvaluationResultV2` (version `evaluator_v2`).
* **W5 Agent Reliability Research:** Formalize `Single vs Planner+Agent vs +Critic vs Full Evidence` (§26–30) with `Tool Selection Accuracy` / `Agent Efficiency` / `Critic Benefit` — re-uses current `trajectory/observability` hooks.
* **W6 Cross-Model Evaluation:** §31–34 matrix (Local Medium + Frontier `NOT FABRICATED`) + `Quality-Cost Frontier`.
* **W7 Human Evaluation:** §36–38 rubric + `Kappa/Alpha` (5–10% sample) in `human-eval/`.
* **W8–W12:** External install `dsa demo` (§39–40), release engineering `§43–47`, docs `§48–51`, citation `CITATION.cff`+`technical-report` (§52–57), final `dsa verify-release v3.0.0` (§63).

**Risks carried into V3:**
* R-01 `MCP_tasks` cash + `Mcp-Session-Id` deprecation pressure — ADR covers; R-03 global `_TOOL_CACHE`; R-05 MCP drift; R-06 sandbox kernelization; R-07 coverage `80%→85%`; R-08 plotted `det. leakage` (Parquet/XLSX unexercised); R-09 LangGraph minor churn; R-10 `rss_mb` portability — all frozen as Phase A context.

---

## Appendix — Live Command Evidence (this working tree)

```text
[1] uv run pytest -q                          → 137 passed, 1 warning (5.6s)
[2] uv run pytest --cov                        → 80% (3926/633/926/203)
[3] uv run mypy packages apps/api --ignore-missing-imports → Success: 87 source files
    uv run mypy . --ignore-missing-imports    → 102 errors in 23 files (tests/research type-arg, non-gate)
[4] uv run ruff check packages apps/api tests → All checks passed
    uv run ruff check .                       → 50 errors (examples/ + docs noise, non-gate)
[5] npm --prefix apps/web run build           → 13/13 routes ✓ (ƒ analysis/[runId], benchmarks, evaluations, runs, failures, research, mcp, datasets)
[6] docker compose config                     → valid (api healthcheck + web depends_on healthy)
[7] uv run dsa --limit 50                    → 50/50 @1.00
[8] uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 → 100/100 @1.00 (11 cats, 30 datasets)
[9] uv run pytest tests/security             → 23 passed
[10] uv run pytest tests/mcp                 → 7 passed
[11] uv run pytest tests/evals               → 2 passed
[12] uv run pytest tests/regression          → 5 passed
[13] uv run python -m mkdocs build --strict  → abort (29 warnings, link/nav) — NOT gate-clean, documented
```

`NOT VERIFIED` items: deep `human-eval` sample, full 100-task ablation manifest `research/results/ablation-9a6e410-full.json`, `dsa reproduce` CLI, `figures/*.png` scripts — explicitly out-of-scope for Phase A.
