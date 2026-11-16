# ADR-005 — A publishable full-catalog real-model run

- Status: Proposed on 2026-11-16; not accepted, not dispatched, and no paid spend or publication authorized by this record · Date: 2026-11-16 · Applies to: `.github/workflows/real-model-evaluation.yml`, the publication gate in `packages/evaluation/src/dsa_evaluation/publication.py`, and the cost-estimate section of `docs/real-model-evaluation.md`
- Related: `docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md` (S3 entry, Appendix C, INV3/INV6/INV8) · `docs/ADR/ADR-004-producer-gaps-behind-s2-exit-2026-11-13.md` (INV4 residual) · `docs/measurement-basis.md` (stage boundary and the `matrix_valid` / `publication_ready` distinction) · `docs/real-model-evaluation.md` (pinned smoke, spend cap, cost table) · `GOVERNANCE.md`

## Problem

S2 is exited, but S3 remains `not started`: ADR-003's Appendix C still records model credentials with a spend ceiling as `not provided`. The pinned real-model workflow is deliberately a **credentialed smoke**, not a publishable run. It declares `RUN_SCOPE: smoke-5` and `TASK_LIMIT: "5"`, and each of its four comparison containers passes `--limit 5`. Under `publication.py`, `publication_ready = matrix_valid and scope == "full"`; a smoke row therefore cannot become publishable by validation alone.

Promoting this workflow is not a single switch. The scope declaration, the task-limit declaration, the actual CLI execution, the per-process spend ceiling, the pricing provenance, the credential source and the labels must all agree across four independently generated manifest sets. If any one of them is changed without the others, the result is either `publication_ready = false` or a `matrix_valid = false` caused by inconsistent shared fields — and, worse, a manifest that claims `full` while the process ran five tasks.

There is also a factual obstacle before any budget decision. `docs/real-model-evaluation.md` estimates a full internal run as `4 × 150 = 600` tasks, while the frozen catalog at `benchmarks/ds-agent-benchmark/catalog.json` contains 50 tasks. A cap chosen from the wrong denominator is not a budget; it is an estimate wearing a budget's clothes.

The free lane is not an escape from this problem. The live probe against `openai-compat` with `glm-4-flash` produced real calls (`call_count = 5`, `input_tokens = 2968`, `output_tokens = 1521`, `total_tokens = 4489`) and `cost_usd = 0`. That is a useful regression anchor, but the publication gate requires `provider == "openai"`, positive unit prices and `cost_usd > 0`. The free lane fails all three clauses by construction.

The question this ADR answers is therefore narrow: **what exactly changes to make a full-catalog real-model run publishable, which prerequisites must be satisfied before it is dispatched, and what makes the decision reversible without rewriting a number or a claimed result?**

## Evidence

Read on 2026-11-16 against `origin/main = f6498a7` (tree `777f8e6c`). Line numbers are anchored to that commit; resolve every citation by content, because a later workflow edit moves offsets.

