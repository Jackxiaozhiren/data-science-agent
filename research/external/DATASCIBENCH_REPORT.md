# DataSciBench External Evaluation Report (V4.3 Phase C, W3 §27)

> **Phase:** C — DataSciBench Integration (DATA_SCIENCE_AGENT_V4_3.md §22-27)
> **Spec:** W3 §22-27, §26 outcome taxonomy, §27 result report, §48 raw→analysis→artifact
> **Date:** 2026-08-28 (execution lane) · **GT-lane addendum:** 2026-09-05 (§9 below — first scored run)
> **Upstream pinned commit:** `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`
> **Runner:** DSA `AgentBackedRunner` (deterministic local pipeline, **no LLM key** — same surface as the V4.2 case studies)
> **Raw data:** `benchmarks/external/datascibench/results/raw_runs.json` (= `research/external/datascibench_results.json`)
> **Adapter:** `benchmarks/external/datascibench/adapter.py` · **Manifest:** `benchmarks/external/datascibench/manifest.json`

---

## 0. Executive summary (honest, §110)

The DSA **adapter pipeline executed all 45 supported DataSciBench tasks end-to-end in 5.8 s**
(45/45 `COMPLETED`). **No score is reported** because the ground truth (gated HF dataset
`zd21/DataSciBench`) is **not present** in this environment
(`GT_STATUS.txt: ground_truth_present: false`). Per §26, a completed-but-unevaluated run is
classified **`failed`** — not passed, and not silently excluded. This report therefore
documents **pipeline execution + honest failure reporting**, which V4.3 §89 explicitly values
above a fabricated high score.

**This is not a benchmark score.** The 45 `failed` outcomes mean *"evaluation not completed
because GT was absent"*, not *"the agent answered incorrectly"*. Treat any percentage derived
from these counts as meaningless until GT-driven evaluation runs (§110: low/dishonest scores
are the failure; honest execution is the deliverable).

---

## 1. Task success (§27 Task Success)

| Metric | Value | Note |
|--------|-------|------|
| Supported tasks | **45** (25 `human_*` + 20 `csv_excel_*`) | of 222 total at pinned commit |
| Runs executed | **45/45** | all reached the agent (`COMPLETED`) |
| Outcome: `passed` | 0 | GT absent — none evaluable |
| Outcome: `failed` | 45 | completed-but-unevaluated (§26) |
| Outcome: `unsupported` | 177 | 10 `dl_*` (no GPU surface) + 167 `bcb*` (TMC path pending) |
| Outcome: `execution_error` | 0 | after runner fix (see §6) |
| Wall time | 5.8 s | sequential, single process |

## 2. Category success (§27 Category Success)

| Category | Tasks | Outcome | Evidence (total) | Tool calls (total) | Median report |
|----------|-------|---------|------------------|--------------------|---------------|
| `human_*` | 25 | 25 failed (no GT) | 60 | 182 | 3,365 chars |
| `csv_excel_*` | 20 | 20 failed (no GT) | 63 | 139 | 3,739 chars |

Both categories exercised the full tool orchestration surface (profile / correlation / chart /
model). **No category was skipped.** Unsupported categories are reported in §5, never filtered.

## 3. Failure types (§27 Failure Types)

Because no GT evaluation ran, *task-level* failures are all of the same honest class
(*unevaluated*). At the **step level**, the agent's 321 tool calls split as:

| Step outcome | Count | Meaning |
|--------------|-------|---------|
| Tool executed / returned | 193 | successful tool invocation (stats, charts, profiles) |
| Tool error | 84 | tool raised during execution on real data |
| `UnsupportedFormatError` | 44 | task dir had **no data file** → agent passed a directory path (human_* tasks with empty `_pick_primary_input`) |

The 44 `UnsupportedFormatError` steps are a **real, honest signal**: upstream publishes
`prompt.json` only; the gated download carries the actual inputs. Without GT + inputs, DSA
analyzes an empty directory. This is exactly the "honest execution, no data" failure the
feasibility audit predicted, and it **will not disappear** until the operator places the gated
distribution (§23/§29).

