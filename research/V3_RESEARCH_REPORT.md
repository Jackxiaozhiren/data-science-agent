# V3 Research Report — Research Validation, External Reproducibility & Open-Source Release

> **Follows §51 structure exactly** · Commit: see `V2_FINAL_BASELINE` / `ROADMAP` · Benchmark: `benchmarks/v2` `0.3.0` `30/100/11` `seed 42` · Evaluator: `evaluator_v2` (§22–25 S01–S10) · Human: `human-eval/` 11/100 (§35–38) · External: `dsa demo` (§39–42) · Release gates §59–62 · No fabricated numbers (§45/61).

---

## Abstract

V2.0 delivered a research-grade Evidence-Grounded Autonomous Data Science System (baseline freeze with regression contract, `EvaluationResultV2` 10×6, Benchmark v2 30/100/11, `L0–L5` reproducibility, `F01–F15`, `Trace/Span`, MCP 2026-07-28 stateless, 23 security cases, 13 frontend routes). V3.0 answers **"is the system truly reliable, verifiable, reproducible, researchable, and independently usable?"** (V3 North Star §2: clone→install→demo→benchmark→trajectory→evidence→replay→reproduce→figures→claims traceable to Evidence/Tool/Computation/Dataset).

This report freezes V3.0 W1–W10: scientific benchmark audit (Q1–Q10), independent reproduction (`reproduction/` + `ReproductionScore`), statistical rigor upgrade (`evaluator_v2` 10 dims, `S01–S10`), reliability research (4 configs × 7 §27 metrics), cross-model frontier (4 classes, 3 frontiers, no fabrication), human evaluation (11/100 stratified, `Kappa/Alpha`), external validation (`dsa demo` one-command), open-source release engineering, and documentation packaging. Gates: `pytest 155 / mypy 92 clean / cov 81% / ruff All checks passed / dsa 50/50 + 100/100 @1.00 / dsa demo pass / compose valid / npm build 13/13`.

---

## Introduction

Data Science Agent targets **reproducible analysis from natural language** (§0 Position: Evidence-Grounded). V2.0 solved completeness; V3.0 must prove research validity (V3 §1). The priority order is `Scientific Validity > Reproducibility > Statistical Rigor > Evaluation Integrity > Security > External Usability > Open-Source Quality > Performance > UI Polish` (§3). Non-goals (§4) are explicitly excluded.

Freeze invariants: architecture frozen (`LangGraph/FastAPI/Next.js/DuckDB/Polars/SQLite/Evidence/Sandbox/MCP/Evaluation`, §5) — only critical issues with ADR (§6) may change it.

---

## Research Questions

From `research/questions/RQs.md` (RQs 1–5):

| RQ | Question | Maps to |
|----|----------|---------|
| RQ1 | Does tool augmentation improve statistical correctness? | Ablation A( LLM-only ) vs B( LLM+Tools ) |
| RQ2 | Does Critic verification reduce unsupported claims? | w/o vs w/ Critic (→ §28 `Critic Benefit = Quality / Cost`) |
| RQ3 | Does Evidence Graph improve traceability? | `evidence_coverage / unsupported_rate / reproducibility` (L4–L5) |
| RQ4 | Does explicit statistical validation improve reliability? | `evaluator_v2` 10 dims / `S01–S10` vs task-success only |
| RQ5 | How does model choice affect reliability? | Cross-model §31–34 (Local vs Open API vs Frontier, no fabrication) |

Limitations logged (§62): LLM stochasticity, model dependence, leakage, dataset/eval/selection bias, cost, local-model limits.

---

## System Architecture

See `docs/architecture.md` — **7 Mermaid diagrams (version-controlled, §49)**:

