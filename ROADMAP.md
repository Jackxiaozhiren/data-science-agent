# Roadmap

> **Source of truth for V3.0 workstreams** — see `DATA_SCIENCE_AGENT_V3_0.md` §7 and `docs/v3/V2_FINAL_BASELINE.md` §15.

## V2.0 Released — Research Grade (v2.0.0)

- Baseline freeze (docs/v2), Evaluation Framework (10×6), Benchmark v2 (30 datasets / 100 tasks / 11 categories, seed 42), Reliability & Reproducibility (L0–L5, F01–F15, Trace/Span), MCP 2026-07-28 stateless (ADR-001), Security hardening (23 cases), Research package (RQs 1–5, ablation A–F), 13 frontend routes — `v2.0.0` at `777dd08`.

## V3.0 — Research Validation, External Reproducibility & Open-Source Release

Status: **in progress** (W1–W8 done through this repo; W9–W12 remain per Phase gate).

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

## Out of scope for V3.0 (per §4 Non-Goals)

Another chatbot, random agent, large tool set, dashboard, vector DB, cloud infra, billing/payment, multi-tenancy, mobile app, custom foundation model, distributed GPU training, large-scale RAG — not core unless they improve reliability/research validity/reproducibility.

## Limitations (carried risks)

- MCP upstream drift (`Mcp-Session-Id` deprecation), global `_TOOL_CACHE`, sandbox in-process scope, `mcp/server 51%` coverage, Windows not tested (see `docs/v3/EXTERNAL_VALIDATION.md`).
