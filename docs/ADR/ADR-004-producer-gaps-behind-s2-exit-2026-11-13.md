# ADR-004 — The producer changes behind S2's exit

- Status: Accepted on merge (2026-11-13) · D1 landed as #191, D2 as #192, D3 as #200 · D4 satisfied on 2026-11-14, when one set of readings met all four predicates and ADR-003's status line moved to `S2 complete` · Date: 2026-11-13 · Applies to: the execution boundary of `profile_dataset`, the failure fields of a run record and of the external-benchmark adapter, and the integrity fields of the export surfaces
- Related: `docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md` (S2 row, INV5, Appendix C) · `GOVERNANCE.md` (architecture changes, frozen surfaces) · `docs/measurement-basis.md` (Stage exit) · `docs/audit/execution-boundary.json` · `docs/audit/attribution.json` · `docs/audit/export-lifecycle.json`

## Problem

ADR-003 gives S2 one exit condition with four clauses, and three of those clauses resolve to a reading. Each of the three readings ends by naming something it cannot close from the documentation side: three matrix cells have no request-time check to decide them, no non-passing external-benchmark run carries a stage or cause code, and no export-side event records a digest of the bytes it wrote.

Those are producer gaps. A reading can describe what a producer wrote; it cannot write it. Closing any of the three therefore means changing code on a surface ADR-003 declared frozen — the execution boundary, the run record (part of the evidence graph) and the export path (part of the evaluation framework) — and ADR-003 says a frozen surface is `superseded by a new ADR, never edited in place`.

So the stage now faces one fork with two honest arms. Either the missing facts get produced, and the exit condition is evaluated against a re-measurement; or the gaps are declared permanent, and S2 is closed as *not obtainable under the current constraints* — a different decision, with its own record, that would have to explain why three named producers were never changed. This ADR takes the first arm and fixes, in advance, the numbers that will count as closed.

The question it answers is therefore narrow: **which producers change, what exactly must they write, and what single set of readings may then be called an exit?**

## Evidence

Read on 2026-11-13 against `origin/main` = `0d4c0a7`. Every number below is a field in a committed record, not a summary typed into prose.

| # | Fact | Source |
|---|---|---|
| E1 | The boundary matrix records 15 cells: 12 are decided by a check that runs at request time and 3 are `undecidable`. All three sit on `profile_dataset` — `process_spawn`, `filesystem_write`, `credential_read` — and all three carry `decided_by: absence`, meaning nothing refuses the capability at request time; only today's import list and body do. | `docs/audit/execution-boundary.json` (`summary`, cells `PD-1`, `PD-4`, `PD-5`) |
| E2 | The attribution reading places 0 of 40 non-passing external-benchmark runs at a stage or cause level, and finds stage boundaries in 0 of 50 deterministic tasks. The frozen baseline is `not_measured` because its 50 tasks contain no failure — an empty denominator, not a zero. | `docs/audit/attribution.json` (`failures.external_bundle.stage_level`, `latency.tasks_with_stage_boundaries`, `failures.frozen_baseline`) |
| E3 | Of 6 lifecycle events, 3 are export-side; 0 of those 3 records a digest. 1 of 6 events runs a parse check, and 48 of 48 committed exports parse at the consumer end. The bundle's manifest carries five keys and none of them is a digest. | `docs/audit/export-lifecycle.json` (`summary`, `adr_divergence`) |
| E4 | A frozen surface is defined as runtime, evidence graph, evaluation framework, plus the benchmark catalogs, and an architecture change touching one needs an ADR with Problem/Evidence/Impact/Alternatives/Migration/Rollback. | `GOVERNANCE.md:20-24` |
| E5 | ADR-003 forbids exactly this kind of edit: "No change to the evidence graph, the evaluator, the benchmark catalogs, the frozen surfaces" (line 34); "no edits to the evaluator or the frozen catalogs" (line 68); "merging changes no runtime behaviour" (line 72); a frozen surface is "superseded by a new ADR, never edited in place" (line 74). INV5 restates it. | `docs/ADR/ADR-003-...-2026-11-09.md:34,68,72,74` · Appendix A |
| E6 | The three producers are single, named places: one tool body for the boundary cells; one run-record projection plus one adapter record for the failure fields; four write/record surfaces for the digests (two tools, the bundle route and its vendored twin, and the committed `artifacts.json` records). | `packages/tools/src/dsa_tools/tools/profile_dataset.py:execute` · `benchmarks/external/datascibench/run_eval.py:70-85` · `src/data_science_agent/_vendor/dsa_api/routers/bundles.py:107-113` · `packages/tools/src/dsa_tools/tools/{export,save}_artifact.py` |
| E7 | The external-benchmark recording that E2 reads is reproducible without a credential: its runner is described as a deterministic local pipeline with no LLM key and its config pins `model=deterministic-local`, so re-recording it costs wall-clock and no spend. | `benchmarks/external/datascibench/results/raw_runs.json` (`runner`, `config`) · `benchmarks/external/datascibench/run_eval.py:1-6,34` |
| E8 | The ADR-003 bundle description names "artifact hashes" among five elements, and the shipped manifest carries none, so two bundles of different bytes are indistinguishable from their manifests. | `docs/audit/export-lifecycle.json` (`adr_divergence.claim_in_document`) |

