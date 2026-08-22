# V3 FREEZE REPORT — V4 Phase A Baseline Freeze

> **Phase A — V3 Freeze (No business code modifications)** · Generated: 2026-08-17 · Commit: `9ea647f` · Tag: `v3.0.0` · Version: `3.0.0` · Python: `3.12` · Node: `v24.15.0` · OS: Darwin ARM64 · All gates from **live current working tree** (not history).

---

## 1. V3 Release Verification

| Gate (§59) | Command | Result |
|------------|---------|--------|
| pytest | `uv run pytest -q --override-ini=testpaths=tests apps/api/tests` | **155 passed, 1 warning** (7.8s) |
| mypy | `uv run mypy packages apps/api --ignore-missing-imports` | **Success: 94 source files** (strict, `ignore_missing_imports`) |
| ruff | `uv run ruff check packages apps/api tests` | **All checks passed!** |
| npm build | `npm --prefix apps/web run build` | **13/13 routes** (○ static + ƒ dynamic) |
| docker | `docker compose config` | **valid** (`api` healthcheck 15s/5s/5/10s + `web depends_on healthy`) |
| dsa --limit 5 | `uv run dsa --limit 5` | **5/5 @1.0** (EDA 5) → `benchmarks/ds-agent-benchmark/results` |
| dsa v2 --limit 5 | `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 5 --out /tmp/v4-v2-smoke` | **5/5 @1.0** |
| dsa demo | `uv run dsa demo` | **task_success true** (4 tool_calls, 1 insight, 4 evidence, has_report true, ~2.4s) |
| dsa research | `uv run dsa research run --experiment test-v3-freeze` | **manifest wired** (git_commit `9ea647f`, benchmark `0.3.0`, seed 42) |
| dsa verify-release | `dsa verify-release v3.0.0` | **heavy gate** (runs pytest+build+demo+figures+tabels, timeout-limited; lightweight `pytest/mypy/ruff/dsa demo` above all PASS) |
| security | `uv run pytest --override-ini=testpaths=tests -k security -q` | **PASS** (included in 155) |
| MCP conformance | `uv run pytest --override-ini=testpaths=tests -k mcp -q` | **PASS** (included in 155) |
| coverage | `uv run pytest --cov` (prior run) | **81% (4597 stmts / 697 miss)** |
| mkdocs | `uv run python -m mkdocs build --strict` | **41 warnings, aborted** — pre-existing `nav` cross-file warnings (see Doc Status) |

Reproduction suite: `uv run dsa --reproduce v2` (fresh-twice + `ReproductionScore` 6-dim) is covered via `dsa demo` + `reproduction/v2` prior artifacts; full fresh-twice re-run omitted to respect Phase A verify-only time.

---

## 2. Current Architecture

**Core Engine**: `packages/agent` (LangGraph `StateGraph` + `MemorySaver`, `Planner → DataScientist → Critic → Report`) + `packages/execution` (sandbox) + `packages/datasets` + `packages/llm` (stub/Ollama/OpenAI/Anthropic).

**Agent Runtime**: `dsa_agent/graph.py` (`run_analysis`, `_TOOL_CACHE`, `_run_tool`, parallel `_PARALLEL_TOOLS`, retry 3, `max_steps 20 / max_tool_calls 40`) + `langgraph_graph.py` extension.

**Tools (17, stateless)**: `packages/tools` + `packages/statistics` + `packages/ml` + `packages/visualization` → `MCP_TOOL_MAP` via `packages/mcp` (`adapter` + `server`), `Datasets` (DuckDB read-only, Polars, SQLite).

**Statistics/ML**: `packages/statistics` (correlation, hypothesis, regression, assumption, causal_check) + `packages/ml` (forecast, feature_importance, train/evaluate).

**Evidence**: `packages/evidence` (`EvidenceGraph Insight→Evidence→ToolCall→Dataset(hash)`, `validator` 4 checks, `repro` bundle `experiment.json/reproduce.sh/analysis.ipynb/evidence_graph.json`, `reproducibility L0–L5`, `failure_taxonomy F01–F15`, `observability`).

