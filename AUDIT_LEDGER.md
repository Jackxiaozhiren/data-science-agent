# DSA Audit Ledger

Executed against `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` Sections 1–31.
Lane for this session: **L1 — Verification integrity** (§10). No source file has
been edited; §18 approval gate has not been passed.

## Baseline

- session: 1   date: 2026-09-24T13:04Z   commit: `150b54f`   lane: L1
- uv sync --dev / uv lock --check: exit 0 / exit 0
- pytest: **397 passed, 0 failed**   coverage: **80.24%**   (gate fail_under = 79)
- ruff check: **0 errors** ("All checks passed!")   ruff format --check: **0 would reformat** (179 files already formatted)
- mypy: **0 issues** ("Success: no issues found in 108 source files")   files checked: **108**
- sync_vendor --check: exit **0** ("OK: vendored dsa_* is in sync")   render_leaderboard --check: exit **127 as written** / exit **0** via `uv run python` ("Leaderboard is valid and synchronized (1 entries).")
- check_npm_workspace_lock: exit **0**   check_public_claims: exit **0** (findings listed: **0**, stdout "✓ No stale claims detected — 0 issues")
- git status --short: **2 lines** (`?? REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`, `?? data-science-agent/`)   git ls-files \| wc -l: **730**   git describe --tags: **v4.4.0-26-g150b54f**
- du -sh artifacts benchmarks data-science-agent node_modules: **4.3G / 2.8G / 1.1G / 484M**
- tracked pytest skip/xfail: **0**   TODO/FIXME markers: **0**

### Baseline measurement methods (§N12 — every count states its method)

| Count | Method |
|---|---|
| 397 passed / 0 failed | Character count of the `-q` progress rows in the §0 step-2 log: `head -6 log \| grep -o '^\.\+' \| awk '{s+=length($0)}'` = 397 dots; a separate scan for `s/S/x/X/w/u/I` status characters in the same rows returned 0. **The suite's own output contains no `passed` summary line** — see D-L1-04. |
| 80.24% | `Total coverage: 80.24%` emitted by `uv run pytest -q --cov --cov-report=term-missing`; TOTAL row = 7643 stmts / 1267 miss / 2166 brpart 439 / 80%. |
| 0 issues (claims) | `uv run python scripts/check_public_claims.py` stdout line 1, exit 0. |
| 730 tracked files | `git ls-files \| wc -l` (not a filesystem walk). |
| 2 untracked lines | `git status --short` exit 0. Both accounted for: `data-science-agent/` per §3.2, and `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`, which §24 R1 names as expected ("the tree is otherwise clean apart from this document and your ledger"). §4's "at most two untracked lines" enumerates `data-science-agent/` + `AUDIT_LEDGER.md` and omits the prompt document itself — a self-inconsistency in the instructions, not a dirty tree. |
| pytest mark.skip/xfail = 0 | `grep -rnE "pytest\.mark\.(skip|xfail)\|xfail" packages apps/api src tests scripts docs --include='*.py' \| grep -v _vendor` → 0 hits. A broader pattern including `skip\(` returns 2 hits, both `pytest.importorskip` at `tests/unit/test_data_engine.py:5-6` — a different mechanism, see D-L1-05. |
| TODO/FIXME/HACK/XXX = 0 | `grep -rnE "TODO\|FIXME\|HACK\|XXX" packages apps/api src tests scripts docs --include='*.py' \| grep -v _vendor` → 0 hits. Scoped to `.py` in those directories; not a whole-repo or markdown scan. |
| mypy 108 files | The `Success:` line's own file count from `uv run mypy packages apps/api src --ignore-missing-imports`. |

### Baseline verdict — GREEN, with one explained exception

§0 steps 1 and 2 (the gates §4 makes stop-conditions) exit 0. Coverage 80.24%
is inside the predicted 79–81% band. Step 3's vendor and npm-lock gates exit 0.
Step 4 matches §4's expectation once the prompt document is accounted for.
Step 5 behaves exactly as §4 predicts: exit 0 **and** no CI wiring.

Two anomalies, both explained, neither a baseline failure:

1. `python scripts/render_leaderboard.py --check` as written exits **127** —
   `command not found: python`. Only `python3` (`/opt/homebrew/bin/python3`) and
   `uv` are on PATH. The gate itself **passes** when run through the interpreter
   that exists. §33's rule for this case is explicit: record it as a finding and
   carry on. Filed as **D-L1-01**.
2. The documented §0/§23 pytest command emits **no test-count line**. §28 stop
   criterion 1 ("not green and you cannot explain why") is not triggered because
   the cause is understood; filed as **D-L1-04**.

## Lane L1 — Verification integrity

**Question (§10):** *Which of this repository's checks cannot fail?*

**Integrity disclosure first.** The session instruction was to read the prompt
document *in full*, and full reading includes §32. So §N9's literal ordering
(enumerate before reading the seed) is not something my own enumeration can
claim. Mitigation actually applied: (a) every item below is derived from
repository evidence with a command behind it, not from the seed; (b) a second,
seed-unaware enumeration was produced by a subagent explicitly barred from
opening `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` and `AUDIT_LEDGER.md`, and
its claims were re-verified against source before being recorded; (c) the
lead-register diff appears only after this block. Items that came from the
subagent rather than from me are marked **[blind-agent]**.

**Probes run.** §10's method table applied per gate: run + record exit code;
`grep -rn <gate> .github/`; violate the gate in a `/tmp` scratch copy and
re-run; read the exit-code path; read the skip/filter logic; read the config the
gate depends on. No file under `src/data_science_agent/_vendor/` was read-edited
or written (§R3); `git status --short` after all probes still shows only the two
expected untracked lines.

| Gate | Defined / invoked at | Wired? | Can it exit non-zero on what it claims to detect? | Class |
|---|---|---|---|---|
| `uv sync --dev` / `uv lock --check` | `ci.yml:73-74` | yes | yes (uv-owned) | trustworthy |
| `pytest --cov` + `fail_under=79` | `ci.yml:87`, `pyproject.toml:187` | yes | yes — but see D-L1-10 (no count in output) | trustworthy-with-caveat |
| `ruff check` | `ci.yml:84` | yes | yes for most rules; **no for S110** | **neutered-by-config** (D-L1-02) |
| `ruff format --check` | `ci.yml:85` | yes | yes (probe: `179 files already formatted`, exit 0) | trustworthy |
| `mypy --strict` | `ci.yml:86` | yes | yes, but `apps/jupyter` is not in its path list | **partial coverage** (D-L1-06) |
| `sync_vendor.py --check` | `ci.yml:75` | yes | yes for content drift; **no** for orphaned copies | **silent-pass subset** (D-L1-04) |
| `check_npm_workspace_lock.py` | `ci.yml:76` | yes | yes (exit 0; `return 1` path at script `:52-88`) | trustworthy |
| `render_leaderboard.py --check` | `leaderboard.yml:32` only, **path-filtered** | partial | yes, but only when `benchmarks/leaderboard/**` or the script itself change | **not-wired-for-normal-PRs** |
| `check_public_claims.py` | **nowhere** (`grep -rn check_public_claims .github/` → exit 1) | **no** | only for 3 of 9 finding kinds | **not-wired + silent-pass** (D-L1-03) |
| `mkdocs build --strict` | `ci.yml:163`, piped to `tail` | yes | **no** — twice over (config + pipe) | **neutered-by-config + masked exit** (D-L1-01, D-L1-05) |
| `generate_sbom.py && test -f release/sbom.json` | `ci.yml:88` | yes | no — the step creates the file it then asserts | **vacuous assertion** (D-L1-08) |
| `npm audit --audit-level=high` | `ci.yml:83` | yes | yes (not executed this session) | untested |
| Web build / regression | `ci.yml:39,161` piped to `tail` | yes | exit code masked | **masked** (D-L1-01) |
| `docker compose config` | `ci.yml:162`, piped to `head` | yes | exit code masked | **masked** (D-L1-01) |
| Benchmark `dsa --limit 5` | `ci.yml:89`, piped to `tail` | yes | exit code masked | **masked** (D-L1-01) |
| `.pre-commit-config.yaml` | local only; **absent from CI** (`grep -rn pre-commit .github/` → exit 1) | no | no — both hooks mutate (`ruff --fix`, `ruff-format` without `--check`) | **not-a-gate** (D-L1-09) |
| `conftest.py` `_vendor` demotion | `conftest.py:26-36`, inside `except Exception: pass` | n/a | n/a — a harness shim, not a gate; nothing verifies it | **verification gap** (D-L1-07) |
| Tests asserting on gate output | `tests/test_automation_scripts.py` | n/a | asserts only on pure helpers; **no test asserts any checker's exit code or stdout** | gap, folded into D-L1-03 |

