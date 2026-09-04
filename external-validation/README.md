# External Validation Kit (V4.3 W8 §76)

> **Spec:** `DATA_SCIENCE_AGENT_V4_3.md` §76 — a validation kit a real independent
> reviewer can use **without internal project knowledge**.
> **Status:** `PENDING EXTERNAL ACTOR` (§75, §127) — the kit is prepared; **no
> independent human review has been conducted** (`NOT CONDUCTED`, §80). Nothing in
> this directory is a completed human study, and no reviewer data may be fabricated.

## What this kit is

Six self-contained files that let a third-party person install, exercise, and
evaluate **Data Science Agent** end-to-end, then return structured feedback:

| File | Purpose |
|------|---------|
| [INSTALL.md](INSTALL.md) | Install the published package and verify its provenance |
| [TASKS.md](TASKS.md) | Six concrete reviewer tasks (install → demo → case study → evidence → reproduction → provenance) |
| [RUBRIC.md](RUBRIC.md) | The seven evaluation dimensions (§78) with 1-5 anchored scales |
| [FEEDBACK_TEMPLATE.md](FEEDBACK_TEMPLATE.md) | The written feedback form |
| [RESULTS_SCHEMA.json](RESULTS_SCHEMA.json) | Machine-readable schema for the scores |

## Design rules honored by this kit

- **No internal knowledge required** (§76): tasks reference only the published PyPI
  package, the public repository, and their own outputs.
- **Blind review** (§77): reviewers are asked to rate **before** reading internal
  benchmark claims (`benchmarks/ds-agent-benchmark/results/`, `research/v4_3/`).
  Honest limitation: self-administered blinding is best-effort; a coordinator-held
  blinding protocol requires a real external actor (§75) and is `PENDING EXTERNAL ACTOR`.
- **No fake reviewers** (§80): no reviewer names, counts, scores, or agreement
  metrics exist anywhere in this kit. If several real reviewers eventually submit
  results, choose the agreement metric by score structure (§79): ordinal 1-5
  dimensions → Krippendorff's α (ordinal) or weighted Cohen's κ; report the choice
  and its rationale alongside the data.

## For reviewers

Start with [INSTALL.md](INSTALL.md), then [TASKS.md](TASKS.md), score with
[RUBRIC.md](RUBRIC.md), and submit via [FEEDBACK_TEMPLATE.md](FEEDBACK_TEMPLATE.md)
(+ one JSON per task set matching [RESULTS_SCHEMA.json](RESULTS_SCHEMA.json)).

## Owner checklist (once a real reviewer is available)

1. Send the reviewer the kit files only (no internal benchmark files).
2. Collect the filled template + JSON result files.
3. Store raw submissions under `research/v4_3/` with consent note and dates.
4. Compute agreement metrics only across **real** submissions; mark results
   `NOT CONDUCTED` until at least one genuine submission exists.
