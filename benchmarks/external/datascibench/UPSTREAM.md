# DataSciBench — Upstream Record (V4.3 W3 §36)

> **Spec:** V4.3 §36 Upstream-First Policy — implementation must be preceded by
> this record. Companion to `docs/v4_3/DATASCIBENCH_FEASIBILITY.md` (feasibility
> audit) and `benchmarks/external/datascibench/manifest.json` (pinned provenance).
> **Date:** 2026-08-28 (feasibility audit) · **Re-stated here:** 2026-09-04 (prompt-completion pass).
> **Status:** All fields below verified live 2026-08-28 against the pinned upstream
> checkout (`84ef3d4d`, shallow clone outside the repo) unless marked otherwise.

---

## 1. Upstream Repository

- **URL:** https://github.com/THUDM/DataSciBench
- **Org:** THUDM / Tsinghua KEG
- **Pinned commit:** `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`
- **Commit date:** 2026-01-21
- **Pin method:** operator fetches the pinned tarball into git-ignored
  `benchmarks/external/datascibench/.workspace/` (see `README.md` Step 1);
  nothing from upstream is vendored into this repository (§37 no-fork-drift).
- **Project page:** https://datascibench.github.io/

## 2. Paper

- **Title:** DataSciBench — An LLM Agent Benchmark for Data Science
- **Identifier:** arXiv:2502.13897 (Findings of ACL 2026)
- **URL:** https://arxiv.org/abs/2502.13897
- **Attribution requirement:** upstream README requests citation of the paper;
  BibTeX is carried in the upstream README (not copied here to avoid drift —
  cite from the pinned checkout).

## 3. Benchmark Commit (frozen for this integration)

```text
benchmark_commit = 84ef3d4d94d7362a5149cf14a73dc168fc4f2f33
benchmark_version = 1.0 (adapter manifest label)
task_count_at_pin = 222 (human_* 25 + csv_excel_* 20 + dl_* 10 + bcb* 167)
```

Any re-pin requires a manifest update + re-run; results are only comparable
within the same pin (§31 manifest).

## 4. License (code)

- **Finding:** **NO LICENSE stated upstream** — no `LICENSE`/`COPYING` file in
  the repository; About section names no license (verified 2026-08-28).
- **Legal default:** all rights reserved by the authors.
- **Consequence (binding, §37):** no DataSciBench prompt, metric, GT, or code
  file may be committed into this repository. Operator-side fetch only.
- **Open item:** file a polite upstream issue asking the authors to state an
  explicit license; update `LICENSE_NOTES.md` when answered.
- **Details:** `benchmarks/external/datascibench/LICENSE_NOTES.md`.

## 5. Data License (ground truth + input datasets)

- **Ground truth dataset:** HuggingFace `zd21/DataSciBench` — **GATED**.
  Download requires an HF account + accepting displayed conditions; terms are
  not visible before acceptance, recorded as **unknown** until a maintainer
  accepts and restates them.
- **Input datasets:** ride the gated distribution — the public repo ships only
  `data/{task_id}/prompt.json`; referenced data files (e.g. `campaign_data.csv`)
  are absent from it (discovered by smoke validation 2026-08-28).
- **Consequence:** without the gated download, runs complete mechanically but
  analyze no data (honest `failed` outcome, never a score).

## 6. Evaluation Methodology

- **Framework:** original TFC (Task-Function-Code) + programmatic per-task
  metrics + Completion Rate.
- **Evaluator entry points (pinned checkout):**
  - `experiments/evaluate.py` (CREvaluator; consumes run artifacts at
    `data/{task_id}/{model}_{run_id}/` containing non-empty `logs.txt` with a
    JSON plan-steps list between `## Current Plan` / `## Current Task` markers)
  - `experiments/evaluate_tmc.py` (TMC path, `bcb*` tasks — adapter v1 pending)
  - `evaluation_results/calculate_final_metric.py` (aggregation)
  - per-task metric definitions: `metric/{task_id}/metric.yaml` (`TMC-list`)
- **Quirk (must be recorded, not normalized):** Completion Rate is capped at
  0.5 when GT is absent.
- **Rule (§33):** the evaluator is used **unmodified**; the adapter only
  converts DSA `ExternalRun` output into the expected `logs.txt` layout (§30).

## 7. Environment Requirements

| Requirement | Needed for | DSA status |
|---|---|---|
| Python 3.12 (DSA runtime) | adapter + agent | ✅ native |
| Upstream checkout at pinned commit (operator `.workspace/`) | task prompts + evaluator | ⚠️ operator step (network) |
| Gated HF dataset (input data + GT) | scoring | ⚠️ operator step (account + acceptance) |
| MetaGPT + upstream `requirements.txt` | reference agent only, not scoring | not needed for DSA runs |
| GPU / wandb login | `dl_*` tasks | ❌ absent → `dl_*` reported `UNSUPPORTED` |
| `evaluate_tmc.py` path | `bcb*` 167 tasks | ⏳ pending → reported with reason |

## 8. Task Structure

- **Layout:** `data/{task_id}/prompt.json` (+ gated data files at eval time).
- **Categories at pin:** `human_*` 25 (open prompts, some with no data file) ·
  `csv_excel_*` 20 · `dl_*` 10 · `bcb*` 167 → **222 total**.
- **Adapter v1 scope:** `human_*` + `csv_excel_*` driven end-to-end (45 tasks);
  `dl_*` → `UNSUPPORTED` (no GPU surface); `bcb*` → pending TMC path (reported
  with reason, never silently filtered, §40).
- **Task mapping (native → DSA):** per-task rows live in the run output
  (`results/raw_runs.json` entries carry `task_id`, `AgentTaskView`,
  `permitted_tools`, `environment`, outcome); semantics are never altered (§39).

## 9. Provenance pointers

- Adapter: `benchmarks/external/datascibench/adapter.py`
- Manifest: `benchmarks/external/datascibench/manifest.json`
- Feasibility: `docs/v4_3/DATASCIBENCH_FEASIBILITY.md`
- License: `benchmarks/external/datascibench/LICENSE_NOTES.md`
- Results: `research/external/DATASCIBENCH_REPORT.md` +
  `benchmarks/external/datascibench/results/`
