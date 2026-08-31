# Project Summary — Data Science Agent (≈2 pages, §84)

> **Spec:** V4.3 W11 §84 — Application Portfolio Artifact: Problem / Why it matters / Architecture / Statistical, AI, Engineering contributions / Research evaluation / Results / Limitations / Links. Max ≈2 pages, no inflated marketing copy.
> **Version:** 4.2.10 (Spec branch) + Phases B–J through W10 (see `docs/v4_3/V4_2_FINAL_TRUTH.md`).

---

## Problem

Turning a natural-language question about tabular data into a trustworthy analysis is still brittle: outputs mix correct stats with hallucinations, traces are lost, and "it works on my benchmark" overstates generalization. Users — students, analysts, researchers — need an autonomous analyst that is *auditable*, not just fluent.

## Why it matters

A wrong but confident analysis (spurious correlation, p-hacked subgroup, un-evidenced causal claim) costs more than no analysis. Evidence grounding — every claim bound to an executable tool call and the dataset `sha256` it ran on — makes automation *reviewable*, and reproducibility (`reproduce.sh` + `analysis.ipynb` + `experiment.json`) makes it *repeatable* on a fresh clone without the author's secrets.

## Architecture (distinctive)

`Next.js 13 routes` → `FastAPI /api/v1/datasets /analysis /artifacts` (+ SSE `/events`) → **LangGraph** (`understand → plan → exec → critic → report`, `max_steps 20`, `max_tool_calls 40`, `retry 3`, `MemorySaver` checkpoints for replay) → **Typed Tool Layer** (17 tools over DuckDB read-only + Polars/SQLite + Python AST sandbox 5 s, Stats/ML/Viz) → **Evidence Graph** (`Insight → Evidence → ToolCall → Dataset hash`, evidence_coverage gating) → Validation (unsupported_claim / causal bar rewrite via `guardrails.py`) → Reports & Artifacts → MCP adapter (stateless, ADR-001) over the same tool layer. Frozen surfaces (LangGraph, FastAPI, DuckDB, Polars, SQLite, Evidence Graph, Python Sandbox, SDK/CLI/Plugin/MCP/Reproduction Engine) require ADR for major changes.

## Statistical contribution

The system enforces a statistical guardrail: `correlation_analysis` (Pearson `r`, `p`), `hypothesis_test` (t/chi-square/factorial where group size ≥2), `assumption_check` (normality, heteroscedasticity), `causal_check` (fails closed — "Treatment not near-binary; association only" unless design warrants). The **Critic** checks `evidence_coverage` (every insight has ≥1 evidence) and rewrites causal language to association when the bar is not met. `evaluator_v2` adds statistical dimensions `S01–S10` behind `details.statistical_eval`.

## AI contribution

Planning is heuristic (no LLM required for the deterministic pipeline) — the graph executes a typed plan (profile → correlation → SQL → stat test → viz → evidence) with async-batched independent tools and a bounded Critic loop. The Evidence Graph is the agent's *memory*: the same evidence is consumed by the markdown report, the Jupyter rich display, and the DataSciBench adapter's `build_logs_txt` (`## Current Plan` marker) for the original evaluator. The architecture is LLM-agnostic (model/provider/seed/temperature captured in `RunConfig`).

## Engineering contribution

**One SDK, many surfaces.** `dsa` CLI (11 subcommands), Python SDK (`Agent`, `Dataset`, `Benchmark`, `Reproduction` — all `Stable`), FastAPI server, MCP server (18 tools, 5 resources), Jupyter magic (`%dsa`/`%%dsa` + `await Agent().analyze()` with rich HTML + notebook `metadata` hash binding), VS Code extension (7 commands, 2 views), plugin runtime (`dsa-time-series 1.0.0` with lifecycle `Discover→Validate→Load→Execute→Disable→Remove`). The **self-contained wheel** (`jack-data-science-agent 4.2.10`, vendored `_vendor/` — `scripts/sync_vendor.py --check`, 0 `dsa-*` Requires-Dist) makes `pip install` standalone. SBOM 192 (CycloneDX 1.4), Trusted Publishing (OIDC, `environment: pypi`, `id-token: write`) with PEP 740 attestations verified for `4.2.10` (`*.publish.attestation`, DSSE envelope, subject digest matches wheel).

