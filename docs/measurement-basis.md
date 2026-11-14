# Measurement basis

ADR-003 sets one exit condition per stage, and this page is the basis for each reading that claims to
meet one. It is deliberately about arithmetic and provenance rather than about targets — a target
picked before the first reading is a preference, not a measurement.

S1 asks for each of four metrics to be recorded once; those readings are below. S2 asks what a
recorded run lets a reader point at: the execution-boundary matrix, the latency and failure
attribution reading, the export-first lifecycle and the contract-version policy are at the end of the
page. They are four of S2's four items, and the stage-exit review after them reads the ADR's four
clauses against one set of readings and declares S2 exited. That declaration is about the exit
condition only; what it leaves unclaimed is listed next to it.

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

### Second reading (2026-11-13)

The first reading is superseded. Two of its three `undecidable` cells gained a check, and the third
was re-attributed after ADR-004 asked what actually runs at request time:

- **process spawn.** The cell was recorded as fenced only by the absence of a process import. The
  format allowlist runs earlier and is what decides the cell: the reader is chosen from six data
  formats, so a loader that executes code cannot be reached through this surface. The observation
  about imports stays as a `read` layer; it is not what refuses the request.
- **filesystem write.** The body writes nothing, which is an observation. A check now captures the
  input's size, modification time and inode before the read and compares them after it, and refuses
  the result when they moved.
- **credential read.** Credential-shaped names and directories are refused before a reader is
  chosen.

The counts move from six open / six fenced / three undecidable to six open / nine fenced / none
undecidable, and `decidability` reaches 1.0. That is not a claim that the surface is contained: each
new cell carries a residual naming what its check does not observe — a write to a path the request
never names, an environment read performed without a path, and a loader added to the allowlist that
executes code. The record's `basis_change` field states the re-attribution in its own words, so a
reader comparing the two readings can tell an improved number from a moved ruler.

## S2 — latency and failure attribution

The second S2 item is not "how fast is the deterministic path". `benchmarks/baseline/README.md` already
answers that question in the negative: the same command on the same commit read 162.3, 73.04 and 89.56
milliseconds within minutes of each other. The question here is narrower and answerable — **what
fraction of a recorded run's clock, and which of its failures, can be pointed at a named part of the
record?** `docs/audit/attribution.json` is the reading, `tests/fixtures/attribution/frame.json` is the
projection it is computed from, and `scripts/measure_attribution.py --verify` rebuilds it field by
field.

### Latency: what a row can name

One clean-tree `dsa --limit 50 --out artifacts/bench-attribution` run supplies 50 rows whose manifest
states `llm_mode=stub` and `call_count=0`. Each row carries one `elapsed_ms`, one `duration_ms` per
tool call, the run object's `created_at` / `updated_at`, and — since ADR-004 D2 — the intervals the
run spent in each status. Three quantities follow without interpretation:

| Quantity | Definition | Why it is a boundary, not a benchmark |
|---|---|---|
| `tool_ms` | the sum of the row's `duration_ms` values | the only time named to an execution unit |
| `residual_ms` | `elapsed_ms - tool_ms` | planning, evidence assembly and report writing have no timestamps of their own |
| `outside_window_ms` | `max(0, elapsed_ms - (updated_at - created_at))` | time even the run object's own clock does not cover |

The second reading: 249 tool calls across 50 tasks, all recorded as `ok`. The per-task tool share has
a median of 0.3709 and a mean of 0.4542, ranging from 0.0 to 0.9529; every one of the 50 rows has a
positive residual, and every one carries the run's own stage intervals. One task runs past the run
object's window by more than the 10 ms resolution band, and the 50 rows together stand 730 ms outside
it. The 181 calls whose `duration_ms` is zero are the important part: the field is an integer
millisecond, so a sub-millisecond call is recorded as no time at all. The share is therefore a **lower
bound on what the record can name**, not a measurement of what tools cost. A second run of the same
clean tree at the same commit moved both the median share and the zero-duration count, so the frame
pins the one run it describes by hash rather than quoting a stable-looking number; the ledger keeps
the second observation as capture-time context, not as part of the reading.

The first reading recorded 0 of 50 rows with a stage field, because the run record had none to
carry. The change to 50 of 50 is a producer change, and the record says so in `basis_change` rather
than leaving it to be inferred from a diff. The first pass stays where it was recorded, as
`docs/audit/attribution-first.json` with a `superseded_by` pointer, and the second points back at it
with `supersedes` — so the pair reads as a ruler change rather than as a number that moved on its own.

