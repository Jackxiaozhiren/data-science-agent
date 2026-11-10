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
| Evidence alignment | conclusions traceable to an evidence node, a computation and a data hash | conclusions sampled from completed runs | `docs/audit/evidence-alignment.json` | **measured, first reading 2026-11-10** |
| Independent re-run | bundles whose layers reproduce in a clean environment and match the recording | bundles sampled | `docs/audit/independent-rerun.json` | **measured, first reading 2026-11-10** |
| Authorization coverage | action classes with a named authorizer and a recorded decision | action classes identified in the tree | `docs/audit/authorization-coverage.json`, `docs/audit/authorization-coverage-second.json` | **measured, two readings 2026-11-10** |

All four rows now carry a reading. That is S1's exit condition met, and nothing more: each row is one
observed instance with its basis written down, not a trend and not a target that was hit.

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

The first reading (2026-11-10, `docs/audit/evidence-alignment.json`) scores a pinned frame at
`tests/fixtures/evidence-alignment/frame.json`. The original reports sit under the gitignored
`/artifacts/` root and together outweigh the documentation tree, so pinning them verbatim would make
the number depend on artefacts no reader can see. The frame keeps instead the fields the walk above
reads, plus a SHA-256 anchor for every source report; `scripts/measure_evidence_alignment.py`
recomputes the reading, the per-hop counts and the frame digest from that file alone. A broken
reference at any hop is recorded together with the hop it broke at, so a full score is never a blank
"all green".

The frame is a **convenience census, not a random sample**: every report visible in one local working
copy at capture time, sorted by run identifier, with no exclusion by outcome. Runs with no conclusions
contribute nothing to either side of the rate. That boundary matters more than the score: these are
mostly test runs, the frame is a projection whose fidelity a checkout cannot independently verify,
and the fourth hop asks that a hash be *recorded*, not that the input still exist. Whether the inputs
still existed was checked once on the capturing machine — 65 of 95 present, all matching their
recorded hash, 30 already gone — but that observation cannot be reproduced from a checkout, so it is
written in the ledger as context rather than made a field of the reading. Every field of the reading
is recomputable from the frame.

The reading therefore says nothing about whether a conclusion is true, whether a tool result agrees
with the evidence node citing it, or whether a run can be reproduced. The last of those is what the
independent re-run metric measures, and it is measured below. A change to the frame or to the hop
definition is a basis change: a new reading is added and this one marked superseded, not rewritten.

## Independent re-run

A bundle counts toward the numerator when a second environment reproduces its recorded layers and the
results match: manifest, pinned environment, ordered execution trace, artefacts and their hashes.

"Clean environment" is part of the claim, not a detail. A re-run executed in the directory that produced
the bundle shares state with it and does not measure independence; until a clean environment is actually
used, this metric stays unmeasured rather than reporting a comfortable number from a shared tree.

### First reading (2026-11-10)

The sample is `benchmarks/baseline`, the only recording in the tree that states its own provenance:
`run_manifest.json` names the stub lane, zero model calls and the commit it was frozen at
(`4259e8f101ed`). One bundle was sampled, one reproduced.

The environment was `git clone` of this repository, checked out at `3b9c0f7ab13f`, with a fresh virtual
environment built from that commit's own `uv.lock` and the repository installed into it. Before the run
the clone had no `artifacts/` directory and no environment directory, and `git status` was empty. Nothing
was read from the working copy that produced the recording.

Two comparisons were made, because they answer different questions:

- **Inside the clean clone**, `dsa --reproduce` runs the benchmark twice and scores the pair. Both runs
  reached the top level on every task: the score is `overall 1.0`, `execution 1.0`, `trajectory 1.0`.
  Its `by_level` block reads `L0..L4 = 0.0, L5 = 1.0`, which is the share of tasks whose *highest*
  level is that level — read as a per-level pass rate it would look like a total failure at L0, which
  is the opposite of the fact.
- **Against the recording**, `scripts/compare_baseline_run.py` compares four layers: the task roster,
  each task's six verdict fields and `error`, the aggregate block with its per-category table, and the
  `execution` block. All four agree; 50 of 50 tasks are present on both sides and no verdict field
  differs on any task. The two sides are different commits by construction, so agreement is also
  evidence that nothing regressed between `4259e8f` and `3b9c0f7ab13f` — it is not a same-commit
  control.

Two exclusions are part of the definition rather than conveniences. `latency_ms` and its aggregate
`mean_latency_ms` are excluded: wall-clock time is a property of the machine, and comparing it would
fail every honest re-run on slower hardware (the recorded mean is 142.9 ms; the fresh mean was 1142.4 ms
on a loaded laptop). `execution.git_commit` is expected to differ and is reported rather than compared.
Every other field in the `execution` block must agree, and a changed `call_count` is a mismatch, because
that would mean the two sides ran different lanes.

The fresh side lives under `artifacts/`, which `.gitignore` excludes, so unlike the evidence frame this
object cannot be shipped. A reader checks this reading by re-running it, which the record's `procedure`
field spells out. The record also states one deviation: a 45 MB wheel failed to download repeatedly, so
it was supplied from outside the registry — its SHA-256 matches the hash `uv.lock` records for that
filename, so the dependency set stayed lock-faithful even though the transfer path was not the plain one.

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
- Not complete. All four rows now carry a first reading, but each is a single observation: none of them
  establishes a rate over repeated runs, and the independent re-run sample is one bundle because only
  one recording in the tree states its own provenance.
