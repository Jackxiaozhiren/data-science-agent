# Real-model evaluation

DSA is offline and deterministic by default. A real-model run must be enabled explicitly so benchmark results cannot accidentally mix the deterministic harness with external-model performance.

## What `real` means

With `DSA_LLM_MODE=real`, the agent planner calls a real model through the OpenAI Responses API. The remaining execution, evidence, critic, and report pipeline continues to use DSA's normal code and tools.

If a requested real-model call fails, DSA raises the real error by default. It does **not** silently substitute the stub provider. An explicit `DSA_LLM_FALLBACK=heuristic` is available for product experimentation, but runs using that fallback should not be published as pure real-model benchmark results.

## Recommended: manual GitHub Actions matrix

The repository includes `.github/workflows/real-model-evaluation.yml`, a `workflow_dispatch`-only workflow for running the four comparison variants under one pinned commit and model selection.

Before the first run, configure `OPENAI_API_KEY` as a GitHub Actions repository or environment secret. Do not paste the key into an issue, pull request, workflow input, command line, or benchmark artifact.

When dispatching **Real Model Evaluation**:

1. enter the exact OpenAI model ID to use for every variant;
2. keep `task_limit=5` for the first credentialed smoke test;
3. use `task_limit=0` only when you intentionally want the full catalog;
4. optionally enter the current input/output USD-per-million-token rates used for that run.

The workflow runs these variants with `fail-fast: false` so one failed row does not hide the state of the others:

- `dsa` with the evidence critic enabled;
- `dsa-no-critic` with the critic disabled;
- `llm-tools` with direct vanilla LLM + public analysis-tool execution;
- `llm-only` with deterministic dataset context and no executable tools.

Each matrix job pins `DSA_LLM_FALLBACK=error`, records the checked-out Git commit, and uploads its own artifact bundle. In addition to the normal benchmark files, `workflow_manifest.json` records the workflow run ID, exact model, variant, task limit, catalog SHA-256, aggregate dataset snapshot SHA-256, and explicit pricing inputs. Artifacts are retained for 30 days by default.

A blank pricing input is allowed for smoke testing. In that case DSA deliberately leaves `cost_usd` as `null`; do not describe that run as cost-complete or publication-ready.

## Run a real-model benchmark locally

For local development, keep the model selection explicit rather than relying on a long-lived default:

```bash
export OPENAI_API_KEY="..."
export DSA_LLM_MODE=real
export DSA_LLM_PROVIDER=openai
export DSA_OPENAI_MODEL="<exact-model-id>"
export DSA_GIT_COMMIT="$(git rev-parse HEAD)"
export DSA_EVIDENCE_CRITIC=on
export DSA_EVALUATION_VARIANT=dsa

dsa --limit 5 \
  --out benchmarks/ds-agent-benchmark/results/dsa \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

For a publishable run, remove `--limit` after the smoke test succeeds.

## Evidence-critic ablation

The evidence critic is enabled by default. To measure its contribution without changing the planner, tools, evidence collection, or report pipeline, repeat the same benchmark with only this setting changed:

```bash
export DSA_EVIDENCE_CRITIC=off
export DSA_EVALUATION_VARIANT=dsa-no-critic

dsa \
  --out benchmarks/ds-agent-benchmark/results/dsa-no-critic \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

For a fair A/B comparison, keep the provider, exact model, benchmark catalog, dataset snapshot, Git commit, model parameters, and pricing assumptions identical between the `on` and `off` runs. Do not mix heuristic fallback runs with pure real-model runs.

The benchmark manifest records:

- `evaluation_variant: dsa` when the critic is enabled;
- `evaluation_variant: dsa-no-critic` when it is disabled;
- `evidence_critic_enabled` and the raw `DSA_EVIDENCE_CRITIC` setting.

Disabling the critic is intended for evaluation ablation only, not as the normal product configuration.

## Vanilla LLM + tools baseline