### Failures: two recordings, one empty denominator

Two deterministic recordings ship in the tree, and neither is a random draw:

- `benchmarks/baseline/results.json` — 50 tasks, none failing. There is no failure to attribute, so
  the record says `not_measured` with the reason "empty denominator". It does not say 100%, and it
  does not say 0/0; both would turn an absent observation into a score.
- `benchmarks/external/datascibench/results/raw_runs.json` — re-recorded on the reviewed commit: 38
  runs the adapter supports, 33 of them not passing by its own `score >= 0.5` mark. Four of those runs
  carry a `FAILED` status and a passing score, because the evaluator grades artifacts and not the run's
  status; the record counts that disagreement in a field of its own rather than adding the two columns
  together. The first recording of this bundle held 45 supported runs and 40 non-passing ones, so the
  denominator moved with the recording — `basis_change` states it.

Attribution is counted at three depths, each derived from fields the record actually carries:

| Depth | What counts | Reading |
|---|---|---|
| outcome | the run's `outcome` value | 33 of 33 |
| artifact | a mechanical signal from the recorded counts: the run did not complete, or produced no report, no tool call, or no evidence | 16 of 33 (all sixteen did not complete) |
| stage | a `failure_stage` or `failure_code` whose value belongs to the closed vocabulary in `dsa_evaluation.failure_codes` | **33 of 33** |

The 17 remaining runs completed with a report, tool calls and evidence and were still graded below the
pass mark; their location is `evaluation` with the code `score_below_threshold`, which says the
evaluator's threshold refused the result and says nothing about why the score was low. Sixteen runs
stopped at `validation` with `validation_hard_fail`: the critic found tool errors the run had already
recorded, and that branch is where the refusal came from. Ten of the 33 carry partial credit, so
"failed" is not a binary state. **Stage-level attribution completeness is 33 of 33**, and every code
in it names a line of code rather than a reason. The empty baseline denominator is unchanged and still
cannot be improved by this reading.

### What changed, and what did not

The producer now writes what this instrument used to report as missing: a stage interval per status,
and one code from a vocabulary closed in code, refused by `assert_known` when a value comes from
anywhere else. Two things this page does not claim. The first is that a code explains a failure —
`score_below_threshold` is the location of a decision, not its cause, and the run that triggered it
carries no field that would name one. The second is that the external bundle is reproducible on a
clean clone: it needs the gitignored `.workspace/`, and the re-recording above is a census of the copy
this machine holds.

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

### The reading, second pass

The first pass (2026-11-11, `export-lifecycle/v1`) asked whether a digest was recorded and found it
in one event of six: `export_artifact` returned a SHA-256 and nothing else did. It stays at
`docs/audit/export-lifecycle-first.json` marked `superseded_by`, and the second reading points back
at it with `supersedes`, so a reader can see what moved instead of taking the new number's word.

**Three of three export-side events now record a digest.** `export_artifact` writes one payload,
reads the file back, raises instead of returning a digest the file does not hold, and reports
`verified`; `save_artifact` does the same and puts the digest in `metadata.sha256`, which is the field
the run record inherits; the bundle manifest carries a `files` list with one `sha256` and one byte
count per archived file, taken from the same bytes `writestr` receives; the 40 entries in the eight
committed `artifacts.json` records each carry `metadata.sha256`; and the plain report export keeps its
strip rule untouched and returns the digest beside the text through `export_with_digest`, which is
what lets the rule go on removing 64-hex tokens from prose.

Recording and checking are not the same claim, so the record now carries both. **Two of the three
export-side events compare the digest here** — the tools against a re-read of the file, the bundle
against the archive's own bytes. The third is `declared`: the 40 committed records name files under a
gitignored artifact root, so the field is counted and the bytes behind it are not re-opened by this
instrument. `scripts/backfill_artifact_digests.py` is what put those 40 digests in place, and it is
also the check: re-running it against a tree that holds the files reports whether any entry still
agrees with the bytes it names.

The parse question did not move: **one event in six has a parse check** — the consumer, which is
every reader after the fact. Re-reading after a write is a writer checking itself, not a consumer
parsing what it was handed, and the two are not added together.

**Parseability today: 48 of 48 committed exports read back** — 40 JSON parsed and 8 Markdown decoded.
`csv`, `png` and `xlsx` have no committed export: run artifacts live under a gitignored root, so a
number there would describe one machine. Those three are recorded `not_measured` with that reason,
not as zero.