1. **System**: Frontend API Agent Tool Data Evidence Reports Repro MCP Observability.
2. **Agent Graph**: `understand → plan → exec_step* → critic → report` with `MemorySaver` checkpoints (pause/resume/replay/fork), budgets `max_steps 20 / max_tool_calls 40 / max_retries 3`.
3. **Tool Architecture**: Typed `async execute` contract; 17 tools (`profile_dataset/run_sql/run_python/describe/correlation/hypothesis/regression/train/evaluate/feature_importance/forecast/visualization/evidence/report/save_artifact`) dispatching to `tools|statistics|ml|visualization|evidence`.
4. **Evidence Graph**: `Insight → Evidence → ToolCall → Dataset(hash)` with 4 validators (`insight_evidence/traceability/unsupported_claim/dataset_hash`).
5. **Data Lineage**: `Dataset(hash+schema) → Profiler/DuckDB/Sandbox → Evidence/Insights → Report → Validation → Bundle → Fresh reproduction L0–L5`.
6. **Evaluation Pipeline**: `Catalog → Runner → Metrics (TaskMetrics) + evaluator_v2 (10 dims S01–S10) → Aggregate (by_category/by_difficulty, bootstrap CI/McNemar/Wilcoxon) → Reliability/Human/Cross-Model`.
7. **Reproduction Pipeline**: `Developer Run → Archive → Fresh Env → Fresh Clone → Fresh Install → Run Benchmark → Compare → ReproductionScore 6-dim + by_level`.

---

## Evaluation Methodology (§59–77, §72–74 Versioning)

- **Benchmark versioning**: `v2.0 → v2.1 → v3.0` (§72); results immutably tagged (`release/v3.0/` §74), `v3.0.1` for corrections, evaluator `evaluator_v1/v2` (§73) — compare only with `evaluator_version` annot.
- **Metrics**: `evaluation_framework.py` `EvaluationResultV2` 10×6 (`task_success/statistical/tool/evidence/unsupported/code/sql/...` × `Tool/Numerical/Statistical/Interpretation/Evidence/Report`), `by_category/by_difficulty`; `significance.py` (`bootstrap_ci/paired_bootstrap/mcnemar/wilcoxon`).
- **Statistical upgrade**: `evaluator_v2` (`statistical_eval.py`) 10 dims (`Method Selection / Assumption Validation / Test Execution / Parameter Estimation / P-value / CI / Effect Size / Interpretation / Causal Language (§24) / Uncertainty (§25)` ) + `S01–S10` taxonomy; causal phrases `{causes, caused by, leads to, impact, drives, results in}` flagged unless evidence includes causal design; uncertainty omissions (`CI/forecast/limitation`) flagged `S10`.
- **Cost/Perf**: `§75–76` — `Token Usage / Estimated API Cost (stub heuristic for local, real billing when keyed) / Runtime / CPU / Memory` + `Cold/Warm start, Analysis/Tool/LLM/Report time, Throughput`; use `Median/P95` not mean-only. Resource limits `§77`: `Max Dataset 100MB / Analysis time / Python 5s / Memory / Output / Agent Steps 20 / Tool Calls 40`.
- **Claim policy (§45/64)**: Every number cites `Benchmark Version + Commit + Report` (e.g. `v2 0.3.0 + commit + docs/v3/V2_FINAL_BASELINE.md`). No `SOTA/Best/Enterprise-grade` without `Metric+Setup+Uncertainty+Limitations`.

---

## Benchmark

### Sources, Licenses, Generation, Validation, Gold Standards (§50)