| # | Fact | Source |
|---|---|---|
| E1 | The workflow is `workflow_dispatch`-only and has no inputs. Scope and limit cannot be overridden at trigger time; the values are version-controlled. | `.github/workflows/real-model-evaluation.yml:3-4` |
| E2 | Job env pins `RUN_SCOPE: smoke-5`, `TASK_LIMIT: "5"`, `DSA_OPENAI_MODEL: gpt-5.6-luna`, input/output rates `0.20`/`1.20` per million, `PRICING_REFERENCE_DATE: 2026-08-29`, and `DSA_GIT_COMMIT: ${{ github.sha }}`. | same file `:16-25` |
| E3 | `DSA_MAX_COST_USD: "2"` is set once in job env and forwarded with `-e` into each of the four comparison containers. The guard is read per process, so the workflow worst case is `4 × 2 = $8`; the run-wide bound is the provider project-level limit. | same file `:19-21,61,108,155,202`; `docs/real-model-evaluation.md` "Spend cap (in-code guard)" |
| E4 | Each of the four `docker run` blocks hardcodes `--limit 5`. Removing the declaration in E2 alone would not make the process read the whole catalog. | same file `:69,116,163,210`; `packages/evaluation/src/dsa_evaluation/runner.py` (`if limit:` branch) |
| E5 | `publication_ready = matrix_valid and scope == "full"`. The gate also requires `llm_mode ∈ {real, openai}`, `provider == "openai"`, `fallback == "error"`, positive workflow prices equal to execution prices, and `cost_usd > 0`. | `packages/evaluation/src/dsa_evaluation/publication.py:136-160,266-286,400-401` |
| E6 | `scope=full` requires `task_limit=0`; `scope=smoke-5` requires `task_limit=5`. With `task_limit=0` the gate requires `n_tasks > 0` but does not require `n_tasks == 0`, so a full row correctly reports `n_tasks = 50`. | same file `:356-388` and the `n_tasks`/`task_limit` clauses in the per-row validation |
| E7 | Four variants (`dsa`, `dsa-no-critic`, `llm-tools`, `llm-only`) each upload `workflow_manifest.json`, `run_manifest.json`, `results.json`, `summary.json` and `raw_runs.json`. The validator compares 13 shared workflow fields across the four manifests and also compares the ordered `task_id` sequence of the raw runs. | workflow `:43-230`; `publication.py:9-27,356-362` |
| E8 | The frozen catalog contains 50 tasks (EDA 8, SQL 7, Statistics 8, Regression 6, Classification 6, Time Series 5, Visualization 5, Data Quality 5). | `benchmarks/ds-agent-benchmark/catalog.json` |
| E9 | The cost table says "Full internal (4 × 150) = 600 tasks"; that is twelve times E8 and is the basis of the suggested `DSA_MAX_COST_USD=5`. | `docs/real-model-evaluation.md` "Cost estimate" table |
| E10 | A free-lane probe wrote `provider = openai-compat`, `model = glm-4-flash`, five real response IDs, `token_usage.total_tokens = 4489` and `cost_usd = 0`. It is a local, uncommitted probe and is not recorded as a reading. | local probe prepared for this review; not in the repository |
| E11 | The same page requires a green pinned smoke on the same commit before any `scope=full` run and says to remove `--limit` only after that smoke succeeds. | `docs/real-model-evaluation.md:40,63,167` |
| E12 | No key, no workflow dispatch, no paid call and no publication followed from the review that preceded this ADR. The exposed Zhipu key is a separate rotation item; #16 and #81 remain open. | `AUDIT_LEDGER.md` entries dated 2026-11-15 and 2026-11-16; repository state at `f6498a7` |

Negative evidence — each statement refutes a premise the obvious promotion would rest on:

- **"`RUN_SCOPE=full` makes the run full."** Refuted by E2, E4 and E6: the manifest declaration, the limit declaration and the CLI argument are three separate values, and a disagreement either fails the gate or lies about scope.
- **"The free lane is cheaper enough to publish."** Refuted by E5 and E10: a zero-price lane cannot satisfy the provider, price and positive-cost clauses regardless of call quality.
- **"`DSA_MAX_COST_USD` is the run budget."** Refuted by E3: it is one guard per process, and the workflow starts four processes. Only the provider project-level limit is a run-wide hard boundary.
- **"The existing cost table justifies the cap."** Refuted by E8 and E9: the table's denominator is 600 tasks and the catalog's is 50.
- **"A validator pass is a maintainer decision."** Refuted by E11, E12 and INV6: the gate computes readiness; the decision to spend, dispatch, publish and close an issue is separate and remains with the maintainer.

## Impact

- **Scope.** One workflow file, one documentation cost table, and this record. No evaluator scoring, no benchmark catalog, no Python source, no new provider and no infrastructure change.
- **Paid change, disclosed.** This is the first record that plans a real paid API run, but it does not itself configure a secret, set a project spend limit, dispatch a run or produce a cost. Those remain external, authorized actions.
- **Records, not edits.** No existing smoke artifact is relabelled. If the pricing snapshot is refreshed, the new date and any changed rate apply only to artifacts produced after the reviewed workflow change; prior artifacts keep their own provenance.
- **Two boundaries, stated separately.** `DSA_MAX_COST_USD` is a per-process refusal threshold forwarded to four containers; the provider project-level limit is the binding run-wide boundary. A document that says one is the other is wrong.
- **Stage boundary preserved.** `matrix_valid` stays a structural predicate over four rows; `publication_ready` additionally requires `scope == "full"`. Neither is inferred from prose.
- **Residual risk unchanged.** INV4 stays `partial`: a deny list is not containment, and this workflow change does not touch the isolation boundary. The first expansion must name that residual, which this ADR does.
- **Public state unchanged.** S3 stays `not started`; #16 stays open until its definition of done is met; #81 stays open with the "future direction" record untouched. No public reply is written here.

## Alternatives

