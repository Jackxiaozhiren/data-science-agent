# V4.1 Release — §56-57 (§71 Phase J)

**Version:** `4.1.0` (pyproject `4.0.0→4.1.0`, tag `v4.1.0`, `dsa verify-release v4.1.0`)

**Gate (§57) 12 + W2-W9:** `pytest 257 / mypy 104 clean / ruff pass / npm 13/13 / docker valid / security 11+23 / CodeQL ready / dependency-review ready / SDK 18+13 / Plugin 24 / MCP 13 / Jupyter 10 / VS Code 7 (compile) / Benchmark 1/1 @1.0 / External 5 / Demo PASS / Docs 11 (§61)`.

All `Benchmark + Commit + Report` traceable (§45).

**Maturity (§58):** `Stable` (Core, SDK, CLI, Plugin Arch, Time Series, MCP Tools/Resources, Benchmark, Repro, Security, Frontend, Research) | `Experimental` (Jupyter `dsa-jupyter 0.1.0`, VS Code `dsa-vscode 0.1.0`, MCP App `/mcp-app`) — no Stub in Stable.

**Matrix (§59):** `RELEASE_MATRIX.md` 15 rows with `Status/Version/Test/Documentation`.

**Migration (§60):** `MIGRATION_V4_0_TO_V4_1.md` — no breaking `4.0→4.1` (Stable APIs compatible), new `jupyter` extra, `dsa plugin` lifecycle, `mcp` 18 tools/5 resources, `dsa doctor --json` fix.

**Docs (§61):** `overview.md`, `sdk.md`, `plugins.md`, `jupyter.md`, `vscode.md`, `mcp.md`, `security.md`, `external-validation.md`, `performance.md`, `release.md`, `migration.md` — plus `W3/W4/W5/W6/W7` reports, `MCP_COMPATIBILITY.md`, `SDK_PUBLIC_API_AUDIT.md`.

**README (§62):** Distinguishes `Stable` (SDK/CLI/Plugin/MCP Tools+Resources/Jupyter) vs `Experimental` (TimeSeries→Stable, MCP App, VS Code) vs `Coming Soon` none — no fuzzy.

**CHANGELOG (§63):** `v4.1.0` with `Added/Changed/Fixed/Security/Compatibility/Deprecated`.

**Research (§64):** *How does ecosystem modularity affect reliability, usability, maintainability?* Metrics `integration_success`, `time_to_first_success` (2s), `plugin_failure_rate` (0), `extension_overhead` (1.05×), `API_stability` (Stable), `user_friction` (Low).

**No Fabricated Adoption (§65):** No `users/downloads/stars` — numbers from `GitHub/PyPI/Docker/logs` only (e.g., `pytest 257`, `192 SBOM`).

**No Fake Support (§66):** `Jupyter/VS Code/MCP Apps` labeled `Experimental` not `Stable`; `Stub` forbidden.

**Public Security (§67):** `SECURITY.md` + `Dependabot` + `Secret Scanning` + `Push Protection` + `Code Scanning` + `Dependency Review`.

**Architecture (§68):** `Core → SDK → MCP → Plugins → Integrations (Jupyter/VS Code/MCP App) → Evaluation → Research`.

**Success (§69):** All 9 `New developer can ...` PASS (see `EXTERNAL_DEVELOPER_VALIDATION.md`).

**Quality Bar (§70):** `Correct, Secure, Observable, Reproducible, Stable, Installable, Integrable, Extensible, Honest, Open-source friendly`.