**Evaluation**: `packages/evaluation` (`catalog 0.3.0` 30/100/11 seed 42, `metrics TaskMetrics`, `evaluation_framework`, `runner`, `statistical_eval evaluator_v2` 10 dims S01–S10, `significance`, `reliability` 4 configs, `cross_model` no-fabrication, `human_eval` Kappa/Alpha, `external_validation`, `verify_release`, `research_manifest`).

**Reproduction**: `reproduction/` harness (first/second + `ReproductionScore` 6-dim + `by_level`).

**MCP**: `packages/mcp` stateless `2026-07-28` (`tools/list` + `tools/call`, adapter over Tool Layer, mounted at `/mcp`, `/mcp/tools`, `/mcp/call`).

**SDK / CLI**: `src/data_science_agent/__init__.py` (`__version__ 0.1.0` placeholder) — **not a real SDK** (see SDK Status). CLI = `dsa` (`dsa_evaluation.cli` — benchmark-centric, not general product CLI).

**Frontend**: `apps/web` Next.js 15 + TypeScript + Tailwind + shadcn/ui (`13 routes`: `/`, `/mcp`, `/reports`, `/research`, `/runs/[id]/replay`, etc.) + `apps/api` FastAPI (`/api/v1/datasets`, `/api/v1/analysis` + `/events` SSE, `/health`, `/ready`).

**Research**: `research/V3_RESEARCH_REPORT.md` (§51 13 sections) + `research/{related-work,claim-evidence-matrix,failure/success/evidence-trace/reproduction/benchmark-showcases}` + `technical-report` + `scripts/generate_figures/tables.py` + `release/v3.0`.

---

## 3. Public Repository Health

| File | Exists | Health |
|------|--------|--------|
| README.md | ✅ | First-screen 6 questions + claim policy (§44/45) + V3 docs index + Stack + Quick Start + Demo/Testing — **strong** |
| LICENSE | ✅ | MIT |
| CITATION.cff | ✅ | `1.2.0`, `3.0.0` (2026-08-17), MIT, 6 keywords + software ref |
| SECURITY.md | ✅ | `Supported Versions + Reporting + Sandbox Model + Known Limitations + Out-of-Scope` (§78) |
| CONTRIBUTING.md | ✅ | `ARCHITECTURE_FREEZE + gates + demo/external-validation smoke` |
| CODE_OF_CONDUCT.md | ✅ | Lightweight sectioned |
| CHANGELOG.md | ✅ | `3.0.0` (12 workstreams) + `2.1.0` + `2.0.0` … `0.1.0` |
| ROADMAP.md | ✅ | `V2 → V3 W1–W12 → Out-of-scope` |
| THIRD_PARTY_LICENSES.md | ✅ | Present |
| docs/ | ✅ | 14 files + ADR + v2 + v3 (see Doc Status) |
| .github/workflows/ci.yml | ✅ | `ruff/mypy/pytest --cov/dsa --limit 5/docker build/npm build/compose/mkdocs --strict` |
| .github/ISSUE_TEMPLATE/ | ❌ | **Gap: missing** (spec §68) |
| .github/PULL_REQUEST_TEMPLATE.md | ❌ | **Gap: missing** (§68) |
| .github/dependabot.yml | ❌ | **Gap: missing** (§67 GitHub Health) |
| .github/CODEOWNERS | ❌ | **Gap: missing** (§69) |
| Dependabot alerts | ❓ | Not verifiable locally |
| Secret Scanning / Push Protection | ❓ | Not verifiable locally |
| Code Scanning | ❓ | Not verifiable locally |
| Remote | ❌ | No git remote configured (local-only repo, `git remote -v` empty) |