This baseline deliberately does **not** call DSA's planner, evidence critic, retry loop, evidence bundle, or multi-agent orchestration. One model call selects a small number of existing analysis tools from their public input schemas, the runner executes those calls directly, and a second model call writes the answer from the tool results.

```bash
export DSA_LLM_MODE=real
export DSA_LLM_PROVIDER=openai
export DSA_OPENAI_MODEL="<exact-model-id>"
export DSA_EVALUATION_VARIANT=llm-tools
export DSA_GIT_COMMIT="$(git rev-parse HEAD)"

dsa \
  --out benchmarks/ds-agent-benchmark/results/llm-tools \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

The default baseline budget is three tool calls. Dataset-path inputs are injected by the runner rather than trusted from model output. Internal DSA-only tools such as evidence creation, critic validation, report generation, and artifact saving are not exposed to the baseline.

## LLM-only baseline

The LLM-only control receives the question plus a deterministic dataset context containing row/column counts, schema, and a fixed preview. It receives no Python, SQL, tool execution, retrieval, critic, or hidden ground truth.

```bash
export DSA_LLM_MODE=real
export DSA_LLM_PROVIDER=openai
export DSA_OPENAI_MODEL="<exact-model-id>"
export DSA_EVALUATION_VARIANT=llm-only
export DSA_GIT_COMMIT="$(git rev-parse HEAD)"

dsa \
  --out benchmarks/ds-agent-benchmark/results/llm-only \
  --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

The default preview is 20 rows. This is intentionally a non-executing control: execution-dependent benchmark metrics are not converted into synthetic successes just because the model returned prose. When publishing comparisons, describe this row as an LLM-only control rather than implying that agent execution metrics are semantic answer-accuracy metrics.

## Baseline controls

The following environment variables are recorded in `run_manifest.json` through `baseline_config` when a baseline is selected:

- `DSA_BASELINE_PREVIEW_ROWS` — default `20`, capped at `100`;
- `DSA_BASELINE_MAX_TOOL_CALLS` — default `3`, capped at `8`;
- `DSA_BASELINE_MAX_TOOL_OUTPUT_CHARS` — default `12000`.

For a fair matrix, hold these values fixed across repeated runs and publish them with the artifacts.

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
- baseline configuration, when applicable
- number of real model calls
- per-call response IDs and latency
- input, output, and total tokens
- explicit pricing assumptions, when supplied
- calculated cost, when pricing assumptions are supplied

`results.json` also embeds the same execution metadata alongside aggregate metrics. `raw_runs.json` retains the baseline final answer, parsed tool plan, dataset context, and executed tool outputs when a baseline is used.

The GitHub Actions workflow adds `workflow_manifest.json` so the catalog and dataset snapshot can be verified independently of mutable branch names.

## Publication rule

A result may be described as a real-model DSA or baseline result only when:

1. `llm_mode` is `real` or `openai`.
2. `provider` and `model` identify the actual external model.
3. `call_count` is greater than zero.
4. The run does not use an undisclosed heuristic fallback.
5. The evidence-critic setting and evaluation variant are disclosed.
6. Baseline configuration is disclosed when the variant is `llm-only` or `llm-tools`.
7. Raw benchmark artifacts and the Git commit are retained.
8. The catalog and dataset snapshot are frozen or cryptographically identified.
9. Cost claims include the explicit pricing assumptions used for that run.

The existing `stub/small` registry entry remains a harness-validation result, not a real-model quality comparison.

## Comparison matrix

Publish the following on the same frozen task set, evaluator, provider, exact model, and model configuration:

| Run | Purpose |
| --- | --- |
| DSA + real LLM | Full evidence-grounded system with LLM planning |
| Vanilla LLM + Python/tool execution | Measures orchestration/evidence value beyond basic tool use |
| LLM-only | Measures value added by executable tools |
| DSA without evidence critic | Ablates the evidence/validation layer |

Do not combine these into a public leaderboard until each row has reproducible provider, model, configuration, commit, latency, token, cost, and raw-artifact metadata.