- **Sources**: Synthetic CSVs generated by `scripts/generate_benchmark_v2.py` (`seed 42`, deterministic) from 10 canonical frames (`ads/clustering/correlation/customer_churn/data_quality/energy/financial/groups/health/outliers/sales` + 10 new `clustering/imbalanced/time_series_long/mixed_types/high_card/high/leakage/missing_heavy/unicode/wide/causal_toy`). Real-world swap would record `source/license/citation` per task (see `THIRD_PARTY_LICENSES.md`).
- **Licenses**: Synthetic are `CC0`; `benchmarks/v2/catalog.json` per-task `license` field is `CC0` (when real datasets are added, license is recorded there).
- **Task Generation**: `generate_benchmark_v2.py` — 50 v1 tasks verbatim preserved + 50 new across 3 net-new categories (`Data Profiling/Clustering/Evidence Validation`), each with `difficulty/gold_method/required_tools/gold_metrics/required_evidence/forbidden_claims`.
- **Task Validation**: `docs/v3/BENCHMARK_AUDIT.md` answers Q1–Q10 (§12): independence, gold correctness, alternative methods (§16 `acceptable_method/metrics/interpretation/evidence/bound`), leakage, representativeness, duplication (`hash` dedup), triviality, underspecification, superficial pattern reward — plus ownership `generator/reviewer` (§14) and difficulty §15.
- **Gold Standards**: Per-task `acceptable_method/acceptable_metrics/acceptable_interpretation/acceptable_evidence/forbidden_interpretation/evaluation_function` (§16), evaluator `evaluator_v2` versioned (§73); prohibits single-method gating.
- **Metrics/Scoring**: `metrics.py` `TaskMetrics` + `aggregate_metrics`; statistical via `evaluate_statistical` → `details.statistical_eval`; tolerances recorded per task.
- **Limitations**: Synthetic bias, `sql_accuracy` heuristic, English-only questions, 100-task sample, local stub LLM — see §13–17 `PENDING` reviewers for full external audit.
- **Seed/Hardware/Software**: `seed 42`, `catalog 0.3.0 sha c493bc69`, `30 datasets / 100 tasks / 11 cats`, `Python 3.12 / uv 0.11.7 / Node v24.15.0 / Darwin arm64`, `uv.lock 114 packages`, live runs below.

### Live benchmark (must-reproduce gates, §9)

| Benchmark | Gate | Live |
|-----------|------|------|
| v1 `ds-agent-benchmark` (20/50/8) | `dsa --limit 50` | `50/50 @1.00` (8 cats @1.0, mean ~47ms) |
| v2 `benchmarks/v2` (30/100/11) | `dsa --catalog ... --limit 100` | `100/100 @1.00` (11 cats @1.0, mean 30–32ms) |

Per-task metadata (excerpt, `benchmarks/v2/catalog.json 0.3.0`):

```json
{"id": "sql-05", "category": "SQL", "dataset": "sales.csv", "difficulty": "medium", "gold_method": "duckdb sql", "evaluation_function": "sql_contains", "source": "synthetic generate_benchmark_v2.py", "license": "CC0", "benchmark_version": "0.3.0", "benchmark_generator": "scripts/generate_benchmark_v2.py seed 42", "human_reviewer": "PENDING", "acceptable_method": ["duckdb sql", "polars"]]
```

---

## Experimental Setup

All plots are reproducible from `research/results/` + `benchmarks/v2` (`§54–57`):

| Experiment | Config | Command |
|------------|--------|---------|
| Ablation A–F | `research/experiments/ablation_matrix.py` (A LLM-only … F Full) + `run_ablation.py` (real `run_benchmark` + `bootstrap_ci/mcnemar`) | `uv run python research/experiments/run_ablation.py --limit 20 --out research/results` |
| Benchmark v1 | `ds-agent-benchmark` catalog | `uv run dsa --limit 50` |
| Benchmark v2 | `benchmarks/v2` 0.3.0 | `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100` |
| Cross-model | `cross_model.py` 4 classes, frontier | `uv run python -m dsa_evaluation.cross_model` |
| Reproduction | `reproduction/v2` fresh twice + `ReproductionScore` | `uv run dsa --reproduce v2 --out reproduction/v2` |
| Human eval | `human-eval/` 11/100 stratified seed 42 | `human-eval/README.md` workflow |
| Demo | local-first stub | `uv run dsa demo` / `uv run dsa external-validation` |

Manifest per run: `experiment_id / git_commit / benchmark_version / dataset_version / model / prompt_version / seed 42 / timestamp / configuration` (§56).

---

## Results

### Ablation Study (§57, RQ1–RQ4)

