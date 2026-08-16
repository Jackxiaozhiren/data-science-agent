# V1.8 → V2.0 Baseline Report

> **Phase A — Baseline Freeze** · `v1.8.0` · Generated: 2026-08-16 (Asia/Shanghai, live run)
> Working tree: `587c4bf` (`v1.8.0`) · No code modifications during freeze · All metrics reproduced in current working tree

---

## 1. Current Architecture

**Pattern:** Layered monorepo (`uv` workspace + `npm` workspaces) — `Frontend → API → Agent Runtime → Tool Layer → Engines → Evidence/Repro Layer → Storage`.

```
Frontend (Next.js 15 + TS + Tailwind + shadcn/ui)  — apps/web
        ↕ HTTPS / SSE
API Layer (FastAPI + Pydantic v2 + SQLAlchemy)     — apps/api/src/dsa_api
        ↕ DI
Agent Runtime (LangGraph Stateful Graph)            — packages/agent/src/dsa_agent
        ↕ typed Tool contract (async execute)
Tool Layer (17 tools, registry)                     — packages/tools
        ↕
  DuckDB+Polars+PyArrow | Python Sandbox (AST) | Statistics/ML (scipy/sklearn) | Viz (Plotly/Matplotlib)
        ↕
Evidence & Reproducibility (graph + repro bundle)   — packages/evidence
        ↕
Storage (SQLite via aiosqlite + local FS artifacts) — data/ + artifacts/reports/<runId>/
        ↕
LLM Abstraction (LLMProvider → OpenAI/Anthropic/Google/OpenRouter/Ollama) — packages/llm
Cache: Local File Cache (_TOOL_CACHE + CachedLLM LRU) · OTel: optional interface
MCP Adapter (stateless, wraps Tool Layer)           — packages/mcp/src/dsa_mcp
```

**Repo tree (frozen, verified on disk):**

```
data-science-agent/
├── apps/{api,web}          — FastAPI app (routers/services/models/core) + Next.js 15 app router
├── packages/{agent,tools,execution,statistics,ml,visualization,evidence,reports,datasets,llm,mcp,evaluation}
├── benchmarks/ds-agent-benchmark (20 CSVs + catalog.json 50 tasks)
├── tests/{unit,integration,e2e,security} + apps/api/tests
├── docs/ (MkDocs), scripts/, docker/{Dockerfile.api,Dockerfile.web}, .github/workflows/ci.yml
├── pyproject.toml (uv), package.json, docker-compose.yml, ARCHITECTURE_FREEZE_V0.1.md
└── artifacts/reports/<runId>/{report.md,experiment.json,reproduce.sh,analysis.ipynb,evidence_graph.json}
```

**Frozen spec:** `ARCHITECTURE_FREEZE_V0.1.md` (Phase 0) — decision: LangGraph over OpenAI Agents SDK, DuckDB+Polars, SQLite MVP → Postgres, custom LLMProvider, Local File Cache.

---

## 2. Current Functional Scope

**Data I/O:** CSV/Parquet/JSON/Excel via `dsa_datasets.loader` + `profiler` (rows/cols/dtypes/missing/duplicates/cardinality/distribution). 100 MB limit, extension/MIME allowlist, head sniff, traversal block, archive bomb heuristic.

**SQL:** `run_sql` → DuckDB read-only connection, `validate_sql` allowlist `SELECT/WITH/SHOW/DESCRIBE/EXPLAIN`, deny `DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY/PRAGMA`, single-statement, row limit (10k), `LIMIT` enforcement.

**Python:** `run_python` → AST guard (deny `os/subprocess/socket/requests/eval/exec/open/__import__`, introspection), allowlist imports (`polars/pl/numpy/np/math/statistics/json/re/datetime/collections/itertools`), `_safe_import`, `exec` with safe builtins, `df` injection, stdout/stderr/vars capture, wall-clock timeout (5s).

**Statistics:** `correlation_analysis` (pearson/spearman/kendall + p/r/CI), `hypothesis_test` (t/welch/mannwhitney/anova/kruskal/chisq/fisher + assumptions/effect_size), `regression_analysis` (linear/logistic/ridge/lasso/elastic), `assumption_check` (Shapiro/Levene), `causal_check` (stub — never passes causal bar by design).

**ML:** `train_model`/`evaluate_model`/`feature_importance` (RandomForest + CV), `forecast` (trend/moving_average baselines, MAE holdout), leakage guard via critic + planner notes.