1. **Keep the pinned smoke workflow forever and call it the real-model baseline.** Rejected: `scope=smoke-5` makes `publication_ready` false by construction, so this is not a baseline but a permanent rehearsal.
2. **Add `workflow_dispatch` inputs for scope, limit, model and prices.** Rejected: E1's lack of inputs is a provenance feature. Free-form dispatch data would let two runs with the same commit and label mean different things.
3. **Publish the free-lane rows.** Rejected by E5 and E10. It would require weakening the provider, price and cost clauses — changing the ruler to fit the answer.
4. **Flip only `RUN_SCOPE` and `TASK_LIMIT`.** Rejected by E4 and E6: the containers would still run five tasks while their manifests declared `full`, producing either a validation failure or a false claim.
5. **Keep the 600-task cost table and reuse the suggested cap without re-deriving it.** Rejected by E8 and E9. A budget based on a nonexistent denominator cannot be reviewed.
6. **Use a managed external evaluation harness with its own billing and observability.** Rejected under INV8 and the scope of ADR-003: it adds infrastructure and a new trust boundary to solve a problem that is entirely a version-controlled workflow shape.
7. **Promote the pinned workflow as one reviewed change with prerequisites, negative controls and rollback — chosen.** It is the only option that keeps provenance pinned, makes the execution match the declaration, and leaves the maintainer's spend and publication decisions explicit.

## Recommendation

Five decisions. Each has an acceptance stated as a predicate over a record or a reviewed file, not as an intention.

- **D1 — scope and execution move together.** Change `RUN_SCOPE` to `full`, `TASK_LIMIT` to `"0"`, and delete all four `--limit 5` arguments in the same reviewed workflow change. Rename the workflow and job labels away from "Smoke" so artifact names agree with scope. *Acceptance:* four manifests report `scope=full`, `task_limit=0`, `n_tasks=50`, and identical ordered `task_id` sequences; no `--limit` remains in any comparison container.
- **D2 — the publishable lane stays paid and pinned.** Keep `DSA_LLM_PROVIDER=openai`, `DSA_LLM_MODE=real`, `DSA_LLM_FALLBACK=error`, `OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}`, the model and the two rates; refresh `PRICING_REFERENCE_DATE` only after a human checks the current source, and change rates in all four generated manifests together if they have moved. *Acceptance:* every row has `provider=openai`, `cost_usd > 0`, positive prices equal across all four manifests, and a pricing reference date whose source is recorded in the review. A free-lane row is never substituted.
- **D3 — the budget is corrected before it is raised.** First correct E9's table to the 50-task catalog, then set `DSA_MAX_COST_USD` to a value derived from that table; `5` is the working proposal with roughly tenfold headroom, not a measured requirement. Keep the four `-e DSA_MAX_COST_USD` forwardings and the per-process wording in the documentation. Configure a provider project-level spend limit as the run-wide bound. *Acceptance:* the documentation's arithmetic and the workflow cap agree; the workflow statement says `4 × cap` is the worst case; the project limit exists before dispatch.
- **D4 — a green pinned smoke on the target commit precedes dispatch.** Run the unmodified pinned workflow on the exact commit that will be dispatched, review the four bundles, and allow no intervening commit before the full run so `DSA_GIT_COMMIT = ${{ github.sha }}` still names the validated tree. *Acceptance:* four smoke rows succeed with `matrix_valid=true`, `publication_ready=false` for the expected scope reason, and the reviewed commit is recorded in the dispatch note.
- **D5 — validation, human provenance review, then a separate publication decision.** After dispatch, run the matrix validator against the four bundles and confirm `matrix_valid=true`, `publication_ready=true`, `scope=full`, `errors=[]`, real response IDs, and matching aggregate token/latency sums. Perform every negative control in Appendix B before calling the gate trustworthy. Only after that review may a maintainer decide, in a separate authorization, to update the README/result registry and close #16. *Acceptance:* the validator output and the negative-control results are both recorded; no publication state changes in the same PR that changes the workflow.

D1–D3 are prerequisites for D4; D5 may not be anticipated. A passing validator without a maintainer review is not a publishable baseline.

## Migration Plan

