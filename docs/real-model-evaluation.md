# Real-model evaluation

DSA is offline and deterministic by default. A real-model run must be enabled explicitly so benchmark results cannot accidentally mix the deterministic harness with external-model performance.

## What `real` means

With `DSA_LLM_MODE=real`, the agent planner calls a real model through the OpenAI Responses API. The remaining execution, evidence, critic, and report pipeline continues to use DSA's normal code and tools.

If a requested real-model call fails, DSA raises the real error by default. It does **not** silently substitute the stub provider. An explicit `DSA_LLM_FALLBACK=heuristic` is available for product experimentation, but runs using that fallback should not be published as pure real-model benchmark results.

## Recommended: manual GitHub Actions smoke

The repository includes `.github/workflows/real-model-evaluation.yml`, a `workflow_dispatch`-only workflow for the first credentialed four-way smoke test.

The workflow intentionally has **no user-supplied workflow inputs**. The model, pricing assumptions, task limit, and comparison variants are pinned in version-controlled YAML so a benchmark run cannot be silently changed by free-form dispatch data.

Before the first run, configure `OPENAI_API_KEY` as a GitHub Actions repository or environment secret. Do not paste the key into an issue, pull request, workflow input, command line, or benchmark artifact.

Then dispatch **Real Model Evaluation Smoke** from the Actions tab. One dispatch runs these four variants independently:

- `dsa` with the evidence critic enabled;
- `dsa-no-critic` with the critic disabled;
- `llm-tools` with direct vanilla LLM + public analysis-tool execution;
- `llm-only` with deterministic dataset context and no executable tools.

The smoke workflow currently pins:

- model: `gpt-5.6-luna`;
- task limit: `5` tasks per variant;
- input price assumption: `$0.20` per 1M tokens;
- output price assumption: `$1.20` per 1M tokens;
- pricing reference date: `2026-08-29`.

Those rates match the OpenAI API model page on the pricing reference date: <https://developers.openai.com/api/docs/models/gpt-5.6-luna>.

The workflow also pins the checkout and setup actions by commit SHA, disables persisted checkout credentials, uses `DSA_LLM_FALLBACK=error`, and exposes `OPENAI_API_KEY` only to the benchmark execution step.

Each variant job uploads its own artifact bundle. In addition to the normal benchmark files, `workflow_manifest.json` records the workflow run ID, exact Git commit, model, variant, task limit, catalog SHA-256, aggregate dataset snapshot SHA-256, pricing assumptions, and pricing reference date. Artifacts are retained for 30 days by default.

This workflow is a **credentialed smoke test**, not a publishable leaderboard run. After all four smoke rows complete successfully and the artifacts are reviewed, add the full-catalog run in a separate reviewed change while keeping the same exact model, evaluator, dataset snapshot, and documented pricing assumptions.

When OpenAI pricing or the chosen benchmark model changes, update the pinned workflow in a pull request before running new publication candidates. Do not retroactively rewrite the pricing assumptions of existing artifacts.

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

For a publishable run, remove `--limit` only after the smoke test succeeds and retain the exact model and pricing assumptions used for the full run.

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

For a fair comparison, hold these values fixed across repeated runs and publish them with the artifacts.

## Pricing assumptions

Model pricing changes over time. The benchmark code therefore does not embed a permanent provider price table.

For local runs, explicitly record the rates used for that run:

```bash
export DSA_INPUT_COST_PER_MILLION="<input price used for this run>"
export DSA_OUTPUT_COST_PER_MILLION="<output price used for this run>"
```

If both values are present, DSA computes `cost_usd` from actual API token usage. If they are absent, `cost_usd` remains `null` rather than inventing a number.

For the GitHub Actions smoke workflow, the exact model, rates, and pricing reference date are pinned in version control. Existing artifacts keep their historical assumptions even if provider pricing changes later.

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

The GitHub Actions smoke workflow adds `workflow_manifest.json` so the catalog, dataset snapshot, pinned model, and pricing snapshot can be verified independently of mutable branch names.

## Automated matrix validation

The four variant directories can be checked as one comparison unit with the built-in validator:

```bash
uv run python -m dsa_evaluation.publication \
  benchmark-artifacts \
  --json \
  --output benchmark-artifacts/matrix_validation.json
```

The validator checks that all four rows retain the required artifacts and agree on the workflow run, Git commit, exact model, catalog hash, dataset snapshot hash, task scope, task limit, and pricing snapshot. It also verifies real-model mode, provider, fallback policy, evaluation labels, critic state, positive call count, response IDs, latency, token usage, explicit pricing, computed cost, raw-run count, and baseline controls.

The report intentionally separates two concepts:

- `matrix_valid=true` means the four rows are internally consistent and suitable for smoke/reproducibility review;
- `publication_ready=true` additionally requires a valid matrix with `scope=full`.

Therefore the current five-task workflow can pass matrix validation while still returning `publication_ready=false`. That is expected and prevents smoke artifacts from being promoted to the public leaderboard.

For a publication gate, use:

```bash
uv run python -m dsa_evaluation.publication \
  benchmark-artifacts \
  --require-publication-ready
```

The GitHub Actions smoke workflow runs the matrix validator automatically after all four rows, uploads `matrix_validation.json` as a separate artifact, and fails the workflow if either a comparison row or the validator fails.

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
9. Cost claims include the explicit pricing assumptions and pricing reference date used for that run.
10. Public comparison rows use the full frozen task set; five-task smoke artifacts are labeled as smoke validation only.
11. The four-row validator reports `matrix_valid=true`.
12. Public leaderboard promotion additionally requires `publication_ready=true`.

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