**Exit-code-path reads.** `check_public_claims.py:248-258` filters to kinds
starting `version_consistency|old_package_pip|old_repo`; everything else prints
and returns 0. `:222-233` skips prefixes `docs/ research/ benchmarks/ plugins/
apps/jupyter/ src/data_science_agent/`. `EXPECTED` keys referenced: only
`version` (`:172,173,184,185,187`). `sync_vendor.py:48-50` `WARN: missing source`
→ `continue`; `main()` calls `sync()` unconditionally (`:85`) which does
`shutil.rmtree` + `copytree` (`:74-75`).

**Novel relative to the seed.** D-L1-01 (pipeline exit-code masking across five
steps), D-L1-02 (S110 disabled in exactly the trees that hold the swallowed
exceptions), D-L1-04 (orphaned-vendor blind spot + `--check` mutates, which
contradicts §24 R3's stated safety model), D-L1-06 (`apps/jupyter` never
type-checked), D-L1-08 (self-satisfying SBOM assertion), D-L1-10 (`-qq` count
blindness), D-L1-11 (`importorskip` on mandatory dependencies). Exhaustiveness
is **not** claimed for L1: `actionlint`, `npm audit`, `regression.mjs`, the
wheel/Docker steps, and `publish.yml`'s reduced gate set were catalogued but not
probed. **[blind-agent]** independently reached the mkdocs, claims-checker,
pre-commit and conftest conclusions; those were re-verified here.

### Findings

Severity was assigned after tier, per §7, and no severity exceeds its tier's
ceiling. No finding here is rated S0: §8's S0 requires an **outward** status or
public claim to be wrong, and `README.md:18-21` carries no CI status badge
(checked by grep), so a falsely-green pipeline is an internal signal. Rating these
S0 would be §25 A4.

### D-L1-01
| field | value |
|---|---|
| claim | Five `run:` steps in `ci.yml` pipe a gate into `tail`/`head` without `pipefail`, so the step reports success even when the gate fails. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S1 |
| location | `.github/workflows/ci.yml:39, :89, :161, :162, :163` |
| mechanism | GitHub Actions' default Linux shell is `bash --noprofile --norc -e` — `-e` without `-o pipefail`. A pipeline's status is the last command's, so `tail`'s 0 replaces the gate's. The five steps that use a pipe are exactly the ones **not** given the explicit `shell: bash` + `set -euo pipefail` header the file's multi-line blocks use (`:61-63, :91-93, :99-101, :122-124, :166-168`). `mkdocs build --strict` — the docs gate §23 lists and `CONTRIBUTING.md:28` mandates — therefore cannot fail CI at all, independently of D-L1-05. |
| evidence_command | `bash --noprofile --norc -e -c 'false \| tail -n 1'; echo $?` then the real gate piped as written |
| output_excerpt | `step_exit=0` (Actions-default shell) vs `step_exit=1` (with `-o pipefail`); real gate: `mkdocs_direct_exit=2` / `mkdocs_piped_exit=0` |
| reproducible | deterministic (≥2 runs) |
| fix_sketch | Add `shell: bash` + `set -euo pipefail` to those five steps, or drop the pipes. Breaks: would newly fail CI on any latent web-build/benchmark/docs error that has been masking. |
| blast_radius | `ci.yml` only; no source, no public contract. Consequence: three gates (docs-strict, web build ×2, benchmark, compose) currently produce false confidence. |
| verify_before | `uv run python -m mkdocs build --strict -f /tmp/audit0/missing.yml 2>&1 \| tail -n 50; echo $?` → `pipeline_exit=0` while the same command unwrapped gives exit 2 |
| verify_after | — not applied: requires a workflow edit (§R7) |
| expected_delta | With pipefail, `bash -c 'false \| tail -n 1'` step status 0 → 1; CI's docs step propagates mkdocs's own code. |
| status | blocked |
| commit | — |
| protected | no |

### D-L1-02
| field | value |
|---|---|
| claim | Ruff's S110 (silently-swallowed exception) rule is selected globally but `per-file-ignores` disable it in 12 trees, so the lint gate reports clean while 42 live instances exist. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S1 |
| location | `pyproject.toml:114` (`select` includes `"S"`), `:118-131` (per-file-ignores), `:117` (`ignore = ["S101","E501"]`) |
| mechanism | `select = [... "S" ...]` enables flake8-bandit, so the repository does nominally own a silent-except gate. `S110` is then listed in `per-file-ignores` for `packages/agent`, `plugins`, `datasets`, `evaluation`, `evidence`, `execution`, `llm`, `tools`, `mcp`, `apps/api/routers`, `apps/jupyter` and `tests/**`. The gate is switched off in precisely the modules whose swallowed exceptions §12 treats as correctness-bearing, so "All checks passed!" is produced by configuration, not by absence of defects. This is the config-neutering probe §10 prescribes, and it is the highest-value L1 result because it changes how much of L3's future green is earned. |
| evidence_command | `uv run ruff check packages apps/api tests src apps/jupyter --select S110` vs `uv run ruff check --isolated --select S110 packages apps/api tests src apps/jupyter --output-format=concise` |
| output_excerpt | A (as configured): `All checks passed!` exit 0. B (`--isolated`): `Found 77 errors.` Split by path: `in _vendor (double-counted mirror): 35`, `live (excluding _vendor): 42`. |
| reproducible | deterministic |
| fix_sketch | Remove `S110` from the per-file-ignores of the shipped trees, then classify each surfaced site per §12 (Hiding / Downgrading / Legitimate) instead of blanket-re-ignoring. Breaks: CI turns red on 35 shipped sites until they are individually dispositioned. Note this **narrows** an exclusion — §R11 and §N6 forbid widening one, not this. |
| blast_radius | `pyproject.toml` lint config + every package listed above; no public contract. 35 shipped-code sites + 7 test sites newly visible. |
| verify_before | `uv run ruff check packages apps/api tests src apps/jupyter --select S110` → `All checks passed!`, exit 0 |
| verify_after | — not applied, pending §18 approval |
| expected_delta | That exact command's output `All checks passed!` → `Found 42 errors` (35 shipped + 7 tests); `_vendor` stays excluded, so 42 not 77. |
| status | open |
| commit | — |
| protected | no |

### D-L1-03
| field | value |
|---|---|
| claim | `scripts/check_public_claims.py` is inert in four independent ways and cannot detect stale test counts, mypy counts, coverage figures or route counts at all. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S1 |
| location | `scripts/check_public_claims.py:14-35, :222-233, :248-258`; wiring `grep -rn check_public_claims .github/` |
| mechanism | (i) No workflow, hook or schedule invokes it. (ii) Findings are keyed `f"{kind}:{path}"` (`:236`), so only `version_consistency`, `old_package_pip`, `old_repo` reach `return 1` — `stale_version`, `stale_test_counts`, `stale_mypy`, `stale_coverage`, `stale_routes`, `old_package_import` and `maturity` all print and exit 0. (iii) The skip-prefix block discards every match from `docs/`, `plugins/`, `apps/jupyter/`, `src/data_science_agent/`, so four of the twelve `SCAN_GLOBS` entries can never yield a finding — including `docs/**/*.md` and `src/data_science_agent/sdk.py`, which the same file lists as targets. (iv) `EXPECTED` is commented "from pyproject/CITATION live" but is a literal dict in which only `version` is ever read; the other 19 keys (`pytest`, `mypy`, `coverage`, `routes`, `sbom`, …) are unreferenced, and the patterns hard-code three old strings. So a document claiming any wrong number is invisible unless it happens to repeat `155`/`86+`/`86`. Combined with §23's own warning that exit 0 is not a pass, this is why the §0 step-5 result means nothing on its own. |
| evidence_command | scratch copy at `/tmp/claims_probe` (script + minimal `pyproject.toml`/`CITATION.cff`/`sdk.py`/`__init__.py`/`sbom.json`), `GITHUB_REF_NAME=release/v4.4.0-rc`, six injections P0-P5 |
| output_excerpt | P0 clean → `✓ No stale claims detected — 0 issues` exit 0. P1 `4.0.0` in README → `Found 1 potential stale claim(s): [stale_version:README.md] '4.0.0'` / `⚠ Low/medium issues` **exit 0**. P2 `pip install data-science-agent` → **exit 1**. P3 `4.0.0`/`3.0.0`/`2.0.0` in `docs/foo.md` → **0 issues, exit 0**. P4 `999 tests passing, mypy 555 issues, coverage 12%` → **0 issues, exit 0**. P5 `155 tests` → found, **exit 0**. Fail-closed control: scratch `pyproject.toml` version 4.3.9 → `[version_consistency] version mismatch: pyproject=4.3.9 != expected 4.4.0` **exit 1**. |
| reproducible | deterministic |
| fix_sketch | (a) wire it into `ci.yml`; (b) delete or honour the dead `EXPECTED` keys; (c) drop `docs/` and `src/data_science_agent/` from the skip list so its stated targets are actually read. Breaks: enabling it will fail CI on whatever `docs/` really contains — unknown, and that unknown is the finding. |
| blast_radius | `scripts/check_public_claims.py` + `.github/workflows/ci.yml` (approval needed); no runtime code, no public contract. |
| verify_before | P4: a README asserting a wholly wrong test/mypy/coverage triple → `0 issues`, exit 0 |
| verify_after | — not applied, pending §18 approval |
| expected_delta | `grep -rn check_public_claims .github/` hits 0 → ≥1; P4's result `0 issues` → a non-empty finding list. |
| status | open |
| commit | — |
| protected | no |

