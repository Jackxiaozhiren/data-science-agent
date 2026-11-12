# Measurement basis

ADR-003 sets one exit condition per stage, and this page is the basis for each reading that claims to
meet one. It is deliberately about arithmetic and provenance rather than about targets — a target
picked before the first reading is a preference, not a measurement.

S1 asks for each of four metrics to be recorded once; those readings are below. S2 asks what a
recorded run lets a reader point at: the execution-boundary matrix, the latency and failure
attribution reading, the export-first lifecycle and the contract-version policy are at the end of the
page. They are four of S2's four items, which closes the item list and not the stage: an exit is a
judgement about the readings, and none is declared here.

Three rules apply to every metric below, each because the opposite caused a real problem here:

1. **A metric is either recorded with a timestamp or written as "not measured".** No metric reports `0`
   for "nobody looked": zero is a reading, and a zero that came from an empty denominator is the exact
   shape `docs/real-model-evaluation.md` was written to keep out of a published table.
2. **The sampling method travels with the number.** A rate computed over 3 hand-picked artefacts and a
   rate computed over 40 random ones are different facts; the denominator alone does not say which.
3. **A basis change is a new record, not an edit.** When a definition moves, the previous reading stays
   and is marked superseded, so a later reader can tell "the number improved" from "the ruler changed".

## S1 — the four metrics

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

## S2 — the boundary matrix

S2 is the stage where ADR-003 replaces a commercial execution sandbox with a boundary published as a
checkable matrix. This is the first of its four items; the others are the three sections after it.

### What a cell means

For every surface that accepts model-authored input, five capabilities are scored: process spawn,
network egress, filesystem read, filesystem write, credential read. A cell's verdict is the outcome
of the **last check to run**, because that is the check a caller actually meets.

| Verdict | Meaning |
|---|---|
| `fenced` | a check runs at request time and refuses the capability |
| `open` | at least one expression reaches the capability |
| `undecidable` | nothing refuses it: the cell is closed only by the absence of a call site in this tree |

The third row is the one worth defending. Recording "fenced" because the code never calls `open`
would describe today's source rather than a boundary: the next edit changes it and no check
objects. Such cells carry `fenced_in_this_tree` true, which keeps the observation without promoting
it to a control. A matrix that scored those as fenced would report a boundary wherever there is only
code.

### First reading (2026-11-10)

`docs/audit/execution-boundary.json` takes the matrix against `ab95872`, and
`scripts/measure_execution_boundary.py` rebuilds it. Every probe is a repository constant, so the
record is recomputable from a checkout with no network and no service: the one file a probe opens is
a CSV this tree ships, and it is opened only to watch the engine refuse it. Of the cells, six are
open, six are fenced and three are undecidable, so twelve carry a request-time decision.
`effect_verified` counts separately and is smaller: it names the cells where a test in this tree has
watched the refusal happen, not merely read the check.

Three findings matter more than the counts:

- **The interpreter has one layer and the SQL surface has two.** `run_sql` pairs a name filter with
  an engine-level fence, so editing the filter leaves the capability closed. `run_python` has no
  engine equivalent, and every one of its cells is open. The asymmetry is the S2 result, not a
  detail of it.
- **Names are not effects.** `open()` is refused while `pl.read_csv` is not; `.environ` is refused
  while the same mapping read through `__dict__` is not. Both spellings sit in the probe set, which
  is why the credential cell reads open rather than fenced.
- **`matrix_valid` is not `publication_ready`.** The record states in its own text that it says
  nothing about the evaluation matrix, and the publication rule keeps its own gate. A green boundary
  matrix would not move a leaderboard row.

The reading says nothing about whether an adversary could reach a capability another way. A
name-based filter is not a containment mechanism, and the record's `not_claimed` field says so in
those words; the test file re-derives every verdict from the layers, so a changed filter changes the
record rather than leaving a stale verdict behind.

## S2 — latency and failure attribution

The second S2 item is not "how fast is the deterministic path". `benchmarks/baseline/README.md` already
answers that question in the negative: the same command on the same commit read 162.3, 73.04 and 89.56
milliseconds within minutes of each other. The question here is narrower and answerable — **what
fraction of a recorded run's clock, and which of its failures, can be pointed at a named part of the
record?** `docs/audit/attribution.json` is the reading, `tests/fixtures/attribution/frame.json` is the
projection it is computed from, and `scripts/measure_attribution.py --verify` rebuilds it field by
field.

### Latency: what a row can name

One clean-tree `dsa --limit 50` run supplies 50 rows whose manifest states `llm_mode=stub` and
`call_count=0`. Each row carries one `elapsed_ms`, one `duration_ms` per tool call, and the run
object's `created_at` / `updated_at`. Three quantities follow without interpretation:

