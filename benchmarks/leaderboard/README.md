# Reproducible Evaluation Registry

This directory is a public, reproducible registry of **validated Data Science Agent evaluation runs**.

It is intentionally not presented as an independent model-quality leaderboard yet. The current registry contains a deterministic `stub/small` harness-validation run, which is useful for regression testing and evaluator verification but should **not** be interpreted as evidence that DSA outperforms real LLM-powered systems.

The table is generated from [`leaderboard.json`](leaderboard.json). The Markdown table is deterministic and must stay synchronized with the JSON source of truth.

> A score is only meaningful with its exact system version, commit, benchmark version, model/configuration, seed, cost, latency, and reproducible artifacts.

## Current validated runs

<!-- leaderboard:start -->

| Rank | System | Version | Benchmark | Model | Task success | Statistical | Evidence | Reproducibility | Latency | Cost |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|
| 1 | DSA | `3.0.0` (`9ea647f`) | `0.3.0` | `stub/small` | 100.0% | 100.0% | 100.0% | 100.0% | 2200 ms | $0.0000 |

<!-- leaderboard:end -->

### How to read the current result

The `stub/small` row validates that the benchmark pipeline, scoring logic, evidence checks, and deterministic reproduction path behave as expected under a controlled test configuration.

It does **not** answer questions such as:

- how DSA performs with GPT, Claude, Gemini, or other real models;
- how DSA compares with a vanilla LLM + Python tool baseline;
- whether the evidence critic improves real-model reliability;
- what real-model quality/cost/latency trade-offs look like.

Those are the next comparison targets. Future real-model runs should be published here with raw artifacts and explicit provider/model configuration.

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

## Recommended real-model baseline matrix

For a credible public comparison, publish at least these configurations on the same frozen benchmark version:

| Configuration | What it tests |
|---|---|
| DSA + real LLM | End-to-end product quality |
| Vanilla LLM + Python/tool execution | Value added by DSA orchestration |
| LLM-only | Value of executed computation |
| DSA without evidence critic | Contribution of the evidence/critic layer |

Each real-model run should record provider, exact model name, temperature, seed where supported, token usage, cost, latency, commit SHA, benchmark version, and raw result artifacts.

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

The repository CI verifies that the registry schema is valid and that this table matches the JSON source.

## Dataset Hub

Benchmark datasets live under `benchmarks/v2/datasets/` and `examples/datasets/`. Dataset contributions must include clear license/source/citation/hash/version metadata.

For the broader evaluation model and current benchmark commands, see [`docs/evaluation.md`](../../docs/evaluation.md).