### The divergence the first pass recorded

ADR-003's bundle sentence names five elements, artifact hashes among them, and the manifest the first
pass read carried none of them as a field. That no longer holds for the digest: `files` names each
archived file with its SHA-256 and its byte count, so two bundles of different bytes now differ in
their manifests. This reading says nothing about the other four elements; it records only that the
one it could check is now present.

### What this reading still does not claim

The digests are not signatures. Nobody outside this repository compares them on receipt, so a
recipient who recomputes one learns that the bytes match the number the server reported, not that the
server is trustworthy. The 40 declared digests are the weaker case in the same direction: they name
bytes this tree does not hold, so a reader either has the files or has a number.

## S2 — the contract-version policy

The ADR names this item and does not define it. Two readings of the phrase are available: the
`/version` payload a deployed API discloses, which S1's served-artifact probe already checks as
`api_version_contract`, and the version token on the records a consumer derives numbers from. This
section takes the second, because the first already has a reading and because a record is what a later
reader meets first. `docs/audit/contract-versions.json` is the register and
`scripts/measure_contract_versions.py` rebuilds it.

### What the ten readings declare

Eleven of the sixteen files under `docs/audit/` carry a `recorded_at`: ten readings and this register.
The other five are gate inputs — a debt ceiling, a gitleaks ignore registry, an advisory exception
list, a lock-divergence list and an orphan-reads registry — and state no date. Of the ten readings,
**six declare a token of their own**: `attribution-reading/v1` and `attribution-reading/v2`,
`execution-boundary-matrix/v2`, `export-lifecycle/v1` and `export-lifecycle/v2` (two pairs, each the
same surface at two passes) and `independent-rerun/v1`. One declares only its input's:
`evidence-alignment.json` carries `evidence-alignment-frame/v1` as `frame_schema` and nothing about
itself. Three declare nothing — both authorization-coverage readings and the served-artifact probe,
all written before any record carried a token.

The seven tokens are well-formed and share no vocabulary: `-reading` appears twice, `-matrix` and
`-frame` once each, three are bare, and two subjects appear at two majors — the attribution reading and
the export lifecycle, in both cases because the second pass changed what a consumer's arithmetic would
do. That is a vocabulary, not a policy — nothing says which suffix a new record should take, and
nothing says what changing one would mean. **No record carries a field stating a bump rule**, which is
the gap this item exists to close.

### What holds a token to the record

Five of the six are compared with something that is not the record itself: the attribution test types
both of its passes' tokens and their two zero counts, the boundary test compares a rebuild, and the
export-lifecycle test compares the second pass with its instrument's constant and types the first
pass's token, so a kept file cannot quietly acquire a new one. The sixth carries a token nothing
asserts — `independent-rerun.json`, whose token is written by the instrument and read by its test
without a comparison. The register records it as `check_kind: none`, and the contract test proves the
label by reading the consumer and finding the token absent, rather than by trusting the record's own
sentence.

### The policy, and what enforces it

Five clauses, in force from 2026-11-12 and not back-dated: seven of the ten readings above predate
them, and the three re-taken since — attribution, the boundary and the export lifecycle — declare
tokens the form accepts.

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

## Stage exit — the four clauses against the four readings

ADR-003's migration table gives S2 one exit condition with four clauses, and its work column four
items. They are not the same four. Three clauses name a reading: boundary decidability is
`docs/audit/execution-boundary.json`, attribution completeness is `docs/audit/attribution.json`, and
artifact parseability is `docs/audit/export-lifecycle.json`. The fourth clause — `matrix_valid` and
`publication_ready` never conflated — is a separation between two gates, not one of the work items.
The fourth item, the contract-version policy (`docs/audit/contract-versions.json`), reads the shape
of records rather than the behaviour they describe; no exit clause names it.

