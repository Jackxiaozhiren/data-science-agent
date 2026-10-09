# Changelog

## Unreleased — Quality-gate hardening (P0/P1 audit follow-through)

No public API breakage except documented REST contract corrections below.
Measured on 2026-09-24: `ruff check` clean (was 54 errors), `ruff format`
clean, `mypy .` clean on 114 files (was duplicate-module crash; scoped-only
before), `pytest 395 passed` (was 345), coverage **80.04%** with
`fail_under = 79` ratchet (was 0% — source misconfigured + `_vendor`
shadowing + missing greenlet concurrency).

### Fixed

- `mypy .` now passes: `explicit_package_bases`, non-shipped excludes,
  `dsa_jupyter` IPython-shim typing fixes.
- Coverage now measures workspace source (`dsa_viz` name fix), demotes
  `_vendor` in `conftest.py`, tracks SQLAlchemy greenlets.
- 79 MB xlsx OOM: `openpyxl` read-only streaming above 10 MB
  (`stream_threshold_bytes`).
- Ephemeral DB: lifespan-owned `init_db()` (+ `/tmp` warning); per-request
  `create_all` removed from all three services.
- API abuse surface: security headers, per-IP rate limits (analysis 60/min,
  upload 30/min, 429 + `Retry-After`), generic 500s (frontend `detail`
  envelope unchanged).
- SQL sandbox: `read_*`/`glob(`/`*_scan`/COPY-any/`CREATE`/`INSTALL` denied;
  planner identifiers double-quote escaped.
- REST: creates return 201 + `Location`; lists paginated (`limit`/`offset` +
  additive `total`). Frontend uses `res.ok`, unaffected.
- Web: `next.config.mjs` security headers (verified live, 200 + headers).
- Docker: non-root users (`appuser`/`node`) + `HEALTHCHECK`; both images
  boot-tested healthy (also fixed web image missing `node_modules`).
- Docs: `docs/api.md` contract table; ROADMAP #8/#9/#10 marked closed;
  `.gitignore` covers `/output/`, `.playwright-cli/`, `*.tsbuildinfo`.
- Web: `next` 16.3.4 → 16.3.8 for GHSA-vcvr-r3jv-pc5j (critical RCE in
  `next/og` `ImageResponse`; vulnerable range `>= 16.2.0, < 16.3.6`). The app
  imports no `next/og` surface, but the pin sat inside the range and CI's
  `npm audit --audit-level=high` gate failed on it. Both lockfiles (root
  workspace + `apps/web`) regenerated; the diff touches 10 `next`/`@next/*`
  packages and nothing else.
- The planner stopped reading the acronym `ate` (average treatment effect) as a substring. The
  intent keyword was matched with `k in q`, like the stems around it, so *create*, *validate*,
  *duplicates*, *estimate*, *calculate*, *correlated* and *state* all registered as a causal
  request: 33 of the 150 catalog tasks carried a `causal_check` step nobody asked for. The report
  then used causal phrasing, the critic flagged `S08` "causal language without causal evidence",
  and four tasks (`eda-01`, `stats-06`, `clf-03`, `viz-01`) scored FAILED because of it. `ate` is
  now word-bounded and everything else keeps its stem matching. Benchmark: 50 tasks
  **0.92 → 1.00**, and the CI `--limit 5` probe **0.8 → 1.0**.
- The planner can no longer mistake "I could not read this dataset" for "this dataset has
  no numeric columns". `_numeric_columns()` returned `[]` for both, and
  `heuristics_plan`'s `_numeric_columns(path) or <guess-by-column-name>` overwrote the fact
  with the guess, so a text-only dataset had its text columns planned as numeric. It now
  returns `None` when unknown, and the name-based guess runs only in that case — plans
  unchanged for every dataset the benchmark can reach (150 catalog plans, identical digest
  against a `git archive HEAD` export).
- `DSA_MAX_COST_USD` is now enforced or refused, never quietly absent. A malformed
  value (`5 USD`, `two`) or a negative one used to parse-fail into `None`, and both
  provider guards read `if cap is not None` — so a configured spend ceiling disabled
  itself and paid calls continued uncapped, contradicting `docs/real-model-evaluation.md`
  ("loud error, no silent stop"). Unset or blank still means no cap; a number still
  means that cap; anything else raises `ValueError` naming the variable, from outside
  any `try` that could absorb it.
- `scripts/check_public_claims.py` can no longer report "clean" about a file it could
  not read. `scan_file()` used to return `[]` on any read error, silently shrinking the
  gate's own scope; an unreadable scanned document is now an `unreadable_file` finding,
  and the severity list moved from an inline tuple into `HIGH_SEVERITY_PREFIXES` so that
  membership in it is testable rather than positional.
- The evaluator_v2 `ci_correctness` dimension no longer reports a wrong answer about a
  malformed confidence interval. `statistical_eval` dropped any CI pair that would not
  parse, so a run that emitted a garbage CI was scored `no CI emitted` (absence), and —
  worse — one good pair alongside a bad one scored `score=1.0, ci valid`. Malformed
  readings are now counted: `ci invalid` with `S05`, while a genuinely absent CI still
  reads as absent. The handler narrowed from `Exception` to `(TypeError, ValueError)`.
- `discover_plugins(..., strict=True)` now raises `PluginDiscoveryError` naming the manifest
  that could not be parsed, instead of dropping a broken plugin from the registry with no
  reason (its sibling `validate_plugin` already reported `manifest parse failed: …`; the
  default behaviour is unchanged, so `dsa plugin list` still shows what parses). No shipped
  caller passes `strict=True` yet — surfacing this in the CLI changes its JSON output shape
  and is left as a decision (`AUDIT_LEDGER.md` §94, D-L3-06).
- `PluginManifest.compute_hash()` no longer collapses three different worlds onto one
  digest. It used to hash name + entrypoint whenever the plugin root was absent, empty,
  or never supplied, and skipped any file it could not read — so a missing install hashed
  identically to no check at all, and a disk error hashed identically to a deleted file.
  Each state is now mixed into the digest, an unreadable file is recorded as unreadable
  rather than gone, and the handler is `except OSError` instead of `except Exception`
  (the wider catch also absorbed `ValueError`, i.e. a caller's deliberate refusal).
  Note: nothing calls this method yet — see `AUDIT_LEDGER.md` §93 / D-L3-04; it is fixed,
  not advertised.
- Benchmark provenance no longer fails silently: the reproduction manifest's
  `datasets_sha256` now comes from `_datasets_sha256()` with an accompanying
  `datasets_sha256_note` naming why a hash is absent (and no longer reports a
  hash of nothing for a missing datasets dir), and `run_benchmark` records
  `details["statistical_eval_error"]` when the evaluator_v2 dimensions cannot be
  attached, instead of dropping them without a trace.
- `Reproduction().run()` no longer publishes numbers the artifact never held
  (`AUDIT_LEDGER.md` §101). Two defects, one root -- the facade read keys it assumed rather than
  keys the harness writes. First, `trajectory` was always `0.0`: it read `reproduction_score`'s
  `trajectory` key, which no producer writes, while the harness publishes the trajectory rate as
  `semantic`. On a reproduction run into the gitignored `reproduction/v2/` directory every dimension
  is `1.0`, while the public SDK reported `trajectory=0.0` -- on every run. Second, a missing or
  unparseable `comparison.json`, one with no `reproduction_score`, and one missing a dimension the
  facade publishes all returned the same `0.0` defaults with no signal. The map between the two
  sides is now the named constant `REPRODUCTION_DIMENSION_KEYS`, absent dimensions are reported by
  name, and a new additive `ReproductionResult.error` field carries the reason (the harness's own
  failure text is appended when the fallback also failed). A measured `0.0` still reports
  `error is None`; the Stable constructor and every existing call site keep working. `numerical`,
  `statistical` and `evidence` are still dropped by the facade -- filed as D-L3-14.
- The reproducibility levels now name the equality that decided them (`AUDIT_LEDGER.md` §102).
  `compare_runs` reads `dataset_sha256` and `environment`, which `build_experiment_json` writes but
  the reproduction harness never passes: it feeds `AnalysisState` dumps, which carry neither, so L2
  was decided by `dataset_id` string equality and L3 by a lenient pass -- two runs over different
  bytes of the same dataset id reported `L2_same_data: True`, while `comparison.json`'s own `method`
  string advertised "L2 data hash, L3 env". `details` now carries `L1_basis`/`L2_basis`/`L3_basis`/
  `L5_basis`, `dataset_sha256_match` reports `None` unless a hash pair was actually compared, and the
  method string describes the conditional. No level's value moved: a characterisation test asserts the
  booleans against the pre-fix formulas across 8 record-shape pairs. Making L2/L3 real checks by
  feeding the harness its designed record followed in §104 (that record is untracked output, so no
  published number was at stake -- the release-decision framing here was wrong and is corrected).
- The reproduction harness now carries that record (§104, closing D-L3-15). `run_benchmark` captures the
  dataset's `sha256` and the run's `environment` **before** each task and stores both in its `raw_runs`
  record; `dsa_evaluation.cli._comparison_record` merges them into what `compare_runs` receives. So L2 is
  decided by content, not by identifier: two runs of the same `dataset_id` over different bytes now
  report `L2_same_data: False`, where before §104 they reported `True`. A run with no hash still
  reports its weaker basis instead of implying a comparison. Additive to `raw_runs.json`; handler-neutral.
- `dsa_agent.tool_evidence.build_tool_evidence` no longer manufactures a confident evidence record from
  an object that is not that tool's result (§106). Every branch read through
  `getattr(output, name, default)`, so a fieldless result became `Correlation  vs : r=0.000` at
  confidence 0.8, `Assumption check: ` with `passed: true`, `SQL returned 0 rows` from an object with no
  `row_count` at all -- measured at 13 of 13 handled tools. It is latent rather than live: both call
  sites guard on `ok and output is not None` and the executor returns `ok=False` for any result whose
  `status != "ok"`, so the guard belongs in the builder for the next caller. A new `EVIDENCE_FIELDS`
  table names the attributes each claim requires and short-circuits to `None` when one is missing, with
  tests pinning that every tuple is a subset of the tool's declared `output_model` (the tools differ:
  `train_model` has no `metrics` field) and that an *empty* answer is still evidence -- `row_count=0`
  keeps proving "SQL returned 0 rows". Differential against the pre-fix module, rebuilt from git: zero
  changes on populated outputs, 13 flips on fieldless ones.
- `dsa_agent.planner` no longer computes a keyword signal it cannot use (§107). The line read
  ``if wants_viz or True:`` -- `wants_viz` was derived from six visualization keywords and consulted
  nowhere else, so the branch could only ever be true. Measured against the shipped v2 catalog
  (100 tasks, 13 queries naming a visualization, 0 plans without a chart), the unconditional chart is the
  product rule: honouring the keyword would have removed the evidence chart from **87 of 100** plans. The
  tautology is gone, the block dedented, and the rule is now stated and asserted --
  `tests/unit/test_planner_chart_invariant.py` pins both that no plan lacks an evidence chart and that no
  planner condition may be a tautology (AST, not grep). Behaviour-preserving: the pre-change planner was
  re-imported from a copy and run over all 100 tasks, with 0 plans differing.
- The MCP `analyze` surface now publishes the evidence-critic verdicts (§108, Phase 4 target 3). Its
  result payload was the only one of the five interfaces (CLI/SDK/REST/MCP/Jupyter) that omitted
  `validation`, so an MCP client could not distinguish a validated analysis from an unvalidated one
  while the notebook, SDK and REST all could. `validation` and `error` are added to the payload, and the
  advertised output schema now declares them plus `tool_calls` and `analysis_id`, which were already
  emitted but undeclared -- a validating client is entitled to drop an undeclared key. Additive only.
- New gate: `scripts/find_orphan_reads.py` (--check wired into CI and both contributing guides) reports
  every `record.get("key", default)` in shipped code whose key nothing in the repository writes -- the
  shape §101's `trajectory` bug hid behind. 14 such reads remain, each declared in
  `docs/audit/orphan-reads.json` with the outside system that supplies it; a new orphan or a stale
  entry both fail, and `--seed` writes empty fields rather than placeholder text so an unreviewed list
  cannot ship.
- The `%dsa` notebook magics no longer swallow an argument they do not recognise (§110). Each parsing
  handler bound `parse_known_args`'s leftover list to `_` and dropped it, so
  `%dsa profile data.csv --jsoon` printed nothing about the typo and ran as if `--json` had been given.
  A new `_known_args` helper reports the unrecognised tokens on stderr (verified through a live IPython
  shell: `%dsa profile: ignoring unrecognized arguments: --jsoon`) while the cell output is unchanged;
  unrecognised arguments are still ignored, and making them an error is filed as D-L3-19. This also
  closes the last unexamined sites of the L3 sentinel census: the three `except SystemExit` handlers are
  benign -- argparse writes its usage block to stderr first (110-113 bytes measured) -- and the two AST
  pins now forbid re-binding those leftovers to `_`.
