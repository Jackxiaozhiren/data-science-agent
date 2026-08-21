# V4 Release Matrix — V4.1 Phase A (v4.0.0 Freeze)

> Each row: `Capability | Status | Version | Test | Documentation` (§59). Status: `Stable / Experimental / Prototype / Stub` per §58.

| Capability | Status | Version | Test | Documentation |
|------------|--------|---------|------|---------------|
| Core Agent (LangGraph Planner→Scientist→Critic→Report) | **Stable** | 4.0.0 | `pytest 157 passed, demo COMPLETED` | `docs/architecture.md` (7 Mermaid §49) |
| SDK (`from data_science_agent import Agent/Dataset/Benchmark/Repro`) | **Stable** | 4.0.0 | `tests/api/compatibility/test_sdk_compat.py`, `uv run python -c "from data_science_agent import Agent"` | `docs/v4/sdk.md`, `src/data_science_agent/sdk.py` |
| CLI (`dsa --help / doctor / init / analyze / profile / benchmark / demo / verify-release`) | **Stable** | 4.0.0 | `uv run dsa doctor` warn, `uv run dsa profile --json` + `benchmark --limit 1 --json` | `docs/v4/cli.md`, `packages/evaluation/src/dsa_evaluation/cli.py` |
| Plugin Arch (`DataSciencePlugin`, manifest, local discovery) | **Stable** | 4.0.0 | `212 passed; dsa plugin list/validate/disable/enable/remove/install (§21) + isolation §25` | `docs/v4/plugins.md`, `packages/plugins/src/dsa_plugins/*`, `docs/v4_1/W3_PLUGIN_HARDENING.md` |
| Time Series Plugin (`dsa-time-series`) | **Stable** ⬆ | 1.0.0 | `forecast/backtest/metrics/viz/evidence (§27) — tests/plugins 24 passed; dsa plugin validate ok` | `plugins/dsa-time-series/README.md`, `plugins/dsa-time-series/src/dsa_time_series/plugin.py` |
| MCP Tools (17, stateless 2026-07-28) | **Stable** | 4.0.0 | `tests/mcp/conformance` in 157, `uv run dsa mcp` 17 tools | `packages/mcp/src/dsa_mcp/adapter.py`, `docs/v4/mcp.md` |
| MCP Resources (`dataset:// evidence:// report://`) | **Experimental** | 4.0.0 | `adapter.list_resources()` 3 resources (smoke) | `packages/mcp/src/dsa_mcp/adapter.py` |
| MCP App (`/mcp-app` shell) | **Stub** | 4.0.0 | `packages/mcp/src/dsa_mcp/app.py` 2 routes PASS | `packages/mcp/src/dsa_mcp/app.py` — no analysis flow yet |
| Jupyter (`%dsa` + `Agent` notebook) | **Experimental** ⬆ | 4.0.0 / 0.1.0 (dsa-jupyter) | `tests/jupyter 10 passed; %dsa profile/analyze + Agent rich + metadata (§28-32)` | `apps/jupyter/src/dsa_jupyter/*`, `apps/jupyter/README.md`, `docs/v4/jupyter.md` |
| VS Code (`Dataset Explorer / Ask DSA`) | **Experimental** ⬆ | 4.0.0 / 0.1.0 (dsa-vscode) | `tests/vscode 7 passed; 6-step flow + 5 failure handlers (§33-35)` | `apps/vscode/src/*`, `apps/vscode/README.md`, `docs/v4/vscode.md` |
| Benchmark (30 datasets / 100 tasks + leaderboard) | **Stable** | 0.3.0 (catalog) / 4.0.0 (platform) | `uv run dsa benchmark --limit 1` 1.0, `benchmarks/leaderboard/leaderboard.json` | `benchmarks/leaderboard/README.md` |
| Reproduction (L0–L5 + `ReproductionScore`) | **Stable** | 4.0.0 | `packages/evidence/reproducibility.py`, `dsa reproduce` | `docs/reproducibility.md` |
| Security & Supply Chain | **Stable** | 4.0.0 | `23 security tests`, `CODEOWNERS`, `dependabot.yml` | `SECURITY.md`, `.github/` |
| Frontend (13 routes) | **Stable** | 4.0.0 | `npm build 13/13`, `docker compose config valid` | `apps/web`, `apps/api` |
| Research (`V3_RESEARCH_REPORT`, claim-evidence, figures/tables) | **Stable** | 4.0.0 | `scripts/generate_*` pass, `research/V3_RESEARCH_REPORT.md` 13 sections | `research/`, `docs/research.md` |

**Notes**: Reads `AGENTS.md` missing (only `ARCHITECTURE_FREEZE_V0.1.md` freeze file exists — not a regression). All `Stub` rows are correctly labeled as such in V4.0 assessment §3; V4.1 §62 requires README to **not** list them under Stable.

**Next**: Phase B onward must turn `Stub → Experimental → Stable` per V4.1 §71 order (W2 SDK/CLI Distribution → W3 Plugin Runtime → W4 Jupyter → W5 VS Code → W6 MCP App → W7 Security → W8 External Validation).