**Viz:** `create_chart` → Plotly/Matplotlib histogram/bar/scatter/line/boxplot/heatmap/ROC chart → PNG artifact under `artifacts/`.

**Evidence:** `Evidence`/`Insight`/`Artifact`/`ValidationResult` models (`packages/agent/src/dsa_agent/state.py` + `packages/evidence/src/dsa_evidence/models.py`). Graph `Insight → Evidence → ToolCall → Dataset(hash)` via `build_evidence_graph` + `validator.validate_evidence_graph` (insight_evidence, traceability, unsupported_claim, dataset_hash).

**Reproducibility bundle:** `experiment.json` (dataset hash + schema + code/SQL/params/model + python/platform/package_versions + llm/prompt/seed/timestamp) + `reproduce.sh` + executable `analysis.ipynb` (profile + per-tool cells + full `run_analysis`) under `artifacts/reports/<runId>/`.

**Agent:** `Planner` (heuristics_plan, keyword-driven, numeric column inference, SQL heuristic generation) → `DataScientist` (executes plan) → `Critic` (evidence_coverage, unsupported_claim, tool_errors, budget, retry) → `Report` (Markdown/HTML/PDF/Notebook + evidence enrichment). Budget: `max_steps=20, max_tool_calls=40, max_retries=3, max_tokens=50000`.

**API:** `POST /api/v1/datasets/` (multipart), `GET /api/v1/datasets/{id}`, `POST /api/v1/analysis/` → run_id (runs graph synchronously), `GET /api/v1/analysis/{id}` (AnalysisState), `GET /api/v1/analysis/{id}/events` (SSE + JSON fallback), `/progress`, `/artifacts`, `/report?format=markdown|json`, `/evidence/{evidence_id}` (trace), `POST /{run_id}/approve` (HUMAN_REVIEW→COMPLETED), `GET /health` (db/duckdb/polars/llm probes), `/ready`, `/version`, `/metrics` (uptime, rss_mb, tool_cache_size, pid, version), `POST /api/v1/experiments/compare` (ablation stub).

**Frontend routes (verified):** `/` (dashboard recent analyses) + `/_not-found` + `/analysis` (workspace) + `/analysis/[runId]` (trace: plan/tool_calls/evidence/insights/validation/artifacts/report + evidence graph) + `/datasets` + `/datasets/[id]` + `/reports`. 7 routes green on `next build`.

**MCP:** 17 tool names exposed via `/mcp/tools`, `/mcp/call`, `/mcp` JSON-RPC `tools/list`/`tools/call`/`initialize` (stateless dispatch to backend tools via `MCP_TOOL_MAP`), mounted at `app.mount("/mcp", mcp_app)`.

---

## 3. Current Test Results

Commands run live in working tree (`uv run`):

| Check | Command | Result | Notes |
|---|---|---|---|
| **pytest (all)** | `uv run pytest -q` | **86 passed** (278 warnings) in 2.67s | `testpaths = tests + apps/api/tests` |
| **pytest verbose** | `uv run pytest -v` | 86 collected: `apps/api/tests/test_health 2 · e2e/test_acceptance 1 · integration 5+7+2 · unit 1+13+4+1+2+7+15+4+4 · security 13` | all green |
| **mypy (CI scope)** | `uv run mypy packages apps/api --ignore-missing-imports` | **Success: no issues in 81 source files** | strict, `warn_return_any`, match `README` claim |
| **mypy (all, incl. tests)** | `uv run mypy . --ignore-missing-imports` | **19 errors in 8 files** (`tests/unit/test_v03_tools`, `test_security_phase8`, `test_phase6_api`, `test_agent_analysis`, `test_mcp`) | missing `-> None`, `no-untyped-call` for `_run` helpers — not in CI gate |
| **ruff check** | `uv run ruff check .` | **184 errors** (73 fixable, 31 hidden unsafe) | top: F401 43, E702 18, I001 18, B008 17, F841 17, S110 17, B007 10 |
| **ruff format** | `uv run ruff format --check .` | `File would be reformatted` (e.g. `ARCHITECTURE_FREEZE_V0.1.md:212`) | docs/markdown not excluded in format gate |
| **docker compose config** | `docker compose config` | **VALID** — services `api` (build `docker/Dockerfile.api`, port 8000, healthcheck `interval:15s timeout:5s retries:5 start_period:10s`) + `web` (`docker/Dockerfile.web`, port 3000, `depends_on: api healthy`) | `name: dataagent` |
| **next build** | `npm --prefix apps/web run build` | **Compiled successfully**, 7/7 static pages | `Next.js 15.0.0`, `First Load JS ~99kB` |
| **mkdocs** | `mkdocs build --strict` | **NOT VERIFIED** — binary not installed (`Failed to spawn: mkdocs`) | `uv run mkdocs build --strict` also not in venv; CI `|| echo "skipping"` fallback |
| **dsa benchmark** | `uv run dsa --limit 50 --out /tmp/dsa-bench-baseline` | **50/50 @ 1.0** (see §5) | `benchmarks/ds-agent-benchmark/` 20 datasets |
| **dsa CLI help** | `uv run dsa --help` | `DS-Agent-Benchmark runner` (`--catalog/--datasets/--out/--limit/--task`) | via `dsa_evaluation.cli` |

