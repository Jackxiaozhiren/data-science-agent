# dsa-time-series — Flagship Plugin (V4 §27, W3 Hardening)

Fully executable plugin per V4.1 §27: `forecast + backtest + metrics + visualization + evidence`.

## Manifest (§22)

`manifest.yaml` requires `name/version/dsa/license/permissions/dependencies/entrypoint/capabilities`:

```yaml
name: dsa-time-series
version: 1.0.0
dsa: {min_version: "4.0.0", max_version: "5.0.0"}
license: MIT
permissions: [dataset.read, process, artifact.write, filesystem.read]  # DENY default §23
entrypoint: {python: dsa_time_series.plugin:register}
capabilities: [forecast, backtest, metrics, visualization, evidence]
```

Validation (§24): `dsa plugin validate` checks manifest/version/license/permissions/capabilities/hash/compatibility.

## Permissions (§23)

Default `DENY`. Required: `dataset.read` (load CSV), `process` (compute forecast), `artifact.write` (PNG), `filesystem.read`. `dsa plugin` validates against `ALLOWED_PERMISSIONS`.

## Lifecycle (§21)

```bash
uv run dsa plugin                      # Discover
uv run dsa plugin validate            # Validate
uv run dsa plugin status dsa-time-series
uv run dsa plugin disable dsa-time-series  # Disable (isolated)
uv run dsa plugin enable dsa-time-series   # Enable
# Install (local copy): dsa plugin install /path/to/plugin
# Remove: dsa plugin remove dsa-time-series
```

Failure isolation (§25): `load_plugin_isolated` / `execute_plugin_tool` never crashes Core Agent, Other Plugins, Benchmark, MCP — returns `{"ok": False, "error": ...}`.

## Capabilities (§27)

| Capability | Method | Description |
|------------|--------|-------------|
| `forecast` | `plugin.forecast(dataset_path, date_col, value_col, periods, method)` | Wraps `ForecastTool` (linear_trend/moving_average/naive), returns `{forecast, metrics:{mae}, diagnostics}` |
| `backtest` | `plugin.backtest(dataset_path, folds)` | Rolling window MAE/RMSE/MAPE, aggregate `mae_mean` |
| `metrics` | `plugin.metrics(forecast_result or y_true/y_pred)` | MAE/RMSE/MAPE |
| `visualization` | `plugin.forecast_viz(dataset_path, forecast_result)` | PNG `artifacts/charts/*_forecast.png` + base64, embeddable in Notebook/Report (§30) |
| `evidence` | `plugin.evidence(dataset_path, forecast_result)` | Evidence dict `Insight→Evidence→ToolCall` with claim/confidence |

## Example

```python
from dsa_plugins.registry import list_plugins, load_plugin, execute_plugin_tool

m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
plugin = load_plugin(m)

# SDK
res = plugin.forecast("benchmarks/v2/datasets/sales.csv", periods=7)
print(res["forecast"][:3], res["metrics"]["mae"])

# Backtest
bt = plugin.backtest("benchmarks/v2/datasets/sales.csv", folds=3)
print(bt["aggregate"]["mae_mean"])

# Viz + Evidence (for Report/Notebook)
viz = plugin.forecast_viz("benchmarks/v2/datasets/sales.csv", res)
ev = plugin.evidence("benchmarks/v2/datasets/sales.csv", res)
print(viz["artifact_path"], ev["claim"])

# Via registry isolated execute
out = execute_plugin_tool(m, "forecast", "benchmarks/v2/datasets/sales.csv", periods=5)
assert out["ok"]
```

## Integration (§27)

- **Agent**: `Agent().analyze(...)` produces evidence; plugin evidence is compatible with `Analysis.evidence` schema (mergeable).
- **SDK**: `from dsa_plugins.registry import execute_plugin_tool` (see above).
- **CLI**: `dsa plugin` lifecycle; `dsa analyze` is core, plugin is complementary.
- **Benchmark**: evaluator `forecast_mae` via `plugin.metrics` / `backtest`.
- **Report**: `viz["artifact_path"]` is `artifacts/charts/*.png` embeddable as `![forecast](...)` in `report.md`.

## Tests (§26)

- Unit: `tests/plugins/test_plugin_lifecycle.py` (manifest/permissions/validation/lifecycle)
- Isolation: `tests/plugins/test_plugin_isolation.py` (§25)
- Integration: `tests/plugins/test_time_series_plugin.py` (forecast/backtest/metrics/viz/evidence + §27 full pipeline + security)

```bash
uv run pytest tests/plugins -v
uv run dsa plugin validate
```

## Security (§24, §45)

- Hash: `PluginManifest.compute_hash(root)` (§45)
- No malicious dependency: `dependencies: []` (audited)
- No typosquatting: name is `dsa-time-series` (exact)
- Permissions DENY default, validated pre-install.
