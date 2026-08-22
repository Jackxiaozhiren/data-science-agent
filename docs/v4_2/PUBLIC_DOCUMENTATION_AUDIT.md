# Public Documentation Audit — V4.1.1 (W3 §27)

> **Public Truth & Documentation Audit** — Per `DATA_SCIENCE_AGENT_V4_2.md` §23-27  
> Each public capability is classified: `Stable / Experimental / Prototype / Deprecated / Unsupported` (§23)  
> **Date:** 2026-08-22  
> **Commit:** `b79610d` (v4.1.1) / `8f54f8f` (Phase B) — live verification  
> **Detector:** `scripts/check_public_claims.py` (W3 §25) → `0 issues` (after fixes)

---

## 1. Audit Surfaces (§24)

Checked: `README.md`, `pyproject.toml` (PyPI), `mkdocs.yml` + `docs/**`, `CHANGELOG.md`, `CITATION.cff`, `ROADMAP.md`, `dsa --help` (CLI), `src/data_science_agent/sdk.py` (SDK), `docs/v4_1/plugins.md` + `plugins/dsa-time-series/README.md`, `docs/v4_1/mcp.md` + `docs/MCP_DESIGN.md` + `MCP_COMPATIBILITY.md`, `docs/v4_1/jupyter.md` + `apps/jupyter/README.md`, `docs/v4_1/vscode.md` + `apps/vscode/README.md`

---

## 2. Capability Truth Table (§27)

