# Cross-Benchmark Matrix (V4.3 Phase E, W5 §33-37)

> **Phase:** E — Cross-Benchmark Scientific Evaluation
> **Spec:** W5 §33-37 · §34 cross-benchmark questions · §35 matrix · §36 Generalization Gap · §37 failure transfer
> **Date:** 2026-08-28
> **Sources:** internal benchmark summaries (`benchmarks/baseline/summary.json`, `benchmarks/v2/catalog.json`, `benchmarks/leaderboard/README.md`), DataSciBench full run (`research/external/datascibench_results.json`, `research/external/DATASCIBENCH_REPORT.md`), 8 case studies (`case-studies/*/outputs/summary.json`), Phase D feasibility audit (`docs/v4_3/DSAGENTBENCH_FEASIBILITY.md`).
> **Status (updated 2026-09-05):** DataSciBench column = **GT SCORED** — 44/45 scored,
> 0 passed (CR ≥ 0.5), mean CR 0.026 (see §3; canonical: `research/external/DATASCIBENCH_REPORT.md` §9).
> DSAgentBench = **NOT CURRENTLY SUPPORTED** (§29). Internal/real-world = V4.2 verified baselines.

---

## 1. The matrix (§35)

| Dimension | DSA Internal v1 | DSA Internal v2 | DataSciBench | DSAgentBench | Real-World Cases |
|-----------|-----------------|-----------------|--------------|--------------|------------------|
| **Benchmark** | `ds-agent-benchmark` | `benchmarks/v2` | THUDM/DataSciBench | vis-nlp/DSAgentBench | 8 case studies |
| **Tasks** | 50 | 100 | **45 supported / 222 total** | 275 (unreleased) | 8 open-ended |
| **Environment** | synthetic CSVs, closed SQL/stats | synthetic CSVs, 11 cats | file-based, original evaluator layout | notebooks/IDEs/terminals/OS (real computer) | open questions, real pipeline |
| **Task success** | 1.00 (50/50) | 1.00 (100/100) | **0.000 (0/44, Wilson 95% [0.000, 0.080])** — GT lane 2026-09-05 | n/a — not run | 1.00 (8/8 `COMPLETED`) |
| **Statistical accuracy** | 1.00 | 1.00 (S01–S10) | mean CR 0.026 (human_ 0.048/max 0.300; csv_excel_ 0.000) | n/a | not scored (open) |
| **Evidence coverage** | 1.00 | 1.00 | 33/45 tasks with 2–5 evidence (123 total) | n/a | 8/8 evidence-grounded |
| **Unsupported claim rate** | 0.06 | n/a | n/a (unevaluated) | n/a | soft failures recorded honestly |
| **Tool efficiency** | — | — | 321 calls / 45 tasks (median 7) | n/a | 5–9 calls / case |
| **Latency** | 47.92 ms mean | — | 5.8 s wall (45 tasks) | n/a | 0.04–1.33 s / case |
| **Cost** | $0 (stub LLM) | $0 (stub LLM) | $0 (stub LLM) | high (real-computer) | $0 (stub LLM) |
| **Unsupported tasks** | 0 | 0 | 177 (10 dl_* + 167 bcb*) | all 275 (unreleased) | 0 |

## 2. Cross-benchmark questions (§34)

| Question | Answer |
|----------|--------|
| Does 100/100 internal performance transfer externally? | **No — measured 2026-09-05.** Internal 1.00 (150/150) vs DataSciBench **0.000 (0/44, Wilson 95% [0.000, 0.080])**: gap = 1.000, descriptive (§3). Dominant causes: output-layout mismatch (adapter v1), VLM-judge credential gap, stub pipeline (§37). |
| Which task categories generalize? | **`human_*` partially (mean CR 0.048, max 0.300); `csv_excel_*` not at all (all 0.000).** Internally all 11 categories hit 1.00. |
| Which do not? | **`dl_*` and `bcb*` are UNSUPPORTED** by adapter v1 (no GPU surface / TMC path pending) — reported with reasons, not silently filtered (§26). |
| Which failures are invisible internally? | **The 44 `UnsupportedFormatError` steps** (empty-input `human_*` tasks) — internal benchmarks always ship a data file, so the "no data file" failure class never occurs internally. This is a **new external failure** (§37). |
| Does Evidence Grounding help externally? | **Not measured.** 33/45 tasks produced evidence; no GT to validate whether it reduced unsupported claims. |
| Does Critic improve external success? | **Not measured.** No ablation ran externally (Phase F, §40 configurations A–F). |
| Does Reproduction still work? | **Yes, at the pipeline level:** 45/45 runs reproducible on the same adapter+commit (see `run_eval.py`, pinned upstream commit). |