| Stage | Entry condition | Work | Exit condition |
|---|---|---|---|
| P0 — this record | S2 exited; S3 credential row still open | Decide D1–D5, with no implementation | Record merged; workflow, secrets and public state untouched |
| P1 — documentation correction | P0 | Rewrite the cost table against the 50-task catalog and state the per-process cap scope | Table arithmetic matches `catalog.json`; no workflow edit |
| P2 — external prerequisites | P0 | Rotate the exposed free-lane key; configure `OPENAI_API_KEY` as a secret and set a provider project-level spend limit | Secret exists, key is never in chat/issue/PR/workflow input; project limit is set |
| P3 — same-commit smoke | P2 | Dispatch the unmodified pinned workflow on the target commit and review four bundles | Four smoke rows green; `publication_ready=false` only for scope |
| P4 — workflow promotion | P3 | One reviewed PR carrying C1–C7 from Appendix A; CI and workflow-shape review green | Manifest scope and execution agree; no frozen surface edited |
| P5 — full run | P4 | `workflow_dispatch` the promoted workflow; download artifacts and `matrix_validation.json` | `matrix_valid=true`, `publication_ready=true`, `scope=full`, `errors=[]`, four ordered task sequences identical |
| P6 — provenance and closure | P5 | Human review of response IDs, pricing source, cap behaviour and negative controls; then a separately authorized publication update | #16 closes only after its definition of done is met; #81 keeps its current state |

P2 and P3 depend on inputs outside the repository. If either is unavailable, the stage stops at its last green predecessor and records the missing input; no estimated cost, substituted key or relaxed gate is used.

## Rollback Plan

- **Workflow PR.** Revert P4 as one unit. Partial reverts are not acceptable because C1, C2 and C3 must agree; restore the pinned smoke labels, scope, limit and cost cap together.
- **Cap trips during a run.** Stop and inspect the call log. Do not lower scope, lower the task count, raise the cap quietly, or relabel the partial artifacts as a full row. Record the run as an interrupted attempt.
- **Pricing turns out to be stale.** Freeze the produced artifacts as they are. Re-check the source, write a new dated pricing record, and re-run; never edit the pricing fields of an existing manifest to make it pass.
- **Key exposure.** Rotate the secret at the provider and in GitHub Actions, then invalidate any copied value. No key is written to the repository, chat, issue, PR, workflow input or artifact as part of the recovery.
- **Validator fails.** Leave `publication_ready=false`, keep the artifacts, and fix the producer or the workflow in a new reviewed change. The validator is not weakened to accept an inconsistent matrix.
- **Job times out.** The job currently allows 180 minutes; a full run is roughly ten times the smoke task volume. If the run times out, raise the timeout in a reviewed change rather than reducing `n_tasks` or reintroducing `--limit`.
- **Publication turns out to be premature.** Revert only the publication update; the workflow and the artifacts stay as records of the run. `matrix_valid` and `publication_ready` keep their definitions, so a withdrawal does not require redefining either.

## Appendix A — Exact field contract

All offsets are anchored to `f6498a7`. Resolve by content before editing.

| # | Location | Current value | Change | Reason |
|---|---|---|---|---|
| C1 | workflow `:23` | `RUN_SCOPE: smoke-5` | `RUN_SCOPE: full` | Source of the manifest `scope` field; required by E5/E6 |
| C2 | workflow `:24` | `TASK_LIMIT: "5"` | `TASK_LIMIT: "0"` | `scope=full` requires `task_limit=0`; read by `scripts/write_real_model_workflow_manifest.py` |
| C3 | workflow `:69,116,163,210` | `--limit 5` in each container | delete the argument in all four places | Changes actual execution; C2 alone changes only the declaration |
| C4 | workflow `:21` | `DSA_MAX_COST_USD: "2"` | `DSA_MAX_COST_USD: "5"` after P1 | Derived from 50 tasks, not E9's 600; per-process, not run-wide |
| C5 | workflow `:16-18,25` | model, two rates, pricing date | keep model and rates unless re-verified; refresh date; change rates in all four manifests if needed | Pricing provenance is part of the shared-field comparison |
| C6 | workflow `:49,96,143,190` | `${{ secrets.OPENAI_API_KEY }}` | unchanged; confirm the secret is configured | Paid lane source is already correct; the key itself never enters the tree |
| C7 | workflow `:1,29` | labels containing "Smoke" | full-run labels | Prevents artifact names from contradicting scope; not a gate clause |

Explicitly unchanged: the four-variant loop, the manifest generator, the validation step, the upload steps, permissions, concurrency, evaluator scoring, runner logic and the frozen catalog.

## Appendix B — Gate contract and negative controls

`publication_ready = matrix_valid and scope == "full"` is computed by `publication.py`, not declared in a page. The full-run change is acceptable only if all clauses below hold over one set of four artifacts.