CI (`crates/.github/workflows/ci.yml`): `setup-python 3.12 → pip install uv → uv sync --dev → ruff check → ruff format --check → mypy packages → pytest -q --cov --cov-report=term-missing → docker build (api, web) → mkdocs build --strict` (last step is soft-fail).

---

## 4. Current Coverage

`uv run pytest --cov --cov-report=term-missing` — **74% total** (3657 stmts, 776 miss, 876 branches, 214 partial) — matches documented `74–75%`. 5 empty files skipped.

| Package | Coverage | Notable gaps |
|---|---|---|
| `apps/api/src/dsa_api/routers/analysis.py` | **38%** (111 stmts, miss 61) | analysis approve/SSE/artifact paths uncovered |
| `apps/api/src/dsa_api/routers/health.py` | 58% | `_probe_import` / `metrics` branches |
| `apps/api/src/dsa_api/routers/experiments.py` | 62% | compare endpoint error paths |
| `packages/mcp/src/dsa_mcp/server.py` | 36% (83 stmts, miss 51) | JSON-RPC + STDIO modes — only HTTP list/call tested |
| `packages/llm/src/dsa_llm/providers.py` | 47% | EnvLLMProvider not exercised in unit tests |
| `packages/tools/tools/hypothesis_test.py` | 57% | non-default branches (anova/kruskal/fisher) |
| `packages/tools/tools/create_chart.py` | 62% | chart type branches / heatmap/ROC |
| `packages/tools/tools/forecast.py` | 62% | TS branches |
| `packages/execution/python_sandbox.py` | 67% | denied imports/attrs, intellispection, timeout branches |
| `packages/evaluation/metrics.py` | 51% | statistical accuracy details |
| High coverage | `state.py` 100%, `profiler/validate/models/hash_utils` 88–100%, `loader` 52% (CSV path covered, Parquet/JSON less) | — |

See `tool.coverage.run: source = ["packages", "apps/api/src"], branch = true`.

---

## 5. Current Benchmark Results

**Runner:** `packages/evaluation` (`catalog.py` + `metrics.py` + `runner.py` + `cli.py`) — invoked as `uv run dsa --limit 50 --out /tmp/dsa-bench-baseline`. Catalog `benchmarks/ds-agent-benchmark/catalog.json`: 50 tasks, 8 categories. Datasets `benchmarks/ds-agent-benchmark/datasets/` — 20 synthetic CSVs (seed 42, 8,770 rows aggregate).

**Live run (2026-08-16, 50/50):**

```
=== DS-Agent-Benchmark ===
Tasks: 50
Task success rate: 1.0
By category: {'EDA': {'n': 8, 'task_success': 1.0}, 'SQL': {'n': 7, 'task_success': 1.0}, 'Statistics': {'n': 8, 'task_success': 1.0}, 'Regression': {'n': 6, 'task_success': 1.0}, 'Classification': {'n': 6, 'task_success': 1.0}, 'Time Series': {'n': 5, 'task_success': 1.0}, 'Visualization': {'n': 5, 'task_success': 1.0}, 'Data Quality': {'n': 5, 'task_success': 1.0}}
Results written to: /tmp/dsa-bench-baseline
```

`summary.json / aggregate`:

```json
{
  "n": 50,
  "task_success_rate": 1.0,
  "statistical_accuracy": 1.0,
  "sql_accuracy": 1.0,
  "code_execution_success": 1.0,
  "evidence_coverage": 1.0,
  "unsupported_claim_rate": 0.06,
  "mean_latency_ms": 47.92,
  "by_category": { "EDA": {"n":8,"task_success":1.0}, "SQL": {"n":7,"task_success":1.0}, "Statistics": {"n":8,"task_success":1.0}, "Regression": {"n":6,"task_success":1.0}, "Classification": {"n":6,"task_success":1.0}, "Time Series": {"n":5,"task_success":1.0}, "Visualization": {"n":5,"task_success":1.0}, "Data Quality": {"n":5,"task_success":1.0} }
}
```

