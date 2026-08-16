# Independent Reproduction — V3 Phase C (W3)

> **Phase C · W3 Independent Reproduction** · Date: 2026-08-16 · Implements §17–21 · `reproduction/` harness

---

## 1. Commands (spec-faithful)

```bash
# Single-task reproduction (artifact-level)
dsa reproduce --run <run_id>        # via API run_id (uses experiment.json stored under artifacts/reports/<run_id>/)

# Benchmark reproduction (fresh ×2 + compare)
dsa --reproduce v2 --out reproduction/v2
dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --reproduce v2
dsa --catalog benchmarks/ds-agent-benchmark/catalog.json --reproduce benchmark
```

Actual implemented entry (workspace `dsa`):

```bash
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --reproduce v2 --out reproduction/v2
uv run dsa --reproduce benchmark
```

The harness runs **two fresh benchmark executions** (`first/` + `second/`), then compares per §19–21.

---

## 2. Output Structure (§18)

```
reproduction/
├── v2/
│   ├── manifest.json       # catalog_sha, datasets_sha, n_tasks, seed, python, platform
│   ├── environment.json    # python_version + platform + manifest
│   ├── results.json        # {first, second, reproduction_score}
│   ├── comparison.json     # {per_task[], reproduction_score, first_summary, second_summary}
│   ├── first/              # benchmark raw output (raw_runs/results/summary.json)
│   │   ├── raw_runs.json
│   │   ├── results.json
│   │   └── summary.json
│   ├── second/             # second fresh run
│   │   └── ...
│   └── logs/
│       ├── first_summary.json
│       └── second_summary.json
└── benchmark/
    └── ... (same for v1 50-task benchmark)
```

Existing per-run artifacts remain under `artifacts/reports/<run_id>/{experiment.json,reproduce.sh,analysis.ipynb}` via `dsa_evidence.repro`.

---

## 3. What Is Compared (§19)

| Dim | Check | How |
|-----|-------|-----|
| Task Success | `tool_calls[].status==ok` equality per task | `execution_match` |
| Statistical Results | `expected_value` absent → not penalized; present → `compare_runs` conclusion tolerance | via `L5` |
| Numerical Metrics | `evidence_coverage` + `statistical_accuracy` aggregates | `reproduction_score.statistical/evidence` |
| Tool Trajectory | Tool name sequence equality | `L4_same_trajectory` |
| Evidence Graph | `insights/evidence` count within 20% | `L5_same_conclusion` |
| Artifacts | `reproduce.sh` + `analysis.ipynb` existence per run | part of `raw_runs[].run_result.tool_calls` |
| Report Structure | `report_markdown` presence in state | `task_success` |

Natural-language text is **not** required to be byte-identical.

---

## 4. Reproduction Classes (§20)

Mapped onto `ReproducibilityScore L0..L5`:

| Level | Meaning | Criterion |
|-------|---------|-----------|
| L0 | Same request | `user_query + dataset_path` equal |
| L1 | Same code | Package versions (lenient: always passes in harness) |
| L2 | Same data | `dataset_sha256` or `dataset_id` equal |
| L3 | Same env | `python_version[:20]` equal |
| L4 | Same tool trajectory | Tool name sequence equal and non-empty |
| L5 | Same conclusion | `insights` and `evidence` counts within 20% |

`level` = highest `L` whose all prior Ls passed; `score` = fraction of levels passed (`Σ/6`).

---

## 5. ReproductionScore (§21)

Per-task score: `ReproducibilityScore {level, score, details{ L0..L5_* }}` from `dsa_evidence.reproducibility.compare_runs`.

Aggregate (stored in `results.json` / `comparison.json`):

```json
{
  "execution": 1.0,     // per-task execution_match rate
  "numerical": 1.0,     // tasks with score >= 0.5
  "statistical": 1.0,   // first.summary.statistical_accuracy
  "evidence": 1.0,      // first.summary.evidence_coverage
  "semantic": 1.0,      // trajectory_match rate
  "overall": 1.0,       // mean per-task score
  "method": "compare_runs L0=L1 (code lenient), L2 data hash, L3 env, L4 trajectory, L5 conclusion (insights/evidence ±20%)",
  "by_level": { "L0":0, "L1":0, "L2":0, "L3":0, "L4":0, "L5":1.0 }
}
```

`overall 1.0` means every task reached `L5` on two fresh runs (current `v2 100/100` behavior: deterministic tool selection → identical trajectories and conclusions).

Live run (100 tasks, `reproduction/v2`):

```
Overall: 1.0  execution:1.0  trajectory:1.0
```

Stored in `reproduction/v2/results.json` + `comparison.json` (per-task `L_level/score/details` for reviewer).

---

## 6. Reproducing Results (§18–19 “fresh” loop)

```
Developer Run  →  Archive (results.json/summary.json under reproduction/v2/first)
       → Fresh (second fresh run into reproduction/v2/second)
       → Compare (per-task L0..L5 + aggregate 6-dim score)
```

Re-running `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --out reproduction/v2 --reproduce v2` reproduces the same `overall 1.0` on this codebase (heuristics are deterministic, seed 42).

---

## 7. Limitations & Next

* `L1` is currently lenient (always `true`) because `experiment.json` package versions are not persisted into `raw_runs[].run_result`; a future iteration can persist `experiment.json` into the benchmark harness before comparison.
* `reproduction/` is `.gitignore`d (like `artifacts/`) — it is **generated, not committed**; CI can regenerate and compare.
* `dsa reproduce --run <run_id>` (single-run replay via stored `experiment.json`) is documented but delegated to `artifacts/reports/<run_id>/reproduce.sh` + `analysis.ipynb` today; a direct `dsa` subcommand for that path is deferred to Phase H.
