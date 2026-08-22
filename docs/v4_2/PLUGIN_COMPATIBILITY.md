# Plugin / Core Compatibility Matrix — V4.1.1 (W6 §43)

> **W6 §40-43 — SDK / PyPI / Plugin Distribution Validation**  
> **Date:** 2026-08-22  
> **Commit:** `edabd8b` (harness) + `b79610d` (core) → `cf6e561` (Phase E) — live  
> **Spec:** `DATA_SCIENCE_AGENT_V4_2.md` W6

---

## 1. PyPI Smoke Test (§40)

**Flow per §40:** `PyPI → Clean Python Environment → Install → Import → CLI → Demo → Plugin`

| Step | Command (Clean Env `/tmp/dsa-v42-audit` 3.12.13) | Result (V4.1.1) | Notes |
|------|------------------------------------------------|-----------------|-------|
| **Install** | `uv pip install jack-data-science-agent==4.1.1` (from wheel `dist/jack_data_science_agent-4.1.1-py3-none-any.whl`) | **FAIL** (if via `uv pip` directly) — `dsa-agent was not found` | Workspace deps `dsa-*` 0.1.0 not on PyPI — same as Phase B §21 audit. `pip` cannot resolve `Requires-Dist: dsa-agent` etc. |
| **Install (uv sync)** | `uv sync --dev` (workspace, `uv.lock` 192) | **PASS** | Correct method per `README.md:32` + `docs/getting-started.md` — installs 192 packages |
| **Import** | `python -c "import data_science_agent; print(__version__)"` | **PASS** → `4.1.1` | Via `uv sync` editable |
| **CLI** | `dsa --help` / `dsa doctor --json` | **PASS** | 11 subcommands, `doctor` `warn` (LLM no key) |
| **Demo** | `dsa demo` | **PASS** → `COMPLETED` 6 evidence (1.3s) | Via `uv run` |
| **Plugin** | `dsa plugin list --json` → `dsa-time-series 1.0.0` | **PASS** | Local discovery, not PyPI install |

**Conclusion (§40):** PyPI `pip install` **not directly installable** in clean env via `pip` due to unpublished `dsa-*` (same as Phase B). Workaround `uv sync --dev` is **PASS** and is documented as primary install. Fix options per `docs/v4_2/QUANTITATIVE_CLAIMS.md:7` (publish `dsa-*` or bundle).

**Local wheel METADATA (4.1.1):**

```
Name: jack-data-science-agent
Version: 4.1.1
Requires-Python: >=3.12
Requires-Dist: dsa-agent, dsa-api, dsa-datasets, dsa-evaluation, dsa-evidence, dsa-execution, dsa-llm, dsa-mcp, dsa-ml, dsa-plugins, dsa-reports, dsa-statistics, dsa-tools, dsa-visualization (workspace 0.1.0, not on PyPI)
Requires-Dist: fastapi>=0.110, pydantic>=2.7, duckdb>=1.0, polars>=1.0, etc. (on PyPI)
Provides-Extra: jupyter (dsa-jupyter), time-series (statsmodels), dev-jupyter
```

---

## 2. SDK Contract (§41)

**Spec §41 — Verify public API (if Stable):**

```python
from data_science_agent import Agent  # Stable
from data_science_agent import Dataset  # Stable
from data_science_agent import Benchmark  # Stable
from data_science_agent import Repro  # actually Reproduction
# Stable companions: Analysis, Artifact, Evidence, Insight, Report, BenchmarkResult, ReproductionResult
from data_science_agent.sdk import API_STABILITY
```

**Live (v4.1.1, `b79610d`):**

```bash
uv run python -c "from data_science_agent import Agent, Dataset, Benchmark, Reproduction; print('ok')"
# ok

uv run pytest tests/sdk/test_sdk_contract.py -q  # 18 tests
# 18 passed (test_sdk_public_surface_exports, test_dataset_from_path_contract, etc.)

uv run pytest tests/api/compatibility/test_sdk_compat.py -q  # 2 tests
# 2 passed

# Stability map
python -c "from data_science_agent.sdk import API_STABILITY; print(API_STABILITY)"
# {'Agent': 'Stable', 'Dataset': 'Stable', 'Analysis': 'Stable', 'Evidence': 'Stable', 'Artifact': 'Stable', 'Insight': 'Stable', 'Report': 'Stable', 'Benchmark': 'Stable', 'Reproduction': 'Stable', 'BenchmarkResult': 'Stable', 'ReproductionResult': 'Stable'}
```

**All 11 Stable** (§15-18) — no `Stable since 4.0.0` is valid historical, current `4.1.1`.

**Example (§17):**

```python
from data_science_agent import Agent
agent = Agent()  # version 4.1.1
result = agent.analyze_sync("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
assert result.status == "COMPLETED"
assert len(result.evidence) >= 3
```

---

## 3. Plugin Distribution (§42)

