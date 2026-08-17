# Contributor Guide — V4 W7 (§46/47)

See `CONTRIBUTING.md` for quick checklist. This doc details V4 ecosystem contributions.

## Architecture (§9)
Core Engine (agent/tools/statistics/ml/evidence/evaluation/mcp) is frozen. Extend via SDK + Plugins + MCP Apps, not core rewrites.

## Setup
`uv sync --dev` · `uv run dsa doctor` · `uv run dsa demo`

## Testing
`uv run ruff check packages apps/api tests` · `uv run mypy packages apps/api --ignore-missing-imports` · `uv run pytest -q`

## Plugin Development (§24–28)
Create `plugins/my-plugin/manifest.yaml` (§25) with `DataSciencePlugin.register_tools()`. Test with `dsa plugin list`.

## Benchmark Development
Add tasks in `benchmarks/v2` via `scripts/generate_benchmark_v2.py` (seed 42, `source/license/citation`).

## PR Process
Open PR with `fix:`/`feat:` prefix. CI must pass. Ask for review via CODEOWNERS.