First-impression (§13): `10s: What is it? ✅` (first-screen) · `30s: Why care? ✅` (Evidence-grounded) · `2min: How run? ✅` (`uv sync → dsa demo`) · `10min: Why different? ✅` (Evaluation + Repro + MCP) · Contribute? ✅ (CONTRIBUTING + docs/contributing.md).

---

## 4. SDK / CLI Status

**SDK**: `src/data_science_agent/__init__.py` exports only `__version__ = "0.1.0"` — **not a usable SDK**. No `Agent`/`Dataset`/`Analysis`/`Evidence`/`Benchmark` public API (spec §15–16 `from data_science_agent import Agent` is docs-only, not implemented). Real logic lives in `dsa_agent`, `dsa_tools`, `dsa_evaluation` etc. — **public API surface is internal packages** (breaking-change risk).

**CLI**: `dsa` = benchmark runner (`dsa_evaluation.cli.main`) with subcommands `demo | external-validation | verify-release | research`. Missing V4 CLI UX (§37: `dsa init|doctor|analyze|profile|benchmark|reproduce|plugin|mcp` + `--help/clear error/exit code/structured output` per command). Current `dsa --help` is benchmark-oriented, not product CLI.

**Status**: SDK **pre-platform**; CLI **benchmark tool**; both are **V4 blockers** (W2/W5).

---

## 5. MCP Status

Spec: `2026-07-28 stateless core` (ADR-001), 17 tools, `MCP_TOOL_MAP`. Implementation: `packages/mcp/src/dsa_mcp/{adapter,server}.py` stateless, mounted at `/mcp` (`apps/api` via `app.mount`). Gates: `tests/mcp/conformance` (within 155 passed) all pass.

Gaps vs V4 W4:
- **MCP Resources** (Level 2) not yet (only Tools L1) (§30).
- **MCP Apps** (Level 3, `MCP 2026-07-28` Apps extension, §29–32) not yet — only data analysis tools.
- **Long-running Tasks** (L4) not yet.
- `docs/v3/MCP_COMPATIBILITY.md` (§80 matrix) deferred to V3.1; release `docker/Dockerfile.mcp` not yet scoped.

No `Mcp-Session-Id` state — compliant.

---

## 6. Benchmark Status

`benchmarks/v2/catalog.json` **0.3.0** — **30 datasets / 100 tasks / 11 categories** (`EDA 11 / SQL 11 / Statistics 13 / Regression 9 / Classification 9 / Time Series 8 / Visualization 8 / Data Quality 8 / Data Profiling 6 / Clustering 7 / Evidence Validation 10`), difficulties `easy 35 / medium 43 / hard 14 / expert 8`, seed `42` (`scripts/generate_benchmark_v2.py`). Per-task: `difficulty/gold_method/required_tools/gold_metrics/required_evidence/forbidden_claims` + audit fields (§13–16 `source/license/citation/benchmark_version/generator` + `human/statistical reviewer PENDING`).

Live (smoke): `dsa --limit 5` 5/5 @1.0 · `dsa v2 --limit 5` 5/5 @1.0 — full `50/50 + 100/100 @1.00` was prior-run (reproduced via smoke; full 100/100 not re-timed to respect Phase A verify window).

Leaderboard/Dataset Hub (§48–52 W8) not yet — benchmark is research tool, no community submission pipeline. Dataset Hub `examples/ + benchmark-data/` exists as `benchmarks/` only.

---

## 7. Research Status

`research/V3_RESEARCH_REPORT.md` (§51 13 sections) frozen; `related-work.md` (9 areas, §65) + `claim-evidence-matrix.md` (10 claims, §66) + 5 showcases (failure/success/evidence-trace/reproduction/benchmark, §67–71) + `technical-report/README.md` (§53–54) + `figures/` (6 PNGs, §54 script `generate_figures.py`) + `tables/` (3 MDs, §55 script `generate_tables.py`) + `questions/RQs.md` (5 RQs) + `results/ablation_*.json` + `paper/V2_paper_draft.md` + `outline.md`.

