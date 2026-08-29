# Plugins

DSA currently uses a local plugin registry; there is no remote marketplace install path.

Installed plugins live under:

```text
plugins/
├── <plugin-name>/
│   ├── manifest.yaml   # plugin.yaml is also discovered
│   └── src/
└── ...
```

A manifest declares compatibility, entrypoint, permissions, dependencies, and capabilities. Permissions are deny-by-default and validated before installation.

Example:

```yaml
name: hello-metrics
version: 0.1.0
type: [metrics]
dsa:
  min_version: "4.0.0"
  max_version: "5.0.0"
license: MIT
entrypoint: { python: hello_metrics.plugin:register }
permissions: [dataset.read, process]
dependencies: []
capabilities: [metrics, evidence]
```

Lifecycle commands:

```bash
uv run dsa plugin validate <manifest.yaml> --json
uv run dsa plugin install <source-directory> --json
uv run dsa plugin list --json
uv run dsa plugin status <name> --json
uv run dsa plugin disable <name> --json
uv run dsa plugin enable <name> --json
uv run dsa plugin remove <name> --json
```

Tool execution currently uses the Python SDK (`dsa_plugins.registry.execute_plugin_tool`) rather than accepting arbitrary tool arguments through the CLI.

For a complete offline example with typed inputs/outputs, evidence provenance, exact lifecycle commands, and an automated round-trip test, see [`docs/plugin-walkthrough.md`](../docs/plugin-walkthrough.md).
