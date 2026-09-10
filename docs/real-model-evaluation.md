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

## Spend cap (in-code guard)

`DSA_MAX_COST_USD` sets a hard per-process ceiling on real-model spend. The
provider prices each call from actual API `usage` × the explicit
`DSA_INPUT/OUTPUT_COST_PER_MILLION` rates, accumulates `spent_usd`, and
**refuses further calls** once the cap is reached (loud error, no silent stop).
Per-call `est_cost_usd` and cumulative spend land in the call log and provider
metadata, so every artifact is auditable. Without the env var, no cap applies —
always set it for credentialed runs, *in addition to* an OpenAI project-level
spend limit (defense in depth; the project limit is the binding one).

## Cost estimate (gpt-5.6-luna @ $0.20/$1.20 per M, 2026-08-29 pricing)

Measured call profile per task: DSA variants = 1 planner call (structured, max
3000 out); llm-tools = plan + answer; llm-only = 1 answer call. Typical usage
≈ 4k input + 1.5k output tokens/task (≈ $0.0026).

| Scope | Tasks | Expected | Upper bound (max tokens) | Suggested cap |
|---|---:|---:|---:|---:|
| 4-variant smoke (CI pinned) | 20 | ≈ $0.05 | ≈ $0.10 | `DSA_MAX_COST_USD=2` |
| Full internal (4 × 150) | 600 | ≈ $1.60 | ≈ $2.50 | `DSA_MAX_COST_USD=5` |

Estimates only — verify against the first smoke's recorded `cost_usd` before
scaling. Never run `scope=full` without a prior green smoke on the same commit.

## Free lanes ($0, no paid key)

Two providers, one class (`OpenAIChatProvider`, chat/completions +
`json_object` structured output, usage mapped incl. Ollama eval counts):

**A. Ollama, local (truly free, private, no signup).** Operator-side:
`ollama serve` + `ollama pull qwen3:8b` (≈5 GB). Then:

```bash
export DSA_LLM_MODE=real DSA_LLM_PROVIDER=ollama DSA_OLLAMA_MODEL=qwen3:8b
export DSA_LLM_FALLBACK=error
export DSA_EVALUATION_VARIANT=dsa DSA_GIT_COMMIT="$(git rev-parse HEAD)"
dsa --limit 5 --catalog benchmarks/ds-agent-benchmark/catalog.json \
  --datasets benchmarks/ds-agent-benchmark/datasets
```

Do NOT set `DSA_MAX_COST_USD=0` here: with a zero cap the provider refuses
before the first call (0 >= 0). Local inference has no metered cost; leave
the cap unset (or set a positive value — untracked $0 spend never reaches it).

16 GB machines run 8B Q4 models comfortably; expect slower and weaker plans
than frontier APIs. Without the daemon/model, calls fail loudly with
connection errors — never silently stubbed.

**B. Hosted free tiers** (e.g. Gemini/Groq OpenAI-compatible endpoints; free
key from the vendor, own rate limits apply):

```bash
export DSA_LLM_MODE=real DSA_LLM_PROVIDER=openai-compat
export DSA_OPENAI_COMPAT_BASE_URL="https://<vendor>/v1"  # vendor's OpenAI-compat URL
export DSA_OPENAI_COMPAT_API_KEY="<free key>"
export DSA_OPENAI_COMPAT_MODEL="<exact model id>"
```

**Labeling rule (non-negotiable):** free rows are valid for *within-model*
comparisons (dsa vs dsa-no-critic vs llm-tools vs llm-only on the SAME
provider+model — RQ2–RQ4 ablations) but must never merge with, or compare
against, paid-lane rows. The publication validator still requires the paid
`openai` lane, so free matrices cannot promote to leaderboard claims — by
design, not oversight. Every artifact records its real provider+model.

## Dry-run verification (2026-09-05, $0 spent)

All four variants executed locally with the stub provider (2 tasks each):
`dsa` 1.0, `dsa-no-critic` 1.0, `llm-tools` 0.0, `llm-only` 0.0 (stub baselines
correctly score 0 — stub echoes, executes nothing). Workflow manifests written
per variant; the matrix validator **correctly rejected** the stub matrix
(`matrix_valid=false`: not real-model mode, zero token usage, pricing
mismatch). The machinery cannot be gamed with stub runs — verified, not assumed.

## Attempt log (honest, no spend without credits)

- **2026-09-08, CI run 34190135991** (triggered manually, pinned workflow):
  all four rows executed, **0.0 success everywhere** — OpenAI API returned
  HTTP 429 `credit_balance_exhausted` ("You have no credits remaining").
  **$0 spent.** Machinery validated end-to-end (key wiring, real-mode error
  propagation without stub fallback, per-row artifacts, matrix validator
  correctly reporting `matrix_valid=false`). Next attempt requires funded
  credits on the OpenAI org; re-dispatch the same pinned workflow unchanged.
- Prior attempts 2026-08-30 (runs 33291103265, 33297462359): `startup_failure`
  before any row executed (workflow-level, no model calls, $0 spent).

