# Quantitative Claims Registry — V4.1.1 (W2 §19)

> **Single Source of Truth for Public Numbers** — Per `DATA_SCIENCE_AGENT_V4_2.md` §19  
> Each public number must record: `Metric / Value / Version / Commit / Source / Date / Methodology`  
> Historical values are retained with `Version + Date + Context` per §18 — not blindly replaced.

**Live verification date:** 2026-08-22  
**Live commit:** `b79610d` (HEAD == `v4.1.1`) — previous `v4.1.0` at `4a0158d` (2026-08-21) and patch `e8794c1` (2026-08-21)  
**Methodology note:** All gates re-executed live via `.venv` (Python 3.12.13, uv 0.11.7, Node v24.15.0, Docker 29.7.2) — not historical.

---

## 1. Core Quality Gates (V4.1.1 Live)

| Metric | Value (Live) | Version | Commit | Source | Date | Methodology |
|--------|--------------|---------|--------|--------|------|-------------|
| **pytest** | `257 passed` (79%, 5140 stmts, 1 warning) | `v4.1.1` | `b79610d` | `uv run pytest -q --cov` (14.3s) | 2026-08-22 | `pytest 8.2`, `pytest-asyncio 0.23`, `pytest-cov 5.0`, `testpaths = ["tests", "apps/api/tests"]`, `--asyncio-mode=auto` |
| **mypy (strict)** | `104 clean` (`packages apps/api src`) / `102` (`packages apps/api`) | `v4.1.1` | `b79610d` | `uv run mypy packages apps/api src --ignore-missing-imports` | 2026-08-22 | `mypy 1.10`, `python_version 3.12`, `strict=true`, `ignore_missing_imports=true` |
| **ruff** | `All checks passed` | `v4.1.1` | `b79610d` | `uv run ruff check packages apps/api tests src apps/jupyter` | 2026-08-22 | `ruff 0.4`, `line-length 100`, `select [E,F,I,B,UP,SIM,S]` |
| **npm routes** | `13/13` | `v4.1.1` | `b79610d` | `npm --prefix apps/web run build` → `Generating static pages (13/13)` | 2026-08-22 | `Next.js 15.0.0`, `TypeScript`, `Tailwind` |
| **docker** | `valid` | `v4.1.1` | `b79610d` | `docker compose config` → `healthcheck interval:15s` | 2026-08-22 | `docker-compose.yml` (api:8000, web:3000) |
| **dsa verify-release** | `12/12 PASS` | `v4.1.1` | `b79610d` | `uv run dsa verify-release v4.1.1` | 2026-08-22 | 12 gates: pytest/mypy/ruff/npm/docker/security/mcp/bench/demo/tables/figures/docs |
| **mkdocs** | `PASS` (`--strict` 0 warnings) | `v4.1.1` | `b79610d` | `uv run mkdocs build --strict` | 2026-08-22 | `mkdocs 1.5`, `material 9.0`, `validation.links.not_found: ignore`, nav `README.md` etc. |

**Historical:**

| Metric | Value | Version | Date | Context |
|--------|-------|---------|------|---------|
| pytest | `~86+` | `v1` | 2026-08-01 | Scaffold (§3) — `README.md:33` original |
| pytest | `155` | `v3.0.0` | 2026-08-17 | `CHANGELOG.md: v3.0.0` — `uv run pytest -q` 155 (unit+integration+security+evals) |
| pytest | `157` | `v4.0.0` | 2026-08-17 | `CHANGELOG.md: v4.0.0` — `fbf6dd7` |
| pytest | `257` | `v4.1.0` | 2026-08-21 | `4a0158d` — W2-W9 added 100 tests |
| mypy | `81` | `v2` | 2026-08-15 | `docs/v2/Baseline Report.md` — `mypy packages apps/api` 81 files |
| mypy | `92` | `v3.0` | 2026-08-17 | `README.md:167` pre-fix — `mypy ... 92 clean` |
| coverage | `81% (4597 stmts)` | `v3.0.0` | 2026-08-17 | `README.md:166` — `pytest --cov` |
| coverage | `79% (5140 stmts)` | `v4.1.1` | 2026-08-22 | Live — stmts grew, coverage dropped (new code) |