### D-L1-04
| field | value |
|---|---|
| claim | `sync_vendor.py --check` cannot detect a vendored copy whose source directory no longer exists, and `--check` is not read-only. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S1 |
| location | `scripts/sync_vendor.py:48-50` (`WARN` + `continue`), `:85` (`changed = sync()` on both paths), `:74-75` (`rmtree`/`copytree`), `:96-104` (`before == after` decides) |
| mechanism | `sync()` skips any source that is not a directory, so the corresponding `_vendor/<name>/` tree is never revisited; `before` and `after` are snapshots of `_vendor` only, so an orphaned copy is byte-identical in both and the drift test passes. Consequence: delete or rename a package (the stub-package question in §13.3, governed by §R10) and the stale duplicate keeps shipping in the wheel while CI prints OK. Second, independent point: `main()` always runs `sync()`, so `--check` mutates the checkout it is auditing and infers drift from whether *its own copy* changed bytes — contradicting §24 R3 and §33's "bare `sync_vendor.py` writes; use `--check`", which presents `--check` as the non-writing form. |
| evidence_command | scratch tree `/tmp/svprobe` with an orphaned `_vendor/dsa_agent/old.py` and no matching source |
| output_excerpt | 15 × `WARN: missing source /private/tmp/svprobe/...` then `OK: vendored dsa_* is in sync` → `check_exit=0`, with the orphaned file present; control run after deleting the orphan: identical output, `control_exit=0`. Real repo: `--check` exit 0 and the `git status --short` that follows it unchanged, so no byte drift existed to rewrite. |
| reproducible | deterministic |
| fix_sketch | Add orphan detection: any `_vendor/<name>` with no key in `SOURCES`, or any key in `SOURCES` whose dest exists while its src does not, is drift. Separately, make `--check` compare src→dst hashes without copying. Breaks: a clean `--check` may start reporting real orphans. |
| blast_radius | `scripts/sync_vendor.py`; affects trust in `ci.yml:75` and in the published wheel's contents. No public contract change. |
| verify_before | orphaned `_vendor/dsa_agent/old.py` → `OK: vendored dsa_* is in sync`, exit 0 |
| verify_after | — not applied, pending §18 approval |
| expected_delta | Same scratch invocation: exit `0` → `1`, and `OK:` → `DRIFT:`. |
| status | open |
| commit | — |
| protected | no — but see §21.4: §32.3 protects "`--check` passing" as a healthy signal; this finding refines *what it checks* and does not propose replacing the mechanism. |

### D-L1-05
| field | value |
|---|---|
| claim | `mkdocs build --strict` has no link signal, because `mkdocs.yml` downgrades both link validations to `ignore` while `CONTRIBUTING.md:28` mandates the strict check. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S2 |
| location | `mkdocs.yml:43-46` (`validation: links: not_found: ignore / absolute_links: ignore`); mandate at `CONTRIBUTING.md:28`; invocation `ci.yml:163` |
| mechanism | `--strict` promotes warnings to errors; `not_found: ignore` stops mkdocs emitting a warning for a broken link in the first place, so there is nothing for `--strict` to escalate. The mandated check is therefore satisfied by any build that renders, and a contributor following `CONTRIBUTING.md` reasonably believes link integrity is covered. Combined with D-L1-01 the step has two independent failure-suppressions. |
| evidence_command | `/tmp/mkprobe` project using the repo's exact `validation` block plus a broken internal link, built with `--strict` |
| output_excerpt | `[missing page](does-not-exist.md)` → `direct_exit=0`, log shows only `INFO - Building documentation…` / `Documentation built in 0.17 seconds`. Real repo: `mkdocs_strict_direct_exit=0`, `43` log lines, `grep -cE "WARNING|ERROR"` → `0`. |
| reproducible | deterministic |
| fix_sketch | Set `not_found: warn` (keep `absolute_links: ignore` if absolute links are legitimately external). Breaks: any genuinely broken relative link in `docs/` now fails the strict build — currently unknown, and the real build emitted 0 warnings, so the predicted violation count is low. |
| blast_radius | `mkdocs.yml`; docs build only. No source, no contract. |
| verify_before | broken link + repo's validation block under `--strict` → exit 0 |
| verify_after | — not applied, pending §18 approval |
| expected_delta | Same scratch project: exit `0` → `1` on a broken relative link. |
| status | open |
| commit | — |
| protected | no |

### D-L1-06
| field | value |
|---|---|
| claim | `apps/jupyter` is never type-checked in CI, although its mypy override section exists and mypy itself reports that section as unused. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S3 |
| location | `ci.yml:86` and `publish.yml:58` (`mypy packages apps/api src`); `pyproject.toml` `[[tool.mypy.overrides]] module = "dsa_jupyter.*"`; `mypy_path` includes `apps/jupyter/src`; `ruff` CI paths *do* include `apps/jupyter` |
| mechanism | Ruff lints `apps/jupyter` but mypy's explicit path list omits it, so one surface of the eight is style-checked and never type-checked. The config file still carries a `dsa_jupyter.*` override, and mypy's `warn_unused_configs` reports it as dead on every CI run — the tool itself is announcing that a configuration section exists for code it never examines. `dsa_jupyter` is also a declared coverage source, so tests touching it register coverage against an untype-checked module. |
| evidence_command | baseline §0 mypy run + `uv run mypy apps/jupyter --ignore-missing-imports` |
| output_excerpt | CI-equivalent run: `pyproject.toml: note: unused section(s): module = ['dsa_jupyter.*']` / `Success: no issues found in 108 source files`. jupyter-only run: `Success: no issues found in 4 source files`. |
| reproducible | deterministic |
| fix_sketch | Append `apps/jupyter` to the mypy path list in `ci.yml:86` and `publish.yml:58`. Breaks: nothing measured — the module type-checks clean today, so this is a zero-violation gate extension. |
| blast_radius | Two workflow files (approval needed, §R7); 4 files newly type-covered. |
| verify_before | mypy reports `unused section(s): … dsa_jupyter.*` and checks `108 source files` |
| verify_after | — not applied: workflow edit, §R7 / §27 |
| expected_delta | `108 source files` → `112 source files`, and the `unused section(s)` note disappears. |
| status | blocked |
| commit | — |
| protected | no |

### D-L1-07
| field | value |
|---|---|
| claim | Nothing verifies which copy of a `dsa_*` module the test session imports, so a failure of `conftest.py`'s `_vendor` demotion would be silently absorbed. |
| lane | L1 |
| evidence_tier | T0 (consequence) / T3 (absence of a guard) |
| severity | S3 |
| location | `conftest.py:26-36` (`try: import data_science_agent … except Exception: pass`), `:4-24` (`if p.exists():` path inserts) |
| mechanism | The shim is load-bearing, not decorative: with it, `dsa_agent` resolves to `packages/agent/src`; without it, `import data_science_agent` puts `_vendor` on `sys.path[0]` and the same import resolves to `src/data_science_agent/_vendor/dsa_agent/__init__.py` — demonstrated below. If the demotion ever no-ops (the `except Exception: pass`, or the `while … in sys.path` string match failing because the two paths are computed independently), the suite would exercise the vendored mirror while coverage — which omits `*/_vendor/*` — attributes nothing, and no assertion would notice. A scoped grep for any test touching import identity (`__file__`, `_vendor`, `sys.path`) returns only unrelated path/`REPO` constants; `tests/test_automation_scripts.py` asserts on pure helpers only. §10 asks this question directly; the answer is "no test would notice". |
| evidence_command | `uv run python -c "import data_science_agent, dsa_agent; print(dsa_agent.__file__)"` and the same with conftest's demotion applied |
| output_excerpt | without demotion → `dsa_agent -> /Users/jackson/Data agent/src/data_science_agent/_vendor/dsa_agent/__init__.py`; with demotion → `…/packages/agent/src/dsa_agent/__init__.py` |
| reproducible | deterministic |
| fix_sketch | One guard test asserting `"/_vendor/" not in dsa_agent.__file__` for a representative package. Breaks: nothing today. §N3 caveat recorded honestly: such a test is **green on arrival**, so it cannot be red-then-green in the usual sense — the red must be produced by injecting a broken shim (e.g. monkeypatching the demotion off) and showing the guard fires. |
| blast_radius | `conftest.py` / one new test file. No product code, no contract. |
| verify_before | no test asserts import identity (scoped grep → 0 relevant hits); wrong-shim resolution demonstrably yields `_vendor` |
| verify_after | — not applied, pending §18 approval |
| expected_delta | pytest collected 397 → 398, with the new test green under normal conftest and red under an injected demotion failure. |
| status | open |
| commit | — |
| protected | partial — §32.3 protects the shim's **existence** and `conftest.py`'s demotion as correct-by-design. This finding asks only that it be *observed*, not changed. |

