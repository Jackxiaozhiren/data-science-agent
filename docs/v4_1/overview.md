# V4.1 Overview — Ecosystem Validation, Integration Hardening & Production Readiness

**Version:** `4.1.0` (tag `v4.1.0`, commit `HEAD`) — `4.0.0 → 4.1.0`  
**North Star (§5):** `Clone → Install → Run → SDK → CLI → Plugin → Jupyter → MCP → Evidence → Report → Contribute` without developer-specific path/secret/private dataset/internal service/manual patch.

**Objective (§4):** Turn `Platform Skeleton` (V4.0, 157 tests, 3 Stubs) into `Real Integrations` → `External Validation` → `Package Distribution` → `Security Hardening` → `Stable Ecosystem`.

**Principles (§6):** `Correctness > Real Usability > Compatibility > Security > Reproducibility > DX > Maintainability > Performance > UI Polish`. Non-Goals (§7): no Enterprise SaaS/Billing/K8s/Foundation Model.

**Architecture Freeze (§8):** `LangGraph/FastAPI/Next.js/DuckDB/Polars/SQLite/Evidence/Evaluation/Sandbox/MCP/SDK/Plugin` — no rewrite without ADR.

**Workstreams (§9):** W1 Freeze & Claim Audit (done `d9efffa`) → W2 SDK/CLI (`d56e927`) → W3 Plugin (`6968a7d`) → W4 Jupyter (`f688410`) → W5 VS Code (`7b65547`) → W6 MCP App (`f969b82`) → W7 Security (`c27546c`) → W8 External Validation (`b5bbe44`+`e27ae7f`) → W9 Performance (`d9e72d0`) → W10 Release (this).

**Success (§69):** New developer can `install (uv sync)`, `run demo`, `use SDK`, `install plugin`, `run Jupyter`, `use MCP`, `inspect evidence`, `reproduce`, `contribute`, `understand Stable vs Experimental` — all verified in `EXTERNAL_DEVELOPER_VALIDATION.md` (7/7, 2s).

**Quality Bar (§70):** `Correct, Secure, Observable, Reproducible, Stable, Installable, Integrable, Extensible, Honest, Open-source friendly` — gates `257 passed / 104 mypy / ruff pass / 13/13 routes / 192 SBOM / CodeQL ready`.

See `RELEASE_MATRIX.md` (§59), `MIGRATION_V4_0_TO_V4_1.md` (§60), `performance.md` (§51-55), `MCP_COMPATIBILITY.md` (§40).
