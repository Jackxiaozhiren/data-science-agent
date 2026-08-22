# Compatibility Matrix — V4.1.1 (W7 §44-46)

> **Integration Compatibility Matrix** — Per `DATA_SCIENCE_AGENT_V4_2.md` §44-46 — At least `OS / Python / Node / Docker / Jupyter / VS Code / MCP Version / Plugin Version` (§45) and smoke matrix for `SDK / CLI / Plugin / Jupyter / MCP / MCP App / Docker / PyPI` (§46, each `Install / Startup / Basic Task / Output / Failure Case`)  
> **Date:** 2026-08-22  
> **Commit:** `edabd8b` (harness) + `b79610d` (core) — live  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` W7

---

## 1. Environment Matrix (§45)

| Component | Version / Requirement | Live Verified | Status | Notes |
|-----------|------------------------|---------------|--------|-------|
| **OS** | `Linux` / `macOS` / `Container` (prior, §37) | `macOS-26.6.2-arm64-arm-64bit` (Darwin 25.6.0, arm64) + `Linux` sim via `/tmp` fresh + `Container` Docker | ✅ | `Windows` **Unsupported** (requires WSL2, not tested per `docs/v4_1/release.md` Compatibility) — must document |
| **Python** | `>=3.12` (per `pyproject.toml:6`) | `3.12.13` (via `uv` `python@3.12`, `/opt/homebrew/opt/python@3.12/bin/python3.12`) — `3.9.6` **fails** (`Requires-Python >=3.12`) | ✅ | `pyproject` `requires-python = ">=3.12"`, `uv.lock` 192, `3.9` not supported |
| **Node** | `>=20` (web app, `docs/getting-started.md`) | `v24.15.0` (npm `11.12.1`) | ✅ | `Next.js 15.0.0` + `TypeScript` + `Tailwind` |
| **Docker** | `Docker >=20` + `Compose v5` | `Docker 29.7.2` `Compose v5.3.1` | ✅ | `docker compose config` valid, `healthcheck` `interval:15s` |
| **Jupyter** | `dsa-jupyter 0.1.0` + `ipython>=8.0` + `nest-asyncio` | `dsa-jupyter 0.1.0`, `IPython 9.16.1`, `ipykernel 6.0`, `nest-asyncio` | ✅ (Experimental) | `pip install "jack-data-science-agent[jupyter]"` metadata correct but `pip` fails for `dsa-*` (use `uv sync`) |
| **VS Code** | `^1.85.0` (`apps/vscode/package.json:7`) | `1.85.0` compat, `dsa-vscode 0.1.0`, `tsc` strict | ✅ (Experimental) | `npm --prefix apps/vscode run compile` → `out/extension.js` |
| **MCP Version** | `2026-07-28` stateless (ADR-001) | `2026-07-28` stateless, `18` tools, `5` resources, `0` `Mcp-Session-Id` | ✅ | `packages/mcp/src/dsa_mcp/adapter.py` `stateless`, `MCP_COMPATIBILITY.md` 9 rows |
| **Plugin Version** | `dsa-time-series 1.0.0` / `dsa-plugins 0.1.0` | `1.0.0` (core `4.1.1`, `Python >=3.12`, `dsa >=4.1,<5`) | ✅ (Stable) | `plugins/dsa-time-series/pyproject.toml:4` `1.0.0` |
| **PyPI** | `jack-data-science-agent 4.1.1` | `4.1.1` local wheel (`dist/jack_4.1.1.whl` `13K` + `7.9M` sdist), `4.1.0` on remote PyPI | ⚠️ Partial | `pip install` fails for `dsa-*` (workspace not on PyPI) — `uv sync` is primary (see `QUANTITATIVE_CLAIMS.md:7`) |
| **REST API** | `FastAPI 0.110` + `Pydantic v2` + `Uvicorn 0.29` | `FastAPI` + `uvicorn[standard]>=0.29` (via `uv.lock`) | ✅ | `apps/api/src/dsa_api/main.py` (`/health`/`/ready`/`/version`) |

---

## 2. Integration Smoke Matrix (§46)

At least `SDK / CLI / Plugin / Jupyter / MCP / MCP App / Docker / PyPI` — each `Install / Startup / Basic Task / Output / Failure Case` (§46)

| Integration | Install | Startup | Basic Task | Output | Failure Case | Status |
|-------------|---------|---------|------------|--------|--------------|--------|
| **Python SDK** | `uv sync --dev` (192 pkgs) | `python -c "from data_science_agent import Agent"` `ok` | `Agent().analyze_sync("sales.csv", "Analyze revenue")` → `COMPLETED` 6 evidence (1.33s, CS01) | `Analysis` `status`/`report_markdown`/`evidence`/`insights`/`artifacts`/`tool_calls` | `FileNotFoundError` for missing dataset, `ValueError` for empty task, `RuntimeError` if `asyncio.run` inside Jupyter loop (use `await`) | **PASS** (`tests/sdk 32` + `CS01` live) |
| **CLI** | `uv sync --dev` + `dsa --help` (11 subcommands) | `dsa doctor --json` → `{status:"warn", LLM warn}` | `dsa analyze benchmarks/v2/datasets/sales.csv --task "Analyze revenue" --json` → `run-063c71fbc2 COMPLETED` | `run_id`/`status`/`report`/`evidence` JSON | `dsa analyze missing.csv` → `FileNotFoundError` JSON `error`; `dsa doctor` `LLM warn` is expected (stub) | **PASS** (`tests/sdk/test_cli_contract 13`) |
| **REST API** | `uv run uvicorn dsa_api.main:app --reload --port 8000 --app-dir apps/api/src` | `GET /health` → `{status, details:{db,duckdb,polars,llm}}` + `GET /ready` | `POST /api/v1/datasets/` (multipart 100MB, MIME sniff) → `POST /api/v1/analysis/` `{dataset_id, user_query}` → `GET /api/v1/analysis/{id}` polling | `AnalysisState` `status` `evidence` `report_markdown` `artifacts` `events` (SSE) | `File` (traversal block), `SQL` (read-only allowlist), `Python` (AST allowlist), `Prompt Injection` (UNTRUSTED DATA) — all `403/400` with `details` | **PASS** (`apps/api/tests/test_health 2` + `demo` via API) |
| **Plugin** | `uv sync --dev` (discover) + `dsa plugin list` | `dsa plugin list --json` → `dsa-time-series 1.0.0` | `dsa plugin validate` + `dsa plugin disable/enable` + `forecast` via `TimeSeriesPlugin` | `validate_manifest()` `[]` (no errors), `load_plugin_isolated` `ok`, `forecast` `MAE` | `dsa plugin validate` typo `pandss` → `typosquat` error; `suspicious entrypoint` `os.system` → `suspicious` error; `dependency confusion` `dsa-evil` → `confusion` error; `disable` writes `.registry_state.json` | **PASS** (`tests/plugins 24` + lifecycle 7/7) |
| **Jupyter** | `uv sync --dev` (workspace) + `pip install "jack-data-science-agent[jupyter]"` (metadata, but `pip` fails for `dsa-*` — use `uv sync`) | `ipython -c "import dsa_jupyter; %load_ext dsa_jupyter"` + `uv run python -c "import dsa_jupyter"` | `ipython` `%dsa profile sales.csv` + `await Agent().analyze()` rich HTML (`display_analysis`) | `dsa_jupyter` `0.1.0` magic, `collect_notebook_metadata` `dataset_hash` etc., chart PNG + base64 | `import dsa_jupyter` in non-`uv` env without `dsa-jupyter` → `PackageNotFoundError` (fallback `4.1.1`); `asyncio.run` in loop → `nest-asyncio` thread fallback | **PASS** (`tests/jupyter 10`, Experimental) |
| **VS Code** | `npm --prefix apps/vscode install && npm run compile` → `out/extension.js` | `VS Code` `1.85.0` compat, `Extension→CLI→Core` (`dsa.ts` `child_process` `uv run dsa --json`) | `VS Code` → `DSA: Open Dataset` (picker `*.csv`) → `Ask DSA` (task) → `Run Analysis` → `View Result` (`ResultPanel` HTML) → `View Evidence` (10 rows) | `Dataset Explorer` (30 `*.csv`), `Evidence Explorer` (`dsa:hasResult`), 7 commands | `LLM unavailable` → `CheckResult` `suggestion: OPENAI_API_KEY / dsa doctor`, `Python unavailable` → `uv sync`, `Dataset missing` → `Open Dataset`, `Plugin failure` → `dsa plugin validate`, `Backend unavailable` → `uvicorn` or CLI fallback | **PASS** (`tests/vscode 7`, Experimental, not Marketplace) |
| **MCP** | `uv sync --dev` + `dsa mcp --json` | `GET /mcp/tools` `GET /mcp/resources` `POST /mcp/call` `POST /mcp` (JSON-RPC `initialize/tools/list/tools/call/resources/list/resources/read`) | `tools/call` `profile_dataset` / `run_sql` / `analyze` (explicit `run_id`) | `18` tools (`profile_dataset` … `analyze`) `5` resources (`dataset://` etc.), `permissions` `read/compute/write`, `tool_class` `SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT` | `MCP` `Tasks` (L4) stub → `NotImplemented` honest; `Mcp-Session-Id` deprecated → stateless `run_id` | **PASS** (`tests/mcp 13` + `MCP_COMPATIBILITY.md` 9 rows) |
| **MCP App** | `uv run uvicorn dsa_api.main:app --app-dir apps/api/src` + `GET /mcp-app/` | `GET /mcp-app/` → HTML `Dataset→Question→Analysis→Evidence→Viz→Report` | `Client→Discover→Call→Open Resource→Render` via `jrpc('tools/list')` + `tools/call analyze` + `resources/read evidence://` | Real HTML `packages/mcp/src/dsa_mcp/app.py` 2 routes, `acceptance 6` | `App` without `uvicorn` → `Backend unavailable` (CLI fallback); `Mcp-Session-Id` not used (stateless) | **PASS** (`tests/mcp/test_mcp_app_acceptance 6`, Experimental) |
| **Docker** | `docker compose build` (`Dockerfile.api` + `Dockerfile.web`) | `docker compose up` (api `8000`, web `3000`) + `healthcheck` `interval:15s` `timeout:5s` | `curl -F "file=@sales.csv;type=text/csv" http://localhost:8000/api/v1/datasets/` → `POST /api/v1/analysis` → `GET /report?format=markdown` | `config valid`, `13/13` routes, `health` `details` | `Large file` `100MB` guard → `413`; `10/50/100MB` degraded per `docs/v4_1/release.md` Compatibility | **PASS** (`docker compose config` valid + `npm build` 13/13) |
| **PyPI** | `pip install jack-data-science-agent` (clean `/tmp/dsa-v42-audit` 3.12) | `python -c "import data_science_agent"` (via `uv sync` editable, not `pip`) | `pip install --no-deps dist/jack_4.1.1.whl` (wheel valid) / `uv sync --dev` (full) | `Name: jack-data-science-agent` `Version: 4.1.1` `Requires-Dist: dsa-*` (workspace, not on PyPI) + `fastapi` etc. on PyPI | `pip install jack 4.1.1` **FAIL** `dsa-agent was not found` (workspace 0.1.0 not on PyPI) — honest limitation per `QUANTITATIVE_CLAIMS.md:7`; workaround `uv sync` | **Partial PASS** (wheel valid, `uv sync` PASS, `pip` needs `dsa-*` publish or bundle per ADR) |

