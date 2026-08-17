# Reproduction Showcase — V3 §70

> **One complete case** `Run A → Archive → Fresh Environment → Run B → Comparison` — `What Matched / What Differed / Why / ReproductionScore`.

## Case: `dsa --reproduce v2 --out reproduction/v2` (fresh twice, 100 tasks, seed 42)

```
Run A (first)
  catalog benchmarks/v2/catalog.json 0.3.0 (30/100/11, seed 42, sha c493bc69)
  datasets benchmarks/v2/datasets (30 CSVs, CC0)
  out reproduction/v2/first/{results.json, summary.json, raw_runs.json}
  ↓ Archive (manifest + environment)
manifest.json {catalog_sha, datasets_sha, n_tasks 100, seed 42, python 3.12, platform Darwin arm64}
environment.json {python_version, platform, manifest}
  ↓ Fresh Environment (no private dataset, no key, local-first stub/small)
Fresh Clone → Fresh Install (uv sync --dev, 114 packages, uv.lock)
  ↓ Run B (second)
reproduction/v2/second/{results.json, summary.json, raw_runs.json}
  ↓ Comparison
comparison.json {per_task: [{L_level, score, execution_match, trajectory_match, conclusion_match, details: {L0..L5}}], reproduction_score: {execution,numerical,statistical,evidence,semantic,overall + by_level L0..L5}}
logs/{first_summary.json, second_summary.json}
```

## What Matched

| Dimension | Value | Note |
|-----------|-------|------|
| execution | 1.0 | `RR tool_calls ok` match per task |
| trajectory | 1.0 | `compare_runs` L4 seq identical (deterministic planner + tool order) |
| numerical | 1.0 | scores ≥0.5 per task (heuristic threshold, see `cli.py`) |
| statistical | 1.0 | `evaluator_v2 statistical_accuracy` stable |
| evidence | 1.0 | `evidence_coverage` 1.0 |
| semantic | 1.0 | `conclusion_match` (insights ±20%, `L5`) |
| **overall** | **1.0** | mean of `compare_runs` scores (100 tasks) |
| by_level | `L0..L5: 1.0 each` | All levels `1.0` (fresh twice deterministic) |

## What Differed

- `elapsed_ms` per task varies by `~5–20ms` (non-semantic); artifacts paths (`/tmp/v2-*` vs `reproduction/v2/*`) differ; `manifest` timestamps differ.

## Why

Deterministic pipeline: `seed 42` + `stub/small` LLM (no sampling) + `DuckDB/Polars` + stateless planner heuristics → identical tool sequences and computed `r=-0.057` etc. Real LLM runs would lower `overall` to `0.8–0.9`.

## ReproductionScore (§21)

```json
{"execution":1.0,"numerical":1.0,"statistical":1.0,"evidence":1.0,"semantic":1.0,"overall":1.0,
 "method":"compare_runs L0=L1 (code lenient), L2 data hash, L3 env, L4 trajectory, L5 conclusion (±20%)",
 "by_level":{"L0":1.0,"L1":1.0,"L2":1.0,"L3":1.0,"L4":1.0,"L5":1.0}}
```

## Run it

```bash
uv run dsa --reproduce v2 --out reproduction/v2
cat reproduction/v2/comparison.json | jq '.reproduction_score'
cat reproduction/v2/results.json | jq '.first.aggregate.task_success_rate'
uv run dsa --reproduce benchmark --out reproduction/benchmark  # v1 50 tasks, also 1.0
```

`reproduction/` is `.gitignore`d (generated), but `docs/v3/REPRODUCTION.md` (§17–21) and this showcase are the persistent record.