Stub-gated ablation is **post-hoc measurement via `reliability.py`** (§27–30) rather than re-running LLM weights; live benchmark `100/100` is the empirical anchor. `reliability.py::evaluate_reliability` computes 7 §27 metrics (`task_success / statistical_correctness (evaluator_v2) / unsupported_claim_rate / evidence_coverage / tool_efficiency / recovery_success / reproducibility`) per config plus §28 `Critic Benefit`, §29 `Tool Selection Accuracy`, §30 `Agent Efficiency`.

Recorded artifacts: `research/results/ablation_*.json` (smoke `limit 2` + `20` pre-V3 + current `dsa 100/100` aggregate anchor). Local stub: `F Full` dominates on evidence-grounding and reproducibility; `task_success` is saturated at `1.0` by deterministic tooling, so separations are on `statistical_overall` and `unsupported_claim_rate`.

### Cross-Model (§31–34, RQ5)

`packages/evaluation/src/dsa_evaluation/cross_model.py` — `4` classes, no fabrication:

| Class | Provider probing |
|-------|------------------|
| `local_small` | `ollama/small` if `OLLAMA_HOST` else `stub/small` (always available §34) |
| `local_medium` | `ollama/medium` if `OLLAMA_HOST` else `stub/medium` |
| `open_api` | `OPENAI/ANTHROPIC/GOOGLE_API_KEY` present → available, else `NOT RUN` |
| `frontier` | `OPENAI/ANTHROPIC` frontier key → available |

Local-first (§34): at least one benchmark must run without paid cloud (`Local LLM + DuckDB/Polars + Local Storage`). Achieved: `dsa v2 100/100` on `stub/small` (`Cloud API Cost = $0`).

Frontiers (§33): `Quality vs Cost / Latency / Tokens` as Pareto frontiers (no claim "Model X is best"; trade-off). Cost model is `stub heuristic: local 0, open 0.002/1k, frontier 0.01/1k — placeholder` (real billing when keyed). See `docs/v3/CROSS_MODEL.md`.

### Statistical Evaluation (§22–25, RQ4)

`evaluator_v2` 10 dims per task + `S01–S10` flags wired into `EvaluationResult.details.statistical_eval` (non-breaking). Causal phrases (`causes/leads to/impact` out of `causes, caused by, leads to, impact, drives, results in`) on observational correlation without causal tool (`causal_check`) emit `S09`; missing `CI/forecast/limitation` when expected emits `S10`. Full taxonomy: `S01 Wrong Test … S10 Uncertainty Omission` (§23). See `docs/v3/STATISTICAL_EVALUATION.md`.

### Failure Analysis (§30/67)

Taxonomy `F01–F15` (`packages/evidence/src/dsa_evidence/failure_taxonomy.py`) and frontend `/failures` (§67). Agent EfficiencyScore from §30 (`duplicate/oscillation/repeated_failures/over_analysis`). Representative cases deferred to individual run traces (`human-eval/samples` + `reproduction/comparison.json`).

### Human Evaluation (§35–38, W7)

`human-eval/samples.json` — **11/100 (11%) stratified** `ratio 0.08, seed 42, hash c3835816` (`clf-04/clus-04/dq-06/eda-08/ev-01/prof-04/reg-08/sql-05/stats-10/ts-06/viz-03`, one per category). Rubric (§36) 8 dims (`Correctness/Clarity/Statistical Validity/Evidence Quality/Interpretation/Uncertainty/Actionability/Report Quality`) × `1 unacceptable … 5 excellent`. Inter-rater §38: `Cohen's Kappa (2 raters) / Krippendorff's Alpha ordinal (3+)` per dimension via `agreement_summary`; tests `152→155` include Kappa/Alpha invariants. Workflow: `copy reviews.template.json → reviews/<reviewer>.json → agreement.json`.

No blocking gate — automated gates remain authoritative (§51 note), human validates them.

---

## Reproducibility (§17–21, §70)