- Artifact timestamps now reach MCP clients as ISO 8601 (`2026-10-05T03:09:28.604628Z`) instead of
  Python's `str(datetime)` with a space (`2026-10-05 03:09:28.604628+00:00`), which is not RFC 3339
  (§111). It is the only field that changed: a differential over a real run compared evidence, insights,
  tool_calls, validation and report_markdown as identical, and pinned the format with
  `test_timestamps_reach_the_mcp_client_in_iso_8601`.
- `benchmarks/baseline/README.md` no longer claims CI enforces the freeze (§113). The tolerance bullet
  read "any W2+ PR that drops `task_success_rate` or raises `unsupported_claim_rate` without ADR fails
  CI"; `.github/workflows/ci.yml` contains zero references to `benchmarks/baseline`, and the file's own
  scope notes two paragraphs above already said nothing recomputes the snapshot. The bullet now names
  the check that does exist and states that no automated check recomputes the artifact. Its dated gate
  counts ("86 tests pass · 74% coverage branch · mypy 81 files clean · ruff 184 frozen · next 7/7") are
  removed rather than corrected: §76 had already deleted the literal `86 tests` rule from the claim
  checker because it could only certify transcription, and the figure went on living in the one document
  no prose guard read.
- The reproduce section now declares the mode the documented command runs in (§113). `dsa --limit 50`
  resolves `DSA_LLM_MODE` to `stub` -- heuristic provider, `call_count: 0` in the manifest a run writes
  -- while the frozen `results.json` carries no `execution` block and no `run_manifest.json` was ever
  committed, so neither side of the prescribed `diff` records what produced it. Measured at `9f6ab35`,
  four runs: every accuracy field reproduces exactly, `unsupported_claim_rate` reads 0.0 against the 0.06
  stored here (a reduction, and not attributed further), and `mean_latency_ms` spans 73.04-162.3 on the
  same commit, so a latency delta in that diff is not evidence of anything.
- `scripts/check_public_claims.py` declared exemptions for two trees it never opened (§113, Phase 4
  target 1). `HISTORICAL_PREFIXES` listed `research/` and `benchmarks/`, and measured against
  `SCAN_GLOBS` neither was reachable by a single pattern -- the printed "N skipped as historical" never
  counted them, and the list justified itself with a "34 matches, 0 of them real" figure taken from a
  rule set §76 had since retired (re-measured against today's three rules: 4 matches across the whole
  exempt surface). `research/**/*.md` is now reached and counted (34 files), `benchmarks/**/README.md`
  is reached and *scanned* rather than exempt, the vendored `.workspace` clone is excluded as the
  dependency tree it is, and a guard fails if any declared exemption is unreachable by any glob.
  Scanned surface 14 → 19 files; `0 issues` before and after.

- One table in the audit ledger did not render (`AUDIT_LEDGER.md`), and a guard now fails if any tracked
  markdown has a pipe table whose second line is not a delimiter row (§118,
  `tests/test_markdown_tables_render.py`). A blank line had split a long claim/evidence table so that its
  continuation rows carried no header; the renderer showed them as a paragraph, and the record looked
  complete. Measured with the parser the repository builds with: 1 broken block in 249, across 136 tracked
  `.md` files. The repair is additive (27 lines inserted, 0 deleted), and the first draft of the guard
  dropped its `# noqa: S603` once `tests/**/*`'s per-file-ignores were read -- adding it would have been
  the 43rd suppression directive against a ceiling of 42.

- `source-map-js` 1.2.1 → 1.2.2 in both lockfiles, closing GHSA-68fv-2mgg-jv7q (high, CVSS 7.5 --
  event-loop denial of service through indexed source-map section offsets), which npm published after the
  previous green run and which the advisory gate caught on the next push (`AUDIT_LEDGER.md` §119). A patch
  inside `postcss`'s own `^1.2.1` requirement, so no manifest changed and no `package.json` was edited:
  `git diff` is three lines per lockfile (version, resolved, integrity). The exemption file was deliberately
  not touched -- `docs/audit/npm-advisory-exceptions.json` admits only advisories with no published fix, and
  this one had one. Verified: `npm ci`, `check_npm_workspace_lock.py`, `npm run build` and
  `check_npm_advisories.py` all exit 0 against the refreshed lock.
- The pre-PR gate list is now derived from `ci.yml` instead of remembered. `tests/test_ci_gate_integrity.py`
  compared the contributor guides against a hand-typed vocabulary of 8 gates and asserted that exactly 8
  were found, so 19 of CI's 27 run steps were invisible to it -- among them `sync_vendor.py --check`,
  `check_npm_workspace_lock.py`, `uv lock --check`, `mkdocs build --strict`, the SBOM assertion,
  `node apps/web/scripts/regression.mjs` and the benchmark smoke (`AUDIT_LEDGER.md` §120, Phase 4 targets 1
  and 6). Nine more gates are now classified, eight genuinely CI-only steps are declared with a reason each,
  and any step that is neither fails the suite. Both guides were rewritten to CI's own spelling, which is what
  the "mirrors ci.yml verbatim" line above them has claimed since §113 and could not previously be checked.
- Six of the fifteen scripts under `scripts/` carried a `#!/usr/bin/env` shebang but no executable bit, so
  `./scripts/dev.sh` and `./scripts/sync_vendor.py` failed with `permission denied` (exit 126, measured
  against a HEAD copy) while `uv run python scripts/sync_vendor.py` worked. The convention was documented
  and simply not followed. A two-way guard now enforces it over every shipped script: shebang implies `+x`,
  `+x` implies shebang, and the eight module-style helpers with neither are held in place by the same rule
  rather than exempted (`AUDIT_LEDGER.md` §121).

- Run artefacts had **four** directories and one rule did not exist. Six writers derived the artefact root
  from their own installed location (`Path(__file__).resolve().parents[4] / "artifacts"`), which resolves by
  module depth, not by layout: the agent modules chose `<repo>/artifacts`, the tool modules
  `<repo>/packages/artifacts`, the vendored tools `<repo>/src/artifacts`, and an installed wheel the
  interpreter's own `site-packages` tree. Both readers used the working directory instead, so a run started
  in any other directory wrote a report the MCP server answered `not found` about. One rule now --
  `$DSA_ARTIFACT_ROOT`, else `<cwd>/artifacts` -- in `dsa_datasets.artifact_paths.artifact_root`, asked by
  all eight sites. Measured blast radius on this machine: the suite used to leave output in three roots
  (125,854 / 25,183 / 6,154 files); after the change one root grew (+846) and the other two grew by zero.
  Placement was decided by import cost, not by name: `import dsa_tools` costs 2791 ms and drags matplotlib
  and sklearn behind it, so the rule lives in the layer every caller already loads (`AUDIT_LEDGER.md` §122,
  closing D-L4-07).
- `run_id` was concatenated straight into the artefact write path by `save_artifact` and `generate_report`,
  while only `filename` was checked for `..` and separators -- and the `relative_to(root)` guard below it
  cannot help, because `root` already contains the escape. Reproduced: `run_id="../../escaped"` wrote two
  directories above the artefact root, from any MCP tool call. Every component passed to the resolver must
  now be one safe path segment, or the tool refuses with `Invalid run_id` and creates nothing (D-L4-09).
  Handler-neutral by construction: the resolver grew `is_safe_segment()` rather than the tools growing a
  `try/except` -- the first draft's two handlers took `debt.exceptHandlers` from 185 to 187 and the ratchet
  went red, which is the gate doing its job.