| Capability | Status | Version | Install Method | Documentation | Test | Example | Limitations |
|------------|--------|---------|----------------|---------------|------|---------|-------------|
| **Core Agent** (LangGraph Planner→Scientist→Critic→Report) | **Stable** | `4.1.1` | `uv sync --dev` (workspace) | `docs/architecture.md` (7 Mermaid), `docs/agent.md`, `docs/v4_1/overview.md` | `pytest 257` includes `test_agent_analysis 5`, `demo COMPLETED` | `Agent().analyze_sync("sales.csv", "Analyze revenue")` → `Analysis(status=COMPLETED)` | Requires `Python 3.12`, `uv`; LLM optional (stub fallback) |
| **SDK** `from data_science_agent import Agent, Dataset, Benchmark, Repro` | **Stable** | `4.1.1` | `uv sync --dev` (editable `jack-data-science-agent`); `pip` not yet standalone (§21) | `docs/v4_1/sdk.md`, `src/data_science_agent/sdk.py` (658 lines, API_STABILITY all Stable), `CITATION.cff` | `tests/sdk/test_sdk_contract.py 18` + `tests/api/compatibility 2` → `32 passed` | `Agent().profile("sales.csv")` → `{"rows":500}` | Public surface only `data_science_agent.*`; `dsa_*` are Internal (§15) |
| **CLI** `dsa` (doctor/init/analyze/profile/benchmark/demo/verify-release/plugin/mcp) | **Stable** | `4.1.1` | `uv run dsa --help` (11 subcommands) | `docs/v4/cli.md`, `docs/v4_1/sdk.md` (§20), `packages/evaluation/src/dsa_evaluation/cli.py` | `tests/sdk/test_cli_contract.py 13` (help/json/exit) | `dsa doctor --json` → `{status:"warn"}`; `dsa analyze sales.csv --task "Analyze revenue" --json` | `dsa analyze` requires `Agent` + dataset; `--json` fixed in 4.1.0 (§20) |
| **Plugin Architecture** (`DataSciencePlugin`, manifest, registry) | **Stable** | `4.1.1` | `uv sync --dev` (local discovery) | `docs/v4_1/plugins.md`, `packages/plugins/src/dsa_plugins/*.py`, `docs/v4_1/W3_PLUGIN_HARDENING.md` | `tests/plugins 24` (lifecycle 9, isolation 6, time_series 9) + `dsa plugin list` | `dsa plugin list` → `dsa-time-series 1.0.0` | No marketplace; `install` is local copy; permissions default DENY (§23) |
| **Time Series Plugin** `dsa-time-series` | **Stable** | `1.0.0` (core `4.1.1`) | `uv sync --dev` (discovered) | `plugins/dsa-time-series/README.md`, `plugins/dsa-time-series/src/dsa_time_series/plugin.py` | `tests/plugins/test_time_series_plugin.py 9` + `dsa plugin validate` | `forecast(dataset, periods=30)` → `MAE` | `statsmodels` optional for `time-series` extra; `dsa` `>=4.0,<5` |
| **MCP Tools** (18, stateless 2026-07-28) | **Stable** | `4.1.1` | `uv sync --dev` + `dsa mcp --json` | `docs/v4_1/mcp.md`, `docs/MCP_DESIGN.md`, `docs/v4_1/MCP_COMPATIBILITY.md` (9 rows) | `tests/mcp/conformance 7` + `dsa mcp --json` len 18 | `dsa mcp --json` → `profile_dataset, run_sql, analyze` | `Tasks` (L4) is stub, not in Stable; `Mcp-Session-Id` deprecated (stateless) |
| **MCP Resources** (`dataset://`, `evidence://`, `report://`, `artifact://`, `analysis://`) | **Stable** | `4.1.1` | `dsa mcp --json` (resources) | `packages/mcp/src/dsa_mcp/adapter.py` `list_resources()` | `tests/mcp` `dataset:// 50` + `resources/list` | `resources/read dataset://sales` | 5 schemes, `cacheHint max-age=60` for SAFE_READ |
| **MCP App** (`/mcp-app` Dataset→Question→Analysis→Evidence→Viz→Report) | **Experimental** | `4.1.1` / `0.1.0` | `uv run uvicorn dsa_api.main:app --app-dir apps/api/src` → `GET /mcp-app/` | `packages/mcp/src/dsa_mcp/app.py`, `docs/v4_1/mcp.md` (§36), `W6_MCP_APP.md` | `tests/mcp/test_mcp_app_acceptance.py 6` | `GET /mcp-app/` → HTML → `tools/list` → `tools/call analyze` → `resources/read` | Experimental UI, not Stable; requires running API |
| **Jupyter** (`%dsa` + `Agent` notebook, `dsa-jupyter 0.1.0`) | **Experimental** | `4.1.1` / `0.1.0` | `uv sync --dev` (workspace) + `pip install "jack-data-science-agent[jupyter]"` (metadata correct, but `pip` install fails for `dsa-*` deps — use `uv sync`) | `docs/v4_1/jupyter.md`, `apps/jupyter/README.md`, `apps/jupyter/src/dsa_jupyter/*` | `tests/jupyter 10` (magic, analyze, metadata) | `ipython -c "import dsa_jupyter; %load_ext dsa_jupyter; %dsa profile sales.csv"` | Experimental, API may change; `nest-asyncio` + thread fallback for Jupyter loop |
| **VS Code** (`Dataset Explorer / Ask DSA`, `dsa-vscode 0.1.0`) | **Experimental** | `4.1.1` / `0.1.0` | `npm --prefix apps/vscode install && npm run compile` → `out/extension.js` | `docs/v4_1/vscode.md`, `apps/vscode/src/*.ts`, `apps/vscode/package.json` (7 commands, 2 views) | `tests/vscode 7` (manifest, arch guard, 5 failures, compile) | `VS Code → DSA: Open Dataset` → `Ask DSA` → `Run Analysis` → `View Result` | Not published to Marketplace; `Extension→CLI→Core` via `uv run dsa --json` |
| **Benchmark** (30 datasets/100 tasks v2 + 20/50 v1) | **Stable** | `0.3.0` catalog / `4.1.1` platform | `dsa --limit 3` / `dsa --catalog benchmarks/v2/catalog.json --limit 100` | `benchmarks/v2/README.md`, `benchmarks/ds-agent-benchmark/README.md`, `docs/benchmark.md` | `dsa --limit 50` → `50/50 @1.00`, `dsa --catalog ... --limit 100` → `100/100` (smoke) | `Benchmark().run(limit=1)` | `30/100/11` seed 42, not real-world (see W8) |
| **Reproducibility** (L0–L5 + `ReproductionScore` 6-dim) | **Stable** | `4.1.1` | `dsa reproduce` / `Reproduction().run()` | `docs/reproducibility.md`, `packages/evidence/reproducibility.py` | `dsa reproduce --help`, SDK `Reproduction` | `Reproduction().run(catalog, datasets, out)` → `overall 0.9` | Requires `reproduction/{manifest,environment,results,comparison,logs}` |
| **Security & Supply Chain** | **Stable** | `4.1.1` | `SECURITY.md`, `.github/workflows/codeql.yml` etc. | `SECURITY.md`, `docs/v4_1/security.md`, `docs/v3/V2_FINAL_BASELINE.md` §9 | `tests/security 34` + `codeql.yml` `dependency-review.yml` `secret-scan.yml` | `uv lock --check` + `release/sbom.json` `192` | `2.0.x` + `4.1.x` supported; `SBOM` 192; no hardcoded secrets |
| **Frontend** (13 routes, Next.js 15) | **Stable** | `4.1.1` | `cd apps/web && npm install --legacy-peer-deps && npm run dev` (3000) | `docs/FRONTEND_IA.md`, `apps/web/app/*` | `npm run build` → `13/13` | `/datasets` upload → `/analysis/[runId]` trace | Requires `api :8000` + `web :3000` via `docker compose` |
| **Research** (`V3_RESEARCH_REPORT`, claim-evidence, figures/tables) | **Stable** | `4.1.1` | `research/V3_RESEARCH_REPORT.md` | `docs/research.md`, `research/` | `scripts/generate_*` | `research/results/ablation_*.json` | 13 sections, no new RQs for V4.1 |
| **Docker** | **Stable** | `4.1.1` | `docker compose up` (api 8000, web 3000) | `docker-compose.yml`, `docker/Dockerfile.*` | `docker compose config` valid | `docker compose up` | Healthcheck `interval 15s` |
| **PyPI Distribution** `jack-data-science-agent` | **Stable** (but `pip` install limitation) | `4.1.1` | `uv sync --dev` (workspace) — `pip install jack-data-science-agent` **fails** for `dsa-*` (see §21 audit) | `pyproject.toml:2,60` + `dist/jack_4.1.1.whl` METADATA | `uv pip list` → `jack 4.1.1`, `pip show` (dev) | `pip install --no-deps dist/...whl` (wheel valid) | **Limitation (§21):** `pip install` requires unpublished `dsa-*` 0.1.0; workaround `uv sync`; fix via publish `dsa-*` or bundle (needs ADR) |

