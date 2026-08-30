# DataSciBench External Evaluation Report (V4.3 Phase C, W3 §27)

> **Phase:** C — DataSciBench Integration (DATA_SCIENCE_AGENT_V4_3.md §22-27)
> **Spec:** W3 §22-27, §26 outcome taxonomy, §27 result report, §48 raw→analysis→artifact
> **Date:** 2026-08-28 · **Upstream pinned commit:** `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`
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

- [ ] Operator: accept HF gate for `zd21/DataSciBench`, place GT + input datasets into
      `.workspace/` (per `README.md`).
- [ ] Wire the original evaluator subprocess (`experiments/evaluate.py`) behind
      `adapter.evaluate()` (recorded in manifest as pending).
- [ ] Re-run with GT + evaluator → real scores, then re-populate this report's §1-2 with
      passed/failed counts and the §27-required table.
- [ ] Feed raw runs into Phase E `CROSS_BENCHMARK_MATRIX.md` (§33-37).
