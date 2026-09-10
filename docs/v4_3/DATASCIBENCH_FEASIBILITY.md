# Phase C Pre-Implementation — DataSciBench Feasibility Audit (V4.3 W3, §22-23, §29)

> **Phase:** C (Inspect step, before any adapter code)
> **Date:** 2026-08-28 · **Status:** audit complete — implementation gated on Phase A/B commits landing
> **Benchmark:** DataSciBench — An LLM Agent Benchmark for Data Science ([arXiv:2502.13897](https://arxiv.org/abs/2502.13897), Findings of ACL 2026; THUDM / Tsinghua KEG)
> **Artifacts:** [GitHub THUDM/DataSciBench](https://github.com/THUDM/DataSciBench) · [Project page](https://datascibench.github.io/) · GT dataset [HF zd21/DataSciBench](https://huggingface.co/datasets/zd21/DataSciBench)

---

## 1. §29 Feasibility Matrix

| Dimension | Finding | Classification |
|-----------|---------|----------------|
| Benchmark identity | Real, published (arXiv 2502.13897, ACL 2026 Findings), actively used (23 models evaluated) | ✅ verified |
| Task prompts | In-repo under `data/{task_id}/` (preprocessed via `notebooks/preprocess_prompt.ipynb`); categories include predictive modeling, data exploration, visualization, DL tasks | ✅ available, no registration |
| Ground truth | **Gated** HuggingFace dataset `zd21/DataSciBench` — must log in and accept conditions to download; README behind the gate is empty; 61 downloads/month | ⚠️ requires HF account + condition acceptance + token (env-provided only) |
| License (code) | **No LICENSE file, no license stated** in the GitHub repo — only a citation request | ⚠️ default all-rights-reserved; research execution is customary but redistribution of their content into this repo is NOT permitted (§23) |
| License (GT data) | Terms behind the HF gate — not reviewable pre-acceptance | ⚠️ unknown until access granted; must record before use |
| Evaluator | Original TFC framework (Task-Function-Code) + programmatic metrics + Completion Rate; invoked via `python -m experiments.evaluate` / `evaluate_tmc` / `evaluation_results.calculate_final_metric` | ✅ original evaluator usable per §16 |
| Evaluator coupling | Reference agent is a bundled MetaGPT "Data Interpreter"; evaluator input format is shaped to its multi-step outputs | ⚠️ adapter must convert DSA run output → their expected format (legitimate: output conversion, not task/evaluator modification) |
| Environment | MetaGPT + `requirements.txt` needed only for the reference agent, not for scoring; DL tasks may require wandb login + GPU | ⚠️ partial |
| Quirk | "Completion Rate" is capped at 0.5 when GT is absent — affects any task we cannot obtain GT for | must be recorded in results, not silently normalized |

## 2. Overall verdict (§29 vocabulary)

```text
PARTIALLY SUPPORTED
```

Implementable **with three conditions**, all satisfiable:

1. **GT access** — maintainer accepts the HF conditions once, stores the token in the environment (never in source; CI via secret). Adapter must fail honestly (`UNSUPPORTED`/`execution_error`) on missing token, never silently.
2. **License clarification** — open a polite upstream issue asking THUDM to state a license; until answered, this repo ships **zero** DataSciBench content (prompts referenced by commit hash + download command, not vendored), which §23 already requires.
3. **Output conversion layer** — DSA `ExternalRun` (evidence/report) → their evaluator's expected input format; conversion lives in the adapter, evaluator stays original.

Category-level expectation: DL tasks are likely `UNSUPPORTED` for DSA (GPU training surface absent) and **will be reported as such per §26** — expected to reduce raw Completion Rate honestly (§110: low score ≠ failure).

## 3. Phase C implementation plan (after commits land)

1. `benchmarks/external/datascibench/` — `adapter.py` (implements Phase B `ExternalBenchmarkAdapter`), `manifest.json` (§18), `README.md`, `LICENSE_NOTES.md` (this audit's license section, incl. upstream-license status), `results/`, `logs/` (§24).
2. Pin benchmark at a specific commit; record `benchmark_commit` + all §18 manifest fields per run; dataset hashes via `dataset_sha256`.
3. Task mapping table (§25): native task → DSA input → permitted tools → environment → output → evaluation, one row per attempted task; unsupported tasks get explicit `UNSUPPORTED` + reason.
4. Results: `research/external/datascibench_results.json` + `research/external/DATASCIBENCH_REPORT.md` (§27) — task/category success, failure types, tool usage, latency, tokens, evidence coverage, unsupported list. Generated from raw runs only (§48).
5. Integrity guards carried over from Phase B: `assert_gold_isolation` before every agent dispatch; `INTEGRITY_RULES` respected (no GT in agent runtime, no evaluator peeking, no retry-until-pass).

## 4. Honest limitations of this audit

- **Evaluator contract — VERIFIED 2026-08-28 (was: implementation-time unknown).** A read-only inspection of the pinned upstream checkout (`84ef3d4`, shallow clone outside the repo) confirmed: the original evaluator consumes run artifacts placed at `data/{task_id}/{model}_{run_id}/` containing a non-empty `logs.txt`; the Completion Rate metric (`src/evaluator/cr_evaluator.py`) parses a JSON list of plan steps between the `## Current Plan` / `## Current Task` markers; per-task metric definitions live at `metric/{task_id}/metric.yaml` (`TMC-list`); results aggregate via `evaluation_results/calculate_final_metric.py`. The adapter's output-conversion layer writes exactly this layout from DSA `ExternalRun`s — **conversion is feasible without modifying the evaluator** (§16 holds). Measured task counts at the pinned commit: `human_` 25, `csv_excel_` 20, `dl_` 10, `bcb*` 167 → 222 total.
- **Input datasets ride the gated distribution (discovered by smoke validation 2026-08-28).** The public repo ships only `data/{task_id}/prompt.json`; the data files the prompts reference (e.g. `campaign_data.csv`) are absent from it. A mechanical smoke run of `human_2` through the real adapter on the fetched workspace exercised the full pipeline (listing 222 tasks → dispatch → deterministic agent run → `logs.txt` conversion) and produced an **empty plan / honest `failed` outcome** — exactly as expected without data. No score was produced and none may be claimed until the operator places the gated download's input datasets and ground truth. Workspace `.workspace/` is now present (git-ignored) with `.upstream_commit` marker and `GT_STATUS.txt: ground_truth_present: false`.
- Web-surface audit only for licensing: no LICENSE upstream, HF GT terms behind the gate — both remain recorded unknowns pending upstream clarification.
- No DataSciBench content has been downloaded into or committed to this repository.
- Adapter v1 scope: `human_*` / `csv_excel_*` driven end-to-end; `dl_*` unsupported (no GPU surface, §26); `bcb*` pending the separate `evaluate_tmc.py` TMC path (reported with reason, never silently filtered). The evaluator subprocess wiring is exercised with the first real compute run (requires HF_TOKEN for GT).