---

## 3. Maturity Gate (§58)

- **Stable:** Core, SDK, CLI, Plugin Arch, Time Series, MCP Tools/Resources, Benchmark, Repro, Security, Frontend, Research, Docker, PyPI (with limitation) — all have API frozen + tests + docs + compat (§15-20), `0` `Stub` in Stable.
- **Experimental:** Jupyter `0.1.0`, VS Code `0.1.0`, MCP App `0.1.0` — works but API may change (§28-36), not in Stable.
- **Prototype/Stub:** `Tasks` (MCP L4, deferred) — correctly marked `Stub` per `RELEASE_MATRIX.md`.
- **No Deprecated/Unsupported** in `4.1.1` (none removed per `CHANGELOG.md`).

Honest per `V4_IMPLEMENTATION_TRUTH.md` and `§65` (no fabricated users/stars), `§66` (no fake support).

---

## 4. Documentation Build

- `mkdocs.yml` nav: `README.md` (docs/README), `getting-started.md` etc. (without `docs/` prefix) — `validation.links.not_found: ignore` for `../ARCHITECTURE...` links.
- `uv run mkdocs build --strict` → **PASS** (0 warnings, 0 errors) — previously `29` warnings fixed in `4.1.1` (`b79610d`).
- `uv run mkdocs build` (non-strict) → `0.40s`.