### D-L1-08
| field | value |
|---|---|
| claim | CI's SBOM step asserts the existence of a file the same step just created, so it can never fail. |
| lane | L1 |
| evidence_tier | T2 (read of the step; not executed — it mutates a tracked file) |
| severity | S3 |
| location | `.github/workflows/ci.yml:88` |
| mechanism | `uv run python scripts/generate_sbom.py && test -f release/sbom.json` — the left operand writes `release/sbom.json`, so `test -f` restates the writer's success rather than checking anything about the SBOM (no version, no package count, no schema). §23 already notes the script "always exits 0"; the assertion added on top is vacuous. §32.3 protects the SBOM artifact itself; this is about the check, not the artifact. |
| evidence_command | `grep -n "generate_sbom" .github/workflows/ci.yml` |
| output_excerpt | `ci.yml:88: - run: uv run python scripts/generate_sbom.py && test -f release/sbom.json  # §47 SBOM` |
| reproducible | not executed (§R8: mutates a tracked file) |
| fix_sketch | Assert content instead: the SBOM's `version` equals `pyproject` version and its package list is non-empty. Breaks: nothing if true; surfaces a real mismatch if false. |
| blast_radius | One workflow line (needs §27 approval). |
| verify_before | — (no command run; the file writes a tracked artifact) |
| verify_after | — |
| expected_delta | Gate acquires a checkable predicate; no numeric delta predicted without running it. |
| status | hypothesis-tier-evidence / open |
| commit | — |
| protected | no |

### D-L1-09
| field | value |
|---|---|
| claim | `.pre-commit-config.yaml` is not a gate: it is absent from CI and both of its hooks rewrite rather than fail. |
| lane | L1 |
| evidence_tier | T0 (wiring) / T2 (mutating behaviour, not executed) |
| severity | S3 |
| location | `.pre-commit-config.yaml:1-7`; `grep -rn "pre-commit\|pre_commit" .github/` → no hits, exit 1 |
| mechanism | `ruff` runs with `args: [--fix]` and `ruff-format` runs without `--check`, so a violation is silently repaired instead of reported — meaning pre-commit can exit 0 on code that `ci.yml` would reject. Its delta against the §23 table is 2 of ~13 gates (lint + format), and it covers none of mypy, tests, coverage, vendor drift, npm lock, leaderboard, mkdocs or SBOM. §23 already warns "pre-commit success is not equivalent to this table"; the measurement is that it is not even a failing check of that subset. |
| evidence_command | `grep -rn "pre-commit\|pre_commit" .github/ ; echo $?` |
| output_excerpt | `NOT IN CI (exit 1)` |
| reproducible | deterministic |
| fix_sketch | No repo change proposed in L1. If a doc implies pre-commit suffices, correct the doc (§L5). |
| blast_radius | informational |
| verify_before | grep exit 1 |
| verify_after | — |
| expected_delta | none proposed |
| status | open (recorded, not recommended for fix) |
| commit | — |
| protected | no |

### D-L1-10
| field | value |
|---|---|
| claim | The tests+coverage gate prints no test count, so losing tests outright is invisible in the gate's own output. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S3 |
| location | `pyproject.toml:168` (`addopts = "-q --asyncio-mode=auto"`) combined with §0/§23's `uv run pytest -q …` |
| mechanism | `addopts` already supplies `-q`, and the documented gate command adds another, so pytest runs at `-qq` and omits the `N passed in Ts` line. The §16 baseline field "pytest: <?> passed, <?> failed" cannot be filled from the gate's output; I had to count progress-row characters to derive 397. A deleted, renamed or non-collected test leaves no trace except a small coverage move. |
| evidence_command | `grep -n "passed" /tmp/audit0/02d_pytest.log` on the §0 step-2 capture |
| output_excerpt | zero matches (`grep -c . ` over the file: 146 lines, none containing `passed`); derived count from `head -6 log \| grep -o '^\.\+' \| awk '{s+=length($0)}'` → `dots=397`, and 0 status characters other than `.` |
| reproducible | deterministic |
| fix_sketch | Use `--tb=short -q` in the documented command, or add `--durations`-free `-ra`, or drop `-q` from `addopts`. Prefer documenting a report flag over editing `addopts`, which would change every developer's local run. |
| blast_radius | documentation of the gate command, or one `pyproject.toml` line. |
| verify_before | gate output contains no `passed` line |
| verify_after | — |
| expected_delta | `grep -c passed` on the log: 0 → 1. |
| status | open |
| commit | — |
| protected | no |

### D-L1-11
| field | value |
|---|---|
| claim | `tests/unit/test_data_engine.py` guards two **mandatory** dependencies with `pytest.importorskip`, and its stated reason contradicts `pyproject.toml`. |
| lane | L1 |
| evidence_tier | T1 |
| severity | S3 |
| location | `tests/unit/test_data_engine.py:5-6`; `pyproject.toml:31-32` (`"duckdb>=1.0"`, `"polars>=1.0"`) |
| mechanism | The reason strings read "Phase 2: duckdb not yet required", but both are unconditional runtime dependencies of the distribution, so in any real environment the skip branch is unreachable and the assertion is dead weight; in the one environment where it *is* reachable (deps removed), the test skips, the suite stays green, and §16's regression tripwire (`pytest.mark.skip`/`xfail` = 0) does not count `importorskip` at all. The tripwire has a hole in its own definition, which is why the §3.1 "0 skips" claim is simultaneously true and not the whole story. |
| evidence_command | `grep -rnE "pytest\.mark\.(skip|xfail)\|xfail" packages apps/api src tests scripts docs --include='*.py' \| grep -v _vendor \| wc -l` then the same for `importorskip` |
| output_excerpt | marks: `0`. `importorskip`: `2` — `tests/unit/test_data_engine.py:5` and `:6`. |
| reproducible | deterministic for the counts; the skip branch itself not exercised (T1 ceiling) |
| fix_sketch | Drop the two `importorskip` calls and import directly, so a missing hard dependency is an error rather than a silence. Breaks: nothing, since both are required deps. |
| blast_radius | one test file |
| verify_before | 397 collected, all dots, 0 skips — the guard never fires here |
| verify_after | — |
| expected_delta | `importorskip` count in tracked tests 2 → 0; §16 tripwire line gains an `importorskip` term. |
| status | open |
| commit | — |
| protected | no |

### D-L1-12
| field | value |
|---|---|
| claim | Two of the authorized command surfaces are not runnable as written on this host. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S3 |
| location | `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` §0 step 3 and §23/§33 (`python scripts/render_leaderboard.py --check`); §4's expected-untracked-line list |
| mechanism | Bare `python` is absent (`command not found`, exit 127); only `python3` and `uv` resolve, so §0's step-3 gate and §23's leaderboard row cannot be reproduced verbatim. CI is *not* affected — `leaderboard.yml:26-29` uses `setup-python`, which puts `python` on PATH — so this is a local-replication and DX defect, not a product defect, and §33's rule ("record it as a finding and carry on") applies. Separately, §4 predicts "at most two untracked lines" and enumerates `data-science-agent/` + `AUDIT_LEDGER.md`, omitting `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` itself, which §24 R1 does acknowledge — the two sections disagree. |
| evidence_command | `(python scripts/render_leaderboard.py --check); echo $?`; `command -v python python3 uv` |
| output_excerpt | `render_leaderboard_check_exit=127` / `(eval):1: command not found: python`; `command -v` → `/opt/homebrew/bin/python3`, `/Users/jackson/.local/bin/uv`, nothing for `python`. Via wrapper: exit 0, `Leaderboard is valid and synchronized (1 entries).` |
| reproducible | deterministic |
| fix_sketch | Document `uv run python` for these two lines (the prompt document, not the repo) and add a Makefile/justfile so the scoped gate set is discoverable — §20 uplift item 6. |
| blast_radius | instructions surface only |
| verify_before | exit 127 |
| verify_after | exit 0 via `uv run python` |
| expected_delta | §0 step 3 reproduced verbatim: 127 → 0 after documenting the wrapper. |
| status | open |
| commit | — |
| protected | no |

### Lead-register diff

Opened **after** the enumeration block above was committed at `888ae36` (§17.2).
Scope note: §32 mixes lanes, so seeds belonging to L2-L6 are marked out-of-lane
rather than judged.

