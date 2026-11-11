# ADR-003 — Zero-Cost Self-Hosted Baseline (R0)

- Status: Accepted · S1 complete (four readings, see `docs/measurement-basis.md`); S2 in progress (two readings: boundary matrix and latency/failure attribution; two items remaining); S3 not started · Date: 2026-11-09 · Applies to: deployment topology (`render.yaml`, `deploy/`), execution isolation, artifact lifecycle, observability, evaluation publication
- Related: `docs/real-model-evaluation.md` (Spend cap, Automated matrix validation, Publication rule 14) · `deploy/render-persistent.example.yaml` · `GOVERNANCE.md` (Money / data) · `docs/ADR/ADR-002-output-artifact-export-2026-09-08.md`

## Problem

Three capability gaps currently converge on one fork: cross-restart persistence, structural execution isolation, and a publishable real-model baseline. Each has a paid answer — Render disk plus paid compute, managed Postgres plus object storage, a commercial execution sandbox (E2B / Modal / Daytona / Vercel Sandbox), or managed observability (Langfuse Cloud / LangSmith / Arize).

The project is constrained to zero-billing resources, with explicitly enabled model tokens as the single, opt-in exception. That constraint invalidates every paid answer, so the question this ADR answers is not whether to buy but what to build instead — and which capabilities must be declared unobtainable rather than quietly approximated.

## Evidence

Verified on 2026-11-09 against `origin/main` = `82a5b34`, by reading each path with `git show FETCH_HEAD:<path>`. The local worktree copy of every file below is byte-identical to that commit except `uv.lock`, whose difference against the local baseline (`61a4af8`) consists of 25 version bumps and one added package (`opentelemetry-api`) with no removals; the `langsmith` entry cited in E6 is `0.14.11` in both.

| # | Fact | Source (line numbers are those of `82a5b34`) |
|---|---|---|
| E1 | The hosted blueprint declares `plan: free` and `autoDeploy: false`, carries no `disk:` block, and points all three writable roots at throwaway paths: `DSA_DATABASE_URL=sqlite+aiosqlite:////tmp/dsa.db`, `DSA_DATASET_DIR=/tmp/datasets`, `DSA_ARTIFACT_ROOT=/tmp/artifacts`. | `render.yaml` |
| E2 | The persistence blueprint declares `plan: 0.5c-512mb` and a 1 GB disk, and states in its own header: "Render attaches disks to paid services only, so there is no free variant of this file." Pricing recorded there on 2026-10-13 — $7/month plus $0.25/GB/month — is explicitly flagged for dashboard re-confirmation. A contract test enforces that every writable root sits under the mount, so the free/paid split is a tested property, not an incidental one. | `deploy/render-persistent.example.yaml` · `tests/contract/test_persistence_blueprint_covers_writable_roots.py` |
| E3 | The real-model workflow is `workflow_dispatch` only, accepts no inputs, pins `RUN_SCOPE: smoke-5` and `TASK_LIMIT: "5"`, and takes credentials exclusively from repository secrets. | `.github/workflows/real-model-evaluation.yml:3-4,20-21,46,92,138,184` |
| E4 | `publication_ready=true` additionally requires a valid matrix with `scope=full`, therefore `task_limit=0`; the five-task pinned workflow can pass matrix validation and still return `publication_ready=false` — by design. | `docs/real-model-evaluation.md:373,378,380,409` |
| E5 | A genuinely free model lane already exists under the heading "Free lanes ($0, no paid key)": Ollama local, described as "truly free, private, no signup"; its rows are labelled `provider=ollama` and are "never merged with paid-lane rows"; the publication validator requires the paid `openai` lane, so a free matrix cannot promote to a leaderboard claim. | `docs/real-model-evaluation.md:162-171,200,263,294` |
| E6 | The lockfile contains no broker, managed-database, payment, or hosted-observability SDK. The only match among `langsmith`, `langfuse`, `arize`, `boto3`, `psycopg`, `psycopg2`, `redis`, `stripe` is `langsmith` 0.14.11, a transitive dependency of `langchain-core`. `opentelemetry-api` is the sole OpenTelemetry package present; no exporter package and no OTLP endpoint variable appears in the lockfile. | `uv.lock:933,1826,1911,2529` |