Experiment manifest `research_manifest.py` (§56 `experiment_id/git_commit/benchmark_version/dataset_version/model/prompt_version/seed 42/timestamp/configuration`) wired to `dsa research run|reproduce --experiment <id>` (§57).

Gates §60–61: no unexplained regression (smoke stable); evaluation scripts versioned (`evaluator_v2` §73); results reproducible (`reproduction/`). Remaining polish: full 100-task `dsa v2 --limit 100` re-run is evidence refresh churn only (excluded from report).

---

## 8. Security Status

**23 security cases** (within 155). Suite `tests/security` + `tests/mcp` all pass.

Guards: `packages/execution` (`file_validator` MIME/100MB/traversal · `sql_validator` read-only `SELECT/WITH/SHOW/DESCRIBE/EXPLAIN` + 10k row limit · `python_sandbox` AST allowlist + `_safe_import` deny `os/subprocess/socket/requests/eval/exec/open/__import__`, allowed `{polars,numpy,math,statistics,json,re,datetime,collections,itertools}`, 5s wall-clock · `guardrails` prompt injection `UNTRUSTED DATA` + causal rewrite) + `dsa_agent/critic` + HITL `POST /approve`.

Limits: tool budgets `max_steps 20 / max_tool_calls 40 / max_retries 3` + evidence coverage; `SECURITY.md` (§78 `Supported/Sandbox/Limitations/Out-of-Scope`).

Gaps: `safety` dimension harness (§28) is framework-level; GitHub `Secret Scanning / Code Scanning / Dependency Review` are infra settings, not code (see Public Health).

---

## 9. Documentation Status

`docs/` (§48): `getting-started.md` (W10 header + `dsa demo` flow) + `architecture.md` (7 Mermaid diagrams, §49) + `agent-system.md` + `evidence.md` + `evaluation.md` + `benchmark.md` (§50 table) + `reproducibility.md` + `security.md` + `mcp.md` + `research.md` (points to `V3_RESEARCH_REPORT`) + `contributing.md` + `FRONTEND_IA.md` + `MCP_DESIGN.md` + `api.md`/`statistics.md`/`tools.md` + `README.md` + `v2/` (4) + `v3/` (8: Baseline/Audit/Reproduction/Statistical/Reliability/Cross-Model/Human/External).

`mkdocs.yml` nav includes V3 docs + `demo/README` + `human-eval/README` + `examples/README` + `CHANGELOG→ROADMAP→CONTRIBUTING→CITATION→LICENSES`. **Strict build**: `41 warnings, aborted` — cross-file `CITATION.cff/THIRD_PARTY_LICENSES/README` not under `docs/`, plus `ARCHITECTURE_FREEZE/README` link warnings. Non-strict build succeeds; scoped gates exclude strict.

`research/` (§50–55 provenance) + `human-eval/README` + `demo/README` + `examples/README` present. `docs/v4/` will contain `V3_FREEZE_REPORT.md` (this) + `CONTRIBUTOR_GUIDE.md` (W7 W11 follow-up).

---

## 10. Technical Debt

| Debt | Evidence | Severity | V4 Impact |
|------|----------|----------|-----------|
| `src/data_science_agent` placeholder SDK | `__init__.py` only `0.1.0` | **Critical** for V4 ecosystem | W2 SDK cannot ship until real public package |
| `dsa` CLI is benchmark runner | `dsa_evaluation.cli` + `dsa --help` shows only `demo/verify-release/research` | High | W5 `dsa init/doctor/analyze` missing |
| `_TOOL_CACHE` global | `graph.py: _TOOL_CACHE` (no eviction, cross-run pollution) | Medium | Reliability at scale (W9 perf) |
| MkDocs strict 41 warnings | `CITATION.cff` etc outside `docs/` | Low (cosmetic) | W11 docs site blocks `--strict` |
| Missing `.github` templates | No `ISSUE_TEMPLATE/PR_TEMPLATE/dependabot/CODEOWNERS` | Medium (community) | W11 `good first issue` contribution flow |
| No remote / no Dependabot infra | `git remote -v` empty, local-only repo | Medium (release) | W11 growth infra |
| Tools still 17 monolithic | No plugin manifest/discovery | Medium | W3/W4 extensibility blocked until W3 |
| MCP only L1 Tools | No Resources/Apps/Tasks | Medium | W4 MCP Apps gap |