| Clause | Where the evidence lives | What the reading actually says |
|---|---|---|
| Boundary decidability | `docs/audit/execution-boundary.json` | 15 of 15 cells are decided by a request-time check; 0 are undecidable, 6 open and 9 fenced |
| Attribution completeness | `docs/audit/attribution.json` | 33 of 33 non-passing external-bundle runs carry a `failure_stage` and a `failure_code` drawn from the vocabulary closed in `dsa_evaluation.failure_codes`, and 50 of 50 tasks carry the intervals the graph recorded; the frozen baseline has an empty denominator and is `not_measured` |
| Artifact parseability | `docs/audit/export-lifecycle.json` | 48 of 48 committed exports parse at the consumer end; 3 of 3 export-side events record a digest (2 of them compared here, the third declared), 1 of 6 lifecycle events runs a parse check, and `csv`, `png` and `xlsx` are `not_measured` |
| `matrix_valid` and `publication_ready` never conflated | `packages/evaluation/src/dsa_evaluation/publication.py` | `publication_ready = matrix_valid and scope == "full"`, so a valid matrix is not a publication decision; each of the four readings says in its own `not_claimed` that `publication_ready` keeps its own gate |

The first three clauses are recorded; the fourth holds as a property of the code and of the records'
own disclaimers. Three gaps were named once — a boundary cell no check could decide, an attribution
that stopped at the artefact, an export whose bytes nobody re-read — and ADR-004 closed them one at a
time. The boundary now names a request-time check in every cell, and the record's `basis_change` says
which cell was re-attributed rather than re-worded. Attribution carries a stage and a code from a
vocabulary the code refuses to extend by accident, and every task carries the intervals the graph
itself recorded. Every export surface writes a digest, and the two whose bytes this tree holds also
compare it.

### The four predicates on one set of readings

A stage exit is not four numbers; it is one judgement that all four clauses hold on the readings that
stand today. Each clause reduces to a predicate over its record, and each record names the commit its
evidence lives at: the boundary and export readings re-read this tree at `7e63717512be`, while the
attribution reading keeps `5cbee4de0906`, the tree its run was taken on, because re-deriving the
record on a later tree may not move a field that describes a finished run. What makes the four one
set is that each is the latest record for its clause, none is superseded, and the two that were
re-taken (`attribution.json`, `export-lifecycle.json`) name the record they replace:

| Clause predicate | Read from | Holds because |
|---|---|---|
| `undecidable == 0` | `execution-boundary.json` → `summary.undecidable` | 0 of 15 cells; every cell names a check that runs at request time |
| `stage_level == non_passing` | `attribution.json` → `failures.external_bundle` | 33 of 33 non-passing runs carry a stage and a code |
| `tasks_with_stage_boundaries == tasks` | `attribution.json` → `latency` | 50 of 50 tasks carry the intervals the graph recorded |
| `export_side_events_with_a_digest == export_side_events` | `export-lifecycle.json` → `summary` | 3 of 3; 2 of those digests are compared in this tree and the third is declared by a surface whose bytes it does not hold |

**The stage is exited.** S2's exit condition holds on that set of readings, the ADR status line now
says `S2 complete`, and `tests/contract/test_s2_exit_review.py` derives each predicate above from its
record and refuses the declaration if any of them is false — so the sentence in bold fails the build
rather than outliving the numbers. The judgement, taken on 2026-11-14 at the maintainer's instruction,
is recorded in `AUDIT_LEDGER.md`; this page carries the arithmetic it rests on.

What the exit does not claim is the part worth writing down:

- **Not a trend.** Each of the three readings is a single observation, pinned to the commit its
  evidence lives at. The two that have a second pass differ from their first because a producer
  changed — a run record that gained stages, an exporter that gained digests — so the pair records a
  difference in the instrument, not a rate over repeated runs.
- **Not `publication_ready`.** That gate is `matrix_valid` and `scope == "full"`, and nothing here
  moves it; the four readings each say so in their own `not_claimed`.
- **Not full export coverage.** `csv`, `png` and `xlsx` remain `not_measured`, and one of six
  lifecycle events runs a parse check. The exit clause asks that every export-side event record a
  digest, not that every export class be re-read.
- **Not S3.** Starting it asks for the open questions in the ADR's Appendix C, and the second of them
  — model credentials with a spend ceiling — is still `not provided`.

## What this page is not

- Not a scorecard: no metric here has a target yet, and the ADR does not set one for S1.
- Not a substitute for the evidence: the numbers live in their own records and are linked, so a change in
  a definition cannot quietly rewrite history.
- Not complete. All four S1 rows carry a first reading, but each is a single observation: none of them
  establishes a rate over repeated runs, and the independent re-run sample is one bundle because only
  one recording in the tree states its own provenance. S2's four items each carry a reading and the
  stage's exit condition holds on them, but the fourth reads the shape of the records rather than the
  behaviour they describe, and an exit is not a claim that a reading will still hold next week.