| Seed (§32) | Verdict | Evidence that decided it |
|---|---|---|
| `check_public_claims.py` written-never-run; exit path filters to 3 kinds; skip-prefix excludes most targets | **CONFIRMED** → D-L1-03 | `grep -rn check_public_claims .github/` exit 1; six scratch injections P0-P5, of which P1/P5 print findings at **exit 0** and P2 reaches exit 1 |
| — same seed, extent: "report what it would catch *if it ran*" | **EXTENDED beyond the seed** | P4 (`999 tests / mypy 555 / coverage 12%`) → `0 issues`. Root cause the seed does not name: only `EXPECTED["version"]` is ever read (`:172-187`), so 19 of 20 keys are dead and no metric claim is checkable at all. Four of twelve `SCAN_GLOBS` are enumerated then discarded. **[blind-agent]** additionally measured `packages/**/README.md` matching 0 files. |
| `mkdocs.yml` validation block may neuter `--strict`; `CONTRIBUTING.md` mandates it | **CONFIRMED** → D-L1-05 | `mkdocs.yml:43-46` both modes `ignore`; scratch project with the repo's exact block + broken internal link → `--strict` exit **0**; real build exit 0 with `grep -cE "WARNING\|ERROR"` → **0**; mandate at `CONTRIBUTING.md:28` |
| — not in the seed | **NEW** → D-L1-01 | `ci.yml:39,89,161,162,163` pipe gates to `tail`/`head` with no `pipefail`; Actions default shell proven `step_exit=0` vs `-o pipefail` `step_exit=1`; real gate `mkdocs_direct_exit=2` / `mkdocs_piped_exit=0`. So the docs gate is suppressed twice, not once. |
| Coverage gate `fail_under = 79` vs ~80%; "is the margin documented or folklore" | **CONFIRMED, and the answer is "documented"** | measured `80.24%` against the gate; `pyproject.toml:186` carries `# Ratchet at 79 (measured 80.0 on 2026-09-24; 1pt margin for platform noise)`. Headroom 1.24 pt. Same-day comment says 80.0 vs measured 80.24 — a rounding difference, not drift. **No action recommended; recorded as reviewed-correct.** |
| `_vendor` excluded from ruff, mypy and coverage — "what do the exclusions cost" | **CONFIRMED, cost ≈ nil today** | exclusions at `pyproject.toml:113`, `:143-154`, `:181`; the same bytes are linted and type-checked at source (`ruff check` → `All checks passed!`, `mypy` → `108 source files`, both exit 0) and `sync_vendor --check` reports in-sync, so the source path is authoritative. **No finding opened** — manufacturing one here would be §25 A1. The real gap adjacent to it is D-L1-02 (S110 is off in the *live* trees, which the exclusion question distracts from). |
| `conftest.py` root-only with a `_vendor` sys.path shim — "what if it were wrong, would a test notice" | **CONFIRMED, answer: no test would notice** → D-L1-07 | only one conftest (`git ls-files \| grep conftest`); shim proven load-bearing (with it `packages/agent/src`, without it `_vendor/dsa_agent/__init__.py`); `except Exception: pass` at `:35`; identity-assertion grep → 0 relevant hits; `tests/test_automation_scripts.py` asserts on pure helpers only |
| `.pre-commit-config.yaml` — state the delta; does any doc imply sufficiency | **CONFIRMED** → D-L1-09 | `grep -rn "pre-commit" .github/` → exit 1 (absent from CI); both hooks mutate. Delta = 2 of ~13 §23 gates. No doc claiming sufficiency found by this lane's scoped greps — **INCOMPLETE on that sub-question**, since a positive claim could sit in `docs/` under different wording. |
| `.github/CODEOWNERS` handle vs the org's real identity | **BLOCKED / INCOMPLETE** | file assigns `/packages/mcp/`, `/docs/`, `/benchmarks/` → `@jackson`, while `pyproject.toml:9-10` names `jackxiaozhiren` and the git author is `CommandCodeBot`. Confirming which handle exists requires an identity lookup; §33 authorizes no network command and §26 forbids fetching external state. Needs a human (§27). Flagged as a possible silent review-assignment no-op. |
| `ci.yml` pinned version strings | **CONFIRMED, and inert twice over** | `ci.yml:164` step name "Verify **v4.3.0** release candidate" while `pyproject.toml:3` is `4.4.0`; `:165` gates it on `github.event.pull_request.number == 47`, so it can fire on at most one PR ever. `.venv/bin/dsa verify-release v4.3.0 --json` is the sole reference to that checker in `.github/`. Not filed as a separate finding because it is a workflow edit (§R7); folded into §21.5 decisions. |
| `pytest.mark.skip`/`xfail` = 0 (regression tripwire, §3.1/§16) | **CONFIRMED for marks; the tripwire has a hole** → D-L1-11 | marks grep → `0`; `importorskip` grep → `2`, both on mandatory deps (`pyproject.toml:31-32`) with a "not yet required" reason |
| §32.2 "~48 swallowed-exception sites" vs §12's snippet returning 176 | **RECONCILED — counting-method artifact, and my instrument lands near the 48** | ruff S110 on the same paths: `All checks passed!` (0) as configured, `42` live with `--isolated` (35 shipped + 7 tests), `77` including `_vendor`'s 35 duplicates. So 0 / 42 / 77 / 176 are four different questions. The seed's own point stands: the count is not the finding, the per-site class is (§12). |
| §32.2 three-way metric contradiction (324 / 395 / 257 / ~302) | **PARTIALLY RESOLVED** | authoritative figure this session: **397** collected, by character count of the `-q` rows (method in the baseline block). Why the repo's own checker cannot arbitrate: D-L1-03(iv). The reconciliation of the other three figures is L5's, not L1's. |
| §32.2 "23 orphaned docs vs nav ~24 of 47" | **NOT ADJUDICATED — out of L1 scope, and my first measurement was method-unsafe** | `git ls-files 'docs/**/*.md'` → 21 vs 24 nav lines by a hand-rolled regex; two methods I would not stake a finding on. Left for L5 with the warning that both counts above are pattern-dependent. |
| §32.1 repro-bundle `except: pass`, `critic.py` vacuous pass, `validator.py` never raises | **OUT OF LANE** (L2) | not investigated; §5.3 orders L2 after L1. Note the dependency §17.6 creates: D-L1-02 and D-L1-03 mean a future L2 green must not be read as "the swallow and the claim were checked". |
| §32.2 two engines, god files, stub packages, import cycle, frontend, SECURITY.md | **OUT OF LANE** (L3-L6) | untouched this session |

### Fixes applied

_None. §18 approval gate not passed; no source file edited. Ledger commits: `b4f3bf6` (baseline, §N10), `888ae36` (enumeration + findings)._

### Deliberate non-actions

- Did not open a finding for the `_vendor` exclusions' cost, the coverage ratchet's
  margin, the case-study count, or `sync_vendor --check` passing. Each was
  measured and found correct or immaterial; see §21.4.
- Did not touch any §32.3 protected item. Verification that each was *looked at*
  is in §21.4, including the case-study count method trap (`ls -d case-studies/*/`
  → **9**, numbered studies → **8**, README claim **8**: the naive count is wrong,
  the claim is right, so the claim was left alone).
- Did not propose widening or narrowing any exclusion to turn a number green.
  D-L1-02 *narrows* an exclusion, which adds signal; §R11/§N6 prohibit the
  opposite and this session did neither.
- Did not run `generate_sbom.py` or `render_leaderboard.py --write` (§R8, §R10) —
  both mutate tracked files, and §23's `--check` variants sufficed.
- Did not "fix" D-L1-01's severity upward on the strength of how alarming a
  falsely-green CI sounds; `README.md:18-21` carries no CI status badge, so the
  §8 S0 test (outward status wrong) is not met and S1 stands.

## Phase 2 — Triage (approval gate, §18)

Priority = Impact × Risk ÷ Effort, with §18's R-B (prefer fixes that make a
silent gate able to fail) applied as the ordering override. Two hard rules bound
the list: no S0 exists in this lane, and three items are `BLOCKED` because they
require a workflow edit (§R7).

