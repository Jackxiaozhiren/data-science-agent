# Changelog

## 4.3.1 — CI Hardening + GT Lane Robustness (V4.3 patch)

### Fixed

- **CI gate `ruff format --check`**: `verify_release.py` long lines reformatted (commit `b957177` had 1 file unformatted) — `ruff format` now `161 files already formatted`.
- **DataSciBench GT lane subprocess**: `adapter.py` now prefers `workspace/venv/bin/python` (has `metagpt`) with `PYTHONPATH`, parses `evaluation_results/{model}_results.csv` `result_cr` for `passed/failed + score`; `TaskOutcome` import fixed, `sys.executable` fallback. GT present but evaluator missing `loguru` now returns `failed` honest with `evaluator_unavailable` detail, not `execution_error`.

### Changed

- Version `4.3.0 → 4.3.1` (patch, no API change; `SBOM 192 → 193`).

### Verified

- `pytest 276`, `mypy 105 clean`, `ruff OK`, `npm 13/13`, `docker valid`, `dsa verify-release v4.3.1 17/17 PASS`; `DataSciBench` `45/45 failed` honest (execution-only until workspace `venv` fully closed; `uv pip` now closes `metagpt`).

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