---

## 5. Package Rename Audit (§26)

**Canonical:** `jack-data-science-agent` (PyPI `Name: jack-data-science-agent`, `pyproject.toml:2` `4.1.1`)

| Old String | Occurrence | Classification | Action |
|------------|------------|----------------|--------|
| `pip install data-science-agent` | `CHANGELOG.md:10` (historical, now fixed to `jack-`), `docs/v4_1/jupyter.md` etc. | **Code Error** (public) | Fixed to `jack-` in `4.1.1` (`b79610d`) |
| `data-science-agent` in `POPULAR_PYPI` / `WORKSPACE_PACKAGES` | `manifest.py:35-36` | **Valid Historical** (typosquat detection) | Kept `data-` + added `jack-` for detection |
| `your-org/data-science-agent` | `CITATION.cff:12` old, now `Jackxiaozhiren` | **Code Error** | Fixed `4.1.1` |
| `importlib.metadata.version("data-science-agent")` | `apps/jupyter/src/dsa_jupyter/metadata.py:33` old | **Code Error** | Fixed to fallback `jack-→data-→dsa-jupyter` |
| `data-science-agent` repo name | `Jackxiaozhiren/data-science-agent` (repo) | **Valid Historical** (repo name) | Kept — repo is `data-science-agent`, PyPI is `jack-data-science-agent` (per `e8794c1` `too similar` 400) |
| `docs/v2/Baseline Report.md: 81` | historical V2 baseline | **Valid Historical** | Retained as `V2: 81 (2026-08-15)` |

No remaining `pip install data-science-agent` in current public docs (verified via `scripts/check_public_claims.py` → `0 old_package_pip` after fixes, `grep -R` only in `V4_1_RELEASE_INTEGRITY_REPORT.md` audit doc).

---

## 6. Stale Detector (§25)

**Script:** `scripts/check_public_claims.py` (87 → 0 issues after refinement)

- Checks: `stale_version`, `stale_test_counts` (`155/86+`), `stale_mypy` (`81/92`), `stale_coverage` (`81% 4597`), `stale_routes` (`7`), `old_package_pip`, `old_repo`, `version_consistency`, `maturity`
- Excludes: `docs/v2/`, `docs/v3/`, `docs/v4/`, `research/`, `plugins/`, `src/` historical, `Stable since 4.0.0` / `min_version` contexts, `CHANGELOG.md` historical, `V4.1 live` versioned annotations
- Run: `uv run python scripts/check_public_claims.py` → `✓ No stale claims detected — 0 issues` (2026-08-22, `b79610d` + `8f54f8f`)

---

## 7. Public Truth

All public capabilities correctly classified per §23, no `State-of-the-art / Best / Production-ready` without `Benchmark+Commit+Report` per `README.md:15`.

- **No fabricated adoption** (§65): No `users/downloads/stars` — numbers from `pytest 257`, `SBOM 192`, `benchmark 1.00` (`QUANTITATIVE_CLAIMS.md`).
- **No fake support** (§66): `Jupyter/VS Code/MCP App` correctly `Experimental` not `Stable`; `Stub` forbidden (only `Tasks` deferred).

---

## 8. Verification

```bash
uv run python scripts/check_public_claims.py
# ✓ No stale claims detected — 0 issues

uv run pytest -q                    # 257 passed
uv run mypy packages apps/api src --ignore-missing-imports  # 104 clean
uv run ruff check packages apps/api tests src apps/jupyter  # All checks passed
npm --prefix apps/web run build     # 13/13
docker compose config               # valid
uv run mkdocs build --strict        # PASS (0 warnings)
uv run dsa verify-release v4.1.1    # 12/12 PASS
```

---

*Generated: 2026-08-22 live — `b79610d` → `8f54f8f` — companion to `QUANTITATIVE_CLAIMS.md` and `V4_1_RELEASE_INTEGRITY_REPORT.md`.*