---

## 2. Security & Supply Chain

| Metric | Value | Version | Commit | Source | Date | Methodology |
|--------|-------|---------|--------|--------|------|-------------|
| **security cases** | `34` (`10 adversarial` + `13 phase8` + `11 w7`) | `v4.1.1` | `b79610d` | `uv run pytest tests/security -q` → `34 passed` | 2026-08-22 | `tests/security/test_adversarial_suite.py 10` + `test_security_phase8.py 13` + `test_w7_supply_chain.py 11` |
| **CodeQL** | `PASS` (workflow exists) | `v4.1.1` | `b79610d` | `.github/workflows/codeql.yml` → `python`+`javascript`, `codeql-action/init` | 2026-08-22 | `codeql.yml` + `dsa verify-release` `security suite` |
| **Dependency Review** | `PASS` | `v4.1.1` | `b79610d` | `.github/workflows/dependency-review.yml` → `fail-on-severity` | 2026-08-22 | PR gate |
| **Secret Scan** | `PASS` | `v4.1.1` | `b79610d` | `.github/workflows/secret-scan.yml` → `gitleaks` full history | 2026-08-22 | No `sk-`/`ghp_`/`api_key` in repo |
| **SBOM** | `192 components` | `v4.1.1` | `b79610d` | `release/sbom.json` `len(components)==192`, `release/sbom.cyclonedx.json` `bomFormat CycloneDX` | 2026-08-22 | `scripts/generate_sbom.py` → `uv.lock` + workspace `jack-data-science-agent` |
| **uv.lock** | `192 packages` | `v4.1.1` | `b79610d` | `uv lock --check` (ci.yml) | 2026-08-22 | `uv 0.11.7`, committed, `pip`+`npm`+`docker` dependabot weekly |

---

## 3. Integration & Distribution

| Metric | Value | Version | Commit | Source | Date | Methodology |
|--------|-------|---------|--------|--------|------|-------------|
| **SDK contract** | `18` (plus 13 CLI, 2 compat) → `32` total | `v4.1.1` | `b79610d` | `uv run pytest tests/sdk -q` → `32 passed` (`test_sdk_contract.py 18` + `test_cli_contract.py 13` + compat) | 2026-08-22 | `data_science_agent.sdk: API_STABILITY Stable` |
| **CLI contract** | `13` | `v4.1.1` | `b79610d` | `uv run pytest tests/sdk/test_cli_contract.py` | 2026-08-22 | `--help/--json/exit 0/1/2` for 11 subcommands |
| **Plugin** | `24` (`dsa-time-series 1.0.0`) | `v4.1.1` | `b79610d` | `uv run pytest tests/plugins -q` + `dsa plugin validate dsa-time-series` → `ok` | 2026-08-22 | `plugins/dsa-time-series` `forecast/backtest/metrics/viz/evidence`, `manifest CURRENT_DSA_VERSION 4.1.1` |
| **MCP conformance** | `7` + `6` app = `13` | `v4.1.1` | `b79610d` | `uv run pytest tests/mcp -q` → `13 passed` | 2026-08-22 | `mcp/conformance 7` + `test_mcp_app_acceptance 6` (`/mcp-app` HTML) |
| **MCP tools** | `18` (incl. `analyze`) | `v4.1.1` | `b79610d` | `dsa mcp --json` → `len==18` | 2026-08-22 | `packages/mcp/src/dsa_mcp/adapter.py` `MCP_TOOL_MAP` |
| **MCP resources** | `5` schemes | `v4.1.1` | `b79610d` | `adapter.list_resources()` → `dataset://, evidence://, report://, artifact://, analysis://` | 2026-08-22 | `dataset:// 50` + others |
| **Jupyter** | `10` (`dsa-jupyter 0.1.0`) | `v4.1.1` / `0.1.0` | `b79610d` | `uv run pytest tests/jupyter -q` → `10 passed` | 2026-08-22 | `%dsa` magic + `Agent` rich + `metadata 6` |
| **VS Code** | `7` (`dsa-vscode 0.1.0`) | `v4.1.1` / `0.1.0` | `b79610d` | `uv run pytest tests/vscode -q` → `7 passed` | 2026-08-22 | `package.json 0.1.0`, `tsc` strict, 7 commands |
| **Benchmark** | `50/50 @1.00` (v1) + `100/100 @1.00` (v2) → smoke `3/3 @1.00` live | `v4.1.1` | `b79610d` | `dsa --limit 3` + `dsa --catalog benchmarks/v2/catalog.json --limit 3` | 2026-08-22 | `benchmarks/ds-agent-benchmark` (20/50/8) + `benchmarks/v2` (30/100/11, seed 42) |
| **Demo** | `PASS` (4 tool_calls, 4 evidence, report) | `v4.1.1` | `b79610d` | `dsa demo` → `COMPLETED` | 2026-08-22 | `dsa_evaluation/cli.py` `demo` |
| **External validation** | `5` (historical, not re-run) | `v4.1.0` | `e27ae7f` | `docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md` → `Fresh Clone 7/7` | 2026-08-21 | Fresh `/tmp` clone, `uv sync` → `dsa demo` 7 tasks |