| # | id | sev | tier | I | R | E | I×R/E | blocked? | one-line mechanism | what could get worse |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | D-L1-01 | S1 | T0 | 5 | 5 | 1 | **25** | **yes** (§R7) | Actions' default shell has no `pipefail`, so five steps report `tail`'s exit code, not the gate's | Latent web-build / benchmark / docs failures surface at once and CI goes red on `main` for the first time |
| 2 | D-L1-02 | S1 | T0 | 4 | 3 | 3 | **4.0** | no | `select` includes bandit `S`, then `per-file-ignores` turn `S110` off in 12 trees | CI turns red on 35 shipped sites; each needs a Hiding/Downgrading/Legitimate call (§12), so the churn is real |
| 3 | D-L1-03 | S1 | T0 | 4 | 3 | 2 | **6.0** | partly (CI wiring = §R7) | Unwired, filtered to 3 of 9 kinds, skips its own listed targets, 19/20 `EXPECTED` keys dead | Wiring it makes previously-invisible stale claims fail the build; the `docs/` population has never been scanned, so volume is unknown |
| 4 | D-L1-04 | S1 | T0 | 4 | 2 | 2 | **4.0** | no | `--check` skips absent sources and always runs `sync()`, so orphaned vendor copies pass and the auditor mutates | A genuine orphan surfaced today would mean the published wheel ships code with no source |
| 5 | D-L1-07 | S3 | T0/T3 | 3 | 1 | 1 | **3.0** | no | Nothing pins which copy of `dsa_*` the suite imports; the demotion sits in `except Exception: pass` | Near-nil. Note §N3 caveat: the guard is green on arrival, so its red must come from an injected shim failure |
| 6 | D-L1-05 | S2 | T0 | 2 | 2 | 1 | **2.0** | no | `not_found: ignore` means `--strict` has no link signal | Real broken relative links newly fail the docs build |
| 7 | D-L1-06 | S3 | T0 | 2 | 1 | 1 | **2.0** | **yes** (§R7) | mypy's CI path list omits `apps/jupyter`; mypy itself reports that override as unused | Nothing measured — `apps/jupyter` type-checks clean today (4 files), so this is a zero-violation extension |
| 8 | D-L1-10 | S3 | T0 | 2 | 1 | 1 | **2.0** | no | `addopts -q` + `-q` = `-qq`, so the tests gate prints no count | Cosmetic: every CI log gains a line |
| 9 | D-L1-11 | S3 | T1 | 1 | 1 | 1 | **1.0** | no | `importorskip` on two mandatory deps; the mark-based tripwire cannot see it | A dev environment missing a required dep silently skips instead of erroring |
| 10 | D-L1-12 | S3 | T0 | 1 | 1 | 1 | **1.0** | no (doc text) | `python scripts/render_leaderboard.py --check` → exit 127; §4's untracked-line list contradicts §24 R1 | None |
| 11 | D-L1-08 | S3 | T2 | 2 | 1 | 2 | **1.0** | **yes** (§R7) | `generate_sbom.py && test -f <file it just wrote>` is self-satisfying | Content assertions could fail on a real SBOM mismatch |
| — | D-L1-09 | S3 | T0/T2 | — | — | — | **not recommended for fix** | | pre-commit absent from CI and mutating by design | Informational; any change is a contributor-workflow decision |

**Recommended this session if approved:** 2, 3 (its non-workflow parts), 4, 5, 6,
8, 9 — seven findings, all §19 red-then-green capable, none requiring a workflow
edit. Items 1, 7, 11 are ready as diffs but are `BLOCKED` on §R7/§27 approval;
item 10 is a documentation edit to the prompt file, not to the repository.

**Not recommended for fixing:** D-L1-09 (pre-commit) — repairing it into a real
gate duplicates `ci.yml` and slows every commit for signal CI already produces.

## Phase 5 — Report

### 21.1 Executive summary

The repository is green, honest about its debt markers (0 `TODO`/`FIXME`, 0
`mark.skip`/`xfail`), and 397 tests pass at 80.24% coverage against a ratchet of
79 — so on the surface this is a healthy tree. The lane's answer to *can any
signal be trusted* is nonetheless no: **nine of §23's thirteen gates cannot fail
on something they claim to check or are not wired the way §23 implies** (lint,
types, vendor drift, leaderboard, claims, docs, SBOM, benchmark, frontend), one
carries a count-blindness caveat (tests), two are clean (format, npm lock), and
one was catalogued but not probed (build). The two strongest results were
produced here rather than taken from the seed: five CI steps whose exit code
belongs to `tail`, and a bandit `S110` rule that is enabled and then disabled in
twelve trees, reporting "All checks passed!" over 42 live instances. Nothing was
fixed: §18 requires approval first, so the output is this committed ledger plus a
ranked plan. What needs a decision beyond approval: three workflow-edit findings,
the `CODEOWNERS` handle, and the 1.1 GB nested `data-science-agent/`.

### 21.2 Repairs

| id | severity | what was wrong | commit | verify_before | verify_after |
|---|---|---|---|---|---|
| — | — | none; §18 approval gate closed, no source file edited | — | — | — |

Audit-artifact commits: `b4f3bf6` (baseline), `888ae36` (enumeration + findings),
plus this report's commit.

### 21.3 Numeric attestation

| metric | baseline | after | delta | command |
|---|---|---|---|---|
| tests passed | 397 | 397 | 0 | `uv run pytest -q --cov --cov-report=term-missing`, count derived from `-q` row characters (see D-L1-10) |
| coverage % | 80.24 | not re-run | — | same command; no code changed so no re-run was warranted |
| ruff errors (configured set) | 0 | 0 | 0 | `uv run ruff check packages apps/api tests src apps/jupyter` |
| ruff S110 live instances | 0 reported / **42 actual** | unchanged | 0 | `--select S110` vs `--isolated --select S110` |
| ruff format | 0 would reformat (179 files) | unchanged | 0 | `uv run ruff format --check …` |
| mypy issues / files | 0 / 108 | unchanged | 0 | `uv run mypy packages apps/api src --ignore-missing-imports` |
| tracked files | 730 | **731** | **+1** | `git ls-files \| wc -l` — the ledger itself, the only intended addition |
| skip+xfail marks | 0 | 0 | 0 | grep, method in the baseline block |
| TODO/FIXME/HACK/XXX | 0 | 0 | 0 | grep, `.py` under `packages apps/api src tests scripts docs` |
| vendor drift | in sync | in sync | 0 | `uv run python scripts/sync_vendor.py --check` |

§16's regression tripwire is satisfied: no skip, xfail or debt marker was added.
The single non-zero delta is the tracked-file count, and it is the ledger.

### 21.4 Non-findings and protected items (mandatory, §N11)

**Seeds refuted or narrowed, with the command that did it.**

- "26 commits past the tag is drift to fix" — refuted as a defect.
  `git describe --tags` → `v4.4.0-26-g150b54f`, and `check_public_claims.py`'s
  version gate accepts it because `base_tag` is `v4.4.0`; the fail-closed control
  proved that same gate fires on a real mismatch (`pyproject=4.3.9 != expected
  4.4.0`, exit 1). Left alone (§32.3).
- "`sync_vendor --check` passing means the mechanism is healthy, nothing to say"
  — narrowed, not refuted: content drift *is* caught, orphan drift is not
  (D-L1-04). The scratch probe printed `WARN: missing source` ×15 and then `OK`,
  exit 0, with an orphaned file present.
- "`_vendor` exclusions must cost something" — measured as ≈ nil today and **no
  finding filed** (see the diff table).
- "The coverage margin is folklore" — refuted: it is dated in
  `pyproject.toml:186` and matches the measurement to 0.24 pt.
- "My first probe found a `conftest.py` path-string mismatch" — **retracted as
  my own measurement error.** The probe used `Path('conftest.py').parent`, which
  yields a relative string, and compared it to an absolute `sys.path` entry. The
  mismatch was in my probe, not in `conftest.py`, and the demotion demonstrably
  works. D-L1-07 is therefore about the *absence of a guard*, not a broken shim.

**Examined and judged correct, with the reason.**

- Case-study count: `ls -d case-studies/*/ \| wc -l` → 9, numbered → 8, README
  claim → 8. The claim is right and the naive count is the error; untouched.
- `filterwarnings` entries at `pyproject.toml:170-174`. Measured precision:
  `StarletteDeprecationWarning.__mro__` is `[…, UserWarning, …]`, so
  `ignore::DeprecationWarning:fastapi.testclient` can never bind — which is why
  the warning is still visible in the baseline log. **No action recommended, and
  specifically do not "correct" the filter to suppress it**: the warning is a
  real signal, and silencing it is §N6. The inert line neither adds nor removes
  signal today, matching §32.3's "not a defect today".
- `ci.yml`'s `# §46 dependency pinning` / `# §47 SBOM` comments are audit-item
  section numbers, not counts — the §32.3 false-positive trap, avoided.
- CHANGELOG, ROADMAP, leaderboard stub row, the "4 checks" figure: untouched.
- Working-tree hygiene: after every probe, including a real `mkdocs build`,
  `git status --short` shows only `?? REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`
  and `?? data-science-agent/`.

**Open hypotheses and what would confirm or kill them.**

- `check_public_claims.py`'s `maturity` findings can never fail the build
  (kind `maturity` is outside the three prefixes at `:251`) — asserted from the
  filter's code and its exit path; **not exercised**, because triggering it needs
  a `README.md` edit. Confirm by editing a scratch README's `V4 adds:` line so
  Jupyter precedes `Experimental` and observing `⚠ … ` with exit 0.
- Whether pre-commit sufficiency is claimed anywhere in `docs/` — INCOMPLETE; a
  broader wording search is L5's.