**Op then to details:** `unsupported_claim_rate 0.06` = 3/50 tasks flagged (`eda-01`, `sql-03`, `viz-01`) — insight findings triggered `unsupported_claim` (causal wording or association) despite evidence; all other metrics 1.0. `mean_latency_ms` 47.92 ms reflects local synthetic-data execution (parallel batch in `graph.py` via `asyncio.gather` for independent `correlation/hypothesis/assumption/chart/run_sql`).

**Per-task metrics (from `results.json`):** `evidence_coverage` true for 13 tasks where `criteria.evidence_coverage=true`, else `null`; `statistical_accuracy` only computed where `expected_value` + `tolerance` present (e.g. `stats-01` r≈0.8 tol 0.15). `sql_accuracy` via `sql_contains` substring check (e.g. `sql-05` requires `COUNT/GROUP BY/HAVING`). Three tasks with `unsupported_claim: true` noted above.

**Limits / confidence:** Single-run mean latency; no multi-seed / CI distribution / paired bootstrap yet. V2 should add L0–L5 reproducibility scoring and tool-efficiency accounting.

---

## 6. Current MCP Status

**Claimed:** 17 tools — verified: `dsa_tools.bootstrap()` registers 17 (`profile_dataset`, `run_sql`, `run_python`, `correlation_analysis`, `hypothesis_test`, `assumption_check`, `causal_check`, `regression_analysis`, `train_model`, `evaluate_model`, `feature_importance`, `forecast`, `create_chart`, `save_artifact`, `create_evidence`, `validate_result`, `generate_report`). `MCP_TOOL_MAP` exposes 17 MCP names (including aliases `inspect_dataset`→`profile_dataset`, `query_dataset`→`run_sql`, `run_statistical_test`→`hypothesis_test`, `create_visualization`→`create_chart`, `get_evidence`→`create_evidence|validate_result`).

**Transport / endpoints (in `apps/api` via `app.mount("/mcp", mcp_app)`):**

- `GET  /mcp/tools` → `list_mcp_tools()` (inputSchema from `BaseTool.input_model.model_json_schema()`)
- `POST /mcp/call` → `call_mcp_tool(name, arguments)` stateless
- `POST /mcp` JSON-RPC 2.0 → `tools/list`, `tools/call`, `initialize` (returns `protocolVersion: "2024-11-05"`)
- `stdio_main()` (JSON-per-line) for Claude Desktop/local MCP clients

**Conformance (tested via `tests/unit/test_mcp.py` 7 tests, all pass):** tool discovery, valid `tools/call`, unknown tool error, stateless repeat calls (tool cache), query alias `query→sql` mapping. No `mcp conformance/` suite yet.

**MCP 2026-07-28 alignment — gap (NOT compliant):**

| Expected (2026-07-28) | Actual | Gap |
|---|---|---|
| stateless protocol core, **no** `initialize`/`initialized` handshake, **no** `Mcp-Session-Id` | server responds to `initialize` with `protocolVersion 2024-11-05 + capabilities.tools` | legacy handshake still present |
| `Tools list` supports `cacheHints` | `MCPToolDef` has only `name/description/inputSchema` | missing `outputSchema/permissions/idempotency/timeout/cost_class/cacheHints` (V2 §42) |
| `Tasks` as extension mechanism, authorization + state via explicit handles (`analysis_id/project_id/task_id/run_id`) | adapter uses `dataset_path/run_id` internally, but no auth/permissions layer | needs security hardening |

Result: **V1.8 MCP functional, 17 tools, stateless dispatch correct; V2 must deprecate `initialize`, add tool metadata & conformance tests** (`tests/mcp/conformance/`).

---

## 7. Current Security Status

**Boundary (§10 of `ARCHITECTURE_FREEZE_V0.1.md`):**