---

## 4. Distribution & Metadata

| Metric | Value | Version | Commit | Source | Date | Methodology |
|--------|-------|---------|--------|--------|------|-------------|
| **pyproject version** | `4.1.1` | `v4.1.1` | `b79610d` | `pyproject.toml:3` | 2026-08-22 | `hatchling` |
| **__version__** | `4.1.1` | `v4.1.1` | `b79610d` | `src/data_science_agent/__init__.py:1` | 2026-08-22 | `import data_science_agent` |
| **Agent._version** | `4.1.1` | `v4.1.1` | `b79610d` | `src/data_science_agent/sdk.py:286` | 2026-08-22 | `Agent().version` |
| **CITATION** | `4.1.1` `2026-08-22` `Jackxiaozhiren` | `v4.1.1` | `b79610d` | `CITATION.cff:9,10,12` | 2026-08-22 | `cff-version 1.2.0` |
| **CHANGELOG** | `4.1.1` + `4.1.0` | `v4.1.1` | `b79610d` | `CHANGELOG.md` | 2026-08-22 | Added/Changed/Fixed/Security/Compatibility |
| **Git tag** | `v4.1.1` → `b79610d` (HEAD==tag) | `v4.1.1` | `b79610d` | `git rev-parse HEAD` == `git rev-parse v4.1.1^{commit}` | 2026-08-22 | `git describe --tags --always` → `v4.1.1` |
| **PyPI name** | `jack-data-science-agent` | `v4.1.1` | `b79610d` | `pyproject.toml:2` + `dist/jack_data_science_agent-4.1.1*.whl` METADATA | 2026-08-22 | `uv build` |
| **PyPI version** | `4.1.1` (local), `4.1.0` (remote until publish) | `v4.1.1` | `b79610d` | `dist/METADATA` vs `https://pypi.org/pypi/jack-data-science-agent/4.1.0/json` | 2026-08-22 | `Name: jack-data-science-agent`, `Requires-Python >=3.12` |
| **Wheel** | `jack_data_science_agent-4.1.1-py3-none-any.whl` `13K` + `.tar.gz` `7.9M` | `v4.1.1` | `b79610d` | `dist/` + `uv pip list` → `jack-data-science-agent 4.1.1` | 2026-08-22 | `hatchling` `packages = ["src/data_science_agent"]` |
| **Extras** | `jupyter` (`dsa-jupyter`), `time-series` (`statsmodels`), `dev-jupyter` | `v4.1.1` | `b79610d` | `pyproject.toml:60-63` | 2026-08-22 | `pip install "jack-data-science-agent[jupyter]"` |

---

## 5. Stale Claim Classification (W2 §18 — Not Blind Replace)