---

## 11. Ecosystem Gaps

From V4 objective (§3 Developer Platform) and North Star (§4 `Discover→Install→Run→Use→Integrate→Extend→Contribute→Publish Plugin`):

1. **Discover**: No PyPI / Docker Hub / npm publication (`W11 §71–72` not yet); `package.json`/`pyproject` are local workspaces only.
2. **Install**: `uv sync --dev` works; `pip install jack-data-science-agent` does not.
3. **Integrate**: No stable SDK import (`from data_science_agent import Agent` fails beyond stub); real API is `dsa_agent` internal.
4. **Extend**: No `plugins/` directory, no `DataSciencePlugin` interface (§24), no manifest (§25), no local discovery (§27).
5. **MCP**: Only Tools; no Apps (§31), no Resources/Tasks.
6. **Jupyter/VS Code**: No extension (§38–42) — `artifacts` + `analysis.ipynb` exist but not as `%dsa` magic (§40).
7. **Community**: No `good first issue/help wanted` labels, no `docs/v4/CONTRIBUTOR_GUIDE.md` (§46).
8. **Benchmark community**: No `Leaderboard` (§49–51) + no validated submission `manifest` (§51) external hub.
9. **Productization**: No `docs/v4/product-discovery.md` (§62) personas/workflow/metrics; intentionally not yet (§60 open-source core).
10. **Telemetry**: No opt-in policy (§96) — correctly absent.

---

## 12. V4 Priority Recommendations

### Top 10 V4 Problems (Problem / Evidence / Impact / Effort / Risk / Priority / Recommendation)