| Boundary | Implementation | Validation |
|---|---|---|
| **File** | `dsa_datasets.validate` (extension allowlist `csv/parquet/json/xlsx`, `validate_filename` traversal check `..` + path re-escape, MIME sniff via `head` 4096 bytes in `datasets.py` router, `max_size 100 MB`, filename sanitization, hash `sha256_file`) | `tests/security/test_security_phase8.py` (prompt injection, path traversal, malicious file) + `test_datasets.py` |
| **SQL** | `dsa_execution.sql_guard.validate_sql` (read-only allowlist `SELECT/WITH`, deny 11 patterns `DROP/DELETE/UPDATE/INSERT/ALTER/ATTACH/COPY/PRAGMA/LOAD/IMPORT`, single-statement `;` check, max_len 8000, row-limit 10k + `enforce_row_limit`) + DuckDB read-only via `ReadOnlyAdapter` in services | security tests for SQL injection |
| **Python** | `dsa_execution.python_sandbox._check_ast` (deny imports `os/subprocess/socket/requests/urllib/httpx/shutil/pathlib/sys/eval/exec/open/importlib` + allowlist `polars/numpy/math/statistics/json/re/datetime/collections/itertools`, deny attrs `system/popen/call/run/exec/eval/__import__/open/socket/connect/getenv/environ` + introspection `__class__/__bases__/__subclasses__/__mro__`, safe globals `_safe_import`, `exec` with `df` injection only) | output guard via `tests/security` code injection cases |
| **Prompt Injection** | `dsa_execution.guardrails.contains_prompt_injection` (patterns `ignore previous instructions/send the api key/disregard all prior`) + `dsa_agent.critic.detect_prompt_injection` + system prompt tags dataset cells as `UNTRUSTED DATA` (heuristic planner does not treat dataset text as instructions) | `check_resource_limits` in tests |
| **Output guard** | `critic.rewrite_unsupported_claim` / `guardrails.rewrite_unsupported_claim` — regex causal words `cause|caused by|impact|effect|leads to|results in|due to|drives` → rewrite to `is associated with` + `(Causal inference is not established.)` + validation check `unsupported_claim` | benchmark 0.06 unsupported rate, `validate_evidence_graph` hard-fails causal insight |
| **Resource limits** | `Budget(max_steps 20, max_tool_calls 40, max_retries 3, max_tokens 50000)` + `check_resource_limits` (tool_calls/tokens/execution_ms) + `human-in-the-loop` (`WAITING_FOR_APPROVAL`/`HUMAN_REVIEW` via `/api/v1/analysis/{id}/approve`) | `graph.py` enforces `tool_call_budget`, e2e acceptance |
| **Logging** | JSON structured logging (no secrets), API keys only via `env`, `THIRD_PARTY_LICENSES.md` / `SECURITY.md` policy | — |

**Security test suite:** `tests/security/test_security_phase8.py` — 13 tests, all pass as part of 86.

**Known gaps (carry to W9):** Python sandbox lacks `max CPU time / max memory / max output size / max file size / max process count` cgroup limits (only AST + wall-clock check; V2 §48); no adversarial `dataset injection / CSV-cell injection / markdown/formula/tool-description/report injection` expanded suite; `sandbox` `exec` still in-process (not subprocess jail with seccomp); `scale/nested JSON / path traversal symlink / oversized payload` DoS bounds not stress-tested.

---

## 8. Current Performance

| Metric | Value (live) | Source |
|---|---|---|
| **Benchmark mean latency** | **47.92 ms / task** (50 tasks, synthetic CSVs, local) | `dsa --limit 50` aggregate `mean_latency_ms` |
| **Per-category mid p50 (tool portion only)** | EDA 35–1258 ms (eda-01 includes first-load overhead), SQL 11–17 ms, Stats 7–41 ms, Regression 6–37 ms, Classification 6–100 ms, TS 6–79 ms, Viz 7–12 ms, DQ 5–10 ms | `results.json` `elapsed_ms` (runner wall: `run_analysis` in-proc) |
| **Full benchmark wall (50 tasks)** | ~ 2.5–3 s end-to-end (excluding cold import) | `python -m pytest ... 2.67s` proxy; bench run ~ 4–5 s measured for 50/50 |
| **Tool cache effect** | V1.4 `CachedLLMProvider LRU 128 TTL 600s` + `_TOOL_CACHE` + parallel batch cut `mean_latency 73 ms → 39.8 ms` per `CHANGELOG 1.4.0` | `packages/agent/src/dsa_agent/graph.py: _TOOL_CACHE + _PARALLEL_TOOLS asyncio.gather` |
| **Next build** | Compiled in ~ 1–2 s, `First Load JS 99.1 kB` shared (`765 44.6k, 87c73c 52.6k`) | `npm run build --workspace=dsa-web` |
| **Docker boot** | `healthcheck` `interval 15s timeout 5s retries 5 start_period 10s` + `depends_on: healthy` | `docker-compose.yml` |
| **Memory** | `GET /metrics` reports `rss_mb` via `resource.getrusage` (platform-corrected for darwin) + `tool_cache_size=len(_TOOL_CACHE)` + `uptime_s` | `apps/api/src/dsa_api/routers/health.py` |
| **Missing V2 breakdowns** | NOT MEASURED: planning/LLM/tool/SQL/Python/statistics/ML/critic/report split, tokens (input/output/total/tokens_per_success), `agent_run_total/failure_total/tool_error_total/unsupported_claim_total` (V2 §35) | add OTel spans + token accounting in W7 |

