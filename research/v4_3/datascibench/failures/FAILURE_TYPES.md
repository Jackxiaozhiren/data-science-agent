# Failure Types — DataSciBench full run (V4.3 W3 §44, W6 input)

> **Source:** `benchmarks/external/datascibench/results/raw_runs.json` step-level
> parse (materialized `logs.txt` plan markers). Describes **tool behavior**, not
> benchmark correctness (GT absent — nothing scored).

## Step-level failures

| Failure | Steps | Trigger | Agent decision | Observed | Benchmark coverage |
|---------|------:|---------|----------------|----------|--------------------|
| `UnsupportedFormatError` (empty input) | 44 | `human_*` task dir has no data file (upstream ships `prompt.json` only) | passed directory path; `profile_dataset` correctly rejected | honest `failed` before evidence | **Benchmark-missing internally** — internal benchmarks always ship a data file; new external class |
| Tool execution errors on real data | 84 | statistical ops on empty/sparse inputs | attempted analysis anyway | error recorded per step | partially covered (see W6 proposal) |

## Task-level outcomes

45 `failed` = completed-but-unevaluated (GT absent). 0 `passed`, 0
`execution_error` (post-fix), 177 `UNSUPPORTED` (`dl_*` 10 no-GPU + `bcb*` 167
TMC-pending).

## Mapping to internal failure clusters (W6 §59)

- Empty-input rejection → **F-new (environment)**: invisible internally.
- Tool errors on degenerate inputs → F01 incorrect routing / S-domain mismatch
  family (see `benchmarks/v3/BENCHMARK_V3_PROPOSAL.md`).
- GT-missing unevaluated → environment failure (gated GT), not agent failure.

**Preservation rule (§17):** these failures are research evidence. Do not delete,
hide, rewrite, or sanitize them.