---

## 3. Compatibility Notes

- **OS:** `Windows` not tested — document as **Unsupported** (requires `WSL2` + `uv`); `Linux`/`macOS`/`Container` are prior (§37) — `reproduction/external` 3 envs cover `macOS` Real + `Linux`/`Container` sim.
- **Python:** `3.9` fails `Requires-Python >=3.12` (verified in Phase B clean venv) — must use `3.12`.
- **Node:** `v24.15.0` > `20` — `npm --legacy-peer-deps` needed for `apps/web` (per `README.md:41`).
- **MCP:** `Tasks` (L4) is `Stub` per `RELEASE_MATRIX.md` — not in Stable, honest.
- **PyPI:** Until `dsa-*` published or bundled, `pip install` is **not** the supported path — `README.md:32` correctly says `uv sync --dev` (honest per §65).

---

## 4. Verification

```bash
# All smoke matrix steps re-executed live via .venv (uv run)
uv run python -c "from data_science_agent import Agent; print(Agent().version)"  # 4.1.1
uv run dsa --help | head  # 11 subcommands
uv run dsa plugin list --json | jq length  # 1
uv run dsa mcp --json | jq length  # 18
uv run python -c "import dsa_jupyter; print(dsa_jupyter.__version__)"  # 0.1.0
npm --prefix apps/web run build 2>&1 | grep "13/13"  # 13/13
docker compose config > /dev/null && echo "valid"  # valid
uv run mkdocs build --strict > /dev/null && echo "PASS"  # PASS
uv run dsa verify-release v4.1.1  # 12/12 PASS
```

---

*Generated: 2026-08-22 live — `b79610d` → `cf6e561` → `d341ce0` — companion to `QUANTITATIVE_CLAIMS.md` + `PUBLIC_DOCUMENTATION_AUDIT.md` + `EXTERNAL_VALIDATION.md`.*
