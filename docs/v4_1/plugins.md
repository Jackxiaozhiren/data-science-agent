# Plugins — V4.1 §21-27 (Stable)

**Lifecycle (§21):** `Discover → Validate → Install → Load → Execute → Disable → Remove` via `dsa_plugins.registry` (`discover_plugins`, `validate_plugin`, `install_plugin`, `load_plugin_isolated`, `execute_plugin_tool`, `disable/enable/remove`, `get_plugin_status`) + `.registry_state.json`.

**Manifest (§22):** `name/version/dsa.min/max/license/permissions/dependencies/entrypoint/capabilities` + `hash` — `PluginManifest.validate_manifest()` §24.

**Permissions (§23):** `filesystem.read/write`, `network`, `process`, `dataset.read/write`, `artifact.write` — default `DENY`, allowlist `ALLOWED_PERMISSIONS`.

**Validation (§24):** `manifest/version/dependency/license/hash/permissions/compatibility` + typosquat/dependency confusion/suspicious entrypoint (§45).

**Isolation (§25):** `load_plugin_isolated`/`execute_plugin_tool` returns `{"ok":False,"error":...}` never crashes `Core Agent/Other Plugins/Benchmark/MCP`.

**Evaluation (§26):** Official `dsa-time-series` has `tests/plugins` 24 (lifecycle 9, isolation 6, time_series 9), `README.md`, `example` in `plugins/dsa-time-series/README.md`, `benchmark task` via `forecast_mae`.

**Flagship (§27):** `dsa-time-series 1.0.0` fully executable: `forecast` (ForecastTool), `backtest` (rolling MAE), `metrics`, `forecast_viz` (PNG+base64), `evidence`, `run_full` — integrated to `Agent/SDK/CLI/Benchmark/Report` (`W3_PLUGIN_HARDENING.md`).