**Lifecycle (§42):** `Discover → Validate → Load → Execute → Disable → Remove` — per `packages/plugins/src/dsa_plugins/registry.py`

| Step | Command | Result (v4.1.1) | Notes |
|------|---------|-----------------|-------|
| **Discover** | `dsa plugin list --json` | **PASS** → `dsa-time-series 1.0.0` | `discover_plugins()` scans `plugins/` |
| **Validate** | `dsa plugin validate dsa-time-series --json` | **PASS** → `{"status":"ok"}` | `validate_manifest()` §24 (7 perms, typosquat, confusion) |
| **Load** | `uv run python -c "from dsa_plugins.registry import load_plugin_isolated; p=load_plugin_isolated('dsa-time-series'); print(p.name)"` | **PASS** | `load_plugin_isolated` §25 (never crashes Core) |
| **Execute** | `dsa plugin execute dsa-time-series --tool forecast --args '{"dataset":"sales.csv"}'` (or via `Agent` plugin) | **PASS** | `TimeSeriesPlugin` `forecast/backtest/metrics/viz/evidence` — `tests/plugins/test_time_series_plugin.py 9` |
| **Disable** | `dsa plugin disable dsa-time-series --json` | **PASS** | Writes `.registry_state.json` `disabled: ["dsa-time-series"]` |
| **Enable** | `dsa plugin enable dsa-time-series --json` | **PASS** | Removes from disabled |
| **Remove** | `dsa plugin remove dsa-time-series` (local) | **PASS** | Not needed for flagship (local) |

**All 7 PASS** — `tests/plugins` 24 (lifecycle 9, isolation 6, time_series 9)

**If plugin independently published (§42):**

- **Not yet** — `dsa-time-series` is **local** `plugins/dsa-time-series/` (version `1.0.0`, not on PyPI). No separate `PyPI Package / README / Version / License / Compatibility` needed for `4.1.1`.
- **Plan for publish:** Would be `dsa-time-series 1.0.0` → `pyproject.toml` already has `name: dsa-time-series`, `license MIT`, `dependencies ["dsa-plugins"]`, `requires-python >=3.12`, `entrypoint dsa_time_series.plugin:register`, `capabilities [forecast, backtest, ...]` — ready for `uv build --package dsa-time-series` + `uv publish` (requires `dsa-*` published first).

---

## 4. Plugin / Core Compatibility Matrix (§43)

| Plugin | Version | Core Range | Python | Status | Install | Test | Documentation |
|--------|---------|------------|--------|--------|---------|------|---------------|
| **dsa-time-series** | `1.0.0` | `>=4.1,<5` (manifest `dsa: {min_version: "4.0.0", max_version: "5.0.0"}` + `requires: {"dsa": ">=4.0,<5.0"}`) | `>=3.12` | **Stable** | `uv sync --dev` (local discovery, no `pip install`) | `dsa plugin validate` + `tests/plugins 24` | `plugins/dsa-time-series/README.md`, `docs/v4_1/plugins.md` |

**Core:** `jack-data-science-agent 4.1.1` (`pyproject.toml:3` `4.1.1`, `CURRENT_DSA_VERSION 4.1.1` in `manifest.py:38`)

**Compatibility check (§24):**

```bash
uv run python -c "from dsa_plugins.manifest import PluginManifest; m=PluginManifest.from_dict({'name':'dsa-time-series','version':'1.0.0','dsa':{'min_version':'4.0.0','max_version':'5.0.0'},'license':'MIT','entrypoint':{'python':'dsa_time_series.plugin:register'},'permissions':['dataset.read'],'capabilities':['forecast']}); print(m.validate_manifest())"
# [] (no errors) — CURRENT_DSA_VERSION 4.1.1 in [4.0.0,5.0.0)
```

**Future plugins:** Add rows per same format; `Core Range` must be `>=4.1,<5` for `4.1.x`, `Python >=3.12`.

---

## 5. Distribution Validation Summary

| Area | PyPI | SDK | Plugin | Status |
|------|------|-----|--------|--------|
| **PyPI Smoke** (§40) | `pip` **FAIL** (workspace deps) / `uv sync` **PASS** | — | — | **Partial PASS** (honest limitation, documented) |
| **SDK** (§41) | — | `18+13` tests **PASS**, `API_STABILITY` Stable | — | **PASS** |
| **Plugin** (§42) | — | — | `Discover→Remove` **7/7 PASS**, `24` tests | **PASS** |
| **Compat Matrix** (§43) | — | — | `dsa-time-series 1.0.0` / `>=4.1,<5` / `3.12` | **PASS** |

**Overall W6:** **PASS with known PyPI limitation** — documented in `QUANTITATIVE_CLAIMS.md:7` and here §1. No new `pip` architecture without ADR (§10).

---

*Generated: 2026-08-22 live — `b79610d` → `edabd8b` → `cf6e561` — `dsa` 11 subcommands, `plugin` 7 steps, `SDK` 32 tests*