Negative evidence — each of these refutes a premise the obvious plan would rest on:

- **"The empty denominator is one of the gaps."** It is not. E2's frozen baseline records a recording in which nothing failed; the three rules in `docs/measurement-basis.md` forbid turning that into a number. A re-run that manufactured a failure would be a different recording, not a closure. D4 therefore does not ask for it.
- **"A recorded digest is a checked digest."** Refuted by E3: the one event that records a digest never re-reads the file, so the number is written and never compared. Recording is the gap; re-reading is the minimum that makes the recording mean something.
- **"Declaring the exit is a documentation change."** Refuted by `tests/contract/test_s2_exit_review.py`, which derives its verdict from these three numbers. Editing the declaration without moving the numbers fails the test, which is the intended behaviour.
- **"The gaps can be argued away by re-reading the same code."** Only partly. A re-read is legitimate where the first reading attributed a cell to an absence while a check was in fact already running earlier in the request — but for two of the three cells no such check exists, and inventing one in prose would be the ruler changing to fit the answer.

## Impact

- **Scope.** One tool body, one run-record projection, one adapter record, four export surfaces, three readings re-taken as second records, and one test rewritten to derive its verdict. No evaluator scoring change, no catalog edit, no new dependency, no infrastructure, no credential, no change to the public API shape.
- **Behaviour change, disclosed.** The boundary guard refuses paths that are read today: credential-shaped names, non-regular files, and paths whose resolved target leaves the permitted roots. This is the only user-visible change in the three decisions, and it must appear in `CHANGELOG.md` and `docs/security.md` in the same PR that lands it, not afterwards.
- **Records, not edits.** Each reading is re-taken as a second record. The first record stays, gains a `superseded_by` pointer, and keeps its numbers, so a later reader can tell "the number improved" from "the ruler changed".
- **Residual risk is unchanged.** The boundary stays boundary-based rather than containment: a request-time guard decides the cells this surface can name, and says nothing about a process that never passes through it. INV4 remains `partial`.
- **What does not move.** `publication_ready` keeps its own gate, the paid lane stays off, and the frozen baseline keeps reading `not_measured`.

## Alternatives

1. **Leave the three gaps open and keep S2 in progress indefinitely.** Rejected: an exit condition that no planned work can satisfy stops being a condition. It also blocks S3 on a status that carries no information.
2. **Declare the exit with the three gaps disclosed as limitations.** Rejected: the exit clause names completeness, and three named gaps are the opposite of it. Declaring an exit while its own readings say otherwise is the `matrix_valid` / `publication_ready` conflation this stage exists to prevent, one level up.
3. **Re-read the records under a relaxed verdict rule — count "fenced by today's code" as decided.** Rejected for two of the three cells: there is no request-time check to point at, so the re-read would assert a check that does not run. Where a check does already run earlier in the request, a re-read is legitimate and P1 may take it, provided the new record says which check it found and the old record is kept.
4. **Close only the cheap gap (export digests) and describe the stage as almost exited.** Rejected: "almost exited" is not a state the record can express, and a partial close would leave the declaration and the readings disagreeing by two.
5. **Change the producers, re-measure, then decide the exit on the new numbers — chosen.** It is the only arm that makes the exit condition decidable by the same instrument that recorded the gap.
6. **Buy the missing structure instead — a managed sandbox, a hosted tracer, an object store.** Rejected under ADR-003 alternative 3 and INV8: every option carries a billing tier, and none of the three gaps is about capability that money would add; each is about a field nobody wrote.

