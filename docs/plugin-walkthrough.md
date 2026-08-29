# Build a Hello-World Plugin

This walkthrough builds, installs, discovers, executes, and removes a tiny deterministic DSA plugin. It works offline, uses no private data, and has an automated round-trip test in the repository.

The complete example lives at `examples/plugins/hello-metrics/`.

## What you will build

`hello-metrics` exposes one `metrics` tool. Given a list of numbers, it returns:

- the input count;
- the arithmetic mean;
- a deterministic evidence/provenance record containing a SHA-256 fingerprint of the normalized input.

No network, filesystem dataset, model API, or paid service is required.

## 1. Minimal layout

```text
examples/plugins/hello-metrics/
├── manifest.yaml
└── src/
    └── hello_metrics/
        ├── __init__.py
        └── plugin.py
```

The local plugin registry looks for `manifest.yaml` or `plugin.yaml`, validates it, and copies an installed plugin into `plugins/<name>/`.

## 2. Manifest

The example manifest is:

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
description: "Deterministic hello-world metrics plugin with explicit evidence provenance"
```

Important rules enforced by the current manifest validator:

- names use lowercase kebab-style characters;
- versions use semantic versioning;
- `entrypoint.python` is `module:attribute`;
- permissions are deny-by-default and must come from the allowlist;
- a license is required and must be allowed;
- DSA version compatibility is checked;
- suspicious entrypoints, dependency-confusion names, and likely typosquats are rejected.

The registry's `metrics` execution path requires both `dataset.read` and `process`, so the example declares those permissions even though this minimal tool receives values directly rather than opening a dataset file.

## 3. Typed tool implementation

The plugin uses Pydantic models for its public input and output contract:

```python
class MetricsInput(BaseModel):
    values: list[float] = Field(min_length=1)


class MetricsOutput(BaseModel):
    count: int
    mean: float
    evidence: EvidenceRecord
```

The entrypoint returns a plugin instance:

```python
def register() -> HelloMetricsPlugin:
    return HelloMetricsPlugin()
```

The plugin exposes `metrics()` as an ordinary typed method. `execute_plugin_tool()` loads the entrypoint in isolation and calls the matching method.

See the full implementation in `examples/plugins/hello-metrics/src/hello_metrics/plugin.py`.

## 4. Evidence and provenance contract

For derived analytical output, return enough information for a reviewer to answer:

1. **What claim was produced?**
2. **What input/source produced it?**
3. **What operation was applied?**
4. **Can the input be fingerprinted or otherwise identified?**
5. **What is the validation state/confidence?**

The example returns a record shaped like:

```json
{
  "id": "ev-...",
  "claim": "Arithmetic mean of 4 supplied values is 2.5.",
  "source_type": "arguments",
  "source_id": "sha256:...",
  "result": {
    "operation": "arithmetic_mean",
    "input_count": 4,
    "input_sha256": "...",
    "mean": 2.5
  },
  "confidence": 1.0,
  "validation_status": "validated"
}
```

This evidence object is explicit plugin output. The plugin registry does **not** automatically promote arbitrary plugin-returned dictionaries into the core Agent evidence graph. If you integrate a plugin into agent orchestration, add the adapter that maps plugin provenance into DSA's normal evidence objects rather than assuming the registry performs that step.

## 5. Validate before installing

From the repository root:

```bash
uv sync --dev
uv run dsa plugin validate examples/plugins/hello-metrics/manifest.yaml --json
```

Expected result:

```json
{"status":"ok"}
```

Validation does not install or execute the plugin.

## 6. Install and discover

Install the example into the local registry:

```bash
uv run dsa plugin install examples/plugins/hello-metrics --json
```

Then verify discovery and status:

```bash
uv run dsa plugin list --json
uv run dsa plugin status hello-metrics --json
```

Installation is a local copy into `plugins/hello-metrics/`; it is not a marketplace or PyPI install.

If `plugins/hello-metrics/` already exists, remove that local copy before reinstalling. The registry intentionally refuses to overwrite an existing installed plugin version.

## 7. Execute the tool

The current CLI intentionally does not accept arbitrary plugin-tool arguments. `dsa plugin execute` tells callers to use the SDK, so use the registry API for execution:

```bash
uv run python -c "from dsa_plugins.registry import list_plugins, execute_plugin_tool; m=next(p for p in list_plugins() if p.name=='hello-metrics'); print(execute_plugin_tool(m, 'metrics', values=[1.0, 2.0, 3.0, 4.0]))"
```

The returned wrapper has the isolation contract:

```text
{"ok": true, "result": {...}, "error": null}
```

For the sample input, `result.mean` is `2.5`, `result.count` is `4`, and the evidence source ID starts with `sha256:`.

If loading or execution fails, `execute_plugin_tool()` returns a structured error instead of crashing the caller.

## 8. Run the automated lifecycle test

The repository includes a focused test that performs the whole lifecycle inside a temporary directory:

```bash
uv run pytest -q tests/test_hello_plugin_example.py
```

It verifies:

- manifest validation;
- installation;
- discovery and enabled status;
- tool execution;
- deterministic metric output;
- evidence provenance fields;
- removal and final `not_found` status.

## 9. Disable, enable, and remove

For an installed plugin:

```bash
uv run dsa plugin disable hello-metrics --json
uv run dsa plugin status hello-metrics --json
uv run dsa plugin enable hello-metrics --json
uv run dsa plugin status hello-metrics --json
```

Clean up the tutorial installation:

```bash
uv run dsa plugin remove hello-metrics --json
uv run dsa plugin status hello-metrics --json
```

The final status should be `not_found`.

## 10. Before proposing a real plugin

Keep the first contribution narrow and auditable:

- declare only permissions the tool actually needs;
- avoid network/process permissions unless the capability genuinely requires them;
- use deterministic behavior where possible;
- type and validate inputs before computation;
- return structured outputs rather than human-only strings;
- attach source/provenance to analytical claims;
- add tests for permission denial, invalid input, and failure isolation when relevant;
- document every new dependency and its license/security implications.

Run the focused test plus the repository gates from [Contributing](contributing.md), including MkDocs strict mode.