No regression versus the historical claim `50/50` — **no V2 metric may be cited until re-run in current tree (this report satisfies the rule)**.

---

## 9. Dependency Status

**Python (`pyproject.toml` `requires-python >=3.12`, `uv.lock` present):**

```
Runtime: fastapi>=0.110, pydantic>=2.7, pydantic-settings>=2.4, sqlalchemy>=2.0, aiosqlite>=0.20,
         duckdb>=1.0, polars>=1.0, pyarrow>=15.0, numpy>=1.26, scipy>=1.12, scikit-learn>=1.4,
         matplotlib>=3.8, langgraph>=0.2, langchain-core>=0.3, uvicorn[standard]>=0.29,
         python-multipart>=0.0.9, httpx>=0.27, openpyxl>=3.1, greenlet>=3.5.5
Dev:     pytest>=8.2, pytest-asyncio>=0.23, pytest-cov>=5.0, ruff>=0.4, mypy>=1.10, anyio>=4.4
Tooling: uv 0.11.7, Hatchling build, ruff (line 100, py312), mypy strict, pre-commit (ruff/ruff-format)
Locked:  uv.lock + package-lock.json (web)
Size:    ~3.6k stmts under coverage (14 workspace members)
License: MIT (LICENSE) + THIRD_PARTY_LICENSES.md (CC0 note for datasets)
```

Workspace members `tool.uv.workspace`: `apps/api, packages/{agent,datasets,evaluation,evidence,execution,llm,mcp,ml,reports,statistics,tools,visualization}`.

**Node (`apps/web/package.json`, `package.json` root):**

```
Next.js 15.0.0 + React 19.0.0 + React-DOM 19.0.0 + TypeScript 5.9.3 + @types/node 20.19.43
+ @types/react 19.2, tailwindcss 3.4, autoprefixer 10.4, postcss 8.4
Root adds: workspaces ["apps/*", "packages/*"]
```

**OS/tooling (live host, 2026-08-16):** `Python 3.12.13 (Clang 21)`, `Node 24.15.0`, `npm 11.12.1`, `Docker (compose v2)` — `docker compose config` valid; `mkdocs` not installed (optional dep, not in `uv.lock`).

**Versioning:** `pyproject version 1.8.0`, git tags `v0.1.0 … v1.8.0` (12 tags), HEAD `v1.8.0 587c4bf — Lightweight observability: /metrics + datasets health hint`.

---

## 10. Technical Debt