| Old Claim | Location | Classification | Action | Current |
|-----------|----------|----------------|--------|---------|
| `86+ tests` | `README.md:33` (V1) / `docs/README.md:25` | **Valid Historical** | Annotated `V1: ~86+ (2026-08-01)` + `V4.1: 257` | `README.md:33` → `257 passed (V4.1 live 2026-08-22 @ e8794c1; V3.0: 155; V1: ~86+)` |
| `81 source files` | `docs/v2/Baseline Report.md` | **Valid Historical** (V2) | Kept as `V2: 81 (2026-08-15)` | Retained |
| `81 source files clean` | `README.md:35` pre-fix | **Code Error** | Replaced with `102 / 104` versioned | Fixed |
| `155 tests` | `CHANGELOG.md: v3.0.0` | **Valid Historical** (V3.0) | Kept as `V3.0: 155 (2026-08-17)` | Retained |
| `155 tests` | `README.md:165` pre-fix | **Code Error** | Replaced with `257 (V4.1; V3.0: 155)` | Fixed |
| `92 source files` | `README.md:167` pre-fix | **Code Error** | Replaced with `104` | Fixed |
| `81% (4597)` | `README.md:166` pre-fix | **Code Error** | Replaced with `79% 5140 (V4.1; V3.0: 81% 4597)` | Fixed |
| `data-science-agent` pip | `CHANGELOG`, `docs/v4_1/jupyter.md` | **Code Error** | Replaced with `jack-data-science-agent` | Fixed |
| `data-science-agent` in `POPULAR_PYPI` | `manifest.py:35` | **Valid Historical** (typosquat detection) | Kept + added `jack-` | Retained + `jack-` |

Full audit in `docs/v4_2/V4_1_RELEASE_INTEGRITY_REPORT.md` §17.

---

## 6. Methodology Notes

- **pytest:** `uv sync --dev` → `uv run pytest -q` (all) → `uv run pytest --cov` (79%). Flaky `fastapi.testclient` deprecation warning ignored.
- **mypy:** `uv run mypy packages apps/api src --ignore-missing-imports` (104) vs `packages apps/api` (102) — difference is `src/data_science_agent` counted when `src` included. CI uses `packages apps/api src`.
- **ruff:** `uv run ruff check packages apps/api tests src apps/jupyter` + `ruff format --check`
- **npm:** `npm --prefix apps/web run build` → Next.js 15, 13 routes (`/`, `/datasets`, `/analysis`, etc.)
- **docker:** `docker compose config` → validates `healthcheck` `interval:15s` `timeout:5s`
- **benchmark:** `dsa --limit 3` (smoke) vs full `dsa --limit 50` (50/50) and `dsa --catalog benchmarks/v2/... --limit 100` (100/100) — smoke used for CI speed, full verified in `dsa verify-release`? No, verify uses `--limit 5`.
- **security:** `uv run pytest tests/security -q` → `gitleaks` + `codeql.yml` + `dependabot.yml`
- **SBOM:** `uv run python scripts/generate_sbom.py` → counts `workspace_pkgs` (14) + `uv.lock` (192 total after dedup) — `jack-data-science-agent` local + pypi deduped by `name+version`.

---

*Generated: 2026-08-22 live — `b79610d` — `docs/v4_2/V4_1_RELEASE_INTEGRITY_REPORT.md` companion.*

---

## 7. Installation Audit (W2 §21-22 — Clean Environment)

**Date:** 2026-08-22  
**Env:** `/tmp/dsa-v42-audit` (uv venv, Python 3.12.13, clean, no cache)  
**Spec:** `python -m venv /tmp/dsa-v42-audit && source .../bin/activate && pip install --upgrade pip && pip install jack-data-science-agent`

