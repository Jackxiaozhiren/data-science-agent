# Measurement basis (S1)

ADR-003 sets a single exit condition for S1: every metric is recorded once, and its basis is defined
before the number is quoted. This page is that definition. It is deliberately about arithmetic and
provenance rather than about targets — a target picked before the first reading is a preference, not a
measurement.

Three rules apply to every metric below, each because the opposite caused a real problem here:

1. **A metric is either recorded with a timestamp or written as "not measured".** No metric reports `0`
   for "nobody looked": zero is a reading, and a zero that came from an empty denominator is the exact
   shape `docs/real-model-evaluation.md` was written to keep out of a published table.
2. **The sampling method travels with the number.** A rate computed over 3 hand-picked artefacts and a
   rate computed over 40 random ones are different facts; the denominator alone does not say which.
3. **A basis change is a new record, not an edit.** When a definition moves, the previous reading stays
   and is marked superseded, so a later reader can tell "the number improved" from "the ruler changed".

## The four metrics

| Metric | Numerator | Denominator | Recorded in | Status |
|---|---|---|---|---|
| Served-artifact agreement | checks whose live reading matches the contract this tree publishes | checks attempted | `docs/audit/served-artifacts.json` | **measured, first reading 2026-11-09** |
| Evidence alignment | conclusions traceable to an evidence node, a computation and a data hash | conclusions sampled from completed runs | not recorded | defined, not measured |
| Independent re-run | bundles whose layers reproduce in a clean environment and match the recording | bundles sampled | not recorded | defined, not measured |
| Authorization coverage | action classes with a named authorizer and a recorded decision | action classes identified in the tree | `docs/audit/authorization-coverage.json`, `docs/audit/authorization-coverage-second.json` | **measured, two readings 2026-11-10** |

The two remaining unmeasured rows are not omissions dressed as plans: S1's own exit condition is to
record each of them once. Until then the honest value is "not measured", and the ADR's rollback path
explicitly allows the baseline to stay unmeasured rather than be filled with estimates.

## Served-artifact agreement

Measured by `scripts/probe_served_artifacts.py`, which reads only what is served — never the repository,
never a version string — and reports four independent checks:

| Check | What it reads | Failure it catches |
|---|---|---|
| `api_version_contract` | the `/version` payload shape | a deployed API that dropped a key the front-end discloses, without failing any request |
| `web_shell_names_chunks` | the page HTML | a shell that returns 200 and references no built JavaScript |
| `web_chunks_answer` | up to 12 named chunks | a half-pruned build: the shell names assets the host does not serve. A chunk the host refuses is a mismatch; a chunk no answer arrived for is unmeasured |
| `web_bundle_targets_documented_api` | a sampled chunk body | a bundle rebuilt without `NEXT_PUBLIC_API_URL`, pointing at an origin nobody documented |

Three properties of this basis matter more than the number:

- **Exit codes are the product.** `0` pass, `1` mismatch, `2` unmeasured. An unreachable host never reads
  as a pass: on a free instance that slept through the budget the question stayed open, and saying
  otherwise is how a gate stops meaning anything.
- **Chunk sampling is bounded, so absence is unproven.** The origin check is therefore *advisory*: it can
  promote a reading but never demote one, and a host that is not seen is recorded as unproven.
- **A refusal and a dropped connection are different facts.** An HTTP answer that says "no" is a fact
  about the build; a connection that never delivered one is a fact about the run, and is recorded as
  unmeasured. The first draft conflated them and reported one transient TLS reset as a half-pruned
  deployment — the instrument failing the way the deployment is not supposed to.
- **The version string is not evidence about a deployment.** `/version` returns a hand-typed value that
  cannot disagree with a running build; on 2026-11-07 it reported `4.6.0` while the served front-end
  still carried the previous build's copy. That is why this metric reads artefacts instead.

