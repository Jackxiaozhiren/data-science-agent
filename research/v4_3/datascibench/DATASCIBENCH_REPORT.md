# DataSciBench Report — V4.3 W3 §44

> **Spec:** V4.3 §44 (Task Success, Category Success, Failure Types, Tool Usage,
> Latency, Token Usage, Evidence Coverage, Unsupported Tasks).
> **Source:** generated from `benchmarks/external/datascibench/results/raw_runs.json`
> only (raw → analysis → artifact, §73). Index copy — canonical narrative:
> `research/external/DATASCIBENCH_REPORT.md`.
> **Date:** 2026-08-28 run · 2026-09-04 index.
> **Upstream pin:** `84ef3d4d94d7362a5149cf14a73dc168fc4f2f33` (see `UPSTREAM.md`).

---

## 1. Task Success

| Metric | Value | Note |
|--------|-------|------|
| Supported tasks | 45 (25 `human_*` + 20 `csv_excel_*`) | of 222 total |
| Runs executed | 45/45 | all reached the agent (`COMPLETED`) |
| `passed` | 0 | GT absent — none evaluable |
| `failed` | 45 | completed-but-unevaluated (§32 taxonomy) |
| `execution_error` | 0 | after runner fix |
| Score claimed | **NONE** | quoting a % here would be fabrication (§130) |

## 2. Category Success

| Category | Tasks | Outcome | Evidence | Tool calls |
|----------|-------|---------|----------|------------|
| `human_*` | 25 | 25 failed (no GT) | 60 | 182 |
| `csv_excel_*` | 20 | 20 failed (no GT) | 63 | 139 |

Both categories exercised the full tool surface. No category skipped.

## 3. Failure Types

| Failure | Steps | Cause |
|---------|------:|-------|
| `UnsupportedFormatError` | 44 | task dir had **no data file** (upstream ships `prompt.json` only; gated download carries inputs) |
| Tool execution errors on real data | 84 | statistical/tool orchestration behavior on empty-input tasks |

The 44 empty-input steps are a **new external failure class invisible internally**
(internal benchmarks always ship a data file) — recorded as pipeline honesty,
not DSA weakness. Details: `failures/FAILURE_TYPES.md`.

## 4. Tool Usage

321 tool calls across 45 tasks (median 7/task, range 3–12): `profile_dataset`,
`correlation_analysis`, `create_chart`, `statistical_test`, model training.

## 5. Latency

Wall 5.8 s for 45 tasks (~0.13 s/task, sequential single process). Per-run
`latency_s` is `None` (SDK `Analysis` exposes no `elapsed_s`); harness-level
measurement, honestly labeled.

## 6. Token Usage

`0` — deterministic local pipeline, stub LLM, no key. Cloud cost `$0`.
Real-model runs will differ; this run measures the **adapter**, not model skill.

## 7. Evidence Coverage

33/45 tasks produced 2–5 evidence records (123 total); 12 produced 0
(empty-input tasks failing before evidence). All evidence carries
confidence/validation metadata from the evidence graph.

## 8. Unsupported Tasks (§40 — retained, never silently excluded)

| Reason | Count | Prefix |
|--------|------:|--------|
| No GPU training surface | 10 | `dl_*` |
| TMC (`evaluate_tmc.py`) path not in adapter v1 | 167 | `bcb*` |

Total: 177 unsupported / 45 supported / 222 benchmark tasks.

## 9. Integrity (§29–§34)

- Original evaluator only, never modified; adapter converts output layout.
- Gold firewall: GT never enters `AgentTaskView`; 0 violations.
- No redistribution (upstream unlicensed; GT gated).
- Pilot-first honored: representative 45-task pilot across categories before
  any full-222 decision (§41–§43: full run deferred until GT lane wired).

## 10. Limitations

1. No score (GT absent). 2. Step counts describe tool behavior, not correctness.
3. `dl_*`/`bcb*` unevaluated. 4. Stub LLM — adapter measurement, not model
benchmark. 5. Empty-input failures expected until gated inputs placed.