Negative evidence — each of these refutes a premise that earlier planning relied on:

- **"Persistence can be had on the free tier"** — refuted by E2, in the vendor's own words.
- **"A configured workflow yields a publishable baseline"** — refuted by E4 plus the historical credentialed attempts that returned a quota-exhaustion error at zero spend.
- **"The version string is deployment evidence"** — refuted in practice: the API reported version `4.6.0` while the served front-end content lagged behind the same commit.
- **"A deny list constitutes an execution boundary"** — refuted by the expressions documented as passing the AST check while still reaching the host; a name-based filter is not a containment mechanism.

## Impact

- **Scope.** Deployment topology, execution-isolation boundary, artifact lifecycle, observability, evaluation publication. No change to the evidence graph, the evaluator, the benchmark catalogs, the frozen surfaces, or the SDK/CLI surface.
- **Explicitly not obtained.** Three capabilities are declared unobtainable under the constraint, and are documented as such rather than implied: (i) server-side data surviving a restart, (ii) structural — as opposed to boundary-based — execution isolation, (iii) a publishable real-model leaderboard row.
- **Replacement targets.** Portability and disclosure replace durability; a verifiable boundary matrix replaces a commercial sandbox; a self-contained reproduction bundle replaces a server-side store.
- **Operational consequence.** Cold starts and ephemeral storage remain observable properties of the public demo and are disclosed at `/version`, not papered over.

## Alternatives

1. **Paid persistence — Render disk on paid compute.** Rejected: E2 states there is no free variant; adopting it violates the zero-billing constraint.
2. **Managed Postgres plus object storage.** Rejected: same constraint, and it additionally introduces a driver, a migration path and a signed-URL surface that a free single instance cannot absorb.
3. **Commercial execution sandbox — E2B / Modal / Daytona / Vercel Sandbox.** Rejected: every option carries a billing tier; self-hosting an isolation layer is not feasible on the free instance's CPU and memory.
4. **External orchestration — Temporal / Restate cloud.** Rejected: managed service with billing, while an in-process checkpoint injection point already exists in the run pipeline (reuse is free, replacement is not).
5. **Export-first plus a self-contained reproduction bundle — chosen.** The server stops pretending to keep data: the bundle carries manifest, environment, pinned dependencies, ordered execution trace and artifact hashes, so a third party can re-run without the session's implicit state. The ephemeral lifetime stays disclosed.
6. **Do nothing — keep the current baseline unchanged.** Valid fallback: it preserves the honest baseline, but leaves the evidence-link, replay and boundary items unmeasured, and leaves the demo's storage behaviour described only by a warning string.

Two further options were considered and rejected on evidence rather than cost:

7. **Publish the free Ollama lane as a leaderboard row.** Rejected: E5 — the validator requires the paid lane, and merging lanes would violate the invariant that deterministic and real-model runs are never mixed.
8. **Treat the version string as a deployment health signal.** Rejected: no timestamp is exposed, so it cannot distinguish a redeploy from a stale container.

## Recommendation

- **Persistence:** adopt export-first plus a self-contained bundle. Acceptance moves from "data survives restart" to "artifacts stay parseable across lifecycle events" and "bundles re-run independently".
- **Isolation:** keep in-process execution, tighten the reachable boundary (allowed hosts, narrowed tool list, credentials never resident in the execution environment), and publish the boundary as a checkable matrix. Record the residual risk explicitly: boundary-based, not structural.
- **Model lane:** do not enable the paid lane by default. Variant comparisons run on the free Ollama lane, which never merges with paid rows and cannot promote.
- **Sequencing:** lead with verification work that needs no new infrastructure — four-layer evidence alignment, independent clean-environment re-run, served-artifact probe, authorization checklist.

## Migration Plan