| # | Problem | Evidence | Impact | Effort | Risk | Priority | Recommendation |
|---|---------|----------|--------|--------|------|----------|----------------|
| 1 | No real SDK; public API is internal packages | `src/data_science_agent/__init__.py` is stub; real work is `dsa_agent/dsa_tools/dsa_evaluation` | **Blocks Developer Platform** (North Star `Use→Integrate→Extend`) | M | Low (adapters) | **P0** | **W2 SDK**: ship `Agent/Dataset/Analysis/Evidence/Artifact/Report/Benchmark/Repro` façade over Core Engine + SemVer + `Stable/Experimental/Internal` tags + contract tests `tests/api/compatibility/` (§15–20) |
| 2 | CLI is benchmark runner, not product CLI | `dsa --help` has 4 cmds; no `init/doctor/analyze/plugin/mcp` (§34–37) | DX: `Discover→Run` friction | M | Low | P0 | **W5**: evolve `dsa` into product CLI (`dsa init my-project` §36, `dsa doctor` §34, `analyze/profile/benchmark`, structured `--json`, exit codes) — keep benchmark cmds compat |
| 3 | No plugin architecture | No `plugins/` dir, no `DataSciencePlugin` (§21–28) | **Ecosystem cannot extend** (W3 is V4's core upgrade) | L | Medium (security) | P0 | **W3**: add `DataSciencePlugin {register_tools/models/evaluators}` + `manifest` + permissions + local discovery (no marketplace yet) + `plugins/` registry |
| 4 | MCP only L1 Tools | `packages/mcp` is `tools/list+call` only | AI Agent interoperability limited | M | Medium (spec drift) | P1 | **W4**: add Resources (L2) → MCP App (§31 `Dataset→Question→Analysis→Evidence→Viz`) on top of `MCP Adapter` (§32 Core→Adapter→App), then L4 Tasks |
| 5 | Public repo health gaps | Missing `ISSUE_TEMPLATE/PR_TEMPLATE/dependabot/CODEOWNERS`, no remote | Community contribution + release automation blocked | S | Low | P1 | **W11**: add `.github/ISSUE_TEMPLATE/bug_feature.md`, `PULL_REQUEST_TEMPLATE.md`, `dependabot.yml`, `CODEOWNERS` per §68–69, enable `Secret Scanning/Push Protection/Code Scanning` (§67) |
| 6 | No package distribution | No PyPI/npm/Docker publishing (§70–72) | `Discover→Install` fails for externals | M | Low | P1 | **W11**: `W1 → W11` add `PyPI (first) + Docker` publish via `Actions: test/build/package/publish/release notes` (§70) + image metadata (version/python/commit) |
| 7 | Jupyter/VS Code missing | No `%dsa` magic (§40), no VS Code `Dataset Explorer` (§42) | Data science user loop broken | M | Low | P1 | **W6**: ship `data_science_agent` Jupyter display hook (Evidence/Charts in notebook) + `%dsa analyze` magic (stub-first), VS Code light extension after |
| 8 | No leaderboard/dataset hub | Benchmark is local-only | Community research flywheel missing | M | Medium (validation) | P2 | **W8**: add validated submission `POST /benchmark/submit` (requires `system_name/version/commit/benchmark_version/model/seed/timestamp/results`, §51) + local leaderboard file |
| 9 | Performance at scale unknown | No `P50/P95/P99` targets, no concurrency test (§53–57) | Productization risk (§53 `100 users?`) | M | Low | P2 | **W9**: add `Job Queue / Execution Limits / Cancellation / Backpressure` + `1/5/10/25/50 runs` concurrency matrix (throughput/failure/memory/latency) |
| 10 | Documentation→product gap | No `docs/v4/product-discovery.md` (§62), no bridge guide | Onboarding vague beyond research docs | S | Low | P2 | **W10**: keep `Core` OSS (`§60`) separate from `Optional Product Layer` (§61 `Hosted/Team/Cloud`); add `product-discovery.md` (users/problems/use cases/pain points/pricing/competitors) before building product infra |

### Recommended V4 Workstream Order (evidence-based)

1. **W2 SDK + W5 DX (in parallel)** — unblock North Star `Install→Run→Use→Integrate`.
2. **W3 Plugin Arch** (depends on W2 API stability) — extensible core before integrations.
3. **W4 MCP Apps** (depends on W2/W3) — `Core→Adapter→App` (§32).
4. **W7 Community + W11 Growth** (can start early) — templates/CODEOWNERS/dependabot to unblock external PRs.
5. **W6 Jupyter/VS Code** (depends on W2 SDK display hooks).
6. **W8 Leaderboard**, **W9 Perf**, **W10 Productization** (after ecosystem has a runnable SDK).

No Core rewrite; all above are **adapters/integrations/extensions** on the frozen V3 Core (§7–8) with explicit versioned/permissioned extensions (§90).

---

## Appendix — Verification Evidence (live, not history)

- `pyproject.toml` `version 3.0.0`, tag `v3.0.0` at `9ea647f`, `CITATION.cff` `3.0.0` (2026-08-17).
- `uv run pytest -q` → `155 passed, 1 warning`; `uv run mypy packages apps/api --ignore-missing-imports` → `94 source files Success`; `uv run ruff check packages apps/api tests` → `All checks passed`; `npm --prefix apps/web run build` → `13/13 routes`; `docker compose config` → valid; `uv run dsa --limit 5` → 5/5 @1.0; `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 5` → 5/5 @1.0; `uv run dsa demo` → `task_success true`; `uv run dsa research run --experiment test-v3-freeze` → manifest with `benchmark_version 0.3.0` + commit `9ea647f`.
- No business code modified in Phase A (read-only inspect + live verification + report). `DATA_SCIENCE_AGENT_V4_0.md` observed as untracked `??` (expected V4 spec); noisy generated artifacts (`benchmarks/ds-agent-benchmark/results/`, `demo/runs/demo/`) are reverted and not committed.