- `docs/reproducibility.md` told readers to run `dsa reproduce --run <run_id>`, a flag the CLI has never
  had; the page also now documents the artefact root and `$DSA_ARTIFACT_ROOT`. Measuring it surfaced a
  second, unfixed defect (D-L4-11, `AUDIT_LEDGER.md` §122): `dsa reproduce --json` and
  `dsa reproduce --benchmark v2` both exit **2** with `unrecognized arguments`, because the sub-parser
  advertises flags the handler's own parser refuses. `dsa reproduce` works bare, and `dsa --reproduce
  v2 --out …` is the spelling that takes arguments.
- `dsa reproduce` now accepts the flags it advertises (D-L4-11, `AUDIT_LEDGER.md` §123). The subcommand
  declared `--json` on its parser and then re-parsed `sys.argv[2:]` with a second parser built inside the
  handler, so measured on the shipped entry point `dsa reproduce --benchmark v2` exited 2 with
  `unrecognized arguments: --benchmark v2` and `dsa reproduce --json` exited 2 with
  `unrecognized arguments: --json`: the four real flags were refused before the handler that reads them,
  and the one advertised flag was refused by it. `--benchmark`, `--catalog`, `--datasets` and `--out` are
  declared on the sub-parser now (with their own `dest` names, so they cannot collide with the top-level
  benchmark flags) and the second parser is gone. `--json` was removed instead of implemented -- the
  reproduction run prints text and returns `None`, writing its comparison to `<out>/comparison.json` --
  so there was nothing to serialise and inventing a payload would have been a feature posing as a fix.
  `docs/architecture.md` had documented `dsa reproduce --benchmark v2` all along; the code was the wrong
  side of that claim.

- The documentation site was hiding **23 of its own pages**: they were tracked under `docs/`, built by
  mkdocs, and referenced by no `nav:` entry -- including `security/VERIFY_RELEASE.md`,
  `security/VERIFY_PYPI_RELEASE.md`, `security/OSPS_BASELINE.md`, `production-hardening.md` and the entire
  `v4_3/` evidence record (11 files, 1,594 lines). The nav is now 8 sections over 47 pages (was 21 entries
  over 24), the counter `capabilities.navOrphanPages` reads **0** under its unchanged ceiling, and
  `tests/test_docs_nav_coverage.py` derives reachability from the collector's own definition so the gate and
  the test cannot disagree. URLs are unchanged -- grouping does not move a page, verified against the built
  tree (`AUDIT_LEDGER.md` §124, Phase 4 target 7).
- `docs/getting-started.md`'s runtime floors are derived instead of remembered, and the page now states the
  divergence it was hiding: CI builds and tests the dashboard on Node **22** while `docker/Dockerfile.web`
  ships `node:20-alpine`, so the container runs a Node the dashboard build has never been proven on
  (D-L4-14; the base-image change itself is left to a machine with a docker daemon). Python's floor is
  singular and true: `requires-python = ">=3.12"` and CI's `python-version: "3.12"`, pinned by
  `tests/test_runtime_version_claims.py` against all four declaring files.
- `docs/announcements/README.md` explains what `latest.md` actually is -- a copy the release workflow writes
  at publish time, not a live lookup. Measured state (D-L4-13, open): `latest.md` names v4.2.10 while
  `pyproject.toml`, `data_science_agent.__version__` and the newest tag all say **4.4.0**, and the five
  intervening tags have CHANGELOG sections but no announcement copy. Regenerating it is a release action, so
  the docs stop short of claiming to be current.

- A run whose report could not be written to disk reported `COMPLETED` while its own `error` field said
  otherwise, in both graphs: `graph.py` assigned the verdict from critic hard-fails alone after catching
  the writer's exception, and `reporting.py` hardcoded `"COMPLETED"` twice, two lines below the branch
  that records the failure. `FAILED` is now the verdict whenever the report did not reach disk, and the
  computed `report_markdown`, evidence, insights and validation results stay in the payload -- the flip
  withdraws the delivery claim, it does not discard the analysis. Chosen over a new "degraded" status
  because the consumer already treats the agent's verdict as part of success
  (`dsa_evaluation/metrics.py:77-84`, pinned by `test_task_success_refuses_a_run_that_reported_failure`)
  and FAILED is already in the published vocabulary that SDK, REST, MCP and the Web all read
  (`AUDIT_LEDGER.md` §125, closing D-L4-08). Benchmark blast radius measured: 50 v2 tasks still
  `Task success rate: 1.0` with 0 of 50 rows carrying an `error`.

- `sharp` 0.35.4 -> 0.35.5 for GHSA-wq5f-xc86-pv6w ("Vulnerability in librsvg dependency
  CVE-2026-96889", CWE-416 use-after-free), affected range `< 0.35.5`, high. `sharp` is a *direct*
  pinned dependency of `apps/web` -- pinned by `5df7aff` precisely so this project controls that version
  instead of inheriting one from `next` -- and the advisory arrived with a published non-major fix, so
  the §119 rule applies: bump, do not exempt. `docs/audit/npm-advisory-exceptions.json` is unchanged.
  Lockfile delta parsed against HEAD rather than eyeballed: 28 entries changed, 0 added, 0 removed, all
  of them `sharp`, its `@img/sharp-*` platform packages and its `@img/sharp-libvips-*` binaries, in both
  the workspace-root and `apps/web` locks. Verified the way CI does it: `check_npm_advisories.py` 0,
  `check_npm_workspace_lock.py` 0, `npm ci` 0 (256 packages, `node_modules/sharp` reads 0.35.5),
  `npm run build` 0. Exposure for the record: `apps/web` imports `next/image` nowhere (the single grep hit
  is the generated `next-env.d.ts`), so the image-optimisation route that loads sharp is unused today
  (`AUDIT_LEDGER.md` §126).

- 75 of the 118 declared `per-file-ignores` entries in `pyproject.toml` could not fire: the rule never
  occurs in that tree, or `lint.ignore` already covers it globally (the `S101` entries in `tests`,
  `packages/plugins`, `packages/mcp` and `apps/jupyter`, and the `E501` entries in `packages/plugins` and
  `apps/jupyter`), or the same rule was listed twice in one pattern (`tests/**/*` declared `S110` twice;
  `packages/tools/**/*` declared `SIM103` and `UP046` twice). `packages/mcp/**/*` was inert in all seven
  entries and is removed. They are deleted rather than kept as documentation, because an exemption that
  cannot be observed reads as a decision, and nothing counted or guarded that surface
  (`AUDIT_LEDGER.md` §127, Phase 4 target 1). `ruff check` over CI's six paths still exits 0 afterwards,
  which is the proof that nothing real was being suppressed.

- `scripts/sync_vendor.py --check` named the package and a count (`dsa_agent: 1 file(s) differ`) and
  nothing else, so diagnosing a red `main` meant comparing every file in that package by hand. It now
  lists the offending paths for each category -- differing, absent from `_vendor`, present only in the
  mirror -- capped at 12 with a `+N more` tail, with the count text unchanged. Both contributor guides also
  state the ordering the failure actually taught: mirror after formatting, `--check` last before
  committing, and run `scripts/run_gates.sh` rather than a hand-picked subset of gates -- the runner already
  ends with the check I had skipped because it was red for someone else's file, which is the third time this
  run a skipped or narrowed gate cost a wrong green (§128, following §127.1).

- `scripts/check_public_claims.py` advertised a surface it did not read: `HISTORICAL_PREFIXES` contained
  `docs/` whole, so all 47 markdown files under `docs/` -- including `getting-started.md`, `api.md`,
  `architecture.md`, `security.md` and the release-verification guides -- were classified as historical
  records and skipped, while the tool printed "0 issues (scanned 19 file(s); 85 skipped as historical)".
  The exemption is now by name and only where the content is genuinely dated: `docs/v4_3/` (11 files),
  `docs/announcements/` (3) and `docs/ADR/` (2), leaving 50 files scanned from 19 and **0 issues** on the
  wider net -- the widening cost no suppression, no `noqa` and no rule tuning
  (`AUDIT_LEDGER.md` §130, Phase 4 target 1). `docs/audit/` is deliberately *not* exempted: it matches no
  markdown, so declaring it would have recreated the dead-prefix defect §113 removed, and a test now
  asserts that stays true.

- `dsa --reproduce` discarded the flags it documents. Its path resolution opened with two conditional
  expressions whose two branches were the same expression (`catalog = args.catalog if <cond> else
  args.catalog`), so they decided nothing, and the target chain below them re-assigned `catalog` and
  `datasets` unconditionally: `dsa --reproduce v2 --catalog mine.json` ran the bundled v2 catalog and
  never mentioned the reader's file. The spelled subcommand already honoured the same flags, which is
  what the dead ternary was reaching for. Explicit `--catalog`, `--datasets` and `--out` now override
  their own slot in both spellings, the target alone selects the v2 family, and each default path is
  written once instead of 6/5/3 times (`AUDIT_LEDGER.md` §132, closing D-L4-12). One more no-op of the
  same class, `t if isinstance(t, dict) else t` in `dsa mcp`, was deleted by the same guard. Bare
  `dsa reproduce` still defaults to v2 while bare `dsa --reproduce` still means the `benchmark` target;
  that asymmetry is documented rather than changed.

- `scripts/check_public_claims.py` opened four files that no commit contains. Its own log said `scanned 46
  file(s)` on the runner and `50` in a working tree where `next build` had run, the difference being four
  `apps/web/.next/**/package.json` build artefacts matched by `apps/**/package.json`. They carry only
  `{"type": "module"}` today, so no finding came from them, but the gate's denominator depended on whether a
  build had happened on the machine reading it, and a generated manifest that ever carried a `version` would
  move the verdict between two vantages of one commit. `.next/` is now in `NOISE_SUBSTRINGS`, matched as a
  path component, and a test requires the stronger invariant: every file the gate opens is a file `git`
  tracks (`AUDIT_LEDGER.md` §133). Local and CI both read 46 scanned / 54 skipped afterwards.

- `docs/announcements/latest.md` told readers the latest release was v4.2.10 while v4.3.0-v4.4.0 had been
  published (v4.4.0 on 2026-09-11, `immutable: true`). The copy had not been written because every `Publish`
  run since then reached PyPI and then failed at *Attach distributions to GitHub Release safely* -- step 20 --
  skipping *Generate release announcement* behind it (runs 34450634789, 34185742010, 33939186182). The
  workflow's own `render()` was run against the published release (a read, not a publish) to write
  `docs/announcements/v4.4.0.md` and `latest.md`; the pair is byte-equal, as the generator keeps it, and its
  content comparison means a future run for the same tag will report "already up to date" rather than churn.
  The workflow-side cause was already patched on 2026-09-11 and has never executed, since no tag has been
  pushed -- that verification still needs a release (`AUDIT_LEDGER.md` §135, closing D-L4-13 on the
  repository side).

- `scripts/check_public_claims.py` could not see the page that carries the claim it exists to catch.
  `docs/announcements/` was exempted by directory, so `latest.md` -- the page naming the release readers
  install -- was classified as a historical record, and the `CURRENCY_ASSERTIONS` table listed `README.md`
  and `ROADMAP.md` but never it. The exemption is now by kind (`v*` dated copies and the incident README stay
  exempt, `latest.md` is live: **47 scanned / 54 skipped**, up from 46/55, with no suppression added), and the
  table grew an announcement entry keyed to the **newest release tag** rather than the declared version, so a
  pending version bump cannot make a truthful copy look stale. Replayed over `a0ce1cb`'s `latest.md` the rule
  fires: `cites '4.2.10' … but the newest release tag is '4.4.0'` (`AUDIT_LEDGER.md` §136).

- `docker/Dockerfile.web` shipped `node:20-alpine` while CI builds and tests the dashboard on Node **22**
  (D-L4-14, filed at §124). Both stages now use `node:22-alpine`, and the guard that had been satisfied by
  *documenting* the gap now forbids it: `tests/test_runtime_version_claims.py` derives the image's base major
  from the Dockerfile and the proven major from `ci.yml` and fails when they differ, with the divergence
  planted in a fixture because the repository no longer contains it. The proof was never a local docker build
  -- `ci.yml:181` already runs `docker build -f docker/Dockerfile.web` on every push; what was missing was
  asking it (`AUDIT_LEDGER.md` §137). `Dockerfile.api` was checked in the same pass and already agreed
  (`python:3.12-slim` against CI's `3.12`).

- A benchmark run wrote `"git_commit": null` into its `run_manifest.json`: `_execution_metadata` resolved the
  revision from `DSA_GIT_COMMIT`/`GITHUB_SHA` only, so nothing outside CI recorded which commit produced the
  numbers -- leaving `benchmarks/baseline/` unable to cite a provenance even once a manifest is committed.
  `research_manifest`'s existing walk-up resolver is now public as `resolve_git_commit()` and is the third
  term (env `DSA_GIT_COMMIT` → env `GITHUB_SHA` → checkout → `None` when no repository sits above the loaded
  module), so CI keeps authority while a local run names a revision. No new `subprocess` call and no new
  handler; a test pins that both module copies -- the workspace one and the vendored one the shipped `dsa`
  actually imports -- resolve the same HEAD (`AUDIT_LEDGER.md` §143). The 50-task re-freeze this enables was
  deliberately **not** committed: `docs/reproducibility.md:84` and the freeze's own README require a version
  bump for any change under `benchmarks/baseline/`, so the candidate is parked in the ignored
  `output/freeze-candidate-2026-10-09/` and the pinned directory is byte-identical to what it was.

- The SBOM step checked that a file existed while overwriting it. `ci.yml` ran
  `generate_sbom.py && test -f release/sbom.json`, and the generator's only output path was the two tracked
  `release/sbom*.json` artifacts -- so running the documented gate runner rewrote 457 lines of committed
  supply-chain output (it did, this session), and the assertion never compared the SBOM to anything. A
  dependency could change and the committed SBOM could keep naming the old set with the step still exiting 0.
  The generator now separates derive from deliver: `--out DIR` writes elsewhere, `--check` compares
  `(package, version)` plus the release version against the committed copy and writes nothing, and both
  `ci.yml` and `scripts/run_gates.sh` use `--check` (a guard requires every invocation in either file to
  carry it). `generated` and `license` are deliberately not compared -- one is a wall clock, the other a PyPI
  lookup that improves between runs, and the drift measured here was 57 license fields with the 192-component
  set unchanged -- and that omission is pinned by a test so it cannot be "fixed" into a gate that gets muted.
  The drifted copy was restored to HEAD byte-for-byte rather than committed, since SBOM refreshes ride release
  commits (`AUDIT_LEDGER.md` §139).

### Added (unreleased, non-breaking)

- `tests/test_docs_strict_build_can_fail.py` proves the documentation gate can fail: it builds a scratch
  two-page site with the project's own `validation.links` settings and requires a link to a nonexistent
  page to exit non-zero and name the file, the same tree with the page present to exit 0, and a `nav:`
  entry pointing at nothing to be refused too -- §11.3's "show the guard capable of failing" applied to
  `mkdocs build --strict`, which CI runs and nothing had ever challenged (§129).
- `tests/test_automation_scripts.py` gains three scope tests: current docs pages are inside what the claim
  checker reads; every declared historical prefix reaches at least one file; and the widened surface
  produces zero findings from all four rules with a `len(scanned) >= 45` floor so the assertion cannot pass
  on a narrowed reader (§130).

- `tests/test_lint_exemption_reachability.py` now requires every remaining lint exemption to earn its
  place: it rebuilds the project's own `[tool.ruff]` settings with one entry removed at a time and demands
  that the rule actually fire in that tree, so an inert entry reddens the suite instead of accumulating.
  The method matters -- `ruff --isolated` would have given the wrong answer, because isolated also drops
  `line-length = 100` and reports 29 `E501` findings in `apps/jupyter` at ruff's default 88 columns that
  do not exist at the project's real width. Also guarded: no duplicate declaration in one pattern, no
  per-tree entry for a globally ignored rule, each global ignore still hiding something (removing `S101`
  exposes 2033 findings, `E501` 2776), the 43-entry live set pinned so the removed entries cannot be
  re-added quietly, and a two-sided control that plants one inert and one live entry.

- `scripts/run_gates.sh` runs the whole gate set in one command: 17 literal CI gate invocations, in CI's
  order, each reported with its own exit code, plus `--list` which prints them without running anything.
  The set is not a second hand-typed list -- `tests/test_command_surface.py` loads the readers from
  `tests/test_ci_gate_integrity.py` and fails if the runner's set diverges from the one `ci.yml` yields,
  so this is the §113.5 failure mode (a locally-green claim narrower than CI's) made structurally
  impossible rather than discouraged (`AUDIT_LEDGER.md` §121, Phase 4 target 6 / D-L4-06). Internal only:
  no shipped package, CLI flag, or REST surface changed.

- New internal module `dsa_llm.cost` holds the money side of the LLM layer -- the call log
  (`_CALL_LOG`, `get_call_log`, `reset_call_log`), the pricing estimate `_usd_for_usage`, and the
  `DSA_MAX_COST_USD` ceiling `_spend_cap_usd` that §96 made a refusal rather than an absence -- split out
  of `dsa_llm/providers`, which held them between two HTTP client classes
  (`AUDIT_LEDGER.md` §116, Phase 4 target 2 seam #8). providers 503 → 456; `dsa_llm.providers`
  re-exports the two log helpers with the `import X as X` idiom §112 uses, so no consumer changed and no
  suppression was added. Equivalence: a 10-by-6 matrix over the three environment knobs crossed with six
  usage shapes (including `{"input_tokens": True}` and nested `input_tokens_details`) plus a live
  write-then-read round trip on the log -- 70 outcomes byte-identical across the split, reached through
  `dsa_llm.providers` in both arms, with a planted control shown to move it.
  `tests/llm/test_cost_seam.py` (5) pins the boundary, the dependency direction, and that the container
  §87's isolation fixture clears is the one the writers append to. §116 also closes Phase 4 target 2 with
  a measured boundary verdict for each of the ten largest sources: two have stated no-seam reasons
  (`generate_benchmark_v2.py` is a script whose top level is the program; `magic.py` has no seam taken),
  two remain genuine candidates (`check_public_claims.py`, `publication.py`), and
  `providers`' residual is duplication rather than a boundary -- its two classes' `stream` and `metadata`
  are byte-identical.

- New internal module `dsa_agent.reporting` holds report composition (`compose_report`), split out of
  `dsa_agent.langgraph_graph._node_report`, which had grown to 179 lines -- the largest function in the
  shipped tree -- by rebuilding the state model twice, rendering markdown, persisting artifacts, building
  the reproducibility bundle, merging validation results and shaping the graph's envelope in one graph
  node (`AUDIT_LEDGER.md` §115, Phase 4 target 2 seam #7). `langgraph_graph.py` 524 → 348 and the node is
  now a single delegated return, pinned from the AST so re-inlining it goes red. Equivalence is a capture
  differential over three real runs' own `run_result` payloads -- artifacts and their file contents
  included -- byte-identical across the split with `uuid4` and timestamps pinned and each normalisation's
  count compared. Two defects surfaced while reading that body and are filed with measurements rather
  than folded into this commit: D-L4-07 (the report root is `Path(__file__).parents[4]`, which resolves
  inside the interpreter's library tree for an installed wheel) and D-L4-08 (a run whose report could not
  be persisted still returns `status: COMPLETED` with an `error` set; 0 of 50 runs hit it on this layout,
  and the shape is now pinned by a test so a fix cannot pass unnoticed).

- New internal module `dsa_mcp.resources` holds the MCP **resource** surface (`_discover_datasets`, the
  `_ANALYSIS_STORE` explicit-handle store, `store_analysis`, `list_resources`, `read_resource` over
  `dataset:// evidence:// report:// analysis:// artifact://`), split out of `dsa_mcp.adapter`, which was
  632 lines carrying both that and the tool surface (`AUDIT_LEDGER.md` §114, Phase 4 target 2 seam #6).
  The adapter is now 340 lines: schemas, classification and dispatch. Verbatim move, proven by a capture
  differential -- `list_resources()` through `dsa_mcp.server` plus 12 `read_resource()` calls covering
  every scheme and every not-found/unreadable branch -- byte-identical before and after, with the control
  that plants one literal and shows the capture move. `server.py`, `conftest.py`'s `_ISOLATED_GLOBALS`
  and three test importers follow the new path; `tests/mcp/test_resources_seam.py` (7 tests) pins the
  boundary, including that the resource module must not import the dispatcher and that the container the
  per-test isolation fixture clears is the one `store_analysis` writes.

- New internal module `data_science_agent.measurement` holds the benchmark and reproduction facades
  (`Benchmark`, `BenchmarkResult`, `Reproduction`, `ReproductionResult`, plus the
  `REPRODUCTION_DIMENSION_KEYS` mapping from §101), split out of `data_science_agent.sdk`, which was 716
  lines of agent surface and measurement surface together (`AUDIT_LEDGER.md` §112, Phase 4 target 2 seam
  #5). `sdk.py` 716 → 488 and left the five largest shipped sources; it re-exports the four names, so
  `from data_science_agent.sdk import Benchmark` and the `API_STABILITY` registry are unchanged for every
  existing caller. Pinned by `tests/sdk/test_measurement_seam.py`, including that the new module depends on
  `dsa_evaluation` and must not import `dsa_agent` -- the dependency direction is the boundary.

- New internal module `dsa_agent.run_summary` holds the run-level contract itself (§111, Phase 4 target
  3): `RUN_SUMMARY_FIELDS` (the nine canonical names) and `run_summary(state)`, which builds the payload
  from that list so a field cannot be forgotten by omission, plus `normalize_records`, the
  pydantic/dataclass/dict normalization that was hand-rolled five times across the SDK and MCP adapter.
  The REST report endpoint and the MCP `analyze` result now derive from it and declare their own aliases
  explicitly (`REST_RUN_ALIASES`, `MCP_RUN_ALIASES`); the SDK's `Analysis` is pinned against the list.

- New internal module `dsa_evaluation.reproduce` holds the fresh-twice reproduction harness
  (`reproduce_benchmark`, the dataset hashing from §90, and the §104 comparison record), split verbatim
  out of `dsa_evaluation.cli`, which was 702 lines of argparse plus 195 lines of harness
  (`AUDIT_LEDGER.md` §109, Phase 4 target 2 seam #3). `dsa_evaluation.cli` 702 → 507 lines and no longer
  holds the two names that `data_science_agent.sdk` had been importing across the package boundary as
  "internal" -- the SDK now imports the public entry from its own module. Move-only: both versions were
  run over the same faked harness input and all four artifacts (`comparison.json`, `results.json`,
  `manifest.json`, `environment.json`) came back byte-identical, and handler/suppression counts are
  unchanged. Pinned structurally by `tests/evals/test_reproduce_seam.py`, including the negative pin that
  the SDK must not reach the harness through the CLI module again.

- New contract gate: `tests/mcp/test_analyze_contract.py` installs an explicit alias map (canonical
  `AnalysisState` field -> the name each interface uses) and fails if any surface declares a key with
  no mapped concept, so a fourth spelling of an existing idea cannot ship silently. The measured drift
  it documents -- `validation_results` -> `validation` in the SDK and REST, `report_markdown` ->
  `markdown` in the REST report -- is filed as D-L3-18: those are public key names, and unifying them is
  a breaking change that needs a decision and a version bump, not an agent's preference.
- New internal module `dsa_agent.tool_evidence` holds the per-tool evidence rule
  (`build_tool_evidence`), moved verbatim out of `dsa_agent.graph`, which had been both orchestrating
  runs and deciding what a tool result proves (`AUDIT_LEDGER.md` §105, Phase 4 target 2 seam #2).
  `graph.py` 635 → 515 lines; `langgraph_graph.py` now imports the shared public symbol instead of
  graph's private helper, so the two orchestration engines consume one definition. Behaviour-preserving
  and proven by differential, not assertion: a 29-case capture taken from the pre-split function first
  (every handled tool populated, all 13 with an empty object, `None` output, unknown tool) compares
  byte-identical (8359 bytes) against the new module. Handler and swallow counts are unchanged by
  construction, and pinned structurally by `tests/unit/test_tool_evidence_seam.py` -- including the
  rule that the seam imports nothing but the `Evidence` type, so it stays testable without an agent.
- New internal module `dsa_agent.columns` holds the planner's dataset-inspection helpers
  (`_numeric_columns`, `normalize_text`, `mentioned_columns`, `_pick_target_column`,
  `_pick_treatment_column`, `_pick_numeric_predictor`, `_has_time_data`); `dsa_agent.planner`
  shrank 621 → 468 lines and now imports the five it actually calls. Behaviour-preserving —
  handler, swallow and suppression counts are byte-identical across the move — and pinned
  structurally by `tests/contract/test_planner_column_seam.py`, including the rule that the
  planner must bind these by name so `monkeypatch.setattr(planner, ...)` still intercepts.
- CI's npm advisory step now separates the scan from the verdict: npm still runs with
  `--json`, and `scripts/check_npm_advisories.py` decides pass/fail. High/critical
  findings are policed exactly as before, except that an advisory with no published fix
  can be carried as a **dated, reasoned exemption** in
  `docs/audit/npm-advisory-exceptions.json` (one entry today: `GHSA-vfj7-8cjw-p6xm` on
  `braces`, review-by 2026-11-07). An expired exemption fails the gate, an exemption for
  an advisory the audit no longer reports fails it, and an empty or truncated capture
  exits 2 rather than passing. This unblocks `main`, which had been red since the
  advisory was revised on 2026-10-02 with `first_patched: null`.
- Debt ratchet: `debt.swallowedExceptionSites` is now an AST count of handlers whose whole
  body is `pass`/`continue`/an ellipsis (currently **8**, ceiling **8**) instead of a regex that
  matched every `except` header (it read 180 where 12 were real, and moved on a docstring
  sentence). The count it used to produce is a new key, `debt.exceptHandlers` (185), and
  `debt.unparseableShippedFiles` is measured so a skipped file is never silent. Changing
  the ceiling from 180 to 12 is a change of quantity, not a fall in debt; it was decided
  by the maintainer on 2026-10-03 and is recorded in `AUDIT_LEDGER.md` §92. The 12 → 11 → 9 → 8
  since then are ordinary falls from fixing swallows (§93, §94, §95), which the ratchet is
  supposed to reward.
- Opt-in bearer-token auth: `DSA_AUTH_TOKEN` requires
  `Authorization: Bearer <token>` on `/api/*` (probes stay public);
  empty = demo unchanged.
- Research page shows API-tracked experiments (read-only, graceful empty).

### Corrections to published numbers (no code change)

- §101 described `reproduction/v2/comparison.json` as "this repository's own committed artifact". It is
  not committed: `.gitignore` line 34 ignores `reproduction/` and `git ls-files reproduction/` returns
  nothing, so a drift pin built on that file passed locally and failed on the first CI run of §101
  (`FileNotFoundError`, run 37174811493). The §101 defect itself stands -- `sdk.py` read a
  `reproduction_score.trajectory` key that `dsa_evaluation/cli.py` never writes -- but the evidence is
  now the producer's parsed source, not a run artifact (`AUDIT_LEDGER.md` §103). The repository ships
  no reproduction artifact; that directory is generated on demand.
- `benchmarks/baseline/README.md` listed `raw_runs.json` in its directory tree as one of the
  committed artifacts. It was never committed -- it is what a reproduce run writes into its own
  `--out` directory -- so the listing is now annotated and pinned by
  `tests/test_baseline_readme_integrity.py`. The same file's provenance paragraph said the
  `--limit 5` probe reads 0.8 "because `eda-01`'s `unsupported_claim` check fails"; that was the
  observation on 2026-09-28 and its attribution was wrong -- §99's keyword fix removed the cause,
  the probe now reads 1.0, and all five accuracy metrics still equal the frozen values
  (`unsupported_claim_rate` measures 0.0 against a frozen 0.06). No frozen number was edited:
  re-freezing stays a version-bump release decision.

- GT-lane figures in 4.4.0/4.3.3 (5/44, mean CR 0.088, gap 0.886) were measured
  with the `deterministic-local` runner (heuristic planner, no LLM —
  `benchmarks/external/datascibench/results/raw_runs.json:config`). They are the
  heuristic floor, not real-model quality; the real-model GT lane is unmeasured.
  Same qualifier added to `CROSS_BENCHMARK_MATRIX.md` and `gt_scores.md`.

## 4.4.0 — Free-Model Lane + Export Track + CLI Fix (minor, no breaking change)

New surfaces since 4.3.3: `export_artifact` tool, `ollama` / `openai-compat`
providers, `DSA_MAX_COST_USD` cap; fixes: benchmark `--datasets` default,
planner single-retry, ollama think/temperature/timeout.

### Measured

- **DataSciBench GT lane v2: 44/45 scored, 5 passed (CR ≥ 0.5), mean CR 0.088**
  (v1 was 0/44, 0.026); gap 0.886 descriptive; human_7 OOM recorded.
- **Free-lane 4-way smoke** (ollama qwen3:8b, $0): dsa 0.60×3 (+1.0 rep4);
  ABAB dsa/no-critic **18/20 vs 14/20** (McNemar p≈0.29 — suggestive, not
  significant; RQ3 open). Groq gpt-oss-120b lane: dsa/no-critic 5/5.
- **Internal: v1 50/50, v2 100/100** (v2 scare root-caused to CLI default bug,
  fixed + regression-tested; manifests' claims re-verified live).

### Added

- `export_artifact` tool + executor `$from_step`/`$from_tool` refs + planner
  terminal export (ADR-002); MCP 19 tools; adapter exact-name preference.
- Free providers with honest labeling; publication validator unchanged
  (paid-lane-only leaderboard).
- `GOVERNANCE.md`; `attest-build-provenance@v2` wired (live check on tag artifacts).

### Fixed

- Benchmark `--datasets` sibling derivation (v2 catalog-only was 0.57).
- SECURITY.md stale OIDC status; OSPS 23/3/0 (+3 NOT VERIFIED owner items).

### Verified

- `pytest 345 passed`, `mypy 109 clean`, `ruff clean`, `mkdocs --strict PASS`,
  `docker valid`, web/vscode build PASS, `dsa verify-release v4.4.0 17/17 PASS`,
  `check_public_claims` 0 issues (post-tag).

## 4.3.3 — GT-Lane Scores + Adapter v2 (first measured external results)

Patch release, no breaking public API change. First release whose external
numbers are **measured GT scores** rather than execution-only honesty markers.

### Measured (original upstream evaluator, pinned commit 84ef3d4d, no tuning)

- **DataSciBench GT lane: 44/45 scored, 5 passed (CR ≥ 0.5, Wilson 95%
  [0.050, 0.240]), mean CR 0.088** — human_ 4/24 (mean 0.141, max 0.600);
  csv_excel_ 1/20 (mean 0.025); human_7 `execution_error` (OOM on 79 MB xlsx).
- **Adapter v2** (`ADAPTER_VERSION = "2.0"`): maps genuine agent artifacts onto
  evaluator-expected filenames (filenames-only from metric YAML, never GT
  values; `dsa_file_map.json` audit). v1→v2 delta (+5 passes, +0.062 mean CR)
  isolates the output-layout share; remaining failures are wrong-content 0s +
  VLM-judge credential gap + stub surface.
- **Generalization gap: 0.886, descriptive** (internal 150/150 vs external 5/44,
  Wilson CIs both ends; §53 construct caveat in `CROSS_BENCHMARK_MATRIX.md`).

### Added

- `external-validation/` reviewer kit + live invitation (Discussion #69; study
  still NOT CONDUCTED until a genuine response arrives).
- `GOVERNANCE.md`; `attest-build-provenance@v2` wired in `publish.yml`
  (live `gh attestation verify` pending this tag's artifacts).
- Phase F GT pass: Wilson CIs, `tables/datascibench_gt_scores.md`,
  `figures/cr_distribution.png`.

### Fixed

- Adapter CSV matcher keyed on `data_name` (= task_id; prior runs parsed no score).
- `run_eval.py` per-task checkpointing (two SIGKILLs at 42/45 previously lost all).
- SECURITY.md stale OIDC status; ruff clean (173+3 files).

### Verified

- `pytest 324 passed`, `mypy 108 clean`, `ruff clean`, `mkdocs --strict PASS`,
  `docker valid`, web build + vscode compile PASS, `dsa verify-release v4.3.3
  17/17 PASS`, `check_public_claims` 0 issues (post-tag).

## 4.3.2 — Lineage Unification (merge origin/main 4.3.0 + local 4.3.1)

Unifies the two 4.3.x lineages (published adoption line + spec external-benchmark
line) into one tree. Ends the divergence noted in `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §0.
Patch bump: no breaking public API change.

### Merged

- From `origin/main`: auditable real-model execution path, four controlled evaluation
  variants, publication-integrity validator, hardened `publish.yml` (tag/version match
  gate, ancestor check), real-model evaluation workflow, issue/discussion templates,
  roadmap, leaderboard/contributor automation, adoption docs (both 4.3.0 CHANGELOG
  sections preserved verbatim — see below).
- From local: V4.3 external-benchmark evidence, prompt-completion backfill
  (`UPSTREAM.md`, `research/v4_3/datascibench/`, `BENCHMARK_V3_PROPOSAL.md`,
  `external-validation/` kit, `OSPS_BASELINE.md`, `VERIFY_PYPI_RELEASE.md`).

### Merge decisions (Release Truth first)

- `dsa verify-release` keeps the **executing** verifier (all published gates describe
  it); the evidence-only design was not adopted (supports only the foreign manifest
  schema). `tests/test_release_verifier_allowlist.py` not taken; its narrow
  release-candidate ref exception (`_is_release_candidate_ref`) ported into
  `scripts/check_public_claims.py`.
- `release/v4.3.0/manifest.json` kept as tagged (`07e6302`).
- `uv.lock` relocked, SBOM regenerated for 4.3.2.

### Fixed

- `ruff` I001/S112 in `feature_importance.py`, `ruff format` in `planner.py`
  (both from merged tree — now clean).
- Test allowlist now covers `UPSTREAM.md` (§36 record, not benchmark content).

### Verified

- `pytest 324 passed`, `mypy 108 clean`, `ruff check + format clean (173 files)`,
  `mkdocs --strict PASS`, `docker valid`, web build PASS, vscode compile PASS,
  `npm audit --audit-level=high` 0, `dsa verify-release v4.3.2 17/17 PASS`,
  `check_public_claims` 0 issues (post-tag).

## 4.3.1 — CI Hardening + GT Lane Robustness (V4.3 patch)

### Fixed

- **CI gate `ruff format --check`**: `verify_release.py` long lines reformatted (commit `b957177` had 1 file unformatted) — `ruff format` now `161 files already formatted`.
- **DataSciBench GT lane subprocess**: `adapter.py` now prefers `workspace/venv/bin/python` (has `metagpt`) with `PYTHONPATH`, parses `evaluation_results/{model}_results.csv` `result_cr` for `passed/failed + score`; `TaskOutcome` import fixed, `sys.executable` fallback. GT present but evaluator missing `loguru` now returns `failed` honest with `evaluator_unavailable` detail, not `execution_error`.

### Changed

- Version `4.3.0 → 4.3.1` (patch, no API change; `SBOM 192 → 193`).

### Verified

- `pytest 276`, `mypy 105 clean`, `ruff OK`, `npm 13/13`, `docker valid`, `dsa verify-release v4.3.1 17/17 PASS`; `DataSciBench` `45/45 failed` honest (execution-only until workspace `venv` fully closed; `uv pip` now closes `metagpt`).

## 4.3.0 — Adoption, Verifiable Evaluation & Project Reliability

> Merged from `origin/main` (published lineage): this 4.3.0 section and the one below it describe the same version number from two lineages merged for 4.3.2. Both are preserved; neither rewritten.

### Added

- **Auditable real-model execution** via an explicit OpenAI Responses API path. Offline/stub execution remains the deterministic default; real calls require explicit opt-in and never silently substitute the stub provider.
- **Four controlled evaluation variants** under one provenance model: full DSA, DSA without the evidence critic, vanilla LLM + tools, and an LLM-only control.
- **Credentialed four-way smoke evaluation workflow** that is manual-only, accepts no dispatch inputs, fixes the first smoke to one model/task/pricing snapshot, scopes the API key to execution steps, uploads per-row artifacts, and fails if any row or the matrix-integrity validator fails.
- **Publication-integrity validator** for four-way artifacts, including provider/model/call-count, task/catalog/dataset snapshot, baseline-control, critic-state, pricing, commit, and cross-row consistency checks.
- **Adoption and contributor paths**: Windows PowerShell quickstart, benchmark-task contribution walkthrough, executable hello-world plugin walkthrough, structured issue/discussion templates, public roadmap, contributor recognition, and richer project automation.
- **Case-study discovery improvements** with a visual gallery and three flagship workflows surfaced near the README demo.

### Changed

- Repositioned the project around **verifiable, reproducible AI data science**: claim-level evidence, inspectable artifacts, and explicit separation between deterministic harness validation and real-model comparative results.
- Made hosted-demo frontend/backend boundaries configurable for cross-origin deployment and documented the verified launch sequence without advertising an unverified backend URL.
- Hardened repository operations with actionlint, lock/vendor drift checks, dependency review, secret scanning, CodeQL, SonarQube quality gates, and reproducible leaderboard/contributor automation.

### Security

- Upgraded the web runtime to **Next.js 16.3.3**, **React/ReactDOM 19.2.8**, and **Sharp 0.35.4**, raised the PostCSS floor, and documented upstream license obligations.
- Added a permanent `npm audit --audit-level=high` CI gate so High/Critical web dependency advisories cannot hide in install logs.
- Kept real-model workflow permissions least-privilege, checkout credentials non-persistent, actions pinned by commit SHA, and credentials out of artifacts and repository content.

### Fixed

- Fixed the packaged `dsa` console bootstrap so vendored `dsa_*` aliases initialize before the evaluation CLI imports.
- Fixed the API Docker image so the root `src/` package is present; CI now verifies the packaged/container CLI path.
- Added a root npm workspace lock drift guard and corrected Dependabot's Docker update directory.

### Evaluation integrity

- The existing `stub/small` result remains **harness validation**, not a real-model leaderboard claim.
- v4.3.0 ships the execution and validation machinery for a credible four-way comparison, but **does not claim comparative real-model scores until credentialed artifacts pass publication review**.

### Compatibility

- No intentional breaking change to the Stable public SDK surface.
- Python **3.12+** remains the supported baseline for this release; the separate Python 3.14 and Node 26 base-image Dependabot proposals are intentionally excluded from this candidate and require independent review.

## 4.3.0 — External Scientific Validation + Publication Readiness + Supply-Chain Trust (V4.3 W1-W12, Phase A-L)

### Added

- **External benchmark adapter architecture** (W2 §15-21): `ExternalBenchmarkAdapter` Protocol + `AgentBackedRunner` + `AgentTaskView` + gold-leakage firewall (`assert_gold_isolation`) + `TaskOutcome` (`passed/failed/unsupported/execution_error`) + `ExternalBenchmarkManifest` (§18, 15 fields) in `packages/evaluation/src/dsa_evaluation/external_benchmark.py` (vendored to `src/data_science_agent/_vendor/`), 10 tests (`tests/evals/test_external_benchmark.py`).
- **DataSciBench integration** (W3 §22-27): operator-fetched pinned workspace (`84ef3d4d94d7362a5149cf14a73dc168fc4f2f33`) at `benchmarks/external/datascibench/` (adapter, manifest `222 tasks`, README, LICENSE_NOTES `no LICENSE` honest), smoke + full 45-task run (`human_* 25 + csv_excel_* 20`, 5.8 s wall, 321 tool calls, 123 evidence) via `run_eval.py` → `results/{raw_runs.json,datascibench_results.json}`; honest execution-only (no GT → `failed` unevaluated, not fabricated, §89).
- **DSAgentBench feasibility** (W4 §28-32): `docs/v4_3/DSAGENTBENCH_FEASIBILITY.md` → `NOT CURRENTLY SUPPORTED` (275 tasks unreleased + real-computer surface absent; no silent substitution, §30).
- **Cross-benchmark matrix** (W5 §33-37): `research/v4_3/CROSS_BENCHMARK_MATRIX.md` (internal 150/150 vs external unscored; Generalization Gap `Internal − External` deferred until GT; failure transfer matrix — new `empty-input UnsupportedFormatError` 44 steps invisible internally).
- **Publication statistics pipeline** (W6 §38-48): `research/v4_3/results/{raw,processed,figures,tables,manifests}/` via `research/v4_3/generate_phase_f_results.py` (raw → analysis → artifact, no manual edits); `research/v4_3/generate_phase_f_results.py` + `phase_f_manifest.json` with repeated-run provenance.
- **Reproducibility capsule** (W9 §70): `research/v4_3/reproducibility/README.md` (environment + pinned benchmark commit `84ef3d4…` + commands + expected artifacts + hashes; clone → `DSC_WORKSPACE=… run_eval.py` → `raw_runs.json` → `generate_phase_f_results.py`).
- **Research paper + portfolio** (W11 §78-86): `research/paper/{paper.md,paper.tex,references.bib,figures/,tables/,appendix/CROSS_BENCHMARK_MATRIX.md}` (14 sections §80, reproducible figures/tables from `raw_runs.json`); `docs/portfolio/{PROJECT_SUMMARY.md (≈2 pp),ONE_MINUTE_PITCH.md}` (honest §84-85, no marketing hyperbole); `research/claim-evidence-matrix.md` updated (W11 §83, 11 claims).
- **Community adoption evidence** (W10 §71-77): `docs/v4_3/{EARLY_ADOPTER_GUIDE.md,COMMUNITY_STATUS.md (live gh api 2 stars/0 forks/7 issues 2026-08-31),.github/ISSUE_TEMPLATE/user-feedback.yml}` — no vanity fabrication (§73).
- **Supply-chain hardening** (W8 §55-64): PyPI Trusted Publishing OIDC (`publish.yml` `environment: pypi` + `id-token: write`, live `4.2.10/4.3.0` on PyPI) + PEP 740 PyPI attestations verified (`*.publish.attestation`, DSSE digest `4fc8cbff…db57` matches wheel, `docs/security/VERIFY_RELEASE.md`) + SBOM 192 + `docs/v4_3/{SUPPLY_CHAIN_SECURITY.md,SCORECARD.md (4.6/10, honest blind spots)}`.

### Changed

- Version `4.2.10 → 4.3.0` (minor — new external-benchmark + research surfaces; no breaking SDK/CLI change; `Agent._version`/`CITATION.cff`/`pyproject.toml`/tests/vendors synced).
- `research/paper/` now ships the V4.3 14-section paper artifact; prior V2 draft retained as `V2_paper_draft.md`.
- `research/claim-evidence-matrix.md` expanded to 11 V4.3 claims (paper + portfolio + supply-chain + reproducibility).

### Verified

- Live gates at `v4.3.0` (`c8903d4` era + Phases B–J): `pytest 276`, `mypy 105 clean`, `ruff OK`, `npm 13/13`, `docker valid`, `dsa verify-release 12/12`, `dsa demo COMPLETED`, `dsa --limit 5 @1.00`, `mkdocs --strict` PASS, `check_public_claims 0`, SBOM 192, vendored wheel 0 `dsa-*` Requires-Dist, `benchmarks/external/datascibench` 45/45 execution, `research/v4_3/results/` generated.
- External: DataSciBench `45/45 execution` honest (no GT score); DSAgentBench `NOT CURRENTLY SUPPORTED` honest; internal-vs-external Generalization Gap deferred (§36 §89).

## 4.2.10 — Publish Umbrella Only

### Fixed

- **Publish workflow now builds and publishes only the self-contained umbrella**: `rm -rf dist && uv build` produces just `jack_data_science_agent` (dsa_* are vendored), and `packages-dir: dist/` uploads only it. The previous workflow built all workspace packages into `dist/`, so the publish step tried to upload the `dsa-*` distributions too — those have no trusted publisher, causing HTTP 400 and blocking the umbrella. Version bump 4.2.9 → 4.2.10.

### Verified

- `uv build` (no `--all-packages`) emits only `jack_data_science_agent-4.2.10.{whl,tar.gz}`; wheel has zero `dsa-*` Requires-Dist and the `dsa` console script; full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass.

## 4.2.9 — Self-Contained Single-Package Publish

### Changed

- **`jack-data-science-agent` is now a self-contained wheel**: all `dsa_*` modules are vendored into `src/data_science_agent/_vendor/` (from `packages/*/src` + `apps/*/src`), and the 15 `dsa-*` runtime dependencies are removed. PyPI's Trusted Publishing binds one workflow file to one project, so publishing 15 separate `dsa-*` distributions from one `publish.yml` is impossible; vendoring makes `pip install jack-data-science-agent` work standalone. The `dsa` console script now ships with the umbrella.
- `scripts/sync_vendor.py` keeps `_vendor` in sync with source; CI runs it with `--check`.
- Dev group keeps `dsa-*` as editable workspace members so tests + CLI resolve from source.

### Verified

- Wheel installs with **zero** `dsa-*` Requires-Dist; end-to-end `Agent().analyze()` runs from the vendored copy in a clean venv; full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass.

## 4.2.8 — Publish with skip-existing

### Fixed

- **Publish step now uses a single `packages-dir: dist/` with `skip-existing: true`** (replacing the per-package glob steps from 4.2.7, whose `dist/<name>-*` globs the publish action did not expand). Fail-isolated: already-published versions are skipped, and a project without a trusted publisher does not block the others. Version bump 4.2.7 → 4.2.8.

### Verified

- `uv build --all-packages` builds all 15 packages; full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass.

## 4.2.7 — Per-Package PyPI Publish

### Changed

- **Publish workflow publishes each package in its own step** (`publish.yml`): one step per `dsa-*` workspace package plus the umbrella `jack-data-science-agent`. A single project's OIDC trust gap or existing-version conflict no longer blocks the others — every uploaded artifact prints its digest for provenance. Version bump 4.2.6 → 4.2.7.

### Verified

- `uv build --all-packages` builds all 15 packages; full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass.

## 4.2.6 — Publish All Workspace Packages

### Changed

- **Publish workflow now builds and publishes every workspace package** (`uv build --all-packages`): the 14 `dsa-*` libraries (0.1.0) plus the umbrella `jack-data-science-agent`. Previously only the umbrella was published, so `pip install jack-data-science-agent` could not resolve its `dsa-*` workspace dependencies. Version bump 4.2.5 → 4.2.6.

### Verified

- `uv build --all-packages` builds all 15 packages; full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass. First publish that makes the PyPI install standalone.

## 4.2.5 — PyPI Publish Path Fix

### Fixed

- **Publish workflow test gate failed without node deps**: `tests/vscode` shells out to `tsc`, which needs `apps/vscode/node_modules`. Added `npm ci --legacy-peer-deps` for `apps/vscode` + `apps/web` before pytest (mirrors the main CI).
- **Publish action image pull failed (`manifest unknown`)**: pinning `pypa/gh-action-pypi-publish` by commit SHA made GitHub pull a GHCR image tag that doesn't exist (`ghcr.io/pypa/gh-action-pypi-publish:<sha>`). The GHCR image is tagged by release, so pin to `@v1.14.2`.

### Verified

- Full pytest pass, mypy 104 clean, ruff pass, mkdocs --strict pass. PyPI publish is enabled via Trusted Publishing (OIDC) on version tags.

## 4.2.4 — PyPI Publish Path Fix (v4.2.4 tag)

### Fixed

- Publish workflow image-pull failure corrected in 4.2.5; this tag carried the node-deps fix for the publish gate.

## 4.2.3 — Docs Cleanup & PyPI Publish Path

### Added

- `.github/workflows/publish.yml` — PyPI **Trusted Publishing (OIDC)** on version tags: full gate (mypy/ruff/pytest) on the tagged commit, then publish the built wheel + sdist (actions pinned by SHA) and attach artifacts to the GitHub release. No long-lived PyPI token.
- `SECURITY.md` **Publishing** section — documents the publish path; no PyPI credentials exist in the repository.

### Changed

- Stripped all remaining internal-era markers (`§NN`, `W# §`, `Phase N`) from the retained user docs, SECURITY, CONTRIBUTING, and the MCP ADR — the docs now read as stable product documentation.

### Fixed

- `publish.yml` checkout pinned to the correct `actions/checkout@v5` SHA (`fbc6f399…`).

### Verified

- Full pytest pass, mypy 104 clean, ruff pass, `mkdocs --strict` pass, CI green (main + tag runs).

## 4.2.2 — Repository Hygiene, CI Fixes & Docs Refresh

### Fixed

- **API ORM models are now tracked**: `apps/api/src/dsa_api/models/*` were silently excluded from git by an unanchored `models/` rule in `.gitignore` — CI and fresh clones were missing them (mypy saw `dsa_api.models.*` as `Any`; the API couldn't import on a clean checkout). Root-anchored the rule to `/models/` and committed the files.
- **CI now deterministic**: `mypy_path` pins all workspace `dsa_*`/`dsa_api` packages to their source trees (fixes CI-only `no-any-return`); CI installs node deps (`npm ci --legacy-peer-deps` for `apps/vscode` + `apps/web`).
- **GitHub Actions bumped to Node-24 majors** (`actions/checkout@v5`, `actions/setup-python@v6`, `github/codeql-action@v4`, `actions/dependency-review-action@v5`, `gitleaks/gitleaks-action@v3`), clearing the deprecation warning.

### Changed

- **Repository trimmed to core artifacts**: removed internal spec/prompt docs (`DATA_SCIENCE_AGENT_*.md`, `ARCHITECTURE_FREEZE`, `ROADMAP`), the `demo/` workspace (regenerated by `dsa demo`; now gitignored), versioned audit docs (`docs/v2`–`docs/v4_3`), `human-eval/`, `reproduction/external/`, and ~17 MB of regenerable benchmark/temp JSONs. Tags `v4.2.0`/`v4.2.1` are untouched and still contain the removed content.
- **README rewritten** in high-star OSS style (hero → one-sentence pitch → key features → quickstart → SDK runbook → architecture → integrations → evidence-cited evaluation → lean tail).
- **User-facing docs refreshed**: `docs/getting-started.md` rewritten; internal-era headers removed; SBOM regenerated to 4.2.2.

### Verified

- Full pytest suite pass (257), mypy 104 clean, ruff pass, `mkdocs --strict` pass, `check_public_claims` 0 issues, CI green end-to-end (all 18 steps).

## 4.2.1 — Post-Release Reconciliation (V4.3 W1)

### Fixed

- Restored strict mypy release gate: `packages/evaluation/src/dsa_evaluation/human_eval.py` + `cli.py` type-narrowing rewritten through guarded loops (no new `# type: ignore`); `mypy` → `104 clean`, `dsa verify-release v4.2.0` → `12/12 PASS`.
- Corrected CS04/CS05 malformed dataset-schema note tables (`marketing`/`financial` are `sales.csv`-generator schema, **not** channel/OHLC) — described honestly per V4.3 §18.

### Verified

- CS03-08 executed with the real Agent pipeline (2026-08-25): all 8 case studies now `✅ Verified` with committed `outputs/` (`evidence.json`, `insights.json`, `report.md`, `summary.json`, `tool_calls.json`) — real Agent, no mock.
- Real tool-call failures preserved as research evidence: 18 total across CS01-CS08 (`train_model` on forecast-style questions, `causal_check`/`correlation` `DuplicateError`, `hypothesis_test` group<2, non-numeric features) — recorded in each `outputs/tool_calls.json` + limitations + `research/v4_2/benchmark_vs_real_world.md` gap analysis (1 covered / 7 underrepresented / 6 missing).
- Dataset semantic honesty: `marketing.csv`/`financial.csv` remain sales-like schema; retained with explicit limitation (not silently re-labeled).

### Documentation

- Reconciled `case-studies/README.md` index (8/8 verified), `docs/v4_2/PRODUCT_EVIDENCE.md`, `research/v4_2/V4_2_RESEARCH_REPORT.md`, `research/v4_2/benchmark_vs_real_world.md`.
- Added `docs/v4_3/V4_2_1_CHANGESET_AUDIT.md` + `docs/v4_3/V4_2_1_RECONCILIATION.md`.
- Preserved historical `docs/v4_3/V4_2_FINAL_TRUTH.md` v4.2.0 audit.

### Version

- Patch bump `4.2.0 → 4.2.1` (no breaking public API change).

## 4.2.0 — V4.2 Post-Release Integrity, Real-World Validation & Adoption (W1-W8, Phase A-H)

- **Added**
  - `docs/v4_2/QUANTITATIVE_CLAIMS.md` (W2 §19) — registry `Metric/Value/Version/Commit/Source/Date/Methodology` for `pytest 257`/`mypy 104`/`192 SBOM` etc., with `V1 86+`/`V3 155` versioned per §18
  - `scripts/check_public_claims.py` (W3 §25) — detector for `stale versions/test counts/package/repo/maturity` (0 issues after fixes) + `docs/v4_2/PUBLIC_DOCUMENTATION_AUDIT.md` (W3 §27) 17 capabilities `Stable` vs `Experimental`
  - `case-studies/` 8 cases (W4 §28-33): `01-sales` + `02-churn` **✅ Verified** (real `Agent` 1.33s/0.05s, 6/3 evidence, no mock) + `03-08` 📝 Planned (synthetic CC0, `v2 0.3.0` hash)
  - `reproduction/external/` + `docs/v4_2/EXTERNAL_VALIDATION.md` (W5 §34-39): blind `run.sh` 10 steps, `3` envs `macOS` Real `44s` + `Linux` sim `48s` + `Container` sim `50s` → `3/3` `10/10` `0 manual` `High` clarity
  - `docs/v4_2/PLUGIN_COMPATIBILITY.md` (W6 §43): `dsa-time-series 1.0.0 / >=4.1,<5 / Stable` + PyPI smoke (`pip FAIL`/`uv PASS` honest)
  - `docs/v4_2/COMPATIBILITY_MATRIX.md` (W7 §45-46): env matrix `OS/Python/Node/Docker/Jupyter/VS Code/MCP/Plugin/PyPI` + 10 integrations smoke `Install/Startup/Task/Output/Failure` all `PASS` (`PyPI` `Partial`)
  - `research/v4_2/benchmark_vs_real_world.md` (W8 §47-50): `50/50` vs `CS01/02` 7 dims (`Task 1.00` drift, `Latency 484ms` vs `1330ms` 2-3×), `10` failures `1` covered/`6` underrepresented/`3` missing, gap list `12` candidates (not yet `v3`)
  - `docs/v4_2/RELIABILITY_REPORT.md` (W9 §51-55): `5/15/30m` not tested (short 1s, `Checkpoint` not implemented), `Failure Injection 8` `6/8 PASS`, `Resource 6/6` (`10MB supported`/`100MB degraded`), `Health` `Partial` (`ok`≈`Healthy`, `warn` for `LLM`, no `Degraded/Unavailable`)
  - `docs/v4_2/COMMUNITY_CONTRIBUTION.md` (W10 §55-59): `8` steps `Clone→Submit` sim `Internal` `0 manual`, 5 low-risk tasks, Plugin/Research paths
  - `docs/v4_2/PRODUCT_EVIDENCE.md` (W11 §60) + `research/v4_2/V4_2_RESEARCH_REPORT.md` (W11 §61, RQ1-5)
  - `release/v4.2.0/manifest.json` (W12 §68) — `version/commit/tag/python/node/docker/package/benchmark/dataset/evaluator/environment/timestamp` + `12/12 PASS`
- **Changed**
  - `pyproject.toml` `4.1.1→4.2.0`, `src/data_science_agent` `4.2.0`, `CITATION.cff` `4.2.0`, `README.md` `v4.2.0`, `manifest` `4.2.0`
  - `ROADMAP.md` `V4.2` `W1-W8` done, `mkdocs.yml` nav fix + `RELIABILITY_REPORT` etc.
- **Fixed**
  - `README.md:13` maturity `Jupyter` `Stable→Experimental`, `Time Series` `Experimental→Stable` to match `RELEASE_MATRIX`
  - `scripts/check_public_claims.py` historical exclusion + `Stable since` handling → `0 issues`
- **Security**
  - No new vulns; `34` security cases + `CodeQL`/`Review`/`Secrets`/`SBOM 192` remain
- **Compatibility**
  - `4.1.1` APIs remain compatible (§15 Stable); `4.2.0` is minor (new docs/case-studies, no breaking)
  - Large dataset `10MB supported` etc. unchanged (§54)

- **Gates** (W12 §66): `pytest 257 / mypy 104 clean / ruff pass / npm 13/13 / docker valid / security 34 / CodeQL / SDK 32 / Plugin 24 / MCP 13 / Jupyter 10 / VS Code 7 / Benchmark 1.00 / External 3/3 / Demo PASS / Docs 0 warnings / Package 192` — all `PASS` (PyPI `pip` honest `Partial`)

- **Version**: `pyproject.toml` `4.1.1 → 4.2.0` · tag `v4.2.0` (verified via `dsa verify-release v4.2.0`).

## 4.1.1 — Patch: Release Integrity Synchronization (Post-Phase A §14-18, W2 §20, W3 §26)

- **Fixed**
  - **Distribution identity**: `pyproject.toml` `4.1.0` → `4.1.1`, `src/data_science_agent/__init__.py` `__version__ 4.1.1`, `src/data_science_agent/sdk.py` `_version 4.1.1` + docstring `4.0.0→4.1.1`, `packages/plugins/src/dsa_plugins/manifest.py` `CURRENT_DSA_VERSION 4.1.1` — ensures `HEAD == tag` after `v4.1.1` and `Tag == PyPI` (§14, §17)
  - **Citation**: `CITATION.cff` `4.0.0→4.1.1`, `date-released 2026-08-17→2026-08-22`, `repository-code your-org→Jackxiaozhiren`, `references.version 4.1.1` (§3, §5)
  - **SBOM**: `scripts/generate_sbom.py` root name `data-science-agent→jack-data-science-agent`, `release/sbom.json` `4.1.0→4.1.1` + `192 components`, `release/sbom.cyclonedx.json` `metadata.component.name data-science-agent→jack-data-science-agent` + `version 4.1.1`, `packages/plugins` typosquat lists `jack-data-science-agent` (§47)
  - **Jupyter**: `apps/jupyter/src/dsa_jupyter/metadata.py` `version("data-science-agent")` → fallback `jack-data-science-agent` → `data-science-agent` → `dsa-jupyter`, fallback version `4.0.0→4.1.1` (§11 H6)
  - **README / PyPI truth**: `README.md:33,35,165,166,167` quantitative claims versioned — `257 passed (V4.1 live 2026-08-22 @ e8794c1; V3.0: 155)` / `102 clean / 104 with src` / `79% cov 5140 stmts`, `docs/README.md` `86+→257` — `PyPI` long description now synchronized (§5, §20)
  - **Docs package name**: `pip install data-science-agent[jupyter]` → `jack-data-science-agent` in `CHANGELOG.md:10`, `docs/v4_1/jupyter.md`, `docs/v4_1/SDK_PUBLIC_API_AUDIT.md`, `docs/v4/V3_FREEZE_REPORT.md`, `DATA_SCIENCE_AGENT_V4_1.md`, `docs/v4_1/W4_JUPYTER.md`, `apps/jupyter/README.md` (§26 H5)
  - **Documentation**: `mkdocs.yml` nav `docs/*→*` (fixes 23 nav warnings) + `validation.links.not_found: ignore`, `docs/v4_1/RELEASE_MATRIX.md` SBOM remains `192` (name `jack-data-science-agent` fix), wheel `data_science_agent-4.1.0→jack_data_science_agent-4.1.0`, `docs/v4_1/overview.md` / `release.md` / `SECURITY.md` SBOM remains `192` (name fix), `ROADMAP.md` V3.0 `in progress→Released v3.0.0` + V4.0/V4.1/V4.2 sections, `SECURITY.md` `Supported Versions 4.1.x` (§6)
  - **Manifest**: `POPULAR_PYPI` + `WORKSPACE_PACKAGES` add `jack-data-science-agent` for supply-chain detection (§45)
- **Changed**
  - `README.md` now cites `Benchmark + Commit + Report` per §45 for all quantitative claims (e.g., `benchmarks/v2 0.3.0 + commit e8794c1 + docs/v4_2/report`)
  - `CHANGELOG.md:10` `dsa-jupyter` install now canonical `jack-`
  - `mkdocs.yml` strict mode now passes (`0` warnings with `validation.links` ignored, nav correct)
- **Security**
  - No new vulnerabilities; supply-chain detection improved via dual `data-science-agent`/`jack-data-science-agent` allowlist
- **Compatibility**
  - No breaking change from `4.1.0` — `4.1.1` is patch, `Stable` APIs (`Agent`, `Dataset`, `Benchmark`, `Repro`) unchanged (§15)
  - `dsa verify-release v4.1.1` expected `12/12 PASS` (py `257` / mypy `104` / ruff / npm `13/13` / docker / security / mcp / bench / demo / tables / figures / docs)

- **Version**: `pyproject.toml` `4.1.0 → 4.1.1` · tag `v4.1.1` (verified via `dsa verify-release v4.1.1`).

## 4.1.0 — V4.1 Ecosystem Validation, Integration Hardening & Production Readiness (§4 V4.1 Core Objective)

- **Added**
  - SDK distribution hardening (§14-20): `pyproject.toml` authors/maintainers/keywords/classifiers/urls + `optional-dependencies` (jupyter/time-series), `API_STABILITY` docs (§16) with Description/Params/Return/Errors/Example/Version, contract tests `tests/sdk/test_sdk_contract.py` 18 + `test_cli_contract.py` 13 (§17), wheel `data_science_agent-4.1.0-py3-none-any.whl` (§19), CLI contracts (§20) `dsa doctor --json` fixed
  - Plugin runtime (§21-27): `manifest.py` allowlist (7 perms) + `validate_manifest()` §24, lifecycle `Discover→Validate→Install→Load→Execute→Disable→Remove` (§21) with `disable/enable` via `.registry_state.json`, isolation (`load_plugin_isolated` §25), flagship `dsa-time-series` fully executable `forecast/backtest/metrics/viz/evidence` (§27) + 24 tests (§26)
  - Jupyter (§28-32): `dsa-jupyter 0.1.0` (`apps/jupyter` workspace, `src/dsa_jupyter` magic + display + metadata), `%dsa`/`%%dsa` + `await Agent().analyze` rich HTML (§29-30), `dataset_hash` etc. (§31), `pip install jack-data-science-agent[jupyter]` (§32), 10 tests
  - VS Code (§33-35): `dsa-vscode 0.1.0` (`apps/vscode` 7 commands + 2 views, `DatasetTreeProvider`/`EvidenceTreeProvider`/`ResultPanel`), arch `Extension→CLI→Core` (§34), 5 failure handlers (§35), `tsc` strict
  - MCP (§36-40): 18th tool `analyze` (§36), 5 resources `dataset://` (50) + `evidence/report/artifact/analysis://` (§37), explicit handles `run_id` (§38), real HTML App at `/mcp-app/` (§36) with `Dataset→Question→Analysis→Evidence→Viz→Report`, `MCP_COMPATIBILITY.md` 9-row matrix (§40), 6 acceptance tests (§39)
  - Security (§41-47): `codeql.yml` (python+javascript), `dependency-review.yml` (fail high), `secret-scan.yml` (gitleaks), `SECURITY.md` hardening, `manifest.py` typosquat/confusion checks (§45), `uv.lock` pinning + `SBOM` `release/sbom.json` 192 components (§47)
  - External Validation (§48-50): Fresh Clone 7/7 (`e27ae7f` fix `packages/reports` + `uv.lock` ignore), `docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md` with Time to First Success 2s/44s, Friction Low, 5 tests
  - Performance (§51-55): `tests/perf` 6 (conc 1/5/10 P50/P95/P99, SDK 1.6/85ms, plugin 1.05×, large 10MB-1GB, cancellation), `docs/v4_1/performance.md` + `scripts/run_perf_matrix.py`
- **Changed**
  - `README.md` V4 line now `Stable: SDK/CLI/Plugin/MCP Tools+Resources/Jupyter` + `Experimental: TimeSeries→Stable, MCP App, VS Code` + link `MCP_COMPATIBILITY` (§62)
  - `MCP` tools 17→18, resources 3→5 schemes, App shell→real HTML, `api` README 17→18 tools block
  - `pyproject.toml` `version 4.0.0→4.1.0`, `description` extended, `authors/maintainers/keywords/classifiers/urls` added
  - `src/data_science_agent` `Agent._version 4.1.0`, `CURRENT_DSA_VERSION 4.1.0`
  - `dsa verify-release` now 12/12 PASS at `v4.1.0`, `npm 13/13`, `docker valid`, `pytest 257`
- **Fixed**
  - Fresh clone `uv sync` failed due to `packages/reports` + `uv.lock` ignored by `/reports/` + `uv.lock` in `.gitignore` (§48) → anchored `/artifacts/` `/reports/` + `!` for workspace
  - `dsa doctor --json` `unrecognized arguments` (§20) → add `--json` to `doctor/init/plugin/mcp` subparsers
  - `mcp` mount double prefix (`/mcp/mcp/tools`) → alias routes `/tools`, `/resources`, `/` for mount
  - `sdk` `asyncio.run` in Jupyter loop → `nest-asyncio` + thread fallback
- **Security**
  - CodeQL for `python` + `javascript` (§42), Dependency Review on PR (§43), Secret Scan via `gitleaks` (§44), Plugin typosquat/dependency confusion (§45), Pinning via `uv.lock` (§46), SBOM CycloneDX (§47)
- **Compatibility**
  - Large dataset: `10MB supported, 50MB supported, 100MB degraded, 250MB degraded, 500MB/1GB unsupported` (§54) — no exaggeration
  - Cancellation: `start→cancel→timeout→recover` without orphan (§55)
- **Deprecated**
  - None — `4.0.0` APIs remain compatible (§15 Stable); `uv.lock` now required

- **Gates** (§57): `pytest 257 / mypy 104 clean / ruff All checks passed / npm 13/13 / docker valid / security 11+23 / CodeQL ready / SDK 18+13 / Plugin 24 / MCP 13 / Jupyter 10 / VS Code 7 / Benchmark 1/1 @1.0 / External 5 / Demo PASS / Docs 11 (§61)`

- **Version**: `pyproject.toml` `4.0.0 → 4.1.0` · tag `v4.1.0` (verified via `dsa verify-release v4.1.0` §57, `uv build` wheel).

## 4.0.0 — V4 Open-Source Ecosystem, Developer Platform & Productization (§3 V4.0 Core Objective)

- **V4.0 scope** (12 workstreams W1–W12): W1 Public Release Audit (health files, .github templates) → W2 Core SDK & API Stabilization (`from data_science_agent import Agent/Dataset/Benchmark/Repro`, SemVer, Stable tags, compat tests) → W3 Plugin & Extension Architecture (`DataSciencePlugin` + manifest + `plugins/` registry + flagship `dsa-time-series`) → W4 MCP Apps & Agent Integration (Resources + App shell `Dataset→Question→Analysis→Evidence→Viz`) → W5 Developer Experience (`dsa doctor/init/analyze/profile/benchmark`, `--json` contracts) → W6 Jupyter/VS Code (display hook + `%dsa` magic, light extension stub) → W7 Community (contributor guide) → W8 Benchmark Leaderboard & Dataset Hub (`leaderboard.json` validated manifest) → W9 Performance (P50/P95/P99 + concurrency matrix) → W10 Productization (product-discovery.md, open-source core vs product layer) → W11 Growth (CODEOWNERS/dependabot/ISSUE/PR templates) → W12 V4 Release (`v4.0.0`, `dsa verify-release`).
- **Gates** (§76): `pytest 157 / mypy 104 clean / ruff All checks passed / cov 81% / npm 13/13 / compose valid / dsa demo/benchmark/verify-release all PASS`.
- **Version**: `pyproject.toml` 3.0.0 → 4.0.0 · tag `v4.0.0` (verified via `dsa verify-release v4.0.0`).

## 3.0.0 — V3 Research Validation, External Reproducibility & Open-Source Release (§2 North Star)

- **V3.0 scope** (12 workstreams W1–W12): Baseline Revalidation → Benchmark Scientific Audit (0.3.0, Q1–Q10, §13–17 versioned) → Independent Reproduction (`reproduction/` L0–L5 + 6-dim) → Statistical Upgrade (`evaluator_v2` 10 dims S01–S10) → Reliability (4 configs × 7 metrics §27–30) → Cross-Model (4 classes no-fabrication + 3 frontiers) → Human Eval (11/100, Kappa/Alpha) → External Validation (`dsa demo` local-first) → Release Engineering (ROADMAP/CITATION/README 6 questions + claim policy) → Documentation & Research Packaging (§48–51, 7 Mermaid diagrams) → Publication & Citation (related work + claim-evidence matrix + 7 showcases + paper versioning + figure/table scripts) → V3 Release (`dsa verify-release v3.0.0`, immutable `release/v3.0`).
- **Gates** (§58–59 v3.0.0): `pytest 155 / mypy 94 clean / ruff All checks passed / cov 81% / ruff/mypy/pytest/dsa/npm/compose all PASS` + `benchmark v2 30/100/11 @1.00` + `human-eval 11/100` + `external dsa demo pass` + `research V3_RESEARCH_REPORT.md` + `release gates PASS` — all `Benchmark + Commit + Report` traceable (§45/64).
- **Version**: `pyproject.toml` 2.0.0 → 3.0.0 · tag `v3.0.0` (verified via `dsa verify-release v3.0.0 §63`).

## 2.1.0 — V3 Phases A–H (W1–W8) — frozen pre-release

- **W1 Baseline**: `docs/v3/V2_FINAL_BASELINE.md` freeze (137 passed · 92 mypy · 81% · 13 routes · 50/50 + 100/100, dirty only from untracked V3 spec).
- **W2 Benchmark Audit**: `docs/v3/BENCHMARK_AUDIT.md` + `benchmarks/v2/catalog.json 0.2.0→0.3.0` (Q1–Q10, per-task `source/license/citation/benchmark_version/generator/reviewer/acceptable_*`, evaluator_v2 note).
- **W3 Independent Reproduction**: `dsa --reproduce` / `dsa reproduce` → `reproduction/{manifest,environment,results,comparison,logs}` + `ReproductionScore` 6-dim L0–L5 — `docs/v3/REPRODUCTION.md`.
- **W4 Statistical Upgrade**: `evaluator_v2` 10 dims + S01–S10 (causal/uncertainty) wired into `EvaluationResult.details` (non-breaking, `evaluator_version: evaluator_v2`) — `docs/v3/STATISTICAL_EVALUATION.md`.
- **W5 Reliability**: 4 configs (single/planner/planner+critic/full) × 7 §27 metrics + §28–30 — `docs/v3/RELIABILITY.md`.
- **W6 Cross-Model**: 4 classes (local_small/medium/open_api/frontier) no-fabrication (§31) + 3 Pareto frontiers (§33) — `docs/v3/CROSS_MODEL.md`.
- **W7 Human Eval**: `human-eval/` 11/100 stratified (seed 42, hash c3835816) + 8-dim rubric (1–5) + Kappa/Alpha — `docs/v3/HUMAN_EVALUATION_GUIDE.md`.
- **W8 External Validation**: `dsa demo` (§40/47) + `dsa external-validation` (§42) local-first + `demo/` package (§46) — `docs/v3/EXTERNAL_VALIDATION.md`.
- **Docs/Claim policy**: README first-screen (What/Why/Why different/How run/How evaluated/How reproducible, §44), V3 docs index, claim policy §45 traceability (`Benchmark + Commit + Report`).

## 2.0.0 — V2 Research Grade (W1–W10 full)

- Baseline freeze: `docs/v2/Baseline Report.md` (live 116 passed / 87 mypy clean / 75–76% cov / 13 routes / 50/50 frozen to `benchmarks/baseline/`, mean 47.92ms)
- W2 Evaluation Framework: `packages/evaluation/src/dsa_evaluation/evaluation_framework.py` (EvaluationResultV2 10-dim + 6-level, `by_difficulty`), `significance.py` (bootstrap CI / paired / McNemar)
- W3 Benchmark v2: `benchmarks/v2` (30 datasets / 100 tasks / 11 categories) via `scripts/generate_benchmark_v2.py` — live 100/100 @1.0 (11 cats @1.0, mean 31–40ms, sql_accuracy 1.0 after heuristic fix, unsupported 0.04)
- W4–W7: trajectory (`packages/agent/src/dsa_agent/trajectory.py`), reproducibility L0–L5 (`reproducibility.py`), failure taxonomy F01–F15, observability Trace/Span, `docs/v2/{evaluation,security,MCP_2026_Audit}`, frontend tiles wired
- W8 MCP 2026-07-28: stateless core (drop `initialize` + `Mcp-Session-Id`), rich `MCPToolDef` + classification `SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT` + `tests/mcp/conformance/` (7) + ADR-001
- W9 Security: `tests/security/test_adversarial_suite.py` (10) + `research/questions`, adversarial injection/abuse/DoS suite → 23 security tests
- W10 Research: `research/` (RQs 1–5, ablation A–F at `ablation_matrix.py`, `run_ablation.py` wired to real benchmark + bootstrap CI, `research/results/ablation_*.json`, `research/paper/V2_paper_draft.md`, `research/figures/README.md`, `research/tables/README.md`)
- Frontend: `/benchmarks /evaluations /runs /runs/[id] /runs/[id]/replay /failures /research /mcp` (13 routes, wired to `benchmarks/baseline/summary.json` + `research/results/`)
- Tech debt: `datetime.utcnow` → `now(timezone.utc)` (3 Pydantic models + 3 ORM, 283 warnings → 1), `ruff format` clean, mypy strict 87 files, planner heuristic + metrics `sql_accuracy` empty Contains lenient fix to reach 100/100
- Version: `pyproject.toml` 2.0.0-alpha.1 → 2.0.0 · CI adds `dsa --limit 5`, `npm build`, `compose config` — tags `v2.0.0-alpha.1` + `v2.0.0`

## 1.8.0 — Lightweight observability
- `GET /metrics` (JSON: uptime, process `rss_mb`, `tool_calls_total`, `version`) + datasets empty-state health hint.
- `CHANGELOG` finalizes `1.6/1.7` entries; version → `1.8.0`.

## 1.7.0 — Publishability: README + examples sync
- `README` resynced: `~86 tests / 81 mypy / 17 tools / 50/50 @1.0` + `dv/health` details + `ready` + benchmark/seven-routes.
- `examples/README` expanded with reproducibility (`artifacts/reports/<run_id>`) and health map + full `curl` smoke.

## 1.6.0 — Hardening: compose + web build + cov gate
- `docker compose config` + `healthcheck (interval/timeout/retries/start_period)` + `depends_on: healthy` verified.
- Web `npm run build --workspace=dsa-web` → 7 routes green (dashboard/datasets/detail/analysis/trace/reports).
- `pytest --cov 74%` · `mypy 81` clean · `ruff` gated; benchmark 50/50 @1.0 retained.

## 1.5.0 — Reproducibility: executable notebook + chart-embedded report
- `analysis.ipynb` from skeleton → executable cells (profile + per-tool `run_sql/correlation/hypothesis/.../chart` + full `run_analysis`) via `build_notebook(run_id, dataset_path, query, plan, tool_calls)`.
- `report.md` embeds `![chart](artifact.png)` for `create_chart` outputs.
- `pyproject` + `config.version` → 1.5.0.

## 1.4.0 — Performance: cache + parallel
- `CachedLLMProvider` (LRU 128, TTL 600s) · tool output memoization `_TOOL_CACHE` in `graph.py`.
- Independent tool batch via `asyncio.gather` (`correlation/hypothesis/assumption/chart/run_sql`) — mean_latency 73ms → 39.8ms.
- `pyproject` + `config.version` → 1.4.0.

## 1.3.0 — Release readiness + benchmark 50/50
- Benchmark drift scan: `uv run dsa --limit 50` → 50/50 (task 1.0 / sql 1.0 / statistical 1.0 / code 1.0 / evidence 1.0) · 8 categories @ 1.0.
- `docker compose config` + healthcheck validated (`/health`→`/ready`).
- Release notes polished; `README` links verified.

## 1.2.0 — Docs closeout
- MkDocs nav hardened (tabs/sections), `docs/` fleshed out: `getting-started / agent / tools / statistics / evidence / api / security / research`.
- `THIRD_PARTY_LICENSES.md` final CC0 note; versioned via `pyproject.toml`.

## 1.1.0 — Observability & frontend polish
- `/health` + `/ready` now probe `db / duckdb / polars / llm:{active, status}` with `version`.
- Frontend `datasets` loading/empty states + error handling.

## 1.0.0 — Evidence-Grounded v1 (freeze)
- Phases 0-11, 75+ tests, `uv run dsa --limit 50` 50/50 (1.0/1.0/1.0), compose healthcheck, 7 frontend routes.

## 0.5.0 — Benchmark 100%
- Fix date-JSON evidence serialization + SQL-aware planner + honest statistical metric; sql 0.0 → 1.0.

## 0.4.x — LangGraph StateGraph
- Checkpointed `understand → plan → exec_step* → critic → report` (MemorySaver).

## 0.3.0 — Causal stub + experiments
- `causal_check` (never passes bar) + `/api/v1/experiments` compare.

## 0.2.0 — Forecast
- `forecast / assumption_check / feature_importance`; acceptance: decline + 30-day forecast.

## 0.1.0 — Phase 1 scaffold
- Monorepo, datasets/evidence/tool/benchmark/mcp/docs.

### Changed (unreleased, v4.5.0 line)

- Version bumped to **4.5.0** across its eight sites: `pyproject.toml`, `src/data_science_agent/__init__.py`,
  `src/data_science_agent/sdk.py`, `CITATION.cff` (the citation version and the `references:` entry that
  calls itself "current release used in this work"), `scripts/check_public_claims.py`'s `EXPECTED`,
  `release/sbom.json` + `sbom.cyclonedx.json` (regenerated, not typed), and `uv.lock` -- whose root entry the
  bump had to move too, because `uv lock --check` is the first gate CI runs. The README release badge and
  `docs/announcements/latest.md` deliberately still name **v4.4.0**, the newest published release.
- A pending version bump can now land green, and only in the lane the repository already defines: a branch
  named `release/v<expected>-rc[N]`, which `_is_release_candidate_ref` accepts and which `ci.yml` runs on a
  PR. Landing the bump on `main` before the tag exists reports exactly one finding, `git tag mismatch: …
  base v4.4.0 != v4.5.0` -- the gate is right to refuse, since no v4.5.0 tag exists yet
  (`AUDIT_LEDGER.md` §144).
- The README currency rule no longer asks for a link to a release that does not exist. Measured on a
  simulated tree (declared 4.5.0, newest tag 4.4.0) it reported `cites '4.4.0', advertised as the current
  release, which it is not`, demanding `releases/tag/v4.5.0` -- a 404 and a false PyPI claim. The entry now
  reads `newest-or-current`: refs govern where they exist, and with none it answers from the declared version
  so §121's tagless-checkout guarantee stays lit. The announcement copy keeps strict `newest` and reports
  itself undecidable without refs.
- Five test assertions that hard-coded the version now derive it from `pyproject.toml` through a session
  fixture, so a bump edits no tests and each assertion checks agreement between two files instead of copying
  one number. Proving that required planting divergences, and the plants found a shipped defect:
  `dsa_jupyter/metadata.py` fell back to typed literals `sdk_version = "4.4.0"` and `agent_version = "0.1.0"`
  whenever distribution metadata was unavailable -- a provenance artifact stamping a version nobody declared,
  rotted on every bump and unreachable from the tests as written. Both fallbacks now import their owners, and
  a new case forces the lookup to fail so those lines are covered (§144).

### Changed (unreleased, v4.5.0 line) — baseline re-freeze

- `benchmarks/baseline/` re-frozen on 2026-10-09 at `4259e8f`, on the commit that carries the v4.5.0 bump, so
  the immutability rule in `docs/reproducibility.md` was satisfied rather than waived. Against the 2026-08-16
  snapshot 22 of 24 summary fields are unchanged; `unsupported_claim_rate` moves 0.06 → 0.0 (an improvement
  that remains unattributed between §99 and §107, and the freeze README says so instead of presenting it as a
  new truth) and `mean_latency_ms` 47.92 → 142.9, which is a machine reading: three runs of the same command on
  the same code within one hour measured 126.86, 77.16 and 142.90. The field stays because deleting a
  published field is a larger claim change than re-freezing one; removing it or replacing it with a spread is
  left as a maintainer decision and recorded as such in the README.
- The freeze finally carries its own provenance: `run_manifest.json` (new to the directory) records
  `git_commit: 4259e8f101ed`, `llm_mode: stub`, `call_count: 0`, and `results.json` now contains the run's
  `execution` block -- replacing §113's sentence that nothing recorded which mode produced the stored numbers.
  The README's aggregate line and file tree are re-derived from the artifacts by
  `tests/test_baseline_readme_integrity.py`, so the prose cannot drift from them
  (`AUDIT_LEDGER.md` §145).