| Stage | Entry condition | Work | Exit condition |
|---|---|---|---|
| S1 trustworthy baseline | this ADR accepted | evidence four-layer alignment, clean-environment re-run, served-artifact probe, authorization checklist | each metric recorded once with a defined measurement basis |
| S2 boundary and attribution | S1 exit | boundary matrix, deterministic-path latency and failure attribution, export-first lifecycle, contract-version policy | boundary decidability, attribution completeness and artifact parseability recorded; `matrix_valid` and `publication_ready` never conflated |
| S3 controlled expansion | S2 exit, and the open questions in Appendix C answered | replay grounded in a real checkpoint (planned only — not implemented in this build, and not to be described as available until a shipped path supports it), cross-environment diffs, decision-event log | each expansion carries its own ADR and passes INV1–INV8 |

No dependency additions, no infrastructure additions, no edits to the evaluator or the frozen catalogs.

## Rollback Plan

- Every item above is a document, a test, or a checklist; merging changes no runtime behaviour. Rollback is a revert of documentation plus the derived checklists — no data migration, no service restart.
- If S1 shows the free lane cannot produce a stable comparison, the baseline remains **unmeasured**. That is a valid, honest outcome and must not be worked around with estimated or simulated numbers.
- If the zero-billing constraint is lifted, alternatives 1–4 re-enter consideration and this ADR is **superseded by a new ADR**, never edited in place.

## Appendix A — Invariant status

| Invariant | Status | Basis and residual risk |
|---|---|---|
| INV1 conclusions trace to computation and data | full | This ADR changes no evidence path; S1 only makes the four layers checkable |
| INV2 reproduction bundle re-runs independently | full | Export-first is the mechanism; acceptance is bundle completeness plus independent re-run |
| INV3 deterministic and real-model runs never mixed | full | Paid lane stays off; Ollama rows are labelled `provider=ollama` and never merged (E5) |
| INV4 credentials and sensitive data never enter the execution environment | **partial** | Boundary tightening only. A deny list is not containment; the residual risk is "the set of hosts able to reach the endpoint grows" |
| INV5 architecture changes need an ADR; frozen surfaces are not edited in place | full | This ADR is that record; no frozen surface is edited |
| INV6 public release, external conclusions, governance config and paid changes need authorization | full | No public action, no governance change, no paid change is taken here |
| INV7 real failures stay visible; failed tool calls are not hidden | full | No hiding mechanism is introduced; the unmeasured baseline is recorded as unmeasured |
| INV8 no paid instance, disk, managed database, object storage, commercial sandbox or hosted observability | full | Every accepted direction is documentation, test, or checklist work on existing free resources |

## Appendix B — Scope of these facts (answers the prior open question on remote verification)

- All facts in E1–E6 were read from `origin/main` at `82a5b34` on 2026-11-09. They are **not** limited to a local working copy: `render.yaml`, `deploy/render-persistent.example.yaml`, `.github/workflows/real-model-evaluation.yml` and `docs/real-model-evaluation.md` are byte-identical between the local baseline `61a4af8` and `82a5b34`; `uv.lock` differs only by merged dependency bumps, with the `langsmith` entry unchanged.
- The live hosted instance was **not** re-verified for this ADR. `/version` exposes no deployment timestamp, so it cannot establish which commit a running container serves; that gap is precisely why the served-artifact probe is an S1 item.
- Observation dates are property of each fact, not of this document. Re-verification is required before any future decision that depends on the numbers in E2 (pricing) or on the workflow shape in E3.
- Line numbers in the evidence table are anchored to `82a5b34`. They shift in later trees — notably in `uv.lock`, where the local baseline carries 25 older package versions — so resolve each citation by content, not by offset alone.

## Appendix C — Open items

| Item | Status | Consequence if unresolved |
|---|---|---|
| Cloud reporting from the `langsmith` SDK in use | **unverified** — a locked SDK is not an enabled service. The lockfile carries no exporter and no OTLP endpoint variable (E6), but a repository-wide configuration sweep was not completed, so reporting stays unproven rather than proven absent | If reporting turns out to be enabled and billable, the observability allowance in INV8 needs re-cutting |
| Model credentials and spend ceiling | not provided | The paid lane stays off; S1–S3 are unaffected |
| Whether the free lane produces a stable enough comparison to substitute for a paid baseline | untested at this date | The baseline stays "unmeasured"; do not substitute estimates |