Pipeline `§70`: `Developer Run → Archive → Fresh Environment → Fresh Clone → Fresh Install → Run Benchmark → Compare` → `reproduction/{manifest.json, environment.json, results.json, comparison.json, logs/}`.

- **Exact vs Numerical vs Semantic vs Analytical** (§20) distinguished in `ReproductionScore` 6-dim (`execution/numerical/statistical/evidence/semantic/overall`) + `by_level L0..L5` (§21) from `reproducibility.py` (`L0 request / L1 code lenient / L2 data hash / L3 env / L4 trajectory / L5 conclusion ±20%`). Live `reproduction/v2` and `reproduction/benchmark` (50/100) fresh-twice `overall 1.0` on deterministic stub (see `reproduction/` ignored artifacts, `docs/v3/REPRODUCTION.md`).

External validation: `dsa demo` (§40/47) one-command `Demo Dataset → Analysis → Evidence → Report` into `demo/runs/demo` and `dsa external-validation` (§42 `Cold/First Launch/Demo/Benchmark` timings) — see `docs/v3/EXTERNAL_VALIDATION.md` (§39–42) and `demo/README.md`. Checklist `fresh_machine_checklist` documents Linux/macOS tested, Windows explicitly `NOT tested` (§41).

---

## Limitations

Per §62/§50: synthetic benchmark leakage risk, single-method bias mitigated by `acceptable_*` (§16), selection/confirmation bias, LLM stochasticity, hardware cost (§75 non-zero), coverage islands (`mcp/server 51%` at `81%` total), Python sandbox in-process scope (§78), `ROADMAP.md` risks `R-01..R-10`. Human/statistical reviewers are `PENDING` for `benchmark 0.3.0` (seed 42 reproducible). V3.1 should add fresh-machine Windows testing and expand Parquet/Excel codec coverage (§8 R-08).

---

## Conclusion

V3.0 W1–W10 make Data Science Agent independently understandable (§2 North Star): any conclusion traces to `Evidence → Tool → Computation → Dataset` (§49 diagrams are version-controlled). All numbers are `Benchmark + Commit + Report` traceable (§45); results are `release/v3.0` immutable (§74). Remaining gates for `v3.0.0` formal release: `W11 Publication/Citation (§52–57 figure/table reproducibility, §56 manifest) + W12 release verification (dsa verify-release v3.0.0 §63)`.

---

## Appendix — Release & Evidence

| Artifact | Location | Gate |
|----------|----------|------|
| Benchmark v2 | `benchmarks/v2/catalog.json 0.3.0 (30/100/11, seed 42)` | `dsa 100/100 @1.00` |
| Baseline | `benchmarks/baseline/` (50/50 @1.00) | `docs/v3/V2_FINAL_BASELINE.md` §7 |
| Audit | `docs/v3/BENCHMARK_AUDIT.md` (Q1–Q10) | W2 |
| Reproduction | `reproduction/v2` + `ReproductionScore 6-dim` | W3 `docs/v3/REPRODUCTION.md` |
| Statistical | `evaluator_v2` + `S01–S10` | `docs/v3/STATISTICAL_EVALUATION.md` |
| Reliability | 4 configs × 7 + §28–30 | `docs/v3/RELIABILITY.md` |
| Cross-model | 4 classes + 3 frontiers | `docs/v3/CROSS_MODEL.md` |
| Human eval | 11/100 samples + Kappa/Alpha | `human-eval/` + `docs/v3/HUMAN_EVALUATION_GUIDE.md` |
| External | `dsa demo` + metrics | `demo/` + `docs/v3/EXTERNAL_VALIDATION.md` |
| Release eng | `ROADMAP/CITATION/SECURITY/CONTRIBUTING` | `docs/v3/V2_FINAL_BASELINE.md` §13–15 |

Gates (§59): `pytest 155 / mypy 92 clean / ruff All checks passed / cov 81% (4597 stmts) / npm build 13/13 / compose valid / security 23 / MCP 7` — `dsa verify-release v3.0.0` is W12.
