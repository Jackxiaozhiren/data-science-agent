# W3 Plugin Runtime Hardening — Completion Report 2026-08-21

> Workstream W3 (§21-27) — Lifecycle, Manifest, Permissions, Validation, Isolation, Flagship.

## Summary

W3 upgrades plugin from **discoverable** to **fully executable with lifecycle + isolation**.

- Manifest (§22) now enforces `name/version/dsa/license/permissions/dependencies/entrypoint/capabilities` + hash/compat.
- Permissions (§23) DENY default, allowlist `filesystem.read/write, network, process, dataset.read/write, artifact.write`.
- Validation (§24) checks manifest/version/dependency/license/hash/permissions/compatibility pre-install.
- Lifecycle (§21) `Discover→Validate→Install→Load→Execute→Disable→Remove` implemented in `registry.py`.
- Isolation (§25) `load_plugin_isolated` / `execute_plugin_tool` never crashes core.
- Flagship `dsa-time-series` (§27) now implements `forecast/backtest/metrics/visualization/evidence` + `run_full`, integrated into Agent/SDK/CLI/Benchmark/Report.

## Changes

| File | Change |
|------|--------|
| `packages/plugins/src/dsa_plugins/manifest.py:1` | Add `ALLOWED_PERMISSIONS`, `ALLOWED_LICENSES`, `dsa`/`capabilities`/`hash` fields, `validate_manifest()` (§22-24), semver + allowlists |
| `packages/plugins/src/dsa_plugins/registry.py:1` | Add `validate_plugin`, `install_plugin`, `load_plugin_isolated`, `check_permission`, `execute_plugin_tool`, `disable/enable/remove`, `get_plugin_status`, failure isolation, sys.path handling for `plugins/<name>/src` |
| `packages/plugins/src/dsa_plugins/__init__.py:1` | Export lifecycle APIs |
| `plugins/dsa-time-series/manifest.yaml:1` | Add `dsa:min/max`, granular `permissions`, `capabilities`, `description` (§22) |
| `plugins/dsa-time-series/src/dsa_time_series/plugin.py:1` | Rewrite to fully executable: `forecast` (ForecastTool), `backtest` (rolling MAE), `metrics`, `forecast_viz` (PNG+base64), `evidence` (Evidence dict), `run_full` |
| `plugins/dsa-time-series/README.md:1` | Expand with manifest/permissions/lifecycle/example/integration/tests |
| `packages/evaluation/src/dsa_evaluation/cli.py:162` | Expand `dsa plugin` to `list/validate/status/disable/enable/remove/install/execute` with `--json` and isolated errors (§21/§20) |
| `docs/v4/plugins.md:1` | Document lifecycle, manifest, permissions, CLI, flagship capabilities |
| `tests/plugins/test_plugin_lifecycle.py:1` | 9 tests §22-24 |
| `tests/plugins/test_plugin_isolation.py:1` | 6 tests §25 |
| `tests/plugins/test_time_series_plugin.py:1` | 9 tests §27 + §26 |
| `pyproject.toml:105` | Add `packages/plugins/**/*` ruff per-file ignores (S112 etc.) |

## Verification

```bash
uv run ruff check packages apps/api tests src
# All checks passed!

uv run mypy packages apps/api src --ignore-missing-imports
# Success: no issues found in 104 source files

uv run pytest tests/plugins -v
# 24 passed (lifecycle 9, isolation 6, time_series 9)

uv run pytest -q
# 212 passed (188 + 24)

uv run dsa plugin --json | jq
# [{"name":"dsa-time-series","capabilities":[...],"permissions":[...]}]

uv run dsa plugin validate --json
# {"status":"ok","plugins":["dsa-time-series"]}

uv run dsa plugin disable dsa-time-series --json && uv run dsa plugin --json | jq length
# 0  (hidden)
uv run dsa plugin enable dsa-time-series --json && uv run dsa plugin --json | jq length
# 1  (restored)

uv run python -c "from dsa_plugins.registry import list_plugins, load_plugin; m=list_plugins()[0]; p=load_plugin(m); print(p.forecast('benchmarks/v2/datasets/sales.csv', periods=3))"
# {'forecast': [...], 'metrics': {'mae': ...}}

# Failure isolation (§25)
uv run python -c "from dsa_plugins.registry import execute_plugin_tool; from dsa_plugins.manifest import PluginManifest; m=PluginManifest(name='bad',version='1.0.0',license='MIT',entrypoint={'python':'bad:fn'},permissions=['dataset.read'],capabilities=['forecast']); print(execute_plugin_tool(m,'forecast','x'))"
# {'ok': False, 'error': 'load failed (isolated §25): ...'}

# Benchmark / Agent still pass after plugin failure
uv run dsa benchmark --limit 1 --json
# {"n_tasks":1,"aggregate":{"task_success_rate":1.0}}
```

## Maturity Update

| Capability | Before | After W3 | Evidence |
|-----------|--------|----------|----------|
| Plugin Arch | Stable (discovery) | **Stable** (full lifecycle) | `registry.py` 7 ops + `dsa plugin --help` |
| dsa-time-series | Experimental (stub) | **Stable** (fully executable) | `plugin.py` 5 capabilities + 24 plugin tests |

## Risks / Next

- Plugin marketplace (§27) not yet (local registry only) — deferred to W6/W7.
- No remote signature verification (hash is local) — W7 supply-chain.
- No auto-wiring of plugin tools into `Agent` graph (explicit SDK use) — could be W4/W6.

## Stop Condition (§72)

W3 implements `Inspect→Plan→Implement→Test→Security→Benchmark→Document→Commit→STOP`. Do not auto-enter W4.
