# Roadmap

> **Source of truth for V3.0–V4.1 workstreams** — V4.1 at `docs/v4_1/release.md` + `CHANGELOG.md:4.1.1` — V4.2 at `DATA_SCIENCE_AGENT_V4_2.md` §7 and `docs/v4_2/V4_1_RELEASE_INTEGRITY_REPORT.md`. Original V3.0 see `DATA_SCIENCE_AGENT_V3_0.md` §7 and `docs/v3/V2_FINAL_BASELINE.md` §15.

## V2.0 Released — Research Grade (v2.0.0)

- Baseline freeze (docs/v2), Evaluation Framework (10×6), Benchmark v2 (30 datasets / 100 tasks / 11 categories, seed 42), Reliability & Reproducibility (L0–L5, F01–F15, Trace/Span), MCP 2026-07-28 stateless (ADR-001), Security hardening (23 cases), Research package (RQs 1–5, ablation A–F), 13 frontend routes — `v2.0.0` at `777dd08`.

## V3.0 — Research Validation, External Reproducibility & Open-Source Release

Status: **Released** `v3.0.0` (W1–W12 Done) — `docs/v3/V2_FINAL_BASELINE.md` + `research/V3_RESEARCH_REPORT.md` + `release/v3.0`.

| Workstream | Status | Gate |
|------------|--------|------|
| W1 Baseline Revalidation | Done | `docs/v3/V2_FINAL_BASELINE.md` (137 passed, 80%, 50/50, 100/100) |
| W2 Benchmark Scientific Audit | Done | `docs/v3/BENCHMARK_AUDIT.md` + `benchmarks/v2/catalog.json 0.2.0→0.3.0` (audited, versioned) |
| W3 Independent Reproduction | Done | `dsa --reproduce` (`reproduction/{manifest,environment,results,comparison,logs}` + `ReproductionScore` 6-dim) — `docs/v3/REPRODUCTION.md` |
| W4 Statistical Evaluation Upgrade | Done | `evaluator_v2` (10 dims S01–S10, causal/uncertainty) wired into `EvaluationResult.details` — `docs/v3/STATISTICAL_EVALUATION.md` |
| W5 Agent Reliability Research | Done | 4 configs (single/planner/planner+critic/full) × 7 §27 metrics + §28–30 — `docs/v3/RELIABILITY.md` |
| W6 Cross-Model Evaluation | Done | 4 classes (no fabrication) + 3 frontiers — `docs/v3/CROSS_MODEL.md` |
| W7 Human Evaluation | Done | 11/100 stratified (seed 42, Kappa/Alpha) — `human-eval/` + `docs/v3/HUMAN_EVALUATION_GUIDE.md` |
| W8 External User Validation | Done | `dsa demo` + `dsa external-validation` (§39–42) local-first — `docs/v3/EXTERNAL_VALIDATION.md` + `demo/` |
| W9 Open-Source Release Engineering | **This phase** | `README` first-screen (6 questions §44), `CITATION.cff`, claim policy §45, license/security/contributing audit, `ROADMAP.md` |
| W10 Documentation & Research Packaging | Next | `docs/` structure §48–50, diagrams §49 (Mermaid), `research/V3_RESEARCH_REPORT.md` §51 |
| W11 Publication & Citation Infrastructure | After W10 | `research/technical-report/` versioning + figure/table reproducibility |
| W12 V3 Release | Final | `v3.0.0` + `dsa verify-release v3.0.0` (§58–63) |


## V4.0 — Open-Source Ecosystem, Developer Platform & Productization (Released v4.0.0 @ fbf6dd7, 2026-08-17)

Status: **Released** `v4.0.0` — SDK (`Agent/Dataset/Benchmark/Repro` Stable), CLI (`dsa doctor/init/analyze`), Plugin Arch (`dsa-time-series` Experimental), MCP Tools/Resources (Stable/Experimental), Jupyter/VS Code (Stub→Experimental), Benchmark Leaderboard, Research Package — `docs/v4_1/V4_IMPLEMENTATION_TRUTH.md`, `docs/v4_1/RELEASE_MATRIX.md`.

## V4.1 — Ecosystem Validation, Integration Hardening & Production Readiness (Released v4.1.0 @ 4a0158d, 2026-08-21; patch v4.1.1 @ 2026-08-22)

Status: **Released v4.1.1** (patch 2026-08-22) — W1 Freeze + W2 SDK/CLI hardening (257 tests, 104 mypy, 13 routes, 12/12 verify) + W3 Plugin (24), W4 Jupyter (10, `dsa-jupyter 0.1.0`), W5 VS Code (7), W6 MCP App (18 tools, 5 resources, 6 acceptance), W7 Security (CodeQL, Review, Secrets, SBOM 193) + W8 External Validation (Fresh Clone 7/7) + W9 Performance + W10 Release — `CHANGELOG.md:4.1.0`, `CHANGELOG.md:4.1.1`, `docs/v4_1/release.md`, `docs/v4_2/V4_1_RELEASE_INTEGRITY_REPORT.md`.

| Workstream | Gate (V4.1) |
|------------|-------------|
| W1 Freeze | `docs/v4_1/V4_IMPLEMENTATION_TRUTH.md` (157→257) |
| W2 SDK/CLI | `tests/sdk 18 + CLI 13`, `API_STABILITY Stable` |
| W3 Plugin | `dsa-time-series 1.0.0 Stable` |
| W4 Jupyter | `dsa-jupyter 0.1.0 Experimental` |
| W5 VS Code | `dsa-vscode 0.1.0 Experimental` |
| W6 MCP App | `/mcp-app` real HTML |
| W7 Security | `193 SBOM`, CodeQL, Review, Secrets |
| W8 External | `EXTERNAL_DEVELOPER_VALIDATION.md` 7/7 |
| W9 Perf | `performance.md` |
| W10 Release | `v4.1.0` + `v4.1.1` patch |

## V4.2 — Post-Release Integrity, Real-World Validation & Adoption (Next, see DATA_SCIENCE_AGENT_V4_2.md)

Status: **Phase A complete** (`docs/v4_2/V4_1_RELEASE_INTEGRITY_REPORT.md` 2026-08-22), awaiting Phase B `Artifact / Metadata Sync` → `W3 Public Truth` → `W4 Case Studies` etc. per §71-72.

## Out of scope for V3.0 (per §4 Non-Goals)

Another chatbot, random agent, large tool set, dashboard, vector DB, cloud infra, billing/payment, multi-tenancy, mobile app, custom foundation model, distributed GPU training, large-scale RAG — not core unless they improve reliability/research validity/reproducibility.

## Limitations (carried risks)

- MCP upstream drift (`Mcp-Session-Id` deprecation), global `_TOOL_CACHE`, sandbox in-process scope, `mcp/server 51%` coverage, Windows not tested (see `docs/v3/EXTERNAL_VALIDATION.md`).