| Quantity | Definition | Why it is a boundary, not a benchmark |
|---|---|---|
| `tool_ms` | the sum of the row's `duration_ms` values | the only time named to an execution unit |
| `residual_ms` | `elapsed_ms - tool_ms` | planning, evidence assembly and report writing have no timestamps of their own |
| `outside_window_ms` | `max(0, elapsed_ms - (updated_at - created_at))` | time even the run object's own clock does not cover |

The first reading: 249 tool calls across 50 tasks, all recorded as `ok`. The per-task tool share has a
median of 0.3536 and a mean of 0.4626, ranging from 0.0 to 0.9493; every one of the 50 rows has a
positive residual, and no row carries a stage-time field. One task stands 1168 ms outside the run
object's window. The 168 calls whose `duration_ms` is zero are the important part: the field is an
integer millisecond, so a sub-millisecond call is recorded as no time at all. The share is therefore
a **lower bound on what the record can name**, not a measurement of what tools cost. A second run of
the same clean tree at the same commit moved both the median share and the zero-duration count, so
the frame pins the one run it describes by hash rather than quoting a stable-looking number; the
ledger keeps the second observation as capture-time context, not as part of the reading.

### Failures: two recordings, one empty denominator

Two deterministic recordings ship in the tree, and neither is a random draw:

- `benchmarks/baseline/results.json` — 50 tasks, none failing. There is no failure to attribute, so
  the record says `not_measured` with the reason "empty denominator". It does not say 100%, and it
  does not say 0/0; both would turn an absent observation into a score.
