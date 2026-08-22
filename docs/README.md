# Documentation Index

- [Getting Started](./getting-started.md) — install, smoke, docker, benchmark, health
- [Architecture Freeze](../ARCHITECTURE_FREEZE_V0.1.md) — system diagram, ERD, tool contracts, security boundary, TDR (Phase 0)
- [Agent](./agent.md) — Planner / Data Scientist / Critic / Reporter, graph, evidence contract
- [Tools](./tools.md) — 17-tool registry (Typed I/O)
- [Statistics](./statistics.md) — correlation / tests / regression / guardrails
- [Evidence](./evidence.md) — `Insight→Evidence→ToolCall→Dataset(hash)`, 4 checks, reproducibility bundle
- [MCP Design](./MCP_DESIGN.md) — Stateless 2026-07-28 adapter over Tool Layer
- [API](./api.md) — `/api/v1` endpoints incl. `/health /ready /version`
- [Frontend IA](./FRONTEND_IA.md) — routes & data flow (Phase 7)
- [Benchmark README](../benchmarks/ds-agent-benchmark/README.md) — 20 datasets / 50 tasks / metrics + `dsa benchmark` CLI
- [Security](./security.md) — file / SQL / Python / prompt / output guardrails
- [Research](./research.md) — benchmark + report stub
- [Examples](../examples/README.md) — `sales.csv / titanic.csv` + curl examples
- [README](../README.md) — Project overview & quick start
- [Changelog](../CHANGELOG.md) — `0.1.0 → 1.2.0`
- [Third-Party Licenses](../THIRD_PARTY_LICENSES.md) — runtime / frontend / datasets

To serve: `uv sync --dev && uv run mkdocs serve` (or `uv run mkdocs build --strict` for CI gate).

## Quick Quality

```
uv run pytest -q         # 257 passed (V4.1 live 2026-08-22; V1: 86+; V3.0: 155)
uv run mypy packages apps/api --ignore-missing-imports
uv run ruff check .
uv run dsa --limit 50
```
