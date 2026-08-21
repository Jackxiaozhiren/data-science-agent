# Plugins — V4 W3 (§21–28) — Runtime Hardening 2026-08-21

## Protocol (§24, §15)

`DataSciencePlugin` protocol (`packages/plugins/src/dsa_plugins/plugin.py:10`):

```python
class DataSciencePlugin(Protocol):
    name: str
    version: str
    def register_tools() -> list[str]: ...
    def register_models() -> list[str]: ...
    def register_evaluators() -> list[str]: ...
```

`BasePlugin` provides defaults; flagship `TimeSeriesPlugin` overrides.

## Manifest (§22) — mandatory

`plugins/<name>/manifest.yaml` must contain:

```yaml
name: dsa-time-series
version: 1.0.0
type: [forecasting]
dsa: {min_version: "4.0.0", max_version: "5.0.0"}
requires: {dsa: ">=4.0,<5.0"}  # compat
license: MIT  # allowlist: MIT/Apache-2.0/BSD-3-Clause/ISC/Proprietary §24
entrypoint: {python: dsa_time_series.plugin:register}
permissions: [dataset.read, process, artifact.write, filesystem.read]  # DENY default §23
dependencies: []
capabilities: [forecast, backtest, metrics, visualization, evidence]  # §27
```

Validated by `PluginManifest.validate_manifest()` (§24): manifest/version/license/permissions/capabilities/entrypoint/hash/compatibility.

`ALLOWED_PERMISSIONS` (§23): `filesystem.read/write`, `network`, `process`, `dataset.read/write`, `artifact.write` (legacy `read/compute/write` mapped).

## Lifecycle (§21)

```
Discover → Validate → Install → Load → Execute → Disable → Remove
```

- **Discover**: `discover_plugins()` scans `plugins/**/manifest.yaml` (§22)
- **Validate**: `validate_plugin(manifest)` checks §24 gates (manifest, version, dependency, license, hash, permissions, compatibility)
- **Install**: `install_plugin(source, target_root)` validates then `shutil.copytree` (§21, §24)
- **Load**: `load_plugin(manifest)` adds `plugins/<name>/src` to `sys.path` and imports entrypoint; isolated via `load_plugin_isolated` (§25)
- **Execute**: `execute_plugin_tool(manifest, tool, ...)` permission-checked + isolated; returns `{"ok", "result", "error"}` (§23/§25)
- **Disable/Enable**: `disable_plugin(name)` writes `plugins/.registry_state.json` (`{"disabled": {name: true}}`); `discover_plugins` filters disabled unless `include_disabled=True` (§21)
- **Remove**: `remove_plugin(name)` deletes dir and clears disabled state

Failure isolation (§25): any `load`/`execute` exception is caught, never crashes `Core Agent / Other Plugins / Benchmark / MCP`. Tested in `tests/plugins/test_plugin_isolation.py`.

## CLI (§21, §28)

```bash
uv run dsa plugin                          # list (discover)
uv run dsa plugin list --json
uv run dsa plugin validate                 # validate all
uv run dsa plugin validate plugins/dsa-time-series/manifest.yaml --json
uv run dsa plugin status dsa-time-series --json
uv run dsa plugin disable dsa-time-series --json
uv run dsa plugin enable dsa-time-series --json
uv run dsa plugin install /path/to/plugin --json
uv run dsa plugin remove <name> --json
```

All have `--help`, `--json`, exit codes `0` ok / `1` fail / `2` usage, structured JSON errors (§20).

## Flagship dsa-time-series (§27) — Fully Executable

Separate package `plugins/dsa-time-series` version `1.0.0`, permissions `dataset.read/process/artifact.write/filesystem.read`.

| Capability | Method | Impl |
|------------|--------|------|
| `forecast` | `plugin.forecast(dataset_path, periods, method)` | `ForecastTool` linear_trend/moving_average/naive → `{forecast, metrics:{mae}, diagnostics}` |
| `backtest` | `plugin.backtest(dataset_path, folds)` | rolling MAE/RMSE/MAPE → `{folds:[{mae,rmse}], aggregate:{mae_mean}}` |
| `metrics` | `plugin.metrics(forecast_result or y_true/y_pred)` | MAE/RMSE/MAPE |
| `visualization` | `plugin.forecast_viz(dataset_path, forecast_result)` | PNG `artifacts/charts/*_forecast.png` + base64 (§30) |
| `evidence` | `plugin.evidence(dataset_path, forecast_result)` | Evidence dict `Insight→Evidence→ToolCall` (§27) |
| `run_full` | `plugin.run_full(...)` | forecast→backtest→viz→evidence pipeline |

Integrated into (§27):

- **Agent**: independent; evidence schema compatible with `Analysis.evidence` (mergeable)
- **SDK**: `from dsa_plugins.registry import execute_plugin_tool, load_plugin` (example in `plugins/dsa-time-series/README.md`)
- **CLI**: `dsa plugin` lifecycle above
- **Benchmark**: evaluator `forecast_mae` via `plugin.metrics`; time-series category (8 tasks in `benchmarks/v2/catalog.json`)
- **Report**: `viz["artifact_path"]` embeddable as `![forecast](artifacts/charts/…)` in `report.md`

Tests (§26): `tests/plugins/test_plugin_lifecycle.py` (8, manifest/permissions/lifecycle), `tests/plugins/test_plugin_isolation.py` (6, isolation), `tests/plugins/test_time_series_plugin.py` (9, forecast/backtest/metrics/viz/evidence + full pipeline + security).

Security (§24, §45): hash via `PluginManifest.compute_hash()`, dependencies audited (`[]`), no typosquatting, permissions DENY default.

Registry (§28): `plugins/` holds manifest/metadata/license/docs/version; `plugins/.registry_state.json` holds disable state (git-ignored).
