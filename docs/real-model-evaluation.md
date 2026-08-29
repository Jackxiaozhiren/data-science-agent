# Real-model evaluation

DSA is offline and deterministic by default. A real-model run must be enabled explicitly so benchmark results cannot accidentally mix the deterministic harness with external-model performance.

## What `real` means

With `DSA_LLM_MODE=real`, the agent planner calls a real model through the OpenAI Responses API. The remaining execution, evidence, critic, and report pipeline continues to use DSA's normal code and tools.

If a requested real-model call fails, DSA raises the real error by default. It does **not** silently substitute the stub provider. An explicit `DSA_LLM_FALLBACK=heuristic` is available for product experimentation, but runs using that fallback should not be published as pure real-model benchmark results.

## Run a real-model benchmark

```bash
export OPENAI_API_KEY="..."
export DSA_LLM_MODE=real
export DSA_LLM_PROVIDER=openai
export DSA_OPENAI_MODEL=gpt-5.6-luna
export DSA_GIT_COMMIT="$(git rev-parse HEAD)"
export DSA_EVIDENCE_CRITIC=on

dsa benchmark \
  --limit 5 \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

For a publishable run, remove `--limit` after the smoke test succeeds.

## Evidence-critic ablation

The evidence critic is enabled by default. To measure its contribution without changing the planner, tools, evidence collection, or report pipeline, repeat the same benchmark with only this setting changed:

```bash
export DSA_EVIDENCE_CRITIC=off

dsa benchmark \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

For a fair A/B comparison, keep the provider, exact model, benchmark catalog, dataset snapshot, Git commit, model parameters, and pricing assumptions identical between the `on` and `off` runs. Do not mix heuristic fallback runs with pure real-model runs.

The benchmark manifest records:

- `evaluation_variant: dsa` when the critic is enabled;
- `evaluation_variant: dsa-no-critic` when it is disabled;
- `evidence_critic_enabled` and the raw `DSA_EVIDENCE_CRITIC` setting.

Disabling the critic is intended for evaluation ablation only, not as the normal product configuration.

## Record cost without hard-coding stale prices

Model pricing changes over time, so DSA does not embed a permanent price table in benchmark code. When publishing a run, record the price assumptions you used:

```bash
export DSA_INPUT_COST_PER_MILLION="<input price used for this run>"
export DSA_OUTPUT_COST_PER_MILLION="<output price used for this run>"
```

If both values are present, DSA computes `cost_usd` from actual API token usage. If they are absent, `cost_usd` remains `null` rather than inventing a number.

## Artifacts

A benchmark run writes the existing result files plus `run_manifest.json`. The manifest records:

- LLM mode
- provider and model
- optional Git commit
- fallback policy
- evaluation variant and evidence-critic setting
- number of real model calls
- per-call response IDs and latency
- input, output, and total tokens
- explicit pricing assumptions, when supplied
- calculated cost, when pricing assumptions are supplied

`results.json` also embeds the same execution metadata alongside aggregate metrics.

## Publication rule

A result may be described as a real-model DSA result only when:

1. `llm_mode` is `real` or `openai`.
2. `provider` and `model` identify the actual external model.
3. `call_count` is greater than zero.
4. The run does not use an undisclosed heuristic fallback.
5. The evidence-critic setting and evaluation variant are disclosed.
6. Raw benchmark artifacts and the Git commit are retained.

The existing `stub/small` registry entry remains a harness-validation result, not a real-model quality comparison.

## Next comparison matrix

Once the first real DSA run is reproducible, publish the following on the same task set and evaluator:

| Run | Purpose |
| --- | --- |
| DSA + real LLM | Full evidence-grounded system with LLM planning |
| Vanilla LLM + Python/tool execution | Measures orchestration/evidence value beyond basic tool use |
| LLM-only | Measures value added by executable tools |
| DSA without evidence critic | Ablates the evidence/validation layer |

Do not combine these into a public leaderboard until each row has reproducible provider, model, configuration, commit, latency, token, cost, and raw-artifact metadata.
