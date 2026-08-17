# Plugins — V4 W3 (§21–28)

`DataSciencePlugin` protocol (§24): `register_tools() / register_models() / register_evaluators()`.

Manifest (§25): `plugins/<name>/manifest.yaml` with `name/version/type/requires/license/entrypoint/permissions`.

Discovery (§27): `dsa plugin list` scans `plugins/**/manifest.yaml`.

Registry (§28): `plugins/` holds manifest/metadata/license/docs/version. Flagship (§81): `plugins/dsa-time-series` (forecasting/backtesting/viz, separate package).
