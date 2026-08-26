# Benchmark

> Head: `benchmarks/v2/README.md` + `benchmarks/v2/catalog.json 0.3.0` + `docs/evaluation.md`.

## Required documentation (§50)

| §50 field | This repo |
|-----------|-----------|
| Dataset Sources | `benchmarks/v2/README.md` + `scripts/generate_benchmark_v2.py` (synthetic, `seed 42`) + `benchmarks/v2/datasets/` 30 CSVs |
| Dataset Licenses | `CC0` (synthetic) per-task `license` in `catalog.json` 0.3.0; real swaps record `THIRD_PARTY_LICENSES.md` |
| Task Generation | `generate_benchmark_v2.py` — 50 v1 verbatim + 50 new across 3 categories |
| Task Validation | `acceptable_* / forbidden_interpretation` per task (§16) |
| Gold Standards | `acceptable_method/acceptable_metrics/acceptable_interpretation/acceptable_evidence/forbidden_interpretation/evaluation_function` (§16), versioned `evaluator_v2` |
| Metrics / Scoring | `packages/evaluation/src/dsa_evaluation/metrics.py` + `statistical_eval.py` (10 dims S01–S10) |
| Limitations | `research/V3_RESEARCH_REPORT.md` Limitations + audit `PENDING` reviewers |
| Seed / HW / SW | `seed 42 / Python 3.12 / uv 0.11.7 / Node v24.15.0 / Darwin arm64 / uv.lock 114 / catalog sha c493bc69` |

Versioning (§72): `v2.0 → v2.1 → v3.0` (this is `0.3.0` catalog); results immutably tagged, `v3.0.1` for fixes.

## Run

```bash
uv run dsa --limit 50 --out /tmp/bench
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100 --out /tmp/v2-100
# 10 canonical tasks for README/docs showcase: §71 in research/V3_RESEARCH_REPORT.md
```