The first reading (2026-11-09, `docs/audit/served-artifacts.json`) recorded all four checks green, and
independently confirmed from the deployed side that all three writable roots are ephemeral
(`storage.durable=false`, `ephemeral_roots=[artifacts, database, datasets]`) — the same fact `render.yaml`
states in the repository, now measured from the outside instead of read from a file. The exact reading
time lives in that file rather than here, so a re-run cannot leave this page quoting a stale moment.

## Evidence alignment

A conclusion counts toward the numerator when a reader can walk from it to the evidence node that
supports it, from that node to the computation that produced it, and from that computation to the input
data with a hash — in one direction, without a gap and without re-running anything.

Sampling is by conclusion, not by run: a run with twelve conclusions and one with two contribute twelve
and two. A conclusion that names a chart but not the computation behind it counts as unaligned, which is
the point of separating "there is evidence" from "the evidence is traceable".

## Independent re-run

A bundle counts toward the numerator when a second environment reproduces its recorded layers and the
results match: manifest, pinned environment, ordered execution trace, artefacts and their hashes.

"Clean environment" is part of the claim, not a detail. A re-run executed in the directory that produced
the bundle shares state with it and does not measure independence; until a clean environment is actually
used, this metric stays unmeasured rather than reporting a comfortable number from a shared tree.

## Authorization coverage

The denominator is the set of action classes a contributor or an agent could take that have external
consequence: publishing a release or a leaderboard row, commenting on or closing an issue, changing
governance or branch configuration, spending money, using a credential, or stating an external
conclusion. The numerator is those classes that name both an authorizer and where the decision is
recorded.

This metric is a checklist that is scored, not a policy document: `GOVERNANCE.md` says who decides, and
this row measures whether every class of action actually lands on one of those deciders.

The first reading (2026-11-10, `docs/audit/authorization-coverage.json`) scored a census of the action
classes named above against `origin/main` = `08be9b5`: 2 of 9 name both an authorizer and a location
where the decision is recorded. It is a census rather than a sample, and the record gives the rule that
expanded the definition's groups into individual classes, plus a file and line for every verdict.

Two distinctions carry most of the weight. First, **a gate is not an authorizer**: `publication_ready`,
`DSA_MAX_COST_USD`, the required `ci` check and the claim guards are all controls, and none of them
names who decides. Second, **a named owner is not an enforced one**: the branch protection read at the
same time requires `ci` only and no review, so `CODEOWNERS` is advisory. Enforcement is deliberately
outside the numerator — including it would turn a question about what the tree says into a different
question about what GitHub does. The reading says nothing about whether any decision was correct.

The two covered classes are release publication and a change to the governance document: in both the
maintainer is named and the tag or pull request is the record. The first record also carried a
proposal for closing the others as text, explicitly not applied. That proposal was a statement about
`08be9b5` and is left unedited.

The owner authorized the proposal on 2026-11-10, and `GOVERNANCE.md` gained a decision-authority
table. A **second reading** (`docs/audit/authorization-coverage-second.json`) then scored the same
nine classes against the merged commit `920d4df` under the same basis and recorded 9 of 9.
The class definitions, method and denominator rule are copied verbatim between the two records, and a
contract test compares them as well as recomputing the second score from the governance table itself;
the change in the number is therefore a change in the tree, not a change in the ruler. The first
reading stays as history, exactly as written.

A full score is a narrow fact: every class now names a decider and a place where the decision is
written down. It is **not** a claim that any control is technically enforced. Branch protection was
re-read at the same time and is unchanged — `ci` required, no required review, `CODEOWNERS` advisory
— and the governance table says so in its own text. Nor does the second reading authorize anything
retroactively, certify a past decision, or create an exception to the zero-billing constraint. Its
`residual` field lists what remains open.

## What this page is not

- Not a scorecard: no metric here has a target yet, and the ADR does not set one for S1.
- Not a substitute for the evidence: the numbers live in their own records and are linked, so a change in
  a definition cannot quietly rewrite history.
- Not complete. Two of S1's four readings do not exist yet, and this page says so in the same table that
  reports the two that do.
