# V4 Implementation Truth — V4.1 Phase A Freeze & Claim Audit

> **V4.0 baseline @ fbf6dd7, tag v4.0.0, version 4.0.0 — read-only audit, no new V4.1 features.** Live verification at 2026-08-21. Gates: `pytest 157 / mypy 102 clean (packages apps/api strict) / ruff All checks / npm 13/13 / docker compose valid / dsa 12/12 PASS / coverage 81%`. `mypy .` shows 112 errors in tests/research (non-gate, see §10 note).

## Maturity Legend

- **Production** — proven in prod, monitored
- **Stable** — API stable, tested, documented (§18)
- **Experimental** — works but API may change
- **Prototype** — minimal viable, not hardened
- **Stub** — scaffold/placeholder, not usable as claimed

---

## Capability Truth Table

| Capability | Status | Evidence | Maturity |
|------------|--------|----------|----------|
| **Core Agent** (LangGraph Planner→Scientist→Critic→Report) | PASS | `packages/agent/src/dsa_agent/graph.py` `run_analysis`, 157 tests, demo `COMPLETED` 4 evidence | **Stable** |
| **SDK** `from data_science_agent import Agent, Dataset, Benchmark, Reproduction` | PASS | `src/data_science_agent/sdk.py` `Agent.analyze/profile`, `Benchmark.run`, `API_STABILITY Stable`, `tests/api/compatibility/test_sdk_compat.py` | **Stable** |
| **CLI** `dsa --help / doctor / init / analyze / profile / benchmark / demo / verify-release` | PASS | `dsa_evaluation/cli.py` 12 subcmds, `uv run dsa doctor` warn, `uv run dsa plugin` → `dsa-time-series` | **Stable** (CLI contracts per §37) |
| **Plugin Arch** (`DataSciencePlugin`, manifest, registry) | PASS | `packages/plugins/src/dsa_plugins/{plugin,manifest,registry}.py`, `plugins/README.md`, `dsa plugin` discovers `dsa-time-series` | **Stable** (discovery+permissions, no marketplace §27) |
| **dsa-time-series Plugin** | PASS | `plugins/dsa-time-series/manifest.yaml` `forecasting`, `src/dsa_time_series/plugin.py` `TimeSeriesPlugin` | **Experimental** (forecast/backtest/viz stubs, not full V4 §81) |
| **MCP** (Tools `stateless 2026-07-28`) | PASS | `packages/mcp/src/dsa_mcp/adapter.py` `MCP_TOOL_MAP` 17, `server.py` mount `/mcp`, conformance in 157 tests | **Stable** |
| **MCP Resources** (`dataset:// evidence:// report://`) | PASS | `adapter.list_resources()` returns 3 resources | **Experimental** (listed but not client-tested beyond smoke) |
| **MCP App** (`/mcp-app` shell) | PARTIAL | `packages/mcp/src/dsa_mcp/app.py` 2 routes (`/`, `/app`), mounted at `/mcp-app` — no real analysis UI (§31 flow) | **Stub** (§31 Dataset→Question→Analysis→Evidence→Viz not yet wired) |
| **Jupyter Integration** | STUB | `apps/jupyter/README.md` explicitly says `stub`, `%dsa analyze` not implemented, `Agent` notebook rendering is SDK facade only | **Stub** (V4.0 assessment §3 correct) |
| **VS Code Integration** | STUB | `apps/vscode/README.md` says `Stub until SDK stabilizes` — no extension manifest/publish | **Stub** |
| **Benchmark** (30 datasets/100 tasks + 50) | PASS | `benchmarks/v2` + `benchmarks/ds-agent-benchmark`, `uv run dsa benchmark --limit 1` @1.0, `benchmarks/leaderboard/leaderboard.json` | **Stable** |
| **Reproduction** (L0–L5 + `dsa reproduce`) | PASS | `packages/evidence/reproducibility L0-L5`, `Reproduction` SDK, `dsa reproduce` + `research_manifest` | **Stable** |
| **Research** (`V3_RESEARCH_REPORT`, claim-evidence, figures/tables) | PASS | `research/V3_RESEARCH_REPORT.md` 13 sections, `scripts/generate_*`, `technical-report` | **Stable** |
| **Frontend** (13 routes, Next.js 15) | PASS | `apps/web` `npm build` 13/13, `apps/api` health/ready | **Stable** |
| **Security/Supply-chain** | PASS | `tests/security` 23 cases, `SECURITY.md` (§78), `dependabot.yml` (pip/npm/docker weekly), `CODEOWNERS`, no hardcoded secrets in git log | **Stable** (CodeQL infra is GitHub setting, not code — expected local PASS) |

---

## Misleading Documentation Check

- **Quantitative claims**: README says `Avoid State-of-the-art / Best / Production-ready without evidence` (§45) — **honest** (cites `Benchmark + Commit + Report`).
- **README V4 line**: `V4 adds: SDK (Agent), product CLI, plugin architecture, MCP Apps, Jupyter/VS Code` — **fixed 2026-08-21** in `README.md:13` to `Stable: SDK/CLI/plugin discovery/MCP Tools | Experimental: MCP Resources/TimeSeries | Stub: MCP App/Jupyter/VS Code` per §62/§58, linking `docs/v4_1/RELEASE_MATRIX.md`.
- **CLI help**: `dsa --help` lists `doctor/init/analyze` without claiming `Production-ready` — **ok**.
- **No fake adoption**: No `users/downloads/stars` fabricated (§65) — **ok**.

## Security / Supply-Chain Risks

- **No hardcoded credentials** in tracked files (audit: `grep` for `API keys/tokens` in repo — none).
- **MCP stateless**: No session state — correct (§38).
- **Plugin permissions**: `read/compute` gated in `manifest.yaml`, stored in `PluginManifest.permissions` — **not yet enforced at runtime** (validate step §24 pending, deny-by-default §23 not fully wired). **Report as risk, not blocker.**
- **GitHub Security**: `Dependabot` ✅, `CODEOWNERS` ✅, `Secret Scanning / Code Scanning / Dependency Review` are repo settings (§67) — not verifiable locally, instruct to enable on remote push.

## API / Integration Risks

- **Public API**: `data_science_agent` facade wraps `dsa_agent.graph.run_analysis` (sync via `asyncio.run`). Risk: event-loop reentry in Jupyter may need `nest_asyncio` (minor).
- **CLI `dsa analyze`**: uses `Agent.analyze_sync` + `--task` positional handling fixed in prior V4 patch — verify `uv run dsa analyze ... --task ... --json` in external validation (§48).
- **Plugin execution**: `dsa-time-series` registers tools/models but not yet wired into `Agent` tool selection — flagged as Experimental.

---

## Verdict

V4.0 is **honest platform skeleton** with Stable core (Agent/SDK/CLI benchmark+analysis/MCP Tools/Benchmark/Repro/Research). Jupyter/VS Code/MCP App are correctly **Stubs** per V4 spec — Phase A confirms docs mostly qualify them; README fixed 2026-08-21 now splits `Stable vs Experimental vs Stub`.

No Critical Issue blocking freeze; `V4.0 FREEZE VERIFIED`. Next: Phase B W2 SDK/CLI Distribution Hardening (§14-20).
