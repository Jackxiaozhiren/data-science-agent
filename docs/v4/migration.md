# Migration V3 → V4 — V4 W12 (§77–78)

No breaking core. New layer: `from data_science_agent import Agent` (was internal `dsa_agent.graph.run_analysis`).

- CLI: `dsa` now product CLI (doctor/init/analyze/profile/benchmark/plugin/mcp) — benchmark cmds compat (`dsa --limit 50`).
- Plugins: new — add `plugins/<name>/manifest.yaml`.
- MCP: Tools compat; Resources/App additive.
- SDK: `Agent.analyze_sync` + `Agent.profile` + `Benchmark/Reproduction`.

Deprecation policy: SemVer (§17) — MAJOR for breaking, MINOR for additive.