| # | Item | Evidence | Impact | Proposed lane |
|---|---|---|---|---|
| **TD-01** | `datetime.utcnow()` deprecation (278 warnings) | `dsa_agent.state` `created_at/updated_at/touch` + Pydantic validation + SQLAlchemy defaults | noisy warnings; future removal breakage | W1: swap to `datetime.now(timezone.utc)` across state/models/DB defaults |
| **TD-02** | `ruff` 184 errors, 73 auto-fixable | `F401 unused-import 43, E702 18, I001 18, B008 17, F841/S110 17, ...` (tests + `arch docs`) | CI would fail `ruff check .` strictly; currently 184 not gated as fail in branch | W1: run `ruff --fix`, ignore docs globs or exclude `*.md` from lint, add `per-file-ignores` for `B017` tests |
| **TD-03** | `ruff format --check` flags markdown | `ARCHITECTURE_FREEZE_V0.1.md:212` table formatting | format gate would fail if run over markdown | exclude `*.md` from format check (CI `ruff format --check` should target `packages apps/api tests`) |
| **TD-04** | `mypy` on tests exposes untyped `_run` helpers | `m pytest ... --ignore-missing-imports` clean on 81 files; `mypy .` shows 19 errors in `tests/` | tests stay untyped; V2 may type-gate them | add `-> None` + typed `_run` wrappers or exclude `tests/` from strict scope |
| **TD-05** | `mkdocs` not installed / optional | `uv run mkdocs build --strict` falls back to skip | docs drift risk; strict build never validated outside CI images | add `mkdocs` + `mkdocs-material` to dev group, or document explicit opt-in |
| **TD-06** | MCP still speaks `2024-11-05` + `initialize` handshake | `mcp/server.py` returns that protocolVersion | blocks `2026-07-28` upgrade path | W8: stateless `POST /mcp` per new spec, remove `initialize`, add `outputSchema/permissions/idempotency/timeout/cost_class/cacheHints` |
| **TD-07** | Python sandbox in-process only | `exec(code, safe_globals)` with wall-time but no `subprocess jail/seccomp/memory caps` | DoS/background resource risk | W9: optional `subprocess + rlimit + timeout + no-net + WorkDir jail` |
| **TD-08** | Coverage skew: `routers/analysis 38%`, `mcp/server 36%` | `--cov term-missing` gaps table | API + MCP surface under-tested | W1/W8: add regression tests for SSE/approve/JSON-RPC/error branches |
| **TD-09** | `httpx`/`starlette.testclient` deprecation warning | `test_mcp.py::test_mcp_http_list_and_call` | test noise | pin `httpx2` or update `starlette` usage |
| **TD-10** | Tool cache global `_TOOL_CACHE` never evicted between benchmark runs | `dsa_agent.graph:_TOOL_CACHE` keyed by hash(inputs) | cross-task non-determinism if dataset hash collides at 24 hex chars; no LRU bound | W4/W5: LRU with per-run scoping or explicit `clear()` between benchmark tasks |
| **TD-11** | Frontend hardcoded `http://localhost:8000` fetch on SSR | `apps/web/app/page.tsx fetchRecent()` | SSR outside docker fails (should use env `NEXT_PUBLIC_API_URL`) | W7/W10: respect env + show API-unavailable gracefully |
| **TD-12** | Benchmark statistical accuracy `1.0` due to loose `_approx_equal tol 0.05` and single-value `r≈0.8 tol 0.15`, not full multi-level scoring | `evaluation/metrics.py` | overstates rigor; V2 needs proper levels 1–6 | W2/W3: replace with explicit `L1 tool / L2 numeric / L3 method / L4 interpretation / L5 evidence / L6 report` + hard thresholds per task |

---

## 11. Regression Risks

| # | Risk | Scenario | Observed / Guard | Mitigated by |
|---|---|---|---|---|
| **R-01** | Benchmark 50/50 fragility — `sql_contains` & heuristic planner | Adding stricter multi-level checks (e.g. require exact `AVG WHERE` column names) could flip some SQL tasks to `false` | heuristic `_heuristic_sql` covers 7 SQL patterns well today | W1 matrix: add `CSV/Parquet/100MB/malformed/unicode/missing/dup/high-card` + exact gold method tests before tightening criteria |
| **R-02** | Evidence + unsupported_claim guard brittleness | Tightening causal regex or requiring `Evidence coverage = 0 if any insight lacks evidence` would turn current 0.06 unsupported into larger failure rate | 3/50 currently flagged | W6 failure taxonomy should record without failing the gate until W2 rubric is finalized |
| **R-03** | Tool cache non-determinism across `--limit 50` vs `--limit 3` sliced order | Cache hit changes `duration_ms` and possibly output repr used in noteboook cells | `_TOOL_CACHE` global | scope cache per task or reset in runner |
| **R-04** | `ruff` gate flip | If CI enforces `ruff check .` strictly (currently 184 errors), existing commits would suddenly fail | — | W1: baseline `184` frozen, gate stays on delta-only until cleanup PR lands |
| **R-05** | MCP initialize deprecation | Removing `initialize` to align with `2026-07-28` stateless core breaks existing `mcp/server.py` clients expecting `protocolVersion 2024-11-05` | — | W8 ADR + dual-mode `initialize` compat flag until next minor |
| **R-06** | Python sandbox escalation | Hardening AST allowlist (e.g. blocking `importlib` dynamic import) may break legitimate `run_python` tasks that compute stats inline | — | add explicit `regression by target` allowlist tests first |
| **R-07** | Coverage gate `74%` threshold sensitivity | Adding uncovered paths (e.g. `routers/analysis` approve) without tests would actually increase misses and drop below gate | total 74% just at threshold | keep gate as floor (≥74%) not exact match, fail only regressions |
| **R-08** | Dataset format drift (Parquet/Excel path) | Loader is CSV-optimized; Parquet `openpyxl` / Arrow round-trip may regress | only CSV exercised in bench | W1/W3: add Parquet + JSON + Excel task cases before switching datasets |
| **R-09** | LangGraph version churn | Pinned `langgraph>=0.2` + `MemorySaver`; newer LangGraph may change `StateGraph` API / checkpoint signature | currently `0.2` | pin exact minor, add integration smoke in `test_langgraph` on upgrade |
| **R-10** | `resource.getrusage` portability for `/metrics` `rss_mb` | Darwin normalizes bytes vs KB differently (current code handles it, but Linux CI differs) | measured values cross-platform | add unit test for `metrics` endpoint across platforms |