| Test | Command | Result | Notes |
|------|---------|--------|-------|
| **pip install (PyPI 4.1.0)** | `uv pip install --python /tmp/dsa-v42-audit/bin/python "jack-data-science-agent==4.1.0"` | **FAIL** — `dsa-agent was not found` | Workspace deps (`dsa-agent`, `dsa-tools`, etc.) not published to PyPI — `pyproject.toml:23-37` lists 14 workspace `dsa-*` as `Requires-Dist`, but only `jack-data-science-agent` is on PyPI. `uv pip` cannot resolve. |
| **pip install (local wheel 4.1.1)** | `uv pip install --python ... dist/jack_data_science_agent-4.1.1-py3-none-any.whl` | **FAIL** (same, `dsa-agent not found`) | Same reason — wheel's `Requires-Dist` includes unpublished `dsa-*`. |
| **pip install --no-deps (local wheel)** | `uv pip install --no-deps dist/...whl` | **PASS** (wheel installs, but deps missing) | Proves wheel itself is valid, but full install requires `uv sync` or publishing workspace packages. |
| **uv sync (dev, workspace)** | `uv sync --dev` (in repo) | **PASS** | Correct installation method per `README.md:32` and `docs/getting-started.md` — installs 192 packages via `uv.lock`. |
| **import (dev venv)** | `python -c "import data_science_agent; print(__version__)"` | **PASS** → `4.1.1` | `.venv` (editable) |
| **dsa --help (dev)** | `dsa --help` | **PASS** | 11 subcommands |
| **dsa doctor (dev)** | `dsa doctor --json` → `warn` (LLM no key) | **PASS** | |
| **dsa demo (dev)** | `dsa demo` → `COMPLETED` (4 evidence) | **PASS** | |
| **Extras: jupyter** | `pyproject.toml:61` `jupyter = ["dsa-jupyter", ...]` | **Metadata PASS**, install FAIL (same workspace `dsa-jupyter` not on PyPI) | `pip install "jack-data-science-agent[jupyter]"` would also fail for `dsa-jupyter`. Use `uv sync --dev` + `dsa_jupyter` workspace. |
| **Extras: time-series** | `time-series = ["statsmodels>=0.14"]` | **PASS** (external dep `statsmodels` is on PyPI, but `pip install "jack-data-science-agent[time-series]"` still fails for base `dsa-*`) | Same base issue, but `statsmodels` itself is available. |

**Conclusion (§21-22):**

- **PyPI distribution is not `pip`-installable in clean env** via `pip install jack-data-science-agent` due to unpublished workspace dependencies. This violates `W2 §21` expectation that `pip install` should work.
- **Recommended fixes (choose one, requires ADR per §10 if architectural):**
  1. **Publish workspace packages** (`dsa-agent`, `dsa-tools`, etc. `0.1.0`) to PyPI (under same `jack-` prefix or `dsa-` org) — smallest change, keeps `pyproject` as is, enables `pip install`.
  2. **Bundle workspace code** into `jack-data-science-agent` wheel (remove `dsa-*` from `dependencies`, include `packages/*/src` via `hatch` `packages` config, keep `tool.uv.workspace` for dev but not for `Requires-Dist`) — makes `jack` self-contained, but loses modular `pip install dsa-agent`.
  3. **Document `uv sync` as only supported install** and update `pyproject.toml` `description` + `README.md` + `PyPI` to state `pip install` not supported, `uv sync` required — honest but reduces PyPI usability.

- **Current workaround (honest):** `README.md:32` and `docs/getting-started.md` correctly say `uv sync --dev` (not `pip install`), and `PyPI` page should add note: `For development, use uv sync; pip install requires published dsa-* (planned)`. Until fix, `W2 §21` is **partial PASS** (via `uv sync`, not `pip`).

**Evidence:**

```bash
# Clean venv 3.12, pip 26.0.1
uv pip install --python /tmp/dsa-v42-audit/bin/python "jack-data-science-agent==4.1.0"
# → dsa-agent was not found in the package registry and jack-data-science-agent==4.1.0 depends on dsa-agent
uv pip install --python /tmp/dsa-v42-audit/bin/python dist/jack_data_science_agent-4.1.1-py3-none-any.whl
# → same
.venv/bin/python -c "import data_science_agent; print(data_science_agent.__version__)"
# → 4.1.1 (dev venv, via uv sync)
```