## Recommendation

Four decisions. Each states its acceptance as a predicate over a record, so "closed" is a number rather than an impression.

- **D1 — the boundary becomes decidable by a check.** `profile_dataset` gains a request-time capability guard that decides `process_spawn`, `filesystem_write` and `credential_read` before any reader runs. The guard is a closed set of refusals attached to the one value the surface accepts; it is not a sandbox, and the record must keep saying so. *Acceptance:* a second boundary record in which `summary.undecidable == 0`, and a probe per cell whose `observed` value is `refused` with a detail naming the check. A cell may move to `fenced` only through such a probe; the verdict rule is not relaxed.
- **D2 — failures carry a location, never a diagnosis.** The run record gains stage boundaries and, when a run does not complete, one code from a closed vocabulary; the external adapter writes the same fields for every task it records. The vocabulary is closed in code — an unknown code fails a test rather than entering a record. *Acceptance:* a fresh attribution reading in which `stage_level == non_passing` and `tasks_with_stage_boundaries == tasks`, with the vocabulary's members listed in the reading itself.
- **D3 — every export-side event records a digest, and the writer re-reads it.** The two tools, the bundle manifest and the committed artifact records each carry a per-file digest; the writer re-reads the bytes it wrote and fails loudly if they disagree. The report export's identifier-stripping rule is deliberate and stays: its digest moves to a field outside the narrative rather than into the prose the rule exists to clean. *Acceptance:* a second export reading in which `export_side_events_with_a_digest == export_side_events`, and the bundle divergence in E8 no longer holds.
- **D4 — the exit is one re-measurement, declared once.** S2 is exited only when a single set of readings satisfies all four: `undecidable == 0`; `stage_level == non_passing`; `export_side_events_with_a_digest == export_side_events`; and `publication_ready` still derived as `matrix_valid and scope == "full"`. The declaration is one PR whose diff is the status line, the measurement page's Stage-exit section, the ledger entry, and a rewritten exit test that derives its verdict from the records instead of asserting it. If any predicate fails, the stage is not exited and the failing predicate is named.

D1–D3 may land in any order and are individually revertible. D4 may not be anticipated: no partial set of the three counts as having exited.

## Migration Plan

| Stage | Entry condition | Work | Exit condition |
|---|---|---|---|
| P0 — this record | S2 readings exist and each names its gap | decide D1–D4 | merged, with nothing implemented |
| P1 — decidable boundary | P0 | request-time guard on `profile_dataset`, one probe per cell, second boundary record, security note and changelog entry | `undecidable == 0` in the new record |
| P2 — coded failures | P0 | stage boundaries in the run record, closed cause vocabulary, adapter fields, fresh deterministic external recording, re-captured attribution frame | `stage_level == non_passing` and `tasks_with_stage_boundaries == tasks` |
| P3 — digested exports | P0 | digests on the four export surfaces plus a writer-side re-read, second export record | `export_side_events_with_a_digest == 3 of 3` |
| P4 — exit review | P1, P2, P3 | re-measure, rewrite the exit test to derive its verdict, declare in status line, measurement page and ledger | D4's four predicates hold in one set of readings |

P2's external half needs the gitignored `.workspace/` under `benchmarks/external/datascibench/`. On a machine that no longer holds it, P2 cannot produce a fresh recording; the stage then stays un-exited and the missing input is recorded, never estimated. This is the one place where the plan depends on something outside the repository.

No dependency additions, no infrastructure additions, no edits to the evaluator's scoring, the task catalogs or the publication gate.

## Rollback Plan

