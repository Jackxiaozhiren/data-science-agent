# Benchmark Leaderboard

A public, reproducible comparison surface for **validated Data Science Agent benchmark submissions**.

The leaderboard is generated from [`leaderboard.json`](leaderboard.json). The Markdown table is deterministic and must stay synchronized with the JSON source of truth.

> A high score is not accepted on prose alone. Submissions must identify the exact system version, commit, benchmark version, model/configuration, and reproducible metrics.

## Current validated submissions

<!-- leaderboard:start -->

| Rank | System | Version | Benchmark | Model | Task success | Statistical | Evidence | Reproducibility | Latency | Cost |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | DSA | `3.0.0` (`9ea647f`) | `0.3.0` | `stub/small` | 100.0% | 100.0% | 100.0% | 100.0% | 2200 ms | $0.0000 |

<!-- leaderboard:end -->

## Submission contract

Each entry in `leaderboard.json` must provide:

```json
{
  "system_name": "DSA",
  "version": "3.0.0",
  "commit": "9ea647f",
  "benchmark_version": "0.3.0",
  "model": "stub/small",
  "task_success_rate": 1.0,
  "statistical_accuracy": 1.0,
  "evidence_coverage": 1.0,
  "reproducibility": 1.0,
  "latency_ms": 2200,
  "cost_usd": 0.0
}
```

Rates must be between `0` and `1`; latency and cost must be non-negative. Ranking is deterministic: task success → statistical accuracy → evidence coverage → reproducibility → latency → cost.

## Contributing a result

1. Run the versioned benchmark from a clean environment.
2. Preserve the exact commit, benchmark version, model/configuration, seed, and raw artifacts.
3. Add the structured result to `leaderboard.json`.
4. Run:

```bash
python scripts/render_leaderboard.py --write
python scripts/render_leaderboard.py --check
```

5. Submit the JSON change, rendered README, and links to reproducible evidence in one pull request.

The repository CI verifies that the leaderboard schema is valid and that this table matches the JSON source.

## Dataset Hub

Benchmark datasets live under `benchmarks/v2/datasets/` and `examples/datasets/`. Dataset contributions must include clear license/source/citation/hash/version metadata.

For the broader evaluation model, including the current benchmark-v2 reference commands, see [`docs/evaluation.md`](../../docs/evaluation.md).