- `benchmarks/external/datascibench/results/raw_runs.json` — 45 runs, 40 not passing (39 `failed`,
  one `execution_error`, using the adapter's own `score >= 0.5` pass mark). It records a wall clock
  for the bundle but no per-task latency at all.

Attribution is counted at three depths, each derived from fields the record actually carries:

| Depth | What counts | Reading |
|---|---|---|
| outcome | the run's `outcome` value | 40 of 40 |
| artifact | a mechanical signal from the recorded counts: the run did not complete, or produced no report, no tool call, or no evidence | 11 of 40 (10 with no evidence, one unfinished) |
| stage | a closed error-code or stage field naming the cause | **0 of 40** |

The 29 remaining runs completed with a report, tool calls and evidence and were still graded below
the pass mark; the record has no field that says whether the plan, a tool's result, the evidence or
the evaluator's expected shape was responsible. Eight of the 40 carry partial credit, so "failed" is
not even a binary state. One run carries a free-text error and that text is not a code. **Stage-level
attribution completeness is 0 of 40**, and the empty baseline denominator cannot improve it.

### What would count as progress

A later reading would need the producer to write a closed stage or cause code and a stage-level
timestamp into the record. That is a change to the producer, not to this instrument, and ADR-003's
migration plan keeps S2 work to documents, tests and checklists — none is written here. Until then the
honest result is a measured gap, and a green matrix in the first S2 item does not fill it.

## S2 — export-first lifecycle

ADR-003 replaces "data survives a restart" with "artifacts stay parseable across lifecycle events",
and its chosen alternative describes a bundle that carries "manifest, environment, pinned
dependencies, ordered execution trace and artifact hashes". The third S2 item is whether that holds
in the tree. `docs/audit/export-lifecycle.json` is the reading and
`scripts/measure_export_lifecycle.py` rebuilds it; nothing in it is a clock, a local run or a
deployment state, so a clean checkout reproduces it.

### What an event is asked

Six events, in the order an artifact meets them: the export tool writes it, the save tool writes it,
the run record lists it, the bundle exports it, the plain report export renders it, and a consumer
reads it back. Each event is asked two questions — does the record carry a digest of the bytes, and
does a shipped path parse them and fail loudly — and each answer is labelled `ran` or `read`, because
a claim obtained by running the code and one obtained by reading it are not the same evidence.

### The reading

**One event in six records a digest, and none of the three export-side events carries one forward.**
`export_artifact` returns the SHA-256 of the bytes it just wrote, matched against a recomputation;
`save_artifact` returns id, path, type and metadata and no digest; the 40 entries in the eight
committed `artifacts.json` records name id, type, path, kind, author and time and no digest; the
bundle's manifest carries `artifact_root`, `excluded`, `included`, `run_id` and `storage`, with zero
digest references in the route; and the plain report export *removes* a 64-hex token on purpose,
which is the rule that module states for itself. A recipient of a bundle can therefore tell which
names were listed and cannot tell whether the bytes behind a name are the ones that were written.

The second question separates even further: **one event in six has a parse check** — the consumer,
which is every reader after the fact. The writers hash or copy and never re-open what they wrote, and
the instrument's own read-back is not a shipped check, so it is not counted as one.

**Parseability today: 48 of 48 committed exports read back** — 40 JSON parsed and 8 Markdown decoded.
`csv`, `png` and `xlsx` have no committed export: run artifacts live under a gitignored root, so a
number there would describe one machine. Those three are recorded `not_measured` with that reason,
not as zero.

### The divergence this reading makes visible

ADR-003's bundle sentence names five elements, artifact hashes among them, and the shipped manifest
carries none of the five as a field. This section does not claim the other four are absent from the
bundle — the files a bundle carries may well hold environment and dependencies. It records the
narrower, checkable fact: no per-file digest reaches the export, so a bundle cannot be checked
against the run that produced it.

### What would count as progress

A digest written at the record event and copied into the manifest, with one reader that compares it,
would move `export_side_events_with_a_digest` off zero. That is a producer change — `save_artifact`'s
output model and the bundle route — and ADR-003 keeps S2 work to documents, tests and checklists, so
it is recorded here as a gap rather than closed by this reading.

## S2 — the contract-version policy

The ADR names this item and does not define it. Two readings of the phrase are available: the
`/version` payload a deployed API discloses, which S1's served-artifact probe already checks as
`api_version_contract`, and the version token on the records a consumer derives numbers from. This
section takes the second, because the first already has a reading and because a record is what a later
reader meets first. `docs/audit/contract-versions.json` is the register and
`scripts/measure_contract_versions.py` rebuilds it.

### What the eight readings declare

Nine of the fourteen files under `docs/audit/` carry a `recorded_at`: eight readings and this register.
The other five are gate inputs — a debt ceiling, a gitleaks ignore registry, an advisory exception
list, a lock-divergence list and an orphan-reads registry — and state no date. Of the eight readings, **four declare a token of their own**:
`attribution-reading/v1`, `execution-boundary-matrix/v1`, `export-lifecycle/v1` and
`independent-rerun/v1`. One declares only its input's: `evidence-alignment.json` carries
`evidence-alignment-frame/v1` as `frame_schema` and nothing about itself. Three declare nothing — both
authorization-coverage readings and the served-artifact probe, all written before any record carried a
token.

The five tokens are well-formed and use three different subjects: two end in `-reading`, one in
`-matrix`, one in `-frame`, one is bare. That is a vocabulary, not a policy — nothing says which
suffix a new record should take, and nothing says what changing one would mean. **No record carries a
field stating a bump rule**, which is the gap this item exists to close.

### What holds a token to the record

Three of the four are compared with something that is not the record itself: the attribution test
types both tokens, the boundary test compares a rebuild, and the export-lifecycle test compares the
record with its instrument's constant. The fourth is decoration — `independent-rerun.json`'s token is
written by the instrument, carried in the file, and read by its test without an assertion on the
value. The register records that as `check_kind: none`, and the contract test proves the label by
reading the consumer and finding the token absent, rather than by trusting the record's own sentence.

### The policy, and what enforces it

Five clauses, in force from 2026-11-12 and not back-dated onto the eight readings above:

| Clause | Rule | Enforced by |
|---|---|---|
| P1 | `schema` is `<subject>/vN`: a kebab-case subject naming the record's own artifact, then a decimal major from 1. A projection's token goes in `frame_schema` under the same form | the token form, in `--verify` and in the contract test |
| P2 | N increments when a consumer's arithmetic would change; adding a key or re-deriving a value for the same key does not | nothing mechanical — a bump edits the record and the register in one change, and the test fails while they disagree |
| P3 | no silent readers: a consumer compares the token, or refuses an unknown value explicitly | `check_kind` per row, plus the post-policy rule in `--verify` |
| P4 | a record that predates the policy and declares no token is read as `v0`, and is not retro-tagged | `effective_version` per row, derived rather than typed |
| P5 | the register travels with the record: every dated file under `docs/audit/` has a row in the change that adds it | the test compares the rows with the directory |

P4 decides what this page does not do: the three unversioned readings stay unversioned. Adding a token
to a record that was already taken would be a basis change in the sense of the third rule at the top
of this page, and this page's answer to a basis change is a new record, not an edited one.

### What would count as progress

Two things, neither of them a document. An assertion in the independent-rerun test would turn the one
decorated token into a checked one; a producer change that wrote a bump rule into each record would
replace the register's inference with the record's own statement. Until then the reading is that the
tree has version strings, no stated bump rule, and one convention that starts today — and the contract
test is what holds that convention in place.

## What this page is not

- Not a scorecard: no metric here has a target yet, and the ADR does not set one for S1.
- Not a substitute for the evidence: the numbers live in their own records and are linked, so a change in
  a definition cannot quietly rewrite history.
- Not complete. All four S1 rows carry a first reading, but each is a single observation: none of them
  establishes a rate over repeated runs, and the independent re-run sample is one bundle because only
  one recording in the tree states its own provenance. S2's four items each carry a reading now; the
  fourth reads the shape of the records rather than the behaviour they describe, and four readings
  are not a stage exit.