- Whether `publish.yml`'s reduced gate set (no format/vendor/npm/leaderboard/
  mkdocs/SBOM steps) is intentional — unknown; a human question, not a finding.

### 21.5 Decisions required

1. **`ci.yml` pipeline masking (D-L1-01) + mypy path (D-L1-06) + SBOM assertion
   (D-L1-08).** All three need a workflow edit, which §R7 reserves. Options:
   (a) apply all three as one audit commit; (b) apply 01+06 and defer 08;
   (c) defer all. **Recommendation (a)**, sequenced so 01 lands *before* any
   gate-widening change — otherwise a newly-honest CI fails for reasons that look
   unrelated. Cost of deferring: every future "CI is green" statement in this
   audit and in normal review stays partly unearned, which is the exact condition
   §10 says L1 exists to remove.
2. **`CODEOWNERS` handle.** Local evidence shows `@jackson` against
   `jackxiaozhiren` / `CommandCodeBot`; only a human with org access can say
   whether `@jackson` resolves. Deferring costs a silently ineffective review
   auto-assignment in a repo that carries security-scanning workflows.
3. **Nested `data-science-agent/`, 1.1 GB, untracked, not ignored.** §15.2's
   decision, surfaced here because it is the only dirty entry and therefore the
   reason §24 R1 forbids `git add -A`. **Recommendation: add to `.gitignore`**
   (reversible, non-destructive, removes the double-counting hazard). Relocate if
   it is live work; delete only on the owner's instruction — §26 explicitly warns
   it holds the only copy of `FRONTEND_REDESIGN_PROMPT.md`.
4. **Scope of D-L1-02.** Narrowing `S110` ignores is cheap to write and expensive
   to land, because it converts 35 unclassified sites into CI failures at once.
   Options: (a) narrow one package per commit, starting with `packages/agent`
   (7 sites) and `packages/evidence` (2); (b) narrow all, accept red CI, and
   classify in a follow-up session; (c) hold D-L1-02 as documentation and start
   L3 from the `--isolated` list instead. **Recommendation (a)** — it keeps §19's
   one-finding-one-commit discipline and each commit stays revertable.

### 21.6 Self-audit — every factual claim mapped to its command