## 4. Tool usage, latency, tokens, evidence coverage (§27)

- **Tool usage:** 321 tool calls across 45 tasks (median 7/task, range 3–12). Full DSA tool
  surface exercised: `profile_dataset`, `correlation_analysis`, `create_chart`,
  `statistical_test`, model training.
- **Latency:** wall 5.8 s for 45 tasks (~0.13 s/task). Per-run `latency_s` is `None` because
  the SDK `Analysis` dataclass does not expose `elapsed_s`; measured at the harness level
  instead (§41 records config; latency provenance is honest, not invented).
- **Token usage:** `0` — deterministic local pipeline, no LLM key (stub). Cloud cost `$0`.
- **Evidence coverage:** 33/45 tasks produced 2–5 evidence records (123 total); 12 tasks
  produced 0 (empty-input tasks that failed before evidence). All evidence carries
  confidence/validation metadata from the DSA evidence graph.

## 5. Unsupported tasks (§26, §27 Unsupported Tasks)

Reported with explicit reasons — **never silently excluded**:

| Reason | Count | Task prefix |
|--------|-------|-------------|
| `deep-learning task: DSA has no GPU training surface` | 10 | `dl_*` |
| `adapter v1 scope: evaluate_tmc (TMC) path not yet implemented` | 167 | `bcb*` |

Total 177 unsupported, 45 supported, 222 benchmark tasks. The `bcb*` TMC evaluation path and
`dl_*` GPU surface are **planned but not implemented** in adapter v1 — both are explicit
`UNSUPPORTED` reasons, not omissions.

## 6. Integrity & provenance (§16, §18, §19, §23, §48)

- **Original evaluator preserved (§16):** the adapter converts DSA output into
  `data/{task_id}/dsa_{run_id}/logs.txt` in the upstream `## Current Plan / ## Current Task`
  layout; the evaluator (`experiments/evaluate.py`) is never modified. Real evaluator
  subprocess scoring is **not wired yet** — it requires GT + `HF_TOKEN` (operator side).
- **Gold firewall (§19):** GT never enters `AgentTaskView`; `assert_gold_isolation` ran
  before every dispatch. 0 gold-key violations.
- **No redistribution (§23):** zero DataSciBench content committed into this repo; upstream
  has no LICENSE. `.workspace/` is git-ignored.
- **Manifest (§18):** `benchmarks/external/datascibench/manifest.json` records pinned commit,
  task counts, license status, evaluator version, integrity notes.
- **Raw→analysis pipeline (§48):** this report and `datascibench_results.json` are generated
  from `raw_runs.json` only. No number above was hand-edited.

## 7. Honest limitations

1. **No score.** GT absent ⇒ all 45 `failed`. Any "task success %" derived from these counts
   is meaningless and must not be quoted.
2. **Step-level failure counts** were parsed from materialized `logs.txt`; they describe tool
   behavior, not benchmark correctness.
