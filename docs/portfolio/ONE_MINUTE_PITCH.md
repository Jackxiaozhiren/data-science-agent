# One-Minute Pitch — Data Science Agent (V4.3 W11 §85)

> **Spec §85 — five questions, no inflated marketing copy. Answer each as the artifact proves it.**

---

## 1) What did I build?

An **evidence-grounded autonomous data science platform** — a question about your data becomes a reproducible analysis with every claim bound `Insight → Evidence → ToolCall → Dataset(sha256)` and a bundle `report.md + evidence_graph.json + reproduce.sh + analysis.ipynb + experiment.json`. The stack is Frontend (Next.js) → API (FastAPI) → **LangGraph** (`plan → exec → critic → report`, budgets 20/40, checkpoints) → Typed Tool Layer (DuckDB/Polars/SQLite + Python AST sandbox + stats/ML/viz) → Evidence Graph → MCP adapter, shipped as a **self-contained wheel** (`jack-data-science-agent`, vendored `_vendor/`, 0 `dsa-*` deps) with one SDK and many surfaces: `dsa` CLI (11 subcommands), Python SDK, MCP (18 tools), Jupyter magic, VS Code extension (7 commands), plugin `dsa-time-series`.

## 2) Why is it difficult?

Three things usually fail together: **statistics** (spurious claims, un-checked assumptions, causal language without a bar), **traceability** (fluent output that detaches claims from the computation that produced them), and **reproducibility** (fresh clone + dataset reference is not enough to replay). Solving one without the other is a demo, not a platform. We solve all three — and then face the honest problem that **internal 1.00 is easy to fake** unless measured on an independent benchmark and an honest external failure taxonomy.

## 3) What is technically distinctive?

- **Evidence Graph + Critic** (not just an agent loop): `unsupported_claim` and causal-bar checks rewrite causal claims to association when the evidence bar is not met; `evidence_coverage` gates the report; `S01–S10` statistical dimensions ride under `details`.
- **External benchmark adapter architecture** (not a patched benchmark): `ExternalBenchmarkAdapter` Protocol + `AgentTaskView` (`extra="forbid"` blocks gold), `assert_gold_isolation` (`gold/ground_truth/rubric` tripwire on every dispatch), `AgentBackedRunner` (lazy `Agent`, deterministic local pipeline), `TaskOutcome` (`passed/failed/unsupported/execution_error` — `COMPLETED` without GT is `failed`, not a pass). The original evaluator is applied inside the adapter, never mediated by the harness.
- **Verifiably produced package** (not just published): OIDC Trusted Publishing (`environment: pypi`) + PEP 740 PyPI attestations (digest-verified for `4.2.10` via DSSE envelope) + SBOM 192 (CycloneDX) + vendor sync guard (`scripts/sync_vendor.py --check`).

## 4) How did I prove it works?

- **Internal:** `ds-agent-benchmark` 50/50 `@1.00` + `benchmarks/v2` 100/100 `@1.00` (closed, synthetic, seed 42) — smoke `5/5` live.
- **External (DataSciBench, pinned 84ef3d4…):** 45 `human_*`/`csv_excel_*` tasks **executed** (5.8 s wall, 321 tool calls, 123 evidence) — **score lane pending GT** (gated `zd21/DataSciBench`), so we honestly report `failed` (unevaluated) rather than a fabricated transfer (§110). This surfaces a new failure class: **empty-input tasks** (`UnsupportedFormatError`, 44 steps) invisible internally.
- **DSAgentBench:** feasibility audit → `NOT CURRENTLY SUPPORTED` (unreleased / real-computer surface) — nothing claimed.
- **Case studies:** 8 open-ended, `COMPLETED` with 3–6 evidence, 18 real tool-call errors preserved (not deleted).
- **Cross-benchmark:** `research/v4_3/CROSS_BENCHMARK_MATRIX.md` (no Generalization Gap until GT — computed, not asserted).
- **Gates:** `pytest 253`, `mypy 104 clean`, `ruff OK`, `npm 13/13`, `docker valid`, `dsa verify-release 12/12`, `check_public_claims 0`, Scorecard `4.6/10` with blind spots annotated, reproducibility capsule `research/v4_3/reproducibility/README.md` (raw → analysis → figures/tables, no manual edits).

## 5) What did I learn?

- **Automation without a firewall is a slow way to fabricate.** The `AgentTaskView` boundary is the only thing that keeps independent benchmarking independent — the prompt is the task input, gold never crosses it.
- **An honest "unscored" beats a measured "1.00" on the wrong definition.** Internal `task_success` vs real `COMPLETED` are different verdicts; conflating them is definition drift.
- **Missing failures are the signal.** The 44 empty-input failures are not a DSA bug — they expose a benchmark design class this platform had never seen.
- **Supply-chain trust is a feature, not a badge.** PEP 740 attestations for a concrete version (`4.2.10`) with digest verification teach the user to verify the download, not to trust the README.

---

*Links: `docs/v4_3/V4_2_FINAL_TRUTH.md` (Phase A truth freeze) · `research/paper/paper.md` (14-section paper artifact) · `research/claim-evidence-matrix.md` · `research/v4_3/reproducibility/README.md` · `docs/v4_3/CROSS_BENCHMARK_MATRIX.md` · `docs/portfolio/PROJECT_SUMMARY.md` (this directory).*