- **Per stage.** P1, P2 and P3 are separate merges over separate surfaces; each reverts without touching the other two. The readings they produce are new files, so a revert restores the previous numbers by restoring the previous record set.
- **If the guard refuses a legitimate caller.** Revert P1 and record the three cells as still `undecidable`. Do not relax the verdict rule to keep the change: a cell that a check does not decide stays undecidable, and an exit that needs it stays undeclared.
- **If P2 cannot be re-recorded.** The stage keeps `not_measured` where it has no data and stays un-exited. Substituting an estimated cause code, or re-labelling the old recording, is prohibited by INV7.
- **If the declaration turns out to be wrong.** P4 is a three-file declaration plus one test; reverting it returns the stage to `in progress` and leaves every reading intact. A wrong exit is cheap to withdraw precisely because it never rewrote a number.
- **If ADR-003 is later superseded** on cost grounds, D1–D3 remain valid producer changes; only the zero-billing justification for rejecting alternative 6 changes, and that would be a new ADR.

## Appendix A — Invariant status

| Invariant | Status | Basis and residual risk |
|---|---|---|
| INV1 conclusions trace to computation and data | full | D2 adds fields to a record; it adds no claim to a conclusion, and the closed vocabulary forbids prose-derived codes |
| INV2 reproduction bundle re-runs independently | **strengthened** | D3 puts a per-file digest in the manifest E8 shows is missing it; a bundle becomes distinguishable by content, not only by name |
| INV3 deterministic and real-model runs never mixed | full | P2 re-records the deterministic lane only; the paid lane stays off and no row is merged across lanes |
| INV4 credentials and sensitive data never enter the execution environment | **partial** | D1 refuses credential-shaped paths at the one surface that accepts a path; that is a check, not containment, and the residual risk is unchanged |
| INV5 architecture changes need an ADR; frozen surfaces are not edited in place | full | This ADR is that record; it authorizes three bounded producer edits and nothing wider |
| INV6 public release, external conclusions, governance config and paid changes need authorization | full | No public action, no governance change, no paid change is taken here or by P1–P3 |
| INV7 real failures stay visible; failed tool calls are not hidden | full | D2 records a location for a failure instead of a cause; an unplaced failure stays visible as unplaced |
| INV8 no paid instance, disk, managed database, object storage, commercial sandbox or hosted observability | full | E7 makes the only re-record that P2 needs a deterministic local run; nothing in P1–P4 spends |

## Appendix B — What "closed" means, numerically

Four predicates, each read from a record rather than typed into a page. This table is the contract P4 is judged against.

| # | Predicate | Record and field | Today |
|---|---|---|---|
| 1 | no cell lacks a request-time decision | `docs/audit/execution-boundary.json` → `summary.undecidable` | 3 |
| 2 | every non-passing external run carries a stage or cause code | `docs/audit/attribution.json` → `failures.external_bundle.stage_level` against `non_passing` | 0 of 40 |
| 3 | every task carries stage boundaries | `docs/audit/attribution.json` → `latency.tasks_with_stage_boundaries` against `tasks` | 0 of 50 |
| 4 | every export-side event records a digest | `docs/audit/export-lifecycle.json` → `export_side_events_with_a_digest` against `export_side_events` | 0 of 3 |

The boundary predicate counts `decided_by: check` only. A cell whose `decided_by` is `absence` is not closed by a sentence, and the fourth clause of the exit condition — the separation between `matrix_valid` and `publication_ready` — is checked by reading the expression in `packages/evaluation/src/dsa_evaluation/publication.py`, not by re-reading a page.

## Appendix C — Open items

| Item | Status | Consequence if unresolved |
|---|---|---|
| A fresh external-benchmark recording for P2 | reproducible from the gitignored `.workspace/` on this machine; not reproducible on a clean clone | P2's external half stays un-exited and S2 keeps `in progress`; no estimated code is substituted |
| The frozen baseline's empty denominator | stays `not_measured` by design | None. D4 does not ask for it, and manufacturing a failure to fill it would be a different recording |
| Paid-lane credentials and spend ceiling | not provided (ADR-003 Appendix C) | S3's model-lane question stays open; P1–P4 do not need it |
| Boundary guard's permitted roots | to be fixed by P1 against the deployment's writable roots | If P1 cannot name the roots, it lands the credential and regular-file refusals and records the root question as open rather than inventing a policy |

Declaring the exit does not open S3. ADR-003's S3 row also requires the open questions in its Appendix C to be answered, and the paid-lane row there is unanswered. P4 therefore closes S2 only.