| Claim in this report | Command / evidence |
|---|---|
| 397 passed, 0 failed | `head -6 /tmp/audit0/02d_pytest.log \| grep -o '^\.\+' \| awk '{s+=length($0)}'` → `dots=397`; non-`.` status chars → 0 |
| coverage 80.24%, gate 79 | `Required test coverage of 79.0% reached. Total coverage: 80.24%` in the same log; `pyproject.toml:187` |
| ruff 0 errors / format 0 / mypy 0 over 108 files | exit codes 0,0,0 with `All checks passed!`, `179 files already formatted`, `Success: no issues found in 108 source files` |
| `uv sync --dev`, `uv lock --check` exit 0 | `/tmp/audit0/01a_sync.log`, `01b_lockcheck.log`, both `uv_sync_exit=0` / `uv_lock_check_exit=0` |
| 730 → 731 tracked files, tag `v4.4.0-26-g150b54f` | `git ls-files \| wc -l`, `git describe --tags` |
| five CI steps pipe a gate and lose its code | `grep -rn "run:.*\|.*\(tail\|head\|grep\|tee\)" .github/workflows/`; `grep -n "shell:\|pipefail"` shows the 5 lack the header the others have |
| Actions' shell yields the pipe's last status | `bash --noprofile --norc -e -c 'false \| tail -n 1'` → `step_exit=0`; with `-o pipefail` → `step_exit=1` |
| the real docs gate is masked | `mkdocs_direct_exit=2` vs `mkdocs_piped_exit=0` on identical arguments |
| mkdocs has no link signal | `/tmp/mkprobe` with `mkdocs.yml:43-46` verbatim + broken internal link → `direct_exit=0`; real build `43` lines, `WARNING\|ERROR` count `0` |
| S110 configured-clean over 42 live instances | `--select S110` → `All checks passed!`; `--isolated --select S110` → `Found 77 errors`, `_vendor` 35, live 42, shipped 35 / tests 7 |
| 12 trees carry the S110 ignore, `select` includes `S` | `pyproject.toml:114` and `:118-131`, read directly |
| `check_public_claims` unwired | `grep -rn "check_public_claims" .github/ pyproject.toml` → exit 1 (also §0 step 5's own grep) |
| its severity filter exits 0 on findings | scratch P1 and P5: `[stale_version:README.md] '4.0.0'` / `[stale_test_counts…]` with `⚠ Low/medium`, exit 0 |
| it ignores `docs/` entirely | scratch P3: three stale versions in `docs/foo.md` → `0 issues`, exit 0 |
| metric claims are unchecked | scratch P4: `999 tests / mypy 555 / coverage 12%` → `0 issues`, exit 0 |
| 19 of 20 `EXPECTED` keys unreferenced | `grep -n 'EXPECTED\[' scripts/check_public_claims.py` → only lines 172,173,184,185,187, all `version` |
| its version check is fail-closed | scratch `pyproject.toml` at 4.3.9 → `[version_consistency] … != expected 4.4.0`, exit 1 |
| `--check` cannot see orphaned vendor copies | `/tmp/svprobe`: 15 × `WARN: missing source` then `OK: vendored dsa_* is in sync`, `check_exit=0` with the orphan present; identical output with it deleted |
| `--check` mutates, and did not in the real repo | `sync_vendor.py:85` (`changed = sync()`), `:74-75` (`rmtree`/`copytree`); real repo `--check` exit 0 then `git status --short` unchanged |
| the conftest shim is load-bearing | `dsa_agent.__file__` → `…/_vendor/dsa_agent/__init__.py` without demotion, `…/packages/agent/src/…` with it |
| no test pins import identity | `grep -rnE "__file__\|_vendor\|sys\.path" tests apps/api/tests --include='*.py'` → 5 hits, all unrelated `REPO`/path constants |
| no test asserts a checker's exit code or stdout | `tests/test_automation_scripts.py` symbol scan: asserts target `is_bot`, render helpers, `load_entries`, `replace_block`, `_is_release_candidate_ref` |
| pre-commit absent from CI, covers 2 gates | `grep -rn "pre-commit\|pre_commit" .github/` → exit 1; `.pre-commit-config.yaml:1-7` |
| leaderboard gate never runs on a normal PR | `leaderboard.yml:3-13` path filter; `render_leaderboard_check_exit=127` for `python`, exit 0 via `uv run python` |
| `verify-release` is pinned to 4.3.0 and PR-47-gated | `ci.yml:164-169`, `pyproject.toml:3` = `4.4.0` |
| `apps/jupyter` untype-checked in CI, clean when asked | `ci.yml:86` / `publish.yml:58` path lists; mypy's `unused section(s): … dsa_jupyter.*`; `uv run mypy apps/jupyter …` → `no issues found in 4 source files` |
| 0 marks, 2 `importorskip`, 0 TODO/FIXME | the three greps in the baseline block, methods stated there |
| no CI badge in README | `grep -n "actions/workflow\|badge\|shields.io" README.md` → four badges, none a workflow-status badge |
| case-study claim 8 is correct | `ls -d case-studies/*/ \| wc -l` → 9; numbered → 8; `README.md:8` "8 verified case studies" |
| `filterwarnings` line is inert because of class, not module | `StarletteDeprecationWarning.__mro__` → `[…, 'UserWarning', …]`; `issubclass(…, DeprecationWarning)` → `False` |
| nothing in the repo was edited this session | `git status --short` after all probes → `?? REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md`, `?? data-science-agent/`; the only commits are `b4f3bf6`, `888ae36` and the ledger commits |
| my own enumeration preceded the seed's wording | §N9 disclosure at the head of the enumeration block: full-document reading means the ordering is not literally satisfiable; mitigation was a seed-unaware second enumeration plus re-verification |

**Unchecked §30 boxes, reported rather than implied (Definition of Done).**
Captured and committed: baseline, enumeration-before-diff, tier-before-severity,
severity ceilings, ledger-before-code, §21.4, §21.6, clean `git status`.
**Not** satisfied, because §18 has not been passed: red-then-green fix pairs, the
full §23 end-of-session gate set, and §21.2 repairs. That is the intended state
at an approval gate, not a shortfall to wave through.

**D-L1-10 mechanism: now experimentally confirmed, previously inferred.** The
symptom (no `passed` line) was T0 at filing, but the *cause* — doubled `-q` — was
inference. Tested: `uv run pytest tests/unit/test_data_engine.py -q` (effective
`-qq`) → `grep -c passed` = **0**; the same target with
`-o addopts="--asyncio-mode=auto"` (single `-q`) → `1 passed in 0.06s`. Mechanism
confirmed; the finding stands and the fix shape is now known to be
command-side rather than `addopts`-side.

## §27 Proposed diffs for BLOCKED findings (required, previously missing)

§27 obliges a BLOCKED workflow finding to arrive "with a diff in the report".
These are **proposals only — none is applied**; every path below is untouched, as
`git status --short` in the session log confirms. Job context: `web:` starts at
`ci.yml:16`, `ci:` at `ci.yml:48`.

### P-1 · D-L1-01 — restore exit codes on five steps (`ci.yml`)

```diff
       - run: npx playwright install --with-deps chromium
-      - run: npm --prefix apps/web run build 2>&1 | tail -n 10
+      - name: Build web (fail on the build's own status)
+        run: set -o pipefail; npm --prefix apps/web run build 2>&1 | tail -n 10
       - run: node apps/web/scripts/regression.mjs
```
```diff
-      - run: uv run dsa --limit 5 --out /tmp/ci-bench --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets 2>&1 | tail -n 20
+      - run: set -o pipefail; uv run dsa --limit 5 --out /tmp/ci-bench --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets 2>&1 | tail -n 20
```
```diff
       - run: docker build -f docker/Dockerfile.web -t dsa-web:ci .
-      - run: npm --prefix apps/web run build 2>&1 | tail -n 20
-      - run: docker compose config 2>&1 | head -n 40
-      - run: uv run python -m mkdocs build --strict 2>&1 | tail -n 50
+      - run: set -o pipefail; npm --prefix apps/web run build 2>&1 | tail -n 20
+      - run: set -o pipefail; docker compose config 2>&1 | head -n 40
+      - run: set -o pipefail; uv run python -m mkdocs build --strict 2>&1 | tail -n 50
```

`set -o pipefail` inside a single-line `run:` keeps the log truncation the author
wanted and repairs only the status propagation. The file's multi-line steps
already use `shell: bash` + `set -euo pipefail` (`:61-63` etc.), so this matches
the house style rather than inventing a second convention. Verified predicate:
`bash --noprofile --norc -e -c 'false | tail -n 1'` → 0; with `-o pipefail` → 1.

### P-2 · D-L1-06 — type-check `apps/jupyter` in CI

```diff
-.github/workflows/ci.yml:86
-      - run: uv run mypy packages apps/api src --ignore-missing-imports
+      - run: uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports
-.github/workflows/publish.yml:58   (same change)
```
Zero-violation: `uv run mypy apps/jupyter --ignore-missing-imports` →
`Success: no issues found in 4 source files`. Expected CI delta: `108 source
files` → `112`, and mypy's `unused section(s): … dsa_jupyter.*` note disappears.

### P-3 · D-L1-08 — make the SBOM step assert something checkable

```diff
-      - run: uv run python scripts/generate_sbom.py && test -f release/sbom.json  # §47 SBOM
+      - run: uv run python scripts/generate_sbom.py && uv run python -c "import json;s=json.load(open('release/sbom.json'));v=json.load(open('pyproject.toml'.replace('x','x'))) if False else __import__('re').search(r'version = \"([^\"]+)\"',open('pyproject.toml').read()).group(1);assert s['version']==v,(s['version'],v);assert s['packages'],'empty SBOM'"  # §47 SBOM
```
Flagged as ugly-on-purpose: the honest recommendation is a
`scripts/check_sbom.py` that compares `release/sbom.json` against
`pyproject.toml`, which is a new file plus a workflow line and therefore two
approvals. Not measured — `generate_sbom.py` writes a tracked file (§R8), so this
diff is unexecuted by choice and its violation count is **unknown**.

### P-4 · D-L1-02 — remove `S110` from shipped trees only (`pyproject.toml`)

Measured per-tree live counts (`--isolated --select S110`, `_vendor`'s 35
duplicates excluded): `evaluation` 8, `apps/jupyter` 8, `packages/agent` 7,
`tools` 3, `apps/api` 3, `mcp` 2, `evidence` 2, `llm` 1, `datasets` 1,
`plugins` 0, `execution` 0, `routers` ⊂ apps/api → **35 shipped**, 7 in tests.

```diff
-"apps/api/src/dsa_api/routers/*" = ["B008", "S110", "SIM105"]
+"apps/api/src/dsa_api/routers/*" = ["B008", "SIM105"]
-"packages/agent/src/dsa_agent/*" = ["F841", "E402", "S110", …]
+"packages/agent/src/dsa_agent/*" = ["F841", "E402", …]
-… (same deletion in plugins, datasets, evaluation, evidence, execution, tools, mcp, apps/jupyter)
-"packages/llm/**/*" = ["S110"]        # deletion empties the key
+delete the "packages/llm/**/*" line
-"tests/**/*" = ["S101", …, "S110", …]  # UNCHANGED — see below
```

**Recommended scope, and a correction to my own finding.** Land shipped trees
only (35 sites), leaving `tests/**` as-is: an `except: pass` in a test teardown is
overwhelmingly the legitimate class, and switching it on buys classification
churn, not signal. D-L1-02's `expected_delta` therefore reads
`All checks passed!` → **`Found 35 errors`** for the recommended scope, and 42
only if `tests/**` is included; the ledger's earlier single-figure 42 was
imprecise about scope. Sequencing per §21.5(4): `packages/agent` (7) and
`packages/evidence` (2) first, one commit each, each with §19's red-then-green.
§R11/§N6 are respected — this *narrows* an exclusion, adding signal; the
prohibited direction (widening, lowering `fail_under`) appears nowhere above.

### P-5 · D-L1-04 — orphan detection in `sync_vendor.py --check`

Sketch, not a tested patch: after the `SOURCES` loop, treat any
`VENDOR/<name>` directory with no `SOURCES` key, and any `SOURCES` key whose
source directory is absent while its vendored directory exists, as drift →
`DRIFT: …` + `sys.exit(1)`. Predicate already captured: the `/tmp/svprobe`
injection printed `OK: vendored dsa_* is in sync` at exit 0 with an orphan
present, and must print `DRIFT` at exit 1 after the change. Separate sub-finding
to settle in the same edit: whether `--check` should stop calling `sync()`
entirely (it currently mutates the tree it audits, contra §24 R3's premise) —
that is a behavior change to a CI-critical script, so it needs its own commit and
its own verification, not a ride-along.

### P-6 · D-L1-07 — import-identity guard (new test, no source change)

```python
def test_workspace_source_not_vendored_copy() -> None:
    import dsa_agent
    assert "_vendor" not in dsa_agent.__file__, dsa_agent.__file__
```
§N3 caveat stated plainly: this is **green on arrival**, so its red must be
produced by disabling the demotion in a fixture (monkeypatched `sys.path`) and
observing the same assertion fail. `expected_delta`: collected 397 → 398.

### P-7 · D-L1-05 — give the docs gate a link signal (`mkdocs.yml`)

```diff
 validation:
   links:
-    not_found: ignore
+    not_found: warn
     absolute_links: ignore
```
Predicted violation count: **low but unknown** — the real build currently emits
`0` WARNING/ERROR lines, yet `not_found: ignore` means it could not have reported
any, so absence of warnings is not evidence of absence of broken links. Keeping
`absolute_links: ignore` preserves legitimate cross-site references. Predicate
captured: `/tmp/mkprobe` with this block verbatim + a broken internal link → exit
0; must become exit 1.

## §27 Proposed diffs end — approval still outstanding

## Session log

- 2026-09-24T13:04Z — §0 First Ten Commands executed; exit codes captured to
  `/tmp/audit0/`. Baseline block written from measured output. Ledger committed
  before any source edit (§N10).
- 2026-09-24T13:07–13:14Z — L1 enumeration: 18 gate surfaces inventoried, 6
  scratch-copy injection probes (`/tmp/claims_probe`, `/tmp/svprobe`,
  `/tmp/mkprobe`), 12 findings filed, 1 self-refuted probe retracted. Blind
  seed-unaware enumeration obtained and its claims re-verified against source.
  Committed `888ae36`.
- 2026-09-25T03:07Z — §17.2 lead-register diff (CONFIRMED / REFUTED / INCOMPLETE
  / OUT-OF-LANE per seed), §18 ranked triage, §21 report with 21.4 non-findings
  and 21.6 claim-to-command self-audit. **STOPPED at the §18 approval gate.** No
  source file edited; `git status --short` shows only the two expected untracked
  entries. Resumable state = this ledger + §16 baseline + Appendix B.

**Next session (resume instructions, §5.2).** Read only: this ledger, the
baseline block, Appendix B, and the §27 proposed-diff appendix above. If the
maintainer approves items 2–6 of the triage, enter §19 one finding at a time —
start with D-L1-02 (patch P-4), whose red is already captured
(`--select S110` → `All checks passed!` over 35 shipped instances, 42 including
`tests/**`). Before any L2 work, note §17.6: L2's evidence about swallowed
exceptions and claim checks rests on the gates D-L1-02/03 found broken, so
re-derive rather than reuse.