3. **`dl_*` and `bcb*` not evaluated** — no claim is made about DSA on those tasks.
4. **Deterministic local pipeline** (stub LLM) — real model inference (OpenAI/Anthropic via
   DSA's provider layer) will produce different trajectories; this run measures the
   *adapter*, not model performance (§41/§42 repeated runs apply to real-model runs).
5. **Input data absent for `human_*` empty dirs** — the 44 `UnsupportedFormatError` steps are
   the predictable no-data failure; they are evidence of pipeline honesty, not DSA weakness.

## 8. Next steps (Phase C completion → Phase E/F)

- [x] Operator: accept HF gate for `zd21/DataSciBench`, place GT + input datasets into
      `.workspace/` (per `README.md`). **Done 2026-09-05** (gt/gt_data + hf_dataset present).
- [x] Wire the original evaluator subprocess (`experiments/evaluate.py`) behind
      `adapter.evaluate()` (recorded in manifest as pending). **Done 2026-09-05**
      (GT lane verified end-to-end; see §9).
- [x] Re-run with GT + evaluator → real scores, then re-populate this report's §1-2 with
      passed/failed counts and the §27-required table. **Done 2026-09-05** (§9).
- [ ] Feed raw runs into Phase E `CROSS_BENCHMARK_MATRIX.md` (§33-37).

---

## 9. GT-lane addendum — first scored run (2026-09-05, §129 honest low-score report)

> **What changed:** GT + input datasets placed in `.workspace/`; workspace venv
> completed for the original evaluator (pandas/matplotlib/sklearn/playwright/
> provider deps per metagpt 0.8.2 pins + a venv-only `sitecustomize` shim for the
> empty `volcenginesdkarkruntime 0.0.1` on py3.9 — benchmark untouched, §16);
> adapter CSV matcher fixed (`data_name` carries task_id, `task_name` is the
> metric group — prior runs parsed no score); driver checkpoints per task
> (`raw_runs.partial.jsonl`) after two SIGKILLs at 42/45.
> **Raw:** `benchmarks/external/datascibench/results/raw_runs.json` (45 records,
> per-run `score` = task Completion Rate). Analysis: `research/v4_3/generate_phase_f_results.py`
> (GT pass) → `research/v4_3/results/{processed,tables/​datascibench_gt_scores.md,figures/cr_distribution.png}`.

### 9.1 Scores (original evaluator, no tuning, no filtering)

| Lane | Scored | Passed (CR ≥ 0.5) | Pass rate (Wilson 95%) | Mean CR |
|---|---:|---:|---|---:|
| `human_*` | 24/25 | 0 | 0.000 [0.000, 0.138] | 0.048 (max 0.300, human_142) |
| `csv_excel_*` | 20/20 | 0 | 0.000 [0.000, 0.161] | 0.000 |
| **Total** | **44/45** | **0** | **0.000 [0.000, 0.080]** | **0.026** |
| human_7 | — | — | `execution_error` (OOM, see §9.3) | n/a |

Per §129 this low score is reported as-is: no test-set tuning, no hidden
failures, no evaluator modification, no skipped hard tasks.

### 9.2 Why so low — failure-cause taxonomy (from evaluator output, not speculation)

1. **Output-layout mismatch (dominant, adapter-side):** metric functions read
   exact filenames (`pd.read_csv("output.csv")`, `predictions.csv`, named PNGs)
   from the run dir; adapter v1 materializes trajectory → `logs.txt` + report
   but does not map agent artifacts onto those names. Example: csv_excel_0 —
   Data Completeness / Visualization / Report Completeness all `Error` on
   missing files. Fixing this is legitimate *output conversion* (§30-allowed)
   and is queued as adapter v2 scope — deliberately NOT done in this pass, so
   this baseline stays an honest pre-fix measurement.
2. **VLM-judge handicap (credential gap, not capability proof):** 3 tasks are
   VLM-only (`human_131/141/19` → structural 0 without an OpenAI key) and 9 are
   mixed (one VLM function each). Their 0s measure missing credentials.
3. **Stub pipeline:** deterministic local pipeline (no LLM) on a benchmark built
   for LLM agents; open-ended analysis vs exact-output scoring.
4. **New external class confirmed:** 44 empty-input `UnsupportedFormatError`
   steps from the execution lane are gone (inputs now placed), replaced by
   scored outcomes — the pipeline-honesty signal served its purpose.

### 9.3 human_7 — `execution_error` (environment, OOM)

79 MB `online_retail_II.xlsx` SIGKills the agent process on this 16 GB box
(exit 137; twice at 42/45 in full runs + once isolated; empty log, no run dir).
Recorded as `execution_error`, not a correctness verdict. No core hack for one
task (§51). Feeds Benchmark V3 proposal C4 (large-table handling).

### 9.4 Generalization gap (§56, now computable)

Internal 150/150 (Wilson 95% [0.975, 1.000]) vs external 0/44 (Wilson 95%
[0.000, 0.080]): **gap = 1.000, descriptive** (§53 caveat: closed exact-match
vs open GT-scored measure different constructs; see `CROSS_BENCHMARK_MATRIX.md`).
