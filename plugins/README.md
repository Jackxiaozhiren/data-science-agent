# Plugins — V4 W3/W4 (§21–28)

Local plugin registry (no marketplace yet, §27).

```
plugins/
├── my-plugin/
│   ├── manifest.yaml   # or plugin.yaml (§25)
│   ├── src/
│   └── README.md
└── ...
```

Manifest example (§25):

```yaml
name: dsa-time-series
version: 1.0.0
type: [forecasting]
requires: { dsa: ">=4.0,<5.0" }
license: MIT
entrypoint: { python: dsa_time_series.plugin:register }
permissions: [read, compute]
```

Discovery: `dsa plugin list` scans `plugins/**/manifest.yaml` (§27).