## Research evaluation (honest)

- **Internal:** `ds-agent-benchmark` 50/50 `@1.00` + `benchmarks/v2` 100/100 `@1.00` (30 synthetic datasets, seed 42, deterministic stub) — smoke `5/5` live, canonical 50/100 preserved in manifests. Internal 1.00 ≠ business usefulness (definition drift, reported in `benchmark_vs_real_world.md` §48).
- **External (DataSciBench, pinned `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`):** 45 `human_*`/`csv_excel_*` tasks executed end-to-end (5.8 s wall, 321 tool calls, 123 evidence, median 7/3 per task) — **no score**, GT gated (`zd21/DataSciBench`). This is the honest execution lane (`failed` honest outcome taxonomy §26, no Generalization Gap computed); the GT lane is `PENDING operator GT placement`.
- **External (DSAgentBench):** feasibility audit → `NOT CURRENTLY SUPPORTED` (275 tasks unreleased + real-computer IDE/terminal/browser/DB surface absent; no silent internal-API substitution, `docs/v4_3/DSAGENTBENCH_FEASIBILITY.md`).
- **Cross-benchmark:** `research/v4_3/CROSS_BENCHMARK_MATRIX.md` — new external failure class surfaced: **empty-input data directories** (`UnsupportedFormatError`, 44 steps, `human_*` tasks with no data file) invisible internally because internal benchmarks always ship a data file.
- **Case studies:** 8 open-ended, `COMPLETED` with 3–6 evidence, 18 real tool-call errors preserved (`train_model` CV continuous, `correlation`/`causal_check` `DuplicateError`, `hypothesis_test` group<2) — not deleted.

## Results (what a reviewer sees)

Clone → `uv sync --dev` → `pytest 253`, `mypy 104 clean`, `ruff OK`, `npm 13/13`, `docker valid`, `dsa verify-release 12/12`, `dsa demo` `COMPLETED`, `dsa --limit 5` `@1.00`, `mkdocs --strict` PASS, `check_public_claims 0`. Open a case study (`case-studies/01-sales/outputs/{evidence.json,tool_calls.json,report.md}`) and trace `Insight → Evidence → ToolCall → Dataset hash`. Re-run it (`Agent().analyze_sync` → same `run_id` shape + `artifacts/reports/<runId>/reproduce.sh`). On `benchmarks/external/datascibench`, re-run the 45-task execution (`DSC_WORKSPACE=… run_eval.py` → `raw_runs.json`), then `generate_phase_f_results.py` → `research/v4_3/results/{processed,tables,figures}/` (raw → analysis → artifact, no manual edits).

## Limitations

- Internal benchmarks are synthetic and closed-task (deterministic stub) — not a real-dirty-data predictor.
- External score until GT is present is **unevaluated** (Generalization Gap §36 not computed; paired tests / CI / effect sizes §43–46 deferred).
- Human evaluation `NOT CONDUCTED` at audit time (template + pipeline exist, `human-eval/samples.json` 11/100, `cohens_kappa`/`krippendorff_alpha` — no invented reviewers, §54).
- Supply-chain still short of §91: GitHub build provenance / Scorecard branch-protection & token least-privilege / Best Practices remain remediation (Scorecard 4.6/10, `SCORECARD.md`).

## Links

- Repo: `https://github.com/Jackxiaozhiren/data-science-agent` · PyPI: `jack-data-science-agent 4.2.10` (attested)
- Paper artifact: `research/paper/paper.md` + `paper.tex`, `references.bib`, `figures/`, `tables/`, `appendix/CROSS_BENCHMARK_MATRIX.md` (generated, not hand-edited)
- Reproducibility capsule: `research/v4_3/reproducibility/README.md` (environment + manifest + commands + hashes)
- Claim → Evidence: `research/claim-evidence-matrix.md` (every number maps to artifact/commit)
- Supply-chain: `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` + `docs/security/VERIFY_RELEASE.md` + `docs/v4_3/SCORECARD.md`
- Getting started: `docs/getting-started.md` (≤5 min install → `uv run dsa demo` → your CSV)