---

## 12. V2 Recommendations

**Principle (V2 §5):** `Correctness > Statistical Rigor > Evaluation Quality > Security > Reproducibility > Observability > Maintainability > Performance > UI` — all W1–W10 keep existing architecture (no rewrite of LangGraph/DuckDB/Polars/FastAPI/SQLite/Agent Graph) unless ADR.

### Recommended workstream order (gate-controlled, test-gated per phase)

```
W1 Baseline & Regression Freeze  (THIS REPORT) → freeze 184 ruff, 74% cov, 50/50@1.0, 86 tests, 7 routes, 17 tools
    ↓
W8 MCP 2026-07-28 Alignment     — small surface, blocks adoption if delayed; ADR for initialize removal
    ↓
W9 Production Security Hardening — adversarial suites build on existing Phase-8 boundary, sandbox limits
    ↓
W2 Evaluation Framework         — replace 50/50 single number with 9-dim + 6-level model (EvaluationResult)
    ↓
W3 Scientific Benchmark         — DS-Agent-Benchmark v2 (30+ datasets / 100+ tasks / 8+ categories / 4 difficulties / gold standard per task)
    ↓
W4 Agent Reliability            — trajectory model, tool-efficiency, retry quality, Critic effectiveness (with/without)
    ↓
W5 Reproducibility & Replay     — L0–L5 scorer, pause/resume/replay/fork/inspect via LangGraph checkpoints aligned to AnalysisRun
    ↓
W6 Failure Analysis             — F01–F15 taxonomy + failure log + Failure dashboard
    ↓
W7 Observability & Telemetry    — Trace/Span/Event/Metric/Artifact, latency breakdown, token-efficiency, Quality-Cost Frontier
    ↓
W10 Research Package            — RQ1–RQ5 + ablation A–F + significance tests (bootstrap/McNemar/Wilcoxon) + results/paper generation
```

**Immediate next steps (do not start Phase B work until this report approved):**

1. Create regression artifacts (outside this report): `benchmarks/baseline/` (results.json/summary.json/raw_runs.json snapshot), `tests/regression/` matrix stubs (Data/Analysis/Agent/Output per §8), `docs/v2/baseline/` (arch snapshot, ERD, tool table, API table, security boundary, roadmap).
2. Add quick wins without touching W2–W10 scope: fix `TD-01 utcnow → now(UTC)`, sort `I001` imports, add `per-file-ignores = B017 for tests/unit/test_datasets.py`, optionally `exclude = *.md` for ruff format — but **do not** start W8–W10 coding.
3. Freeze gates: `pytest 86 pass / mypy 81 clean / ruff 184 (frozen) / coverage 74% (floor) / next build 7/7 / compose valid / bench 50/50 @ 1.0 / unsupported 0.06 / mean_latency 47.92ms` — any W2+ PR must not regress these without explicit ADR + test update.

---

## Appendix — Reproduction Snapshot (live)

```bash
# All commands were run live (not copied from docs/history):
uv run pytest -v                      # 86 passed, 278 warnings
uv run pytest --cov --cov-report=term-missing   # 74%
uv run mypy packages apps/api --ignore-missing-imports  # Success: no issues in 81 source files
uv run ruff check .                  # 184 errors (73 fixable)
uv run ruff check . --statistics
docker compose config                # valid (api + web)
npm --prefix apps/web run build      # 7/7 routes
uv run dsa --limit 50 --out /tmp/dsa-bench-baseline   # 50/50 @1.0
ls benchmarks/ds-agent-benchmark/datasets | wc -l    # 20
git tag --list | sort -V             # v0.1.0 … v1.8.0 (12 tags)
```

**Environment at run time:** `Python 3.12.13 · Node 24.15.0 · npm 11.12.1 · uv 0.11.7 · Docker compose v2 · Darwin arm64` · repo version `1.8.0` · benchmark mean latency `47.92 ms`.

---

## Status Line

**BASELINE FROZEN — awaiting Phase B approval.** This document is the authoritative V1.8 snapshot; future gates compare against it.