## Free-lane smoke results (2026-09-09, ollama qwen3:8b, $0)

First within-model 4-way comparison, internal v1 5-task smoke
(`--limit 5`, think on, temperature 0.1, `DSA_MAX_COST_USD` unset — local
inference is unmetered). Planner needed `think` (without it qwen3:8b echoes
the schema), one validation retry, and a 600 s timeout; all three are now
defaults for the ollama lane with tests.

| Variant | Pass | Wilson 95% | Repeats |
|---|---:|---|---|
| dsa | 0.60, 0.60, 0.60, **1.00** | pooled 12/20 [0.39, 0.81] | ×4 |
| dsa-no-critic | 1.00 ×3 | pooled 15/15 [0.80, 1.00] | ×3 |
| llm-tools | 0.20 | [0.04, 0.62] | ×1 |
| llm-only | 0.00 | [0.00, 0.43] | ×1 |

**Correction appended same day — do NOT read a critic effect into the table.**
All dsa-variant failures were plan-validation flakes; no-critic had zero in 15
runs (naively p≈0.0005). A follow-up dsa repeat run *after* the no-critic block
scored **1.0**, implicating environmental drift over time (server warmup), not
the critic flag — which touches nothing in the plan path (verified by code
inspection: planner/provider read no critic setting). The dsa-vs-no-critic gap
is therefore **time-confounded, inconclusive**. Lesson recorded: variant
comparisons on stochastic local models require **interleaved ABAB order**,
never all-of-A-then-all-of-B. RQ3 stays open pending an interleaved design.
Rows labeled provider `ollama`, model `qwen3:8b`; never merged with paid-lane rows.

## Free-lane smoke results (2026-09-10, Groq `openai/gpt-oss-120b`, $0)

Second within-model 4-way comparison, internal v1 5-task smoke
(`--limit 5`, `DSA_LLM_PROVIDER=openai-compat`,
`DSA_OPENAI_COMPAT_BASE_URL=https://api.groq.com/openai/v1`,
`DSA_LLM_FALLBACK=error`, `DSA_MAX_COST_USD=2`, commit `712e9201`).
All four rows share the task sequence `eda-01..eda-05`, real mode, and zero
non-rate-limit errors; every call carries a Groq `chatcmpl-*` response ID.
Spend $0 (free tier, `cost_usd` unpriced by design).

| Variant | Pass | Clean (excl. 429s) |
|---|---:|---|
| dsa | 5/5 (1.00) | 5/5, zero errors |
| dsa-no-critic | 5/5 (1.00) | 5/5, zero errors (after one cooldown re-run; first attempt had 1× TPM 429) |
| llm-tools | 1/5 (0.20) | 1/1 clean success; 4× HTTP 429 TPM-429 (free-tier 8000 tokens/min ceiling) |
| llm-only | 0/5 (0.00) | 5/5 clean, honest control zero |

Reading (honest, n=5 each): the DSA pipeline rows are clean 5/5 while both
vanilla baselines score ~0 — but **no ablation claim is supported**.
dsa and dsa-no-critic tie at ceiling (no critic signal at n=5 EDA), and the
llm-tools row is **incomplete by infrastructure, not capability**: its fast
plan+answer bursts exceed Groq's 8000 TPM free limit, while the slower DSA
rows spread the same token budget over minutes and stay under it. A paced
runner (honor `retry-after`) would be needed for a fair llm-tools row; that
is a product change, out of scope for this smoke. Rows labeled provider
`openai-compat`, model `openai/gpt-oss-120b`; never merged with paid-lane
rows. Local rows carry no `workflow_manifest.json`, so the publication
validator reports `matrix_valid=false` for them by design.

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

The validator checks that all four rows retain the required artifacts and agree on the workflow run, Git commit, exact model, catalog hash, dataset snapshot hash, task scope, task limit, and pricing snapshot. It also verifies real-model mode, provider, fallback policy, evaluation labels, critic state, positive call count, response IDs, per-call latency and token usage, aggregate call rollups, explicit positive pricing, computed positive cost, raw-run count, and baseline controls.

The task set is also treated as provenance, not just a count. Every row must contain non-empty, unique task IDs in `raw_runs.json`, and all four rows must contain the same ordered task-ID sequence and the same `n_tasks`. A `scope=full` matrix is valid only with `task_limit=0`; the pinned smoke scope is valid only with `task_limit=5`.

The report intentionally separates two concepts:

- `matrix_valid=true` means the four rows are internally consistent and suitable for smoke/reproducibility review;
- `publication_ready=true` additionally requires a valid matrix with `scope=full` and therefore an unlimited (`task_limit=0`) run over the frozen catalog.

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
11. All four rows contain the same unique ordered task-ID sequence and task count.
12. Per-call model usage/latency reconciles with aggregate execution metadata.
13. The four-row validator reports `matrix_valid=true`.
14. Public leaderboard promotion additionally requires `publication_ready=true`, `scope=full`, and `task_limit=0`.

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
