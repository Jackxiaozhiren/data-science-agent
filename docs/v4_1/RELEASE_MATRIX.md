# V4.1 Release Matrix — V4.1 (§59, §58 Maturity Gate)

> Each row: `Capability | Status | Version | Test | Documentation` (§59). Status: `Stable / Experimental / Prototype / Stub` per §58 — no Stub in Stable.

| Capability | Status | Version | Test | Documentation |
|------------|--------|---------|------|---------------|
| Core Agent (LangGraph Planner→Scientist→Critic→Report) | **Stable** | 4.1.0 | `pytest 257 passed, demo COMPLETED` | `docs/architecture.md` (7 Mermaid) |
| SDK (`from data_science_agent import Agent/Dataset/Benchmark/Repro`) | **Stable** | 4.1.0 | `tests/sdk 18 + tests/api/compatibility 2 — API_STABILITY Stable` | `docs/v4_1/sdk.md`, `src/data_science_agent/sdk.py` (658 lines) |
| CLI (`dsa --help / doctor / init / analyze / profile / benchmark / demo / verify-release`) | **Stable** | 4.1.0 | `tests/sdk/test_cli_contract 13 — all --help/--json/exit 0/1/2` | `docs/v4/cli.md`, `packages/evaluation/src/dsa_evaluation/cli.py` |
| Plugin Arch (`DataSciencePlugin`, manifest, local discovery) | **Stable** | 4.1.0 | `212→257: dsa plugin list/validate/disable/enable/remove/install + isolation` | `docs/v4_1/plugins.md`, `packages/plugins/src/dsa_plugins/*` |
| Time Series Plugin (`dsa-time-series`) | **Stable** | 1.0.0 (dsa 4.1.0) | `forecast/backtest/metrics/viz/evidence — tests/plugins 24, validate ok` | `plugins/dsa-time-series/README.md`, `plugins/dsa-time-series/src/dsa_time_series/plugin.py` |
| MCP Tools (18, stateless 2026-07-28) | **Stable** | 4.1.0 | `tests/mcp/conformance 7 + test_mcp_app_acceptance 6 — 18 inc. analyze` | `packages/mcp/src/dsa_mcp/adapter.py`, `docs/v4_1/mcp.md`, `MCP_COMPATIBILITY.md` |
| MCP Resources (`dataset:// evidence:// report:// artifact:// analysis://`) | **Stable** | 4.1.0 | `dataset:// 50 + evidence/report/analysis/artifact — resources/list + read 5 schemes` | `packages/mcp/src/dsa_mcp/adapter.py` |
| MCP App (`/mcp-app` Dataset→Question→Analysis→Evidence→Viz→Report) | **Experimental** | 4.1.0 / 0.1.0 | `GET /mcp-app/ HTML + acceptance 6 — Client→Discover→Call→Open Resource→Render App` | `packages/mcp/src/dsa_mcp/app.py`, `tests/mcp/test_mcp_app_acceptance.py` |
| Jupyter (`%dsa` + `Agent` notebook) | **Experimental** | 4.1.0 / 0.1.0 (dsa-jupyter) | `tests/jupyter 10 — %dsa + Agent rich + metadata 6` | `apps/jupyter/src/dsa_jupyter/*`, `docs/v4_1/jupyter.md` |
| VS Code (`Dataset Explorer / Ask DSA`) | **Experimental** | 4.1.0 / 0.1.0 (dsa-vscode) | `tests/vscode 7 — 6-step + 5 failures` | `apps/vscode/src/*`, `docs/v4_1/vscode.md` |
| Benchmark (30 datasets / 100 tasks + leaderboard) | **Stable** | 0.3.0 (catalog) / 4.1.0 (platform) | `uv run dsa benchmark --limit 1` 1.0, `leaderboard.json` | `benchmarks/leaderboard/README.md` |
| Reproduction (L0–L5 + `ReproductionScore`) | **Stable** | 4.1.0 | `packages/evidence/reproducibility.py`, `dsa reproduce` | `docs/reproducibility.md` |
| Security & Supply Chain | **Stable** | 4.1.0 | `tests/security/test_w7 11 + 23 — CodeQL, Review, Secret, SBOM 192` | `SECURITY.md`, `.github/workflows/codeql.yml`, `release/sbom.json` |
| Frontend (13 routes) | **Stable** | 4.1.0 | `npm build 13/13`, `docker compose config valid` | `apps/web`, `apps/api` |
| Research (`V3_RESEARCH_REPORT`, claim-evidence, figures/tables) | **Stable** | 4.1.0 | `scripts/generate_*` pass, `research/V3_RESEARCH_REPORT.md` 13 sections | `research/`, `docs/research.md` |

**Notes:** Honest (§66): `Experimental` rows (Jupyter/VS Code/MCP App) are **not** in `Stable`; `Stub` is now `0` — all former Stubs are at least `Experimental`. No `users/downloads/stars` fabricated (§65) — numbers from `pytest 257`, `SBOM 192`, `benchmark 1.0`.

**Maturity Gate (§58):** `Stable` = API frozen + tests + docs + compat (§15-20); `Experimental` = works but API may change (§28-36); no `Prototype`/`Stub` remains except `Tasks` (MCP L4, deferred).

**Release:** `v4.1.0` (pyproject `4.1.0`, tag `v4.1.0`, `dsa verify-release v4.1.0` 12/12 PASS, `uv build` wheel `data_science_agent-4.1.0`).
