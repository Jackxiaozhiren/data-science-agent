# Evaluation

> Canonical implementation: `packages/evaluation/src/dsa_evaluation/` (`evaluator_v2`, 10 dimensions, S01–S10)

## What the evaluation is for

DSA uses versioned, frozen benchmark suites to catch regressions and measure reproducibility across the analysis pipeline.

A benchmark score must always be interpreted together with the **model/configuration that produced it**. Deterministic stub runs are useful for validating the evaluator and orchestration harness, but they are not independent evidence of real-LLM model quality.

For public reporting, distinguish these two classes explicitly:

1. **Harness-validation runs** — deterministic/stub configurations used to verify scoring, tools, evidence, and reproduction behavior.
2. **Real-model evaluation runs** — runs backed by an identified provider/model/configuration with recorded cost, latency, commit, benchmark version, and raw artifacts.

Do not compare the two as if they measured the same thing.

## Framework

`EvaluationResultV2` measures 10 dimensions:

- task success
- statistical quality
- tool use
- evidence quality
- unsupported claims
- code quality
- SQL quality
- reproducibility
- safety
- latency

The evaluator also tracks six analysis levels (`Tool → Numerical → Statistical → Interpretation → Evidence → Report`), category/difficulty breakdowns, and significance helpers such as `bootstrap_ci`, `mcnemar`, and `wilcoxon` in `significance.py`.

Evaluator versions must be recorded with every result. Results produced by different evaluator versions should not be compared without an explicit annotation and compatibility rationale.

## Statistical rigour

The v2 evaluator includes the S01–S10 taxonomy, covering failure modes from incorrect statistical testing through causal overreach and uncertainty omission.

## Reliability and cross-model work

Research artifacts include:

- reliability configurations such as `single`, `planner`, `planner+critic`, and `full`;
- ablation work in `research/V3_RESEARCH_REPORT.md`;
- cross-model analysis and Pareto-frontier work;
- human-evaluation methodology.

Where those artifacts rely on synthetic, stubbed, historical, or otherwise non-current configurations, they should be labeled accordingly when surfaced in product-facing documentation.

## Reproducing the evaluation harness

```bash
uv run dsa --limit 50
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100
uv run dsa --reproduce v2 --out reproduction/v2
```

The repository currently records deterministic benchmark-suite results such as `50/50` and `100/100`. These are useful for regression testing of the frozen suite and evaluator pipeline. **They should not be presented as real-model comparative performance unless the corresponding run identifies a real model/provider and reproducible configuration.**

## Public result registry

See the [Reproducible Evaluation Registry](https://github.com/Jackxiaozhiren/data-science-agent/tree/main/benchmarks/leaderboard) for validated result records and their provenance.

The current `stub/small` entry should be read as a harness-validation result. The next public-evaluation milestone is to add real-model baselines on the same frozen benchmark version.

Recommended minimum comparison matrix:

| Configuration | Purpose |
|---|---|
| DSA + real LLM | End-to-end product quality |
| Vanilla LLM + Python/tool execution | Incremental value of DSA orchestration |
| LLM-only | Value of executed computation |
| DSA without evidence critic | Contribution of evidence/critic safeguards |

For every real-model run, preserve at least:

- provider and exact model name;
- model parameters (temperature, seed where supported, relevant tool settings);
- DSA version and commit SHA;
- benchmark/evaluator version;
- token usage and cost;
- latency;
- raw outputs and evaluation artifacts.

This makes future claims independently inspectable instead of relying on headline percentages alone.