## 3. Generalization Gap (§36)

```
Generalization Gap = Internal Benchmark Score − External Benchmark Score
```

**Computed 2026-09-05** — external score now defined (GT lane). Per §36 the gap
is **not alone statistically meaningful**; accompanied by:

- **Confidence interval:** internal 150/150 Wilson 95% [0.975, 1.000]; external 0/44 Wilson 95% [0.000, 0.080] (Phase F §43, Wilson z=1.96)
- **Category breakdown:** human_ 0/24 (mean CR 0.048) vs csv_excel_ 0/20 (mean CR 0.000) — see §2
- **Failure analysis:** output-layout mismatch (dominant) + VLM-judge credential gap + stub pipeline (§37 below)

> **"DSA achieves 1.00 internally (150/150 v1+v2). Externally (DataSciBench GT lane,
> 44 scored): pass rate 0.000, mean CR 0.026 — gap = 1.000 (descriptive, §53 caveat:
> closed exact-match vs open GT-scored measure different constructs)."**

This replaces the pre-GT §110 posture above (kept in git history) — no fabricated transfer claim in either direction.

## 4. Failure transfer matrix (§37)

| Failure class | Known internally? | Observed externally? | Classification |
|----------------|-------------------|----------------------|----------------|
| Empty-input / missing data file (`UnsupportedFormatError`) | **No** | **Yes** (44 steps, `human_*` no-data tasks) | **New external failure** — invisible internally |
| Tool execution error on real data | Partially | Yes (84 steps) | Tool orchestration / statistical failure |
| GT-missing ⇒ unevaluated | No | Yes (all 45) | Environment failure (gated GT) |
| Unsupported task category | No | Yes (177) | Benchmark-coverage gap (dl_*, bcb*) |
| Planning failure | Not observed | Not observed | — |
| Evidence failure | Not observed | Not observed | — |

The dominant **new external failure** is the **empty-input class**: internal benchmarks always
ship a data file; DataSciBench publishes prompts without inputs, so the adapter must handle
"task dir has no data" — which DSA's `profile_dataset` correctly rejects (unsupported format).
This is pipeline honesty, not DSA weakness, and is the §37 "environment failure" sub-type.

## 5. Honest limitations

1. **DataSciBench column is now GT-scored (2026-09-05).** Low scores reported
   as-is per §129: 0/44 passed, mean CR 0.026. Pre-GT execution-only history kept in git.
2. **DSAgentBench column is NOT CURRENTLY SUPPORTED** (Phase D §28-32): artifacts unreleased +
   no real-computer surface. Nothing claimed.
3. **Internal 1.00 and Real 1.00 use different success definitions** (exact-match vs
   `COMPLETED`) — the V4.2 `benchmark_vs_real_world.md` §48 drift applies here too.
4. **csv_excel_ 0.000 conflates three causes** (output-layout mismatch + VLM-judge
   credential gap on 5 mixed tasks + stub pipeline) — see canonical report §9.2, not
   a single capability verdict.

## 6. Feed-forward to Phase F (§38-48)

- Populate §1 rows for DataSciBench with **GT-driven scores** once operator places GT + wires
  the original evaluator (`adapter.evaluate` subprocess).
- Compute Generalization Gap + binomial CI + category breakdown (§36, §43).
- Run ablation configs A–F (§40) on DataSciBench supported tasks for RQ2/RQ3 (evidence/critic
  contributions).