1. Per row: `evaluation_variant` matches its directory; `llm_mode ∈ {real, openai}`; `provider == "openai"`; `fallback == "error"`.
2. Per row: `execution.model == workflow.model` and `execution.git_commit == workflow.git_commit`.
3. Per row: critic state matches the variant — `dsa` = `(True, on)`, `dsa-no-critic` = `(False, off)`, `llm-tools` and `llm-only` = `(None, not-applicable)`.
4. Per row: `call_count > 0` and equals the number of `llm_calls`; each call has a non-empty `response_id` and positive `latency_ms` and `total_tokens`.
5. Per row: aggregate input/output/total tokens equal the sums of the individual calls; aggregate `model_latency_ms` equals the sum of individual latencies.
6. Per row: aggregate `total_tokens > 0` and `model_latency_ms > 0`.
7. Per row: `pricing.source == "explicit environment rates"`; workflow unit prices are positive and equal execution prices; `cost_usd > 0`.
8. Per row: `n_tasks > 0` and equal across the four files and to the length of `raw_runs`; `task_limit >= 0`, and when `task_limit > 0`, `n_tasks == task_limit`. For this ADR `task_limit = 0` and `n_tasks = 50`.
9. Per row: `llm-tools` and `llm-only` carry the same `baseline_config`.
10. Across rows: the 13 shared workflow fields agree; `n_tasks` agrees; ordered `task_id` sequences in `raw_runs` agree.
11. Across rows: `scope=full` implies `task_limit=0`; the inverse smoke pair also holds.
12. Per row: `workflow_manifest.json`, `run_manifest.json`, `results.json`, `summary.json` and `raw_runs.json` are all present.

Before trusting a green result, flip each control once and require red:

| Flip | Required failure |
|---|---|
| Restore `RUN_SCOPE: smoke-5` only | `publication_ready=false`, `matrix_valid=true` |
| Apply C1 without C2 | `scope=full requires task_limit=0` |
| Apply C2 without C3 | manifest/actual task mismatch; ordered task sequences differ |
| Change model or price in only one variant | cross-row shared-field comparison fails |
| Use `openai-compat` instead of `openai` | provider clause fails, alongside zero prices and zero cost |
| Set one row's `total_tokens` to `0` | positive-total clause fails; the repair recorded in the preceding entry is what makes this detectable |

## Appendix C — Invariant status

| Invariant | Status | Basis and residual risk |
|---|---|---|
| INV1 conclusions trace to computation and data | full | Every acceptance above reads a field in an artifact; no prose claim becomes a number |
| INV2 reproduction bundle re-runs independently | full | The five required artifacts and the pinned commit/catalog/model tuple are preserved; no bundle is relabelled |
| INV3 deterministic and real-model runs never mixed | full | This ADR concerns the `openai` lane only; the free lane stays a regression anchor and no row is merged across lanes |
| INV4 credentials and sensitive data never enter the execution environment | **partial** | The secret is passed only from GitHub Actions to the comparison containers; a deny list is still not containment, and the residual is named here rather than closed |
| INV5 architecture changes need an ADR; frozen surfaces are not edited in place | full | This record is the ADR; the workflow is not a frozen surface, and evaluator/catalog/runner code is untouched |
| INV6 public release, external conclusions, governance config and paid changes need authorization | full | No secret, spend, dispatch, publication, issue state or governance change is taken by this record |
| INV7 real failures stay visible; failed tool calls are not hidden | full | Capped or timed-out runs stay as interrupted attempts; no partial row is promoted to full |
| INV8 no paid instance, disk, managed database, object storage, commercial sandbox or hosted observability | full by scope | No infrastructure is added; a paid model API call under an authorized secret is a measured run, not a paid service deployment |

## Open items

| Item | Status | Consequence if unresolved |
|---|---|---|
| Exposed free-lane key | rotation pending, outside the repository | Rotate before any further free-lane probe; unrelated to the paid lane's provenance |
| `OPENAI_API_KEY` secret and provider project-level spend limit | not configured by this record | D2–D5 cannot start; the paid lane stays off |
| Corrected 50-task cost table | P1, not done here | C4's proposed cap has no reviewed basis |
| Green pinned smoke on the dispatch commit | P3, not done here | No full run may be dispatched |
| Human provenance review and negative controls | P6, not done here | A validator result is not a publication decision |
| #81 external evidence layer | open; "future direction" only | No public reply, no code, no change to its four re-evaluation preconditions |
| S3 entry | still `not started` | This ADR plans an expansion; it does not provide the credential row that opens the stage |
