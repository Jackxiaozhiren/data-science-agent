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
| `.github/CODEOWNERS` handle vs the org's real identity | **BLOCKED → RESOLVED, and the finding was real** | At filing time §33 authorized no network command, so the row could only say "needs a human". On 2026-09-25 the maintainer explicitly asked for the identity lookup, which authorized four read-only `gh api` calls: `gh api user` → login **`Jackxiaozhiren`** (id 104724357, `type=User`); `gh api users/jackson` → **a different person** (id 4491093); `gh api repos/.../collaborators/jackson` → **404**, and the collaborator list is `[Jackxiaozhiren]` alone; `gh api repos/Jackxiaozhiren/data-science-agent` → `private=false`, `owner.type=User`. So all 7 `@jackson` entries are an invalid owner → GitHub treats the file as not-configured, and review auto-assignment was a silent no-op exactly as feared. No leakage risk (that account holds no permission here). Repaired by pointing all 7 at `@Jackxiaozhiren`, structure kept so per-path ownership stays readable. |
| `ci.yml` pinned version strings | **CONFIRMED, and inert twice over** | `ci.yml:164` step name "Verify **v4.3.0** release candidate" while `pyproject.toml:3` is `4.4.0`; `:165` gates it on `github.event.pull_request.number == 47`, so it can fire on at most one PR ever. `.venv/bin/dsa verify-release v4.3.0 --json` is the sole reference to that checker in `.github/`. Not filed as a separate finding because it is a workflow edit (§R7); folded into §21.5 decisions. |
| `pytest.mark.skip`/`xfail` = 0 (regression tripwire, §3.1/§16) | **CONFIRMED for marks; the tripwire has a hole** → D-L1-11 | marks grep → `0`; `importorskip` grep → `2`, both on mandatory deps (`pyproject.toml:31-32`) with a "not yet required" reason |
| §32.2 "~48 swallowed-exception sites" vs §12's snippet returning 176 | **RECONCILED — counting-method artifact, and my instrument lands near the 48** | ruff S110 on the same paths: `All checks passed!` (0) as configured, `42` live with `--isolated` (35 shipped + 7 tests), `77` including `_vendor`'s 35 duplicates. So 0 / 42 / 77 / 176 are four different questions. The seed's own point stands: the count is not the finding, the per-site class is (§12). |
| §32.2 three-way metric contradiction (324 / 395 / 257 / ~302) | **PARTIALLY RESOLVED** | authoritative figure this session: **397** collected, by character count of the `-q` rows (method in the baseline block). Why the repo's own checker cannot arbitrate: D-L1-03(iv). The reconciliation of the other three figures is L5's, not L1's. |
| §32.2 "23 orphaned docs vs nav ~24 of 47" | **NOT ADJUDICATED — out of L1 scope, and my first measurement was method-unsafe** | `git ls-files 'docs/**/*.md'` → 21 vs 24 nav lines by a hand-rolled regex; two methods I would not stake a finding on. Left for L5 with the warning that both counts above are pattern-dependent. |
| §32.1 repro-bundle `except: pass`, `critic.py` vacuous pass, `validator.py` never raises | **OUT OF LANE** (L2) | not investigated; §5.3 orders L2 after L1. Note the dependency §17.6 creates: D-L1-02 and D-L1-03 mean a future L2 green must not be read as "the swallow and the claim were checked". |
| §32.2 two engines, god files, stub packages, import cycle, frontend, SECURITY.md | **OUT OF LANE** (L3-L6) | untouched this session |

### Fixes applied

Approved by the maintainer ("我都听你的，请按照你的思路建议进行", read as approval of
the presented §18 plan including the §R7 workflow edits). Executed per §19: one
finding = one change = one commit, each with a captured failing output before it.

| finding | commit | verify_before (red) | verify_after (green) |
|---|---|---|---|
| D-L1-01 pipeline masking | `4ffc7b7` | guard test named `ci.yml:39,:89,:161,:162,:163`, `1 failed` exit 1; real gate exit 2 unwrapped vs exit 0 piped | `2 passed` exit 0 |
| D-L1-06 mypy path | `0f16921` | guard names `ci.yml, publish.yml`, `1 failed`; mypy reported `unused section(s): … dsa_jupyter.*` over `108 source files` | `no issues found in 112 source files`, unused-section note gone |
| D-L1-05 mkdocs link signal | `c44cf3a` | guard failed quoting `{'not_found': 'ignore', 'absolute_links': 'ignore'}`; scratch build with that block + broken link → exit 0 under `--strict` | `3 passed`; real `--strict` exits 1 naming 7 links (the gate acquired the ability to fail) |
| **D-L1-13** (new) 7 broken links | `1e000b7` | `strict_exit=1`, 7 × `WARNING - Doc file … target is not found` | `strict_exit=0`, WARNING/ERROR count 0, `](../` in `docs/**/*.md` → 0 |
| D-L1-04 vendor orphan blind spot | `c0a008d` | scratch `_vendor/dsa_gone/old.py`, no source → 15 × `WARN: missing source` then `OK`, exit **0** | same tree → `DRIFT: … no workspace source: dsa_gone` exit **1**; deleted → 0; **real repo still 0** (no false positive: `_vendor` = the 15 `SOURCES` keys + `__pycache__`, which the rule excludes) |
| D-L1-07 import-identity guard | `01cbb7d` | §N3 caveat honoured — no ordinary red exists for a green-on-arrival guard, so a **negative control** test asserts the broken resolution (`dsa_agent` → `_vendor/…`) really occurs, which is what makes the companion assertion non-vacuous | `3 passed`; no `noqa` added; the one `S603` that `tests/**` hides is recorded as Legitimate, not suppressed |
| D-L1-03 (partial) dead `EXPECTED` keys | `fcf702a` | differential rather than red/green: `✓ No stale claims detected — 0 issues` exit 0 with 19 unreferenced keys | identical output and exit; re-read reports `unreferenced: []`; module's 13 tests pass |
| self-inflicted format violation | `b2d76bf` | `ruff format --check` → `1 file would be reformatted → tests/test_ci_gate_integrity.py:84`, introduced by my own `c44cf3a` | `181 files already formatted`, guards still pass |

**My own §27 proposal P-7(c) refuted by measurement.** I had proposed dropping
`docs/` from the checker's skip list. Running `scan_file` across all 47 tracked
`docs/*.md` with today's context handling yields **8 findings, all 8 false
positives** — `docs/v4_3/V4_2_FINAL_TRUTH.md` quotes `86+ tests`, `81 source
files` and `pip install data-science-agent` *in order to record their absence* —
and 2 are `old_package_pip`, which is in the fail list, so the change would have
made the gate red on correct prose. The skip list is crude but is currently
suppressing false positives, not real ones. Filed as **D-L1-14**; not attempted.

### Findings added during repair

### D-L1-13
| field | value |
|---|---|
| claim | Seven links in `docs/` point outside the docs tree and 404 on the rendered site. |
| lane | L1 (surfaced by an L1 gate repair; the defect class is L5's) |
| evidence_tier | T0 |
| severity | S2 |
| location | `docs/README.md:12,15,16,17,18`; `docs/announcements/latest.md:35`; `docs/announcements/v4.2.10.md:35` |
| mechanism | mkdocs resolves links only inside `docs_dir`, so a relative `../CHANGELOG.md` can never resolve even though the target exists in the repository. Invisible until D-L1-05 gave `--strict` a link signal. |
| evidence_command | `uv run python -m mkdocs build --strict` |
| output_excerpt | before `strict_exit=1` + 7 WARNING lines; after `strict_exit=0`, `WARNING/ERROR count: 0` |
| reproducible | deterministic |
| fix_sketch | applied — repointed at canonical repo blob URLs; `absolute_links: ignore` retained so external refs stay unchecked by design |
| blast_radius | 3 docs files; no code, no contract |
| verify_before | `strict_exit=1`, 7 named warnings |
| verify_after | `strict_exit=0`, 0 warnings |
| expected_delta | docs-gate WARNING count 7 → 0 |
| status | fixed |
| commit | `1e000b7` |
| protected | no |

### D-L1-14
| field | value |
|---|---|
| claim | The claim checker cannot distinguish a stale value from a document quoting that value to assert its absence, so its `docs/` skip is load-bearing false-positive suppression. |
| lane | L1 |
| evidence_tier | T0 |
| severity | S1 |
| location | `scripts/check_public_claims.py:106-134` (`scan_file` context window), `:222-233` (skip list) |
| mechanism | `scan_file` whitelists by filename fragments (`CHANGELOG.md`, `MIGRATION`, `QUANTITATIVE_CLAIMS`, `"V4.1 live"`, `"Historical"`) rather than by whether a match is an affirmative or a negated/historical mention. `docs/v4_3/` matches no carve-out, so widening the scan flags the reports that are *auditing* the old numbers. Consequence: the superficially honest fix (drop the skip) breaks the gate, so the gate's reach cannot widen until the matcher is reworked. |
| evidence_command | `importlib` load of the module + `scan_file` over `git ls-files docs` (see session log) |
| output_excerpt | `docs/*.md tracked: 47` / `findings if docs/ were scanned: {'stale_version': 2, 'stale_test_counts': 2, 'stale_mypy': 2, 'old_package_pip': 2} total: 8` |
| reproducible | deterministic |
| fix_sketch | Needs a decision, not a diff: extend the filename carve-outs to `docs/v4_3/` (cheap, keeps the blind spot) or make the matcher negation-aware (real work; every added carve-out risks hiding a true stale claim — §N6 cuts both ways). Not attempted. |
| blast_radius | the checker's detection strategy; 47 `docs/` files |
| verify_before | 8 findings, all false, 2 build-failing |
| verify_after | — not attempted |
| expected_delta | deliberately unstated; would need a labelled true-vs-negative set first |
| status | open |
| commit | — |
| protected | no |


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

The repository was green, honest about its debt markers (0 `TODO`/`FIXME`, 0
`mark.skip`/`xfail`), and 397 tests passed at 80.24% coverage against a ratchet
of 79. The lane's answer to *can any signal be trusted* was still no: **nine of
§23's thirteen gates could not fail on something they claimed to check, or were
not wired the way §23 implies** — and the two largest were found here rather than
taken from the seed: five CI steps whose exit code belonged to `tail`, and a
bandit `S110` rule enabled and then disabled in twelve trees, reporting
"All checks passed!" over 42 live instances.

Seven fixes landed, one commit each, every one red-before-green or
differential-verified: the pipeline masking, the mypy coverage gap, the docs
gate's missing link signal (plus the 7 genuinely broken links it then exposed),
the vendor orphan blind spot, the import-identity guard, and the claim checker's
19 dead expectation keys. Tests 397 → 403, coverage held at 80.24%, all ten
non-mutating §23 gates exit 0.

Two things were deliberately **not** done, and each is a decision rather than an
omission: **D-L1-02** (narrowing `S110`) was left because landing it turns 35
sites red and classifying them is L3's work under §5.3's ordering — I kept the
measured violation list instead; and my own proposal to drop the checker's
`docs/` skip was **refuted by measurement** (8 findings, all false, 2 of them
build-failing), which is now D-L1-14. Still open for the maintainer: the
`CODEOWNERS` handle, the 1.1 GB nested `data-science-agent/`, wiring the claim
checker into CI at all, and making `--check` stop mutating the tree it audits.

### 21.2 Repairs

| id | severity | what was wrong | commit | verify_before | verify_after |
|---|---|---|---|---|---|
| D-L1-01 | S1 | 5 CI steps piped a gate into `tail`/`head`; Actions' default shell has no `pipefail`, so the step reported the truncator's status | `4ffc7b7` | guard named all 5 lines, `1 failed` exit 1; real gate exit 2 direct vs **0 piped** | `2 passed`, exit 0 |
| D-L1-06 | S3 | `apps/jupyter` linted but never type-checked; mypy called its own override unused | `0f16921` | `108 source files` + `unused section(s)` | `112 source files`, note gone, exit 0 |
| D-L1-05 | S2 | `--strict` had no link signal; `CONTRIBUTING.md:28` mandates it anyway | `c44cf3a` | scratch build with the repo's block + broken link → exit 0 | real `--strict` exit 1, 7 links named |
| D-L1-13 | S2 | 7 out-of-tree docs links, 404 on the site | `1e000b7` | exit 1, 7 WARNINGs | exit 0, 0 WARNINGs, 0 `](../` left |
| D-L1-04 | S1 | `--check` blind to a vendored copy whose source is gone | `c0a008d` | orphan present → `OK`, exit 0 | → `DRIFT`, exit 1; real repo still exit 0 |
| D-L1-07 | S3 | nothing pinned which copy of `dsa_*` tests import | `01cbb7d` | negative control shows `_vendor` resolution is reachable | `3 passed`, guard non-vacuous |
| D-L1-03 | S1 | 19 of 20 `EXPECTED` keys dead, under a comment claiming they were live | `fcf702a` | `0 issues`, 19 unreferenced | same output, `unreferenced: []` |
| own slip | — | I committed an unformatted line; the format gate caught it | `b2d76bf` | `1 file would be reformatted` | `181 files already formatted` |

### 21.3 Numeric attestation

| metric | baseline | after | delta | command |
|---|---|---|---|---|
| tests passed | 397 | **403** | +6 | `uv run pytest -q --cov --cov-report=term-missing`, counted over the `%`-bearing progress rows (D-L1-10 means the gate still prints no count) |
| coverage % | 80.24 | **80.24** | 0.00 | same command; TOTAL 7643 stmts / 1267 miss unchanged — my edits touched tests, `scripts/` and docs, none in coverage `source` |
| skip / xfail | 0 | 0 | 0 | character scan of the progress rows: no `s/S/x/X/f/F/e/E` marks. First count attempt returned 6 `s` and was **wrong** — it had read the warnings block's file paths; corrected in the session log |
| ruff errors | 0 | 0 | 0 | `uv run ruff check packages apps/api tests src apps/jupyter` |
| ruff format | 0 (179 files) | 0 (**181** files) | +2 files, 0 violations | `uv run ruff format --check …` |
| mypy issues / files | 0 / 108 | 0 / **112** | +4 files covered | `uv run … mypy packages apps/api src apps/jupyter …` (the widened CI form) |
| tracked files | 730 | **733** | **+3** | `git ls-files \| wc -l`; `git diff --name-status 150b54f..HEAD --diff-filter=A` lists exactly AUDIT_LEDGER.md + the 2 new test files |
| TODO/FIXME/HACK/XXX | 0 | 0 | 0 | grep, `.py` under `packages apps/api src tests scripts docs`, `_vendor` excluded |
| ruff S110 live instances | 0 reported / 42 actual | **unchanged** | 0 | D-L1-02 was deliberately **not** landed this session; see §21.5 |
| vendor drift | in sync | in sync | 0 | `uv run python scripts/sync_vendor.py --check` |
| npm lock / leaderboard / claims | 0 / 0 / 0 | 0 / 0 / 0 | 0 | the three `--check` gates, all exit 0 |
| docs `--strict` | exit 0 but **unable to fail on links** | exit 0, 0 WARNINGs, **now able to fail** | capability, not a number | `uv run python -m mkdocs build --strict` |
| benchmark | not run | exit 0, 5 tasks, success 1.0 | — | `uv run dsa --limit 5 …`; harness/stub figure, **not** real-model quality (§32.3) |

**Not run at session end, stated rather than implied:** `generate_sbom.py` (§R8,
mutates a tracked file), `uv build`, the web build / `regression.mjs` /
`npm audit`, and the Docker steps. `ruff format --check` and `pytest --cov` were
re-run after the last commit; the two commits after the final full pytest run are
formatting-only and a ledger edit, so no gate result is stale except by that
reasoning.

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

1. **`ci.yml` pipeline masking (D-L1-01) + mypy path (D-L1-06) — APPROVED and
   DONE** (`4ffc7b7`, `0f16921`), sequenced as recommended so 01 landed first and
   the newly-honest docs gate could then expose D-L1-13 rather than look like an
   unrelated failure. **SBOM assertion (D-L1-08) still deferred**: it needs a
   content predicate, and I declined the one-liner in P-3 as unreadable — the
   honest shape is a `scripts/check_sbom.py`, which is a new file plus a workflow
   line, i.e. two more approvals.
2. **`CODEOWNERS` handle — CLOSED and REPAIRED (2026-09-25).** The maintainer
   asked for the identity lookup, which settled what §33 had blocked: the account
   is `Jackxiaozhiren`, `@jackson` is an unrelated person who is not a
   collaborator here (`gh api .../collaborators/jackson` → 404; sole collaborator
   is the owner). All 7 entries now read `@Jackxiaozhiren`. Evidence in the
   lead-register row above.
3. **Nested `data-science-agent/`, 1.1 GB — CLOSED, and it is NOT junk.** It is a
   second clone of this repository: `git -C data-science-agent remote -v` → same
   `origin`, HEAD `e49a441` dated 2026-08-30 (the v4.3.0 line, while the outer
   tree is 4.4.0), and `git -C data-science-agent status --short` shows
   **uncommitted** work: 4 modified (`apps/web/app/globals.css`,
   `apps/web/package.json`, `apps/web/tailwind.config.js`, `package-lock.json`)
   plus 4 untracked paths. I tested each untracked path against the outer tree
   with `[ -e ]`: `FRONTEND_REDESIGN_PROMPT.md`, `apps/web/components/`,
   `apps/web/lib/format.ts`, `apps/web/lib/theme.tsx` are **all MISSING outside**.
   So §26's warning is understated — four paths, not one, exist only there.
   Resolution: `/data-science-agent/` added to `.gitignore` with a comment naming
   the constraint. Not deleted, not moved — moving a directory containing a live
   `.git` and uncommitted work is destructive-adjacent and was not authorized.
   Verified the ignore rule cannot hide tracked work: `git ls-files -i -c
   --exclude-standard` → empty, `git ls-files | wc -l` still 733, and no gate
   reads `git status`/`--porcelain` (`git grep -l` over scripts/tests/.github →
   no hits), so nothing's dirtiness check was weakened.
4. **Scope of D-L1-02 — NOT LANDED, decision still live.** Measured inventory,
   `_vendor` duplicates excluded: `packages/evaluation` 8, `apps/jupyter` 8,
   `packages/agent` 7, `packages/tools` 3, `apps/api` 3, `packages/mcp` 2,
   `packages/evidence` 2, `packages/llm` 1, `packages/datasets` 1,
   `packages/plugins` 0, `packages/execution` 0 → **35 shipped**, 7 in `tests`.
   Option (a) — narrow one package per commit — remains the recommendation, but
   each commit turns CI red until those sites are classified
   Hiding/Downgrading/Legitimate, which is L3's lane and follows L2 in §5.3.
   Landing it inside an L1 session would have spent L3's budget on red CI.
5. **`sync_vendor --check` still mutates what it audits** (`:85` → `sync()` →
   `rmtree`/`copytree` at `:74-75`), and §24 R3 / §33 still describe `--check`
   as the non-writing form. Deliberately left out of `c0a008d`: making it
   hash-compare without copying is a behaviour change to a CI-critical script and
   needs its own verification. Recommend it as the first item of the next session.

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

| 403 tests after repair, 0 skips | progress rows only: 5×72 + 43 dots, `s/S/x/X/f/F/e/E` scan over those rows → empty; `Required test coverage of 79.0% reached. Total coverage: 80.24%` |
| 733 tracked files, +3 | `git ls-files \| wc -l`; `git diff --name-status 150b54f..HEAD --diff-filter=A` → exactly 3 `A` lines |
| the 6 `s` I first counted were my error | `grep -o '[sSxX]'` over `sed -n '1,8p'` included the warnings block's file paths; per-line character analysis showed rows 1-6 carry no marks. Corrected, not caveated |
| 35 shipped / 7 test S110 sites, per tree | `uv run ruff check --isolated --select S110 --output-format=concise …` then `_vendor` split, re-listed in §21.5(4) |
| docs gate went 1→0 on warnings, links | `uv run python -m mkdocs build --strict` before and after `1e000b7`; `grep -cE "^(WARNING\|ERROR)"` 7 → 0 |
| vendor orphan: 0→1, real repo still 0 | `/tmp/svprobe3` exit 1 `DRIFT … dsa_gone`; `/tmp/svprobe4` control exit 0; `uv run python scripts/sync_vendor.py --check` exit 0 |
| 8 false positives from scanning docs/ | `importlib` load of `check_public_claims.py` + `scan_file` over `git ls-files docs` → `total: 8`, samples show negation sentences |
| `EXPECTED` cleanup behaviour-preserving | same output/exit before and after; `unreferenced: []`; `tests/test_automation_scripts.py` → `13 passed` |
| benchmark exit 0, 5 tasks, rate 1.0 | `uv run dsa --limit 5 …` → `Task success rate: 1.0`; §32.3: harness figure, not real-model quality |
| no `noqa`/exclusion/threshold added | `git diff 150b54f..HEAD` contains no `noqa`, no `per-file-ignores` edit, no `fail_under` change; the two candidate suppressions in my own new test file were removed, and the remaining `S603` is disclosed as hidden-by-config |
| workflow edits were authorised | maintainer message 2026-09-25: "我都听你的，请按照你的思路建议进行", following a §18 list that named ci.yml/publish.yml edits as needing approval |

**§30 Definition of Done — what is met and what is not.**
Met: baseline captured and committed before any code (§N10, `b4f3bf6`);
enumeration before the lead diff; tier before severity, no ceiling exceeded;
one finding = one change = one commit, each with a captured before/after pair;
§21.4 and §21.6 present; no suppression, exclusion, threshold or dependency
change; vendor drift re-checked; `git status --short` clean apart from the two
expected untracked entries; ≤8 fixes (7) and ≤2 structural (1 — the `ci.yml`
gate semantics).
**Not met, stated plainly:** the *full* §23 table did not run — SBOM, `uv build`,
the web build / `regression.mjs` / `npm audit`, and Docker were skipped, and the
`mkdocs`/benchmark gates were run directly rather than through a real Actions
runner, so the pipefail repair is verified by shell semantics, not by an
observed CI run. D-L1-02's fix is therefore the only high-ranked item still open.

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

## §27 Proposed diffs end — approved 2026-09-25 and executed; the session log below records what landed and what was refuted

## §34 Follow-up lane — `--check` non-mutation, closed same day

**D-L1-05 residual, CLOSED (`5400c01`).** The open question from §27 was whether
`--check` should stop calling `sync()` at all. It did, and the reason it had to is
sharper than "it mutates": the old `main()` snapshotted bytes, called `sync()`
(which rewrites `_vendor`), then compared its own repair against the state it had
replaced. So a DRIFT verdict described a condition that no longer existed by the
time anyone could look at it. `check()` now compares source bytes to vendored
bytes and writes nothing; `sync()` calls the same `_diff`, so "check says OK" and
"sync says nothing to do" are one judgement instead of two overlapping ones.

**Unplanned sub-finding, folded into the same commit.** `sync()`'s fast path was
guarded by `if src_files == dst_files and not changed:`. `changed` accumulates
across packages, so once any package drifted, every later package was rmtree'd,
recopied, and appended — `Synced: dsa_agent, dsa_api` for a copy that had not
moved. Dropped because sharing `_diff` made the guard wrong, not to tidy.

**D-L1-15 — NEW, filed and FIXED (`544eedd`), S2.** `SOURCES` keys the orphan
check, so a package whose directory is deleted while its vendored copy remains is
not an orphan by that test: `--check` printed WARN, found nothing, and exited 0
with a stale module still headed for the wheel — the exact scenario §27's own
comment says the orphan check was added to catch. Red captured by injection
(§9.2): scratch tree with `_vendor/dsa_reports/` and no source → `exit=0`,
stdout `OK: vendored dsa_* is in sync`. Safety of the tightened verdict measured
first: all 15 declared sources exist and the real `--check` emits zero WARN
lines, so the new branch cannot fire outside its scenario.

**Verification run for this lane.** `tests/test_sync_vendor_check.py`, 5 cases,
scratch-tree subprocesses only — the real `_vendor` is never reachable from them.
Two of the five are genuinely red-then-green against `git show HEAD:scripts/…`
(deterministic, captured in the commit messages); three were green on arrival and
say so: the faithful-copy case guards against the opposite failure (phantom drift
→ permanently red CI), and the two orphan cases are regression tripwires whose red
exists only by deleting the guard. Real tree after both commits: `--check` exit 0,
`git status -- src/.../\_vendor` empty. Full suite **408 passed**, coverage
**80.24%** (gate 79), ruff and `ruff format --check` clean on `scripts` and
`tests`, mypy `Success: no issues found in 108 source files`.

**Budget, stated plainly.** §28 caps a lane at 8 fixes. L1 has now landed **9**
(7 in the repair phase, plus `5400c01` and `544eedd`), plus 3 config/ledger
commits. I proceeded past the cap on the maintainer's standing instruction to
follow my own recommended order, and record the overrun rather than renumbering
the findings to hide it.

## §35 D-L1-14 — the root cause was not the matcher, it was a lying scope

**Measured.** `SCAN_GLOBS` advertises `docs/**/*.md`, `plugins/**/README.md` and
`src/data_science_agent/sdk.py`; an anonymous skip list inside `main()` then
dropped every one of those matches. Per-glob counts (matched → scanned):
`docs/**/*.md` 47 → **0**, `plugins/**/README.md` 2 → **0**,
`src/.../sdk.py` 1 → **0**, and `packages/**/README.md` 0 → 0 (a fourth entry
that matches nothing at all, for a different reason). 51 files declared as
public surface, never opened, while the tool printed `0 issues`.

**Why the skip is load-bearing, and stays.** Running the current `PATTERNS`
across those 51 yields **34 findings, of which 0 are real and 2 are
build-failing**. Both HIGH hits are `old_package_pip` matching the sentence
"no `pip install data-science-agent` (old package)" — a document asserting the
*absence* of the command. `stale_test_counts`/`stale_mypy` fire the same way on
"no stale `86+ tests`". ~25 of the 34 are `stale_version '4.0.0'` from SDK
docstring maturity labels ("Stable since 4.0.0"), which the release matrix
requires. So D-L1-14 is two defects, not one, and only one is fixable by a
narrower regex: the dead-glob lie is fixed now; the negation blindness is what
still blocks widening scope, and the checker is **still not wired into CI** —
wiring it today buys a red build on 8 known-false findings.

**Landed (`dcc99f5`).** `NOISE_SUBSTRINGS` + `HISTORICAL_PREFIXES` are now named
at module level with the measurement in the comment, `scan_scope()` is the one
place that splits declared from read, and the verdict prints its own
denominator: `✓ No stale claims detected — 0 issues (scanned 14 file(s); 51
skipped as historical)`. Two tests in `tests/test_automation_scripts.py`:
`scan_scope` on the real tree (glob advertised, skip non-empty, partition is
clean) and a scratch pair where byte-identical text under `docs/` and
`README.md` gets opposite verdicts — that pair *is* the blind spot, written as
an assertion, and it will fail on the day someone teaches the matcher negation.
Red basis: `scan_scope` does not exist in HEAD's copy (executed:
`hasattr(old, 'scan_scope')` → `False`), so both are new-capability tests, not
red-then-green in the D-L1-05 sense.

**Concurrent history — the tree moved under this lane.** Between `e1ecb6f` and
this section, five more commits landed on `main` that this session did not make
(`6680b37` opt-in bearer auth, `7bf7408` `dsa_api` vendor sync, `4ca9c69` ruff
format, `e28c184` changelog, `7397c47` benchmark adapter v3), and three files
are dirty that I never opened (`README.md`,
`packages/evaluation/src/dsa_evaluation/external_validation.py`,
`tests/evals/test_external_validation.py`). Checked rather than assumed: all
six of this lane's commits are ancestors of HEAD (`merge-base --is-ancestor`),
`CODEOWNERS` still reads `@Jackxiaozhiren`, ci.yml still has 5 `set -o pipefail`,
`mkdocs.yml` still `not_found: warn`, and all three guard-test files exist in
HEAD. Those three dirty files were left alone and are not in any commit of mine.
Consequence for the record: the suite count moved **408 → 415** and coverage
**80.24% → 80.40%** because of someone else's added tests, so the §34 numbers
describe an older HEAD and every inherited figure needs re-measuring before use.

**Budget.** That makes **10** fixes landed in this lane against §28's cap of 8.
Recorded as an overrun under standing maintainer instruction, not renumbered.

## §36 Re-baseline at `77587f1` — one real catch, one instrument error of mine, one new finding

**Position.** HEAD `77587f1`, `main` is **ahead 2 / behind 0** of `origin/main`:
the parallel session's chain was pushed, this lane's last two commits were not,
and nothing here pushed anything. No new commits appeared since §35.

**Gate battery** (each exit code captured unpiped into its own log — the masking
pattern this lane was chartered to remove): pytest **415 passed**, ruff
`All checks passed!`, mypy `Success: no issues found in 112 source files`,
claims `0 issues (scanned 14; 51 skipped as historical)`, mkdocs `--strict` 0,
**`sync_vendor --check` → 1**.

**The vendor exit-1 is the §34 fix earning its keep.** Output names the culprit:
`- dsa_evaluation: 1 file(s) differ`, and `git status -- _vendor` is empty, so
the *source* is ahead of the vendored copy: another session has
`packages/evaluation/src/dsa_evaluation/external_validation.py` modified and
unsynced. Under the pre-`5400c01` code this exact invocation would have rewritten
`_vendor`, then compared its own repair and printed `OK: vendored dsa_* is in
sync`. Write mode was deliberately not run — silently absorbing someone else's
in-flight work is the failure being fixed, not a fix.

**D-L1-16 (mine to report, not to hide): `scripts/` is outside every static gate.**
`git ls-files scripts` → 12 entries (11 `.py` + `dev.sh`), and none of the three
CI commands name it: `ruff check packages apps/api tests src apps/jupyter`,
`ruff format --check packages apps/api tests src apps/jupyter`, `mypy packages
apps/api src apps/jupyter`. Measured cost of closing it today: `ruff check
scripts` → 0 and `ruff format --check scripts` → 0, so **two of the three gates
are free right now**; `mypy scripts/*.py` → **59 errors in 6 files**
(`generate_benchmark_v2` 23, `run_perf_matrix` 13, `check_public_claims` 11,
`generate_sbom` 10, `generate_benchmark_datasets` 1, `check_npm_workspace_lock`
1). It matters because workflows execute these files: `update_contributors.py`,
`render_leaderboard.py`, `generate_release_announcement.py` and
`write_real_model_workflow_manifest.py` all run in CI with no static gate between
them and a runtime failure. `sync_vendor.py` is mypy-clean, which is why today's
rewrite type-checks; `check_public_claims.py`, edited in §35, carries 11 of the 59.
**Not landed**: appending `scripts` to the two ruff lines is a two-token edit of
`.github/workflows/*`, which §24 gates behind approval, and it binds every future
edit of those 11 files. The diff, for a yes/no:

```diff
-- run: uv run ruff check packages apps/api tests src apps/jupyter
-- run: uv run ruff format --check packages apps/api tests src apps/jupyter
+- run: uv run ruff check packages apps/api tests src apps/jupyter scripts
+- run: uv run ruff format --check packages apps/api tests src apps/jupyter scripts
```

**Instrument error, retracted rather than worked around.** My first battery run
used `ruff format --check .`, which is wider than any CI gate; it returned 1 and
the offender was `AUDIT_LEDGER.md:862`, a code fence inside this audit log. There
is no repo-root format gate, so there was nothing to fix: I did not reshape the
ledger to satisfy a gate that does not exist. Separately, my per-file error split
first summed to 61 against mypy's own "59 errors in 6 files" because the pattern
also caught `note:` lines; recounted with `NN: error:` it matches.

## §37 D-L1-16 landed, and why the vendor sync was declined

**Landed (`7bd7b78`).** `ci.yml` `ruff check` + `ruff format --check` and
`publish.yml` `ruff check` now name `scripts`. Verified by running the three
edited commands verbatim, exit codes captured unpiped: all 0, and the format line
now reports 193 files. mypy was deliberately left out (59 errors / 6 files).
Two side observations, not landed: `publish.yml` has **no** `ruff format --check`
step at all, so the release pipeline checks style but not formatting — the same
species of asymmetry as the mypy-path bug filed as D-L1-06.

**Item 1 (sync `_vendor`) — measured, and the premise was wrong.** HEAD's
`packages/evaluation/src/dsa_evaluation/external_validation.py` and its vendored
copy hash identically (`9a9b385e…` both), so `origin/main` is consistent and
remote CI is not red. The drift exists only as another session's uncommitted
+44/−9 source edit. And `ci.yml:75` already runs `sync_vendor.py --check`, so
whichever commit introduces source-without-sync is caught there — now honestly
(exit 1, naming `dsa_evaluation: 1 file(s) differ`) rather than repaired-and-
passed, which is what the pre-`5400c01` code did.
Syncing anyway would have written a vendored copy of unreviewed third-party WIP
into *my* commit while its source stayed uncommitted, manufacturing exactly the
source/vendor inconsistency the gate exists to prevent. The 415-passing figure is
not evidence that the wheel is fine either: `conftest.py` puts workspace `src`
ahead of `_vendor`, so the suite exercises the new source while the stale copy
would be what ships — which is precisely the case line 75 stands between.
Handed back to the owner as the one-liner: `uv run python scripts/sync_vendor.py`
inside the same commit as their source change.

**Budget.** Eleven landed changes in this lane versus §28's cap of 8. The last
one is a gate addition rather than a defect repair, which is arguably the safer
half of the overrun; recorded rather than reframed.

## §38 Actions corroborates the repairs — the strongest evidence this lane has had

Everything asserted so far was produced by this lane running commands on this
machine. Queried the real thing instead: `gh run view 36129208262` — workflow
`CI`, `event=push`, `headSha=7397c47`, `conclusion=success`, jobs
`web-regression` + `ci` (31 steps), and **`7397c47` carries all six of this
lane's first-stage commits** (`ccbb66a … e1ecb6f` are its ancestors).

Steps that executed the exact text this lane wrote, all `success`:

| Repaired in | Step as it ran on GitHub's runner |
|---|---|
| D-L1-01 | `set -o pipefail; uv run python -m mkdocs build --strict 2>&1 \| tail -n 50` |
| D-L1-01 | `set -o pipefail; npm --prefix apps/web run build 2>&1 \| tail -n 20` |
| D-L1-01 | `set -o pipefail; uv run dsa --limit 5 … \| tail -n 20` |
| D-L1-06 | `uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports` |
| §34 | `uv run python scripts/sync_vendor.py --check` — the non-mutating `check()` |
| D-L1-05/13 | mkdocs `--strict` passing means the 7 repointed links held in a real build and `not_found: warn` did not break it |
| D-L1-07 | `uv run pytest -q --cov --cov-report=term-missing` — the guard tests ran on a fresh checkout |

**§30's open hole is now closed by a better instrument than I am.** The gates
this ledger kept listing as "never run" — `generate_sbom.py`, `Build wheel and
sdist`, `Smoke-test clean wheel install`, `docker build` for both Dockerfiles,
`npm audit --audit-level=high`, `regression.mjs`, `uv lock --check` — are all
`success` in that run, on a clean runner, which is stronger evidence than the
local box can give. Item (4) of the queue is therefore retired as measured.

**What remains genuinely unverified:** this lane's last five commits
(`dcc99f5`, `77587f1`, `d71cb85`, `7bd7b78`, `4708da8`) exist only locally —
`main` is ahead 5 and pushing is not this lane's to do. Of the five, only
`7bd7b78` touches a CI job, adding `scripts` to two ruff lines; locally both
exit 0, and the first pushed run will be the real answer. One self-correction
while gathering this: I first reported "no docs job on push" because `head -40`
truncated the 31-step job list — the mkdocs step was there all along, and the
conclusion I withdrew was an artifact of my own pipeline, not of the workflow.

## §39 mypy over `scripts/`: 59 → 37, and one real defect under the annotations

Done per the queue's item 4, three commits (`ef47c3b`, `0f5662a`, `d023d26`):

| File | before → after | what it actually was |
|---|---|---|
| `check_public_claims.py` | 11 → **0** | 4 missing annotations, plus **three live defects** |
| `generate_sbom.py` | 10 → 1 | one reused loop variable, one dead fallback, one Any leak |
| `check_npm_workspace_lock.py` | 1 → **0** | Any through a `dict[str, Any]` signature |
| `generate_benchmark_datasets.py` | 1 → **0** | missing `-> None` |

**The one that mattered was not a typing problem.** `check_version_consistency()`
called `re.search(...).group(1)` on three files; when a pattern is absent that
raises `AttributeError`, which the two-lines-below `except Exception` converted
into a single `"version check error: …"` string — retiring the entire five-way
consistency check, including the sbom and git-tag comparisons that never ran.
Same signature as D-L1-02's swallowed swallows, found by *following* an
annotation error instead of silencing it. Verified by execution, not argument: on
a tree with no `version = ` line, HEAD returned the one swallowed message while
the fixed module returns three named mismatches; the regression test fails
against HEAD's copy, so it is not green-on-arrival.

**Two things I declined.** `generate_sbom.py:182` needs the components list
hoisted out of the SBOM literal to type honestly, and the only way to verify a
rewrite there is to run a script that overwrites tracked `release/sbom.json`,
which §R8 forbids — so one error stands rather than an unverifiable edit. I also
nearly filed the `Path`-indexed-as-dict cluster as a runtime crash; reading the
file showed each loop rebinds `p`, so it was shadowing, not a bug, and the fix is
a rename rather than a defect report.

**Suite after all of it: 416 passed**, `ruff check`/`format` clean on `scripts`,
and the npm lock gate re-executed to confirm unchanged behaviour.

**Lane status, plainly.** This takes §28's cap of 8 from a stretch to 14 landed
changes. The remaining 37 mypy errors are in `generate_benchmark_v2` (23) and
`run_perf_matrix` (13) — research-side generators, not gates, and the kind of
work L3's lane is scoped for. The highest-value move is no longer to write more
fixes but to get these nine local commits pushed so Actions, not this laptop,
rules on them.

## §40 The push, its result, and a number of mine that was tree-contaminated

**Pushed** `7397c47..2d1e72f` (10 commits, fast-forward, no force). The three
files belonging to the concurrent session stayed uncommitted and did not go.
Before pushing I refused to treat "my working tree is green" as "HEAD is green":
a detached worktree at `2d1e72f`, driven with the existing `.venv/bin/ruff`,
`ruff check`/`format --check` (193 files), `sync_vendor --check` and the claim
checker all exit 0 on HEAD alone, then the worktree was removed.

**Result.** Run `36220751348`: `conclusion=success`, jobs `ci` and
`web-regression`, with the steps this lane rewrote executing as written —
`ruff check … scripts`, `ruff format --check … scripts`, `sync_vendor --check`,
mypy over `apps/jupyter`, `generate_sbom.py`, and four `set -o pipefail` steps
including mkdocs `--strict`. The remote reported `Required status check "ci" is
expected`, so **`scripts/` is now linted and format-gated by a merge-blocking
check** — D-L1-16 closed by CI rather than by my machine.

**Correction, by addendum.** §35 and §39 quote `scanned 14 file(s)`. On a clean
checkout of the same commit the checker says **10**. The four extras were
untracked build residue in this working tree that `SCAN_GLOBS` matches, so the
number described my machine, not the repository. Nothing in the argument changes
— 51 files are still declared and never read, on either count — but the habit
that produced it is the same one §36 caught: an instrument reading taken in a
dirty tree is not a fact about the commit. Any future count should be quoted from
a clean worktree or from CI.

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
  and 21.6 claim-to-command self-audit. Stopped at the §18 approval gate; no
  source file edited. Resumable state = this ledger + §16 baseline + Appendix B.
- 2026-09-25, repair phase — maintainer approved. Seven findings fixed, one
  commit each: `4ffc7b7` (D-L1-01), `0f16921` (D-L1-06), `c44cf3a` (D-L1-05),
  `1e000b7` (D-L1-13, new), `c0a008d` (D-L1-04), `01cbb7d` (D-L1-07),
  `fcf702a` (D-L1-03 partial), plus `b2d76bf` formatting a line my own commit had
  broken. Three of my own claims died in the process and are recorded as such:
  P-7(c) refuted by measurement (→ D-L1-14), a 6-skip count that was my grep
  reading the warnings block, and a guessed "+8" tracked-file delta that
  measured +3.
- Session end: 403 tests, coverage 80.24%, ten non-mutating §23 gates exit 0.
  SBOM / `uv build` / web / Docker not run — see §30 note above.
- 2026-09-25, follow-up — the two human decisions closed; 2 files, **3** commits
  (`ccbb66a` CODEOWNERS, `1e733d4` `.gitignore`, `0552996` this ledger). First
  draft of this line said "1 commit", which was wrong at the time of writing it.
  The maintainer authorized the identity lookup §33 had ruled out, and it
  confirmed rather than dissolved the finding: `@jackson` is a real but unrelated
  account with no permission here, so CODEOWNERS was inert. Both repairs are
  config-only (`.github/CODEOWNERS`, `.gitignore`); no `_vendor` touch, no
  workflow touch.
  Verification actually run for this step: `git check-ignore -v` matches on two
  paths (exit 0), `git ls-files -i -c --exclude-standard` → empty, `git ls-files`
  still 733, `git grep -l` for porcelain / `diff --exit-code` gates → no hits, and
  `tests/test_ci_gate_integrity.py` + `tests/test_import_identity.py` → 6 passed.
  The full 403-test suite and coverage were NOT re-run for a config-only change;
  the figures two lines above still describe the repair phase, not this one.
- 2026-09-25, §34 lane — D-L1-05 residual and D-L1-15 closed in `5400c01` and
  `544eedd`, with `tests/test_sync_vendor_check.py` added (5 cases). Numbers for
  this step are the current ones: **408 passed**, coverage **80.24%**, mypy 108
  files clean, ruff and format clean on `scripts` + `tests`, real `--check` exit 0
  with `_vendor` unmodified. This took the lane to 9 fixes against §28's cap of 8;
  §34 says so instead of renumbering.

- 2026-09-26, §35 — D-L1-14 root-caused and half-closed in `dcc99f5`. The
  finding as filed ("matcher mishandles negation") was really two defects
  sharing a symptom, and the bigger one was invisible: 51 files declared in
  `SCAN_GLOBS` and silently dropped by a skip list inside `main()`, so `0
  issues` never meant the public surface was clean. Scope honesty landed; the
  negation blindness is documented as what still blocks widening, and the
  checker is deliberately still not wired into CI. Two new tests. Also recorded:
  HEAD moved under this lane (five commits by another session, three files dirty
  that I never opened), my six commits verified intact, and the suite count
  consequently re-measured at 415 / 80.40% on a tree that is partly not mine.

- 2026-09-26, §36 — re-baselined after the branch moved: 415 passed, mypy 112
  files clean, claims honest, mkdocs strict clean, and `sync_vendor --check`
  exit 1 on real third-party drift — which the pre-`5400c01` code would have
  erased and reported as OK. Filed D-L1-16 (`scripts/` outside all three static
  gates; 2 of 3 close for free today, mypy needs 59 fixes). Retracted my own
  invented root-level format gate instead of editing the ledger to please it.

- 2026-09-26, §37 — D-L1-16 landed in `7bd7b78` (three ruff lines now name
  `scripts`; verified by running the edited commands, all exit 0). The vendor
  sync the maintainer approved was **not** run: measured first, it turned out
  HEAD and `origin/main` are source/vendor consistent and `ci.yml:75` already
  gates the drift, so syncing would only have committed another session's
  unreviewed WIP into the wheel path out from under its own source.
- 2026-09-26, §38 — traded local measurement for Actions evidence and the lane's
  repairs came back corroborated: run `36129208262` on `7397c47` (which carries
  the first six) is `success` across both jobs, with the pipefail steps, the
  widened mypy paths, mkdocs `--strict`, the non-mutating `--check` and the
  guard tests all executing as written. That run also closes §30's
  release-surface hole from the better side — SBOM, wheel build, clean-install
  smoke test and both Dockerfiles are green on a clean runner. Withdrew my own
  "no docs job on push" reading: `head -40` had truncated a 31-step job list, so
  the missing step was my pipeline, not the workflow.
- 2026-09-26, §39 — took item 4: mypy over `scripts/` 59 → 37 in three commits,
  including one genuine silent-failure repair inside the version-consistency
  check. Declined the one edit that could not be verified without overwriting
  tracked `release/sbom.json`, and withdrew a crash I had nearly reported. Suite
  416 passed. Lane now stands at 14 changes against a cap of 8, so the
  recommendation is to stop repairing and get the nine commits pushed.
- 2026-09-26, §40 — pushed (10 commits, fast-forward) after verifying HEAD alone
  in a throwaway worktree; Actions came back green on both jobs with the new
  `scripts` gates running as a required check. Corrected my own `scanned 14`
  figure to 10 on a clean checkout — a dirty-tree measurement posing as a
  commit fact.
- 2026-09-26, §41 — `fc9485f` pushed on its own (fast-forward) and Actions run
  `36223063691` returned `success` on `ci` and `web-regression`, closing the
  "five unpushed commits unverified" caveat §40 left in item (4) above. Then
  wrote the L3 dispatch block: re-measured D-L1-02 at 35 shipped / 19 files
  (unchanged by this lane's 15 commits), found 8 of those blocks silenced twice
  by a co-ignored `SIM105`, caught and corrected my own 43-site count that came
  from keying by reported line when the two rules point at different lines of
  one block, and flagged that 3 of the 35 sit in the file another session has
  open.

**Next session (resume instructions, §5.2).** Step nil: re-measure before
trusting any number in this ledger — HEAD was `7397c47` at the time of writing
and another session is committing to the same branch. Then: (1) decide D-L1-14's
remaining half — teach `PATTERNS` to separate "disclaims this old number" from
"asserts it" (measured cost of not doing so: 34 matches, 0 real, 2 build-failing,
over the 51 files still excluded), or retire the numeric patterns and keep only
version-consistency + maturity, which are mechanically decidable; (2) wire the
claim checker into CI only after (1), and note the CI-critical-script change gets
its own commit; (3) D-L1-02 package-by-package as L3 work, 35 shipped sites;
(4) closed by §38 — those gates are green in Actions run `36129208262`, on a
commit carrying this lane's repairs, so the release surface was measured by a
better instrument than a local rerun; what remains unverified is only this
lane's five unpushed commits, and a push is not this lane's to do;
(5) §37 landed the free half of D-L1-16 — what remains is mypy over `scripts/*.py`
(59 errors across 6 files, split in §36) and the absent `ruff format --check`
step in `publish.yml`. Before
any L2 work, note §17.6: L2's evidence on swallowed exceptions and claim checks
rests on gates D-L1-02/03 found broken, so re-derive rather than reuse.

**Revised judgement on item (1), stated so the next session does not execute the
wrong plan.** I had framed D-L1-14's remaining half as "teach `PATTERNS`
negation, or retire the numeric patterns". Neither is right, and the reason is
already measured in §35: retiring the numeric patterns would not unlock widening
scope, because the *name* patterns fail on the same corpus the same way — both
HIGH findings there were `old_package_pip` firing on a sentence that asserts the
command is absent. And the numeric patterns do have a job on the 14 files that
are assertion-shaped by design, where a README that still says an old count is
exactly the drift being policed (prospective value, not measured: they report
0 findings there today). So the open question is narrower than filed — it is
which corpora are safe to scan, now that §35 made that choice visible — not
whether the matcher can be made to understand negation.

## §41 L3 dispatch block for D-L1-02 — re-measured at `fc9485f` so the next lane does not inherit this lane's stale numbers

**Context, in one line each.** This lane (L1) is closed: `fc9485f` is the last
commit, pushed, and Actions run `36223063691` came back `conclusion=success` on
jobs `ci` and `web-regression` — so the pushed head is green under every gate
this lane added, including `ruff check … scripts` as a required check. The only
high-ranked finding left is D-L1-02, and §10 puts it in L3, not here. What
follows is measured, not recalled. Where this block and the "Next session" list
above disagree about D-L1-02's shape, §41 governs — the numbers there were taken
before the `scripts` gates and the `--check` repair landed.

1. **The inventory survived 15 commits.** At `fc9485f`,
   `ruff check --isolated --select S110 packages apps/api apps/jupyter` reports
   **35 shipped sites across 19 files** — identical to §21.5(4) and P-4. By
   package: `evaluation` 8, `apps/jupyter` 8, `agent` 7, `tools` 3, `apps/api` 3,
   `mcp` 2, `evidence` 2, `llm` 1, `datasets` 1; `plugins` and `execution` 0.
   By file the load-bearing ones are `langgraph_graph.py` 5, `magic.py` 5,
   `external_validation.py` 3, `display.py` 3, then `adapter.py`/`repro.py`/
   `research_manifest.py`/`routers/health.py` 2 each.
   `src/data_science_agent` outside `_vendor` has **0** sites; `_vendor` holds 35
   duplicates and is excluded by `pyproject.toml:113`, so no per-file-ignore in
   the list governs it — which is why this finding needs no vendor sync (§R3,
   §R4 untouched).

2. **New sub-finding: 8 of the 35 blocks are silenced by two ignore entries at
   once.** 9 of the 11 shipped lines in `pyproject.toml:120-131` carry `SIM105`
   alongside `S110`, and `--select SIM105` reports 8 sites — all 8 inside blocks
   already counted under S110, established in (3). Two
   consequences. (a) For a tree whose line carries both, drop **both** in the
   same commit: fixing the block to `contextlib.suppress(...)` is precisely what
   SIM105 asks for, so a leftover `SIM105` entry ends up governing nothing and
   keeps an unused exclusion alive — the direction §R11 forbids. (b) `datasets`
   and `llm` carry S110 only; those two lines take a single deletion.

3. **How the overlap was established, and an instrument error of my own.** First
   pass keyed locations by `path:line` and unioned the two rules, yielding "43
   distinct sites, 8 invisible to S110". False: S110 reports the `except` line
   and SIM105 the `try` line of the same block — read directly at
   `packages/evidence/src/dsa_evidence/repro.py`, where `try:` at 94 draws
   SIM105 and its `except Exception: pass` at 96 draws S110. The count was then
   re-established **without** any line-distance heuristic, by per-file multiset:
   `--select SIM105` puts its 8 sites in 8 files, no file has more SIM105 than
   S110 hits, and every one of those files has S110 hits — so there is no block
   only SIM105 can see. D-L1-02's true scope stays **35**, and any future count
   of it must de-duplicate by block, not by reported line.

4. **Ordering constraint this lane created.** 3 of the 35 live in
   `packages/evaluation/src/dsa_evaluation/external_validation.py` — the file the
   concurrent session has open and uncommitted (+44/−9 there, +27/−0 in its test,
   plus an unrelated +4/−3 in `README.md`).
   Its diff adds and removes **no** `except`/`pass` pair (verified by grepping
   the diff), so the 3 are pre-existing and the count is stable. Still: run
   `evaluation` **last**, after that session lands, or the L3 commit will collide
   with someone else's unreviewed hunk. Its commit also trips `ci.yml:75`
   (`sync_vendor --check`) unless that session syncs — that is its owner's call,
   not L3's to make silently.

5. **Per-tree recipe (§19 red-then-green, one tree per commit).** (a) Delete
   `"S110"` — and per (2), `"SIM105"` where present — from that one
   `pyproject.toml` line. (b) Count what that tree will report —
   `uv run ruff check <tree> --output-format=concise`, then
   `grep -c ": S110"` — and expect exactly that tree's number from (1), in that
   order: 8/8/7/3/3/2/2/1/1. Two of the nine trees live under `apps/`, not
   `packages/`. P-4's `expected_delta` was written for the whole finding.
   (c) Classify every site Hiding / Downgrading /
   Legitimate (§12) and fix the code, not the config: `contextlib.suppress(...)`
   for the Legitimate ones, a real handler or a raised error for the others.
   (d) `uv run ruff check packages apps/api tests src apps/jupyter scripts`,
   `ruff format --check`, `mypy`, `pytest -q --cov` — all four before committing.
   (e) Stage **by filename**: the worktree carries another session's edits and
   `git add -A` would swallow them (§R2).

6. **Acceptance, stated falsifiably.** Done = the `ruff check` invocations in
   `ci.yml:84` and `publish.yml` exit 0 with `S110` gone from all shipped
   lines, **no new `# noqa`** and no widened `per-file-ignores` anywhere (§R11 —
   this finding is closed only by adding signal), `tests/**` line 121 untouched
   (P-4's scope decision), suite green, `fail_under` unchanged at 79. A green
   that was reached by re-adding an ignore is not done.

7. **Budget.** §28 allows ≤8 fixes per lane; this lane landed ~15 and says so in
   §39/§40. That overrun is this lane's recorded debt, not a precedent for L3.

## §42 L3 execution of D-L1-02 — 27 of the 35 sites, eight trees, and the §41 claim about vendor sync that was wrong

**Context, in one line each.** L3 ran the §41 dispatch at `06a22c6` (§41 measured at
`fc9485f`; the one commit between them is §41 itself, so the inventory was current).
Eight commits, one per tree, 27 sites; `packages/evaluation`'s 8 sites were left
untouched as instructed, and the concurrent session's three dirty files were never
staged. Everything below was measured in this session; where §41 and this section
disagree, §42 is right about the tree as it now stands and §41 was right about the
tree as it stood at `fc9485f` — except item (3), which is a factual error in §41.

1. **Re-baseline confirmed §41's inventory exactly.** At `06a22c6`,
   `ruff check --isolated --select S110 packages apps/api apps/jupyter` reports **35
   sites**, by package `evaluation` 8, `apps/jupyter` 8, `agent` 7, `tools` 3,
   `apps/api` 3, `mcp` 2, `evidence` 2, `llm` 1, `datasets` 1, and `plugins`/
   `execution` 0 — the nine-tree split in §41(1), file for file. `--select SIM105`
   reports 8 sites in 8 files, none of them in a file lacking S110 hits, so §41(3)'s
   per-file-multiset argument holds and the overlap was not re-derived by line
   number. Baseline gates before any edit: ruff rc=0, format rc=0 (182 files),
   mypy rc=0 (112 source files), `pytest -q --cov` rc=0 at **80.40%**, `fail_under` 79.

2. **The eight trees, and what each site turned out to be.** Per-tree red was
   captured by deleting that tree's `S110` (and `SIM105` where the line carried it)
   and counting what ruff then reported; every count matched §41(1) before the code
   was touched. Class is §12's.

   | tree | commit | red | classes | what the fix was |
   |---|---|---|---|---|
   | `packages/agent` | `25443fd` | 7 | 5 Downgrading, 1 Hiding, 1 dead-code deletion | an incomplete reproducibility bundle and a failed report write are recorded (`evidence_bundle` / `langgraph_fallback` failed ValidationResults, `analysis2["error"]`); silent re-runs of the non-LangGraph engine now say so; the ground-truth block is gone (D-L3-01) |
   | `apps/jupyter` | `a1eea4d` | 8 | 7 Downgrading, 1 Legitimate | chart/preview/formatter/magic-registration failures print what they skipped; `nest_asyncio` probe became `contextlib.suppress` |
   | `packages/tools` | `b4f3edf` | 3 | 2 unreachable, 1 Legitimate | two dead handlers deleted so a surprise raises; `con.close()` in `finally` is `contextlib.suppress(Exception)` |
   | `apps/api` | `f415f61` | 3 | 1 Hiding (real bug), 2 Legitimate | rss unit fix + falsifiable test (D-L3-02); `unlink` and `_TOOL_CACHE` narrowed to `suppress(OSError)` / `suppress(ImportError)` |
   | `packages/mcp` | `e745563` | 2 | 2 Hiding | an unreadable artifact says `unreadable: <err>` instead of `not found` |
   | `packages/evidence` | `4ed13e6` | 2 | 2 Downgrading | missing package version recorded as `not-installed`/`unreadable`; a failed `chmod` is disclosed inside `reproduce.sh` |
   | `packages/llm` | `e4a6776` | 1 | 1 Legitimate | `suppress(ValidationError)` — the exception the file already imports and handles at 225/380 — and the now-empty ignore **line** deleted rather than left as `[]` |
   | `packages/datasets` | `ea25851` | 1 | 1 Hiding-by-erasure | per-statistic `_as_float`; a bulk `except: pass` could erase six already-computed statistics |

   Three sites — two in `packages/tools` and the one in `packages/datasets` — deserve
   the specific note that they were **not** reachable: `assumption_check.py` raises
   `ToolExecutionError` for any non-numeric column before the Levene cast, and the
   Levene cast uses that same `cols[0]`; `evaluate_model.py`'s split uses
   `stratify=y` for a binary target, which guarantees both classes in `y_test`; and
   in `profiler.py` polars returns null — not an error — for every numeric edge case
   probed (all-null, empty, single-row, NaN/Inf, UInt64 near 2**63). So the honest
   repair was deletion, not invented handling.

   How much each commit was differentially probed, stated exactly: `packages/datasets`
   + `packages/llm` were (6 series × full `ColumnProfile` dump, and three stub-schema
   cases, diffed against `git show HEAD:` copies of the same files — byte-identical),
   and `packages/agent`'s planner was (all 15 `expected_tool: run_sql` questions plus
   two controls, byte-identical — see (4)). The two `packages/tools` deletions were
   **not** differentially probed; they rest on the guard argument above and on the
   suite, and a probe of them would have needed the exception branch to be reachable,
   which is the thing being denied.

3. **§41(1) is wrong: this finding does need a vendor sync, and the lane was not
   authorized to run it.** §41(1) concluded "`_vendor` holds 35 duplicates and is
   excluded by `pyproject.toml:113`, so no per-file-ignore in the list governs it —
   which is why this finding needs no vendor sync." The first half is true and
   irrelevant: `_vendor` is excluded from *linting*, but it is a **copy of the
   sources**, so editing a source drifts the mirror by construction. Measured at
   `25443fd`, i.e. after tree 1 alone, `scripts/sync_vendor.py --check` exits **1**
   naming `dsa_agent: 2 file(s) differ`. At lane end (`ea25851`) it exits **1**
   across eight mirrors — `dsa_agent` 3, `dsa_api` 2, `dsa_tools` 3, `dsa_jupyter` 2,
   `dsa_datasets` 1, `dsa_evidence` 1, `dsa_llm` 1, `dsa_mcp` 1 = **14 files from this
   lane**, plus `dsa_evaluation` 1, which is the concurrent session's uncommitted
   edit and not mine.
   Why the mandated per-commit gates could not catch this: the four gates this lane
   was told to run (ruff / format / mypy / pytest) do not include `sync_vendor
   --check`; it lives at `ci.yml:75`, one line above the ruff gate at `ci.yml:84`. And
   `tests/test_sync_vendor_check.py` builds **scratch trees in tmp_path** — it proves
   the checker audits honestly, and asserts nothing about the real mirror. So nine
   consecutive green `pytest -q --cov` runs said nothing about drift. §N-level lesson:
   a gate that audits a generated copy is not the same as a test that audits it.
   **BLOCKED, decision for the maintainer, recommendation: run
   `uv run python scripts/sync_vendor.py` and commit the regeneration as its own
   explicit change** (§R8's "if you must regenerate, commit the regeneration"). L3
   did not do it because this lane's rails forbid bare invocation of that script, and
   hand-editing `_vendor` is forbidden by §R3 — repairing the mirror silently is
   exactly the unreviewable diff §R8 exists to prevent. **Until that commit exists,
   pushing `06a22c6..ea25851` turns `ci.yml:75` red.** That is a correct red, and the
   next lane must not resolve it by re-adding anything.

4. **D-L3-01 — shipped planning code consulted the benchmark answer key (S1, T0,
   confirmed, leak removed).** `packages/agent/src/dsa_agent/planner.py` read
   `ground_truth.expected_tool` out of `benchmarks/v2/catalog.json` and forced
   `wants_sql = True` whenever a user query matched a catalog `question`, inside
   `heuristics_plan` — the default planner, because `plan_analysis` routes
   `DSA_LLM_MODE` stub/heuristic (the CI/benchmark mode, `ci.yml:128`) straight to it.
   15 of the 100 catalog tasks have `expected_tool: run_sql`, and those same tasks
   carry `required_tools: ["run_sql"]` / `gold_method: "run_sql"`, which is what
   `generate_benchmark_v2.py:160-161` derives the scoreable fields from.
   It never executed: `_P(__file__).resolve().parents[3]` from
   `packages/agent/src/dsa_agent/planner.py` is `packages/`, so the probe path is
   `packages/benchmarks/v2/catalog.json`, which does not exist (measured: `EXISTS:
   False`; `parents[4]` is the repo root). Plans for all 15 run_sql questions plus two
   controls are byte-identical before and after the deletion.
   The second-order finding is worse than the first, and it is an **absence**: no
   test keys on the v2 planner consulting ground truth at all. `grep -rn "leakage"
   tests/` returns exactly one hit, `tests/evals/test_external_benchmark.py:124`
   `"gold leakage firewall"`, which guards the *external* benchmark path, not
   `heuristics_plan`. The only reason the leak was not live is that a path constant
   is off by one — so the suite cannot distinguish "no leak" from "leak code that
   never runs", and any future change that repairs the path silently enables it.
   **Recommendation for the next lane:** a source-level pin asserting no shipped
   module under `packages/` or `apps/` reads `benchmarks/**` or the `expected_tool`
   key (`git ls-files | grep -c "^benchmarks/"` = 70, and `benchmarks/v2/catalog.json`
   is tracked, so the answer key is present in every checkout, including CI). Not
   added here: it is a new test surface, outside this lane's 8 fixes.

5. **D-L3-02 — `/metrics` under-reported RSS by 1024x on Linux (S2, T0, FIXED in
   `f415f61`).** `apps/api/src/dsa_api/routers/health.py` carried a
   "macOS reports bytes, Linux reports KB — normalize" comment and then applied the
   identical bytes formula on both branches, so a Linux process divided kilobytes by
   1024\*1024. The `except Exception: pass` wrapped the whole block, so a wrong number
   and an unavailable `resource` module looked the same from outside. The unit was
   measured rather than assumed: allocating 64 MiB on this Mac moved `ru_maxrss` by
   67,092,480, i.e. bytes, so the bytes formula is the macOS-correct one. The fix is
   the per-platform divisor plus `tests/unit/test_metrics_rss_unit.py`, parametrised
   over Darwin/Linux: against the pre-fix handler the Linux case fails
   (`((122404864 / 1024) - 0.01) <= 116.73`), against the fix it passes. Nobody saw it
   because macOS is the branch the old code got right, and this lane's machine is a
   Mac — CI's Linux runners are the ones that were reading wrong numbers, and `/metrics`
   has no assertion on `rss_mb` at all today.

6. **Filed, not fixed.** Kept short and deliberate; §19 step 10.
   - **D-L3-03 (S2, reachable, Hiding-class, not an S110 site).**
     `assumption_check.py` records a check that *failed to run* as
     `{"error": ..., "passed": True}` in two places (normality at line 84, levene at
     line 126, measured at `ea25851`). `overall_pass` — and therefore the
     recommendation "Assumptions hold (p>0.05)." — is unaffected by that error, so an
     assumption check that could not execute reports the assumption as satisfied.
     This is the same defect class as D-L1-02 but invisible to S110, because the
     handler is not `pass`. Worth sweeping for across `packages/tools`.
   - **D-L3-04 (§12 ambient state, untouched by design; S0-candidate for the next
     lane).** `apps/api` `/metrics` reads `dsa_agent.graph._TOOL_CACHE` and publishes
     its length as `tool_calls_total` — in a multi-worker API process that number is
     one worker's count, labelled as a total. The cache itself is the larger question:
     `_TOOL_CACHE: dict[tuple[str, str], tuple[Any, bool, str | None]]` at
     `graph.py:45`, keyed by `(tool_name, sha256(inputs))` at `graph.py:88-90`, written
     and read at `graph.py:94-104` — **no run identity and no dataset-content
     component**, so a tool called with the same `dataset_path` in a later run gets the
     first run's result even if the file on disk changed. §12 names exactly this shape
     as an S0. L3 narrowed only the exception that swallow at the metrics endpoint; the
     key needs its own lane (invalidation policy, and a bounded cache — it never
     evicts).
   - **D-L3-05 (config hygiene, three dead exclusions).** `packages/plugins` and
     `packages/execution` still list `S110`+`SIM105` while measuring **0** sites, so
     both entries govern nothing — §R11's direction. Separately, `ignore = ["S101",
     "E501"]` at `pyproject.toml:117` already disables E501 globally, which makes the
     `"E501"` entries in the `plugins` and `apps/jupyter` lines no-ops by
     construction; and the `tests/**` line lists `"S110"` **twice**. All four are
     deletable with zero behavioural risk and were left alone because they are not
     this lane's finding.

7. **What remains of D-L1-02.** Eight shipped trees are clean; the in-scope measure
   is now `ruff check --isolated --select S110 packages/agent packages/tools
   packages/mcp packages/evidence packages/llm packages/datasets apps/api
   apps/jupyter` → **All checks passed** (was 27). The whole inventory is at 8, all in
   `packages/evaluation`, which is out of scope for L3 and blocked behind the
   concurrent session's uncommitted `external_validation.py` (3 of the 8). Order for
   whoever picks it up: let that session land, then `evaluation`'s line 125 loses
   `S110`+`SIM105` **last**, then delete the two dead lines from (6), and only then can
   §41(6)'s acceptance ("S110 gone from all shipped lines") be claimed.
   Rails held: `tests/**` line 121 untouched (P-4), `fail_under` still 79, **zero** new
   `# noqa` across all nine commits (verified by grepping `git diff 06a22c6..HEAD` for
   the string: 0 matches), no new ignore entry anywhere, nothing under `_vendor`
   edited, no dependency, no push, no branch/tag/PR.

8. **An error of my own, recorded because the lane's point is honest numbers.**
   `f415f61` shipped `test_metrics_rss_unit.py` with a strict lower bound comparing an
   unrounded `before/divisor` against a value the handler rounds to 2dp. It passed in
   isolation and passed four full-suite runs, and failed on the fifth: `ru_maxrss` is
   a high-water mark, so under memory pressure the reading was 470.2839…, rounded to
   470.28, and `470.2839 <= 470.28` is false. Fixed in `a680b80` with a ±0.01 bound
   that still fails against the pre-fix handler; run 5/5 to show it is not order-dependent.
   Green-on-arrival is not the same as green-always, and a test that only fails under
   load is still a test that can fail.

9. **Budget.** §28 allows ≤8 fixes: this lane landed exactly **8 tree fixes** plus one
   commit correcting a test its own tree 4 introduced (`a680b80`), which is
   bookkeeping, not a ninth fix. Coverage, baseline then after trees 1→8 in order:
   80.40, 80.40, 80.42, 80.47, 80.53, 80.53, 80.50, 80.51, 80.51 — never below the 79
   floor, and the only dip (`4ed13e6`, evidence) is two failure-path handlers the suite
   does not exercise, recorded there rather than avoided by deleting the branches.
   Statements 7676 → 7654 across the lane (the deletions in trees 3, 7, 8). The four
   gates ran before every commit and returned rc=0, rc=0, rc=0, rc=0, except the one
   genuine red in (8). **Not pushed.** The vendor regeneration in (3) is the first
   thing any push needs.

## §43 D-L3-04 promoted from inference to reproduction, plus the vendor-sync runbook §42(3) leaves behind

**Context, in one line each.** With L3's eight trees committed and nothing pushed, the two
open items were the one §42 filed but did not fix (the tool cache's invalidation key) and
the one §42 blocked on a maintainer decision (regenerating `_vendor`). The first was still
free to work on and needed no authorization; this section is what measuring it produced,
and then the runbook for the second.

1. **D-L3-04 is real, and it is worse than §42 said.** §42 inferred the defect from the key's
   shape. Reproduced now, in one process, deterministic, no mocking.

### D-L3-04
| field | value |
|---|---|
| claim | `_TOOL_CACHE` keys on the tool name plus the hashed *input dict*, which carries the dataset **path string**, so a long-lived process replays one run's result — success or failure — to every later run that names the same path, whatever the file now contains |
| lane | L3 (§12 ambient state) |
| evidence_tier | T0 (executed against the shipped module, deterministic) |
| severity | **S0** |
| location | `packages/agent/src/dsa_agent/graph.py:45` (declaration), `:85-90` (key), `:93-106` (get/set); mirrored byte-for-byte at `src/data_science_agent/_vendor/dsa_agent/graph.py:45,85,95-96,104`, so the published wheel carries it too |
| mechanism | Two failure modes, not one. (a) *Stale success*: the key cannot see content change, so a profile computed before a dataset is overwritten is handed to the run after it, and the run's evidence, insights and report all describe data that no longer exists. (b) *Poisoned failure*: line 101-104 stores `(None, False, error)` under the same key as a success, so one transient miss — file not yet written, a mount that lagged — makes that dataset permanently unreadable **for the lifetime of the process**, and every later retry gets the first error back rather than executing the tool. (a) is silently wrong numbers in a product whose guarantee is verifiable numbers; (b) turns a momentary fault into a stuck run with no path to recovery short of a restart |
| evidence_command | re-create the two probes from (2) below (they write only under `/tmp`, deliberately not committed) and run `NO_PROXY='*' no_proxy='*' uv run python /tmp/dl304/repro2.py`, then `… repro4.py` |
| output_excerpt | repro2: `mean reported run1 : [2.5]` / `mean reported run2 : [2.5] <-- served from cache, file already changed` / `mean reported run3 : [250.0] <-- after evicting the key`; repro4: `run1 (no such file) ok=False err='File not found: /tmp/dl304/ds4.csv'` / `run2 (file now valid) ok=False err='File not found: ...'` / `run3 (fresh key) ok=True` / `=> failure replayed for an identical, now-valid dataset: True`; both scripts exit 0 |
| reproducible | deterministic |
| fix_sketch | Three separable pieces, cheapest first: **(i)** stop caching failures — on `ok=False` return without storing, which alone kills mode (b) in four lines; **(ii)** put run identity in the key by threading `run_id` into `_run_tool`, which is the §12 requirement and kills (a) across runs while preserving within-run dedup, at the cost of a signature change reaching all three call sites (enumerated in `blast_radius` below); **(iii)** bound it — the dict is written and never evicted anywhere (`grep -rn "_TOOL_CACHE"` returns only the declare/read/write plus the metrics read), so a long-lived API process grows it without limit, and `len()` of that growth is what `/metrics` publishes as `tool_calls_total`. What it would break: any test or product path that relies on the cache to avoid re-executing a tool across runs; the cache is also what makes a notebook re-run cheap, so (ii) should keep within-run hits |
| blast_radius | `packages/agent` — all three `_run_tool` call sites are affected (`graph.py:324`, `graph.py:439`, `langgraph_graph.py:91`), the `_vendor` mirror and therefore the wheel, every long-lived consumer (`apps/api` worker, Jupyter kernel), plus `/metrics`' reported number |
| verify_before | `repro2.py` above: `run2 == run1 (stale) : True` with the file already rewritten |
| verify_after | the same script prints `run2 == run1 (stale) : False`, and `repro4.py`'s last line flips to `False` once failures are not stored |
| expected_delta | `repro2` run2 mean `[2.5]` → `[250.0]`; `repro4` run2 `ok=False` → `ok=True`; `/metrics` `tool_calls_total` should stop being reported as a process-global count or be renamed to say so |
| status | **open** — not fixed in L3: it is a structural change (§28 caps structural edits at two, and this lane spent its budget on the eight trees), and (ii) needs a decision about whether a cached result is allowed to cross a run boundary at all |
| commit | — |
| protected | no |

2. **The two probes, verbatim, so the claim survives this session.**

   ```python
   # repro2 — stale success. File is rewritten between run1 and run2; same inputs.
   DS.write_text("v\n1\n2\n3\n4\n")            # mean 2.5
   o1, _, _ = await _run_tool("profile_dataset", {"path": str(DS)})
   DS.write_text("v\n100\n200\n300\n400\n")    # mean 250.0
   o2, _, _ = await _run_tool("profile_dataset", {"path": str(DS)})
   _TOOL_CACHE.pop(_tool_cache_key("profile_dataset", {"path": str(DS)}), None)
   o3, _, _ = await _run_tool("profile_dataset", {"path": str(DS)})
   # -> mean_of(o1)==[2.5]  mean_of(o2)==[2.5]  mean_of(o3)==[250.0]

   # repro4 — poisoned failure. The FIRST call is the one that fails, so the error is stored.
   # (an earlier draft of this probe put the deletion second and proved nothing: with one
   # key, every later call is a cache hit and the tool never ran — the test was vacuous.)
   o1, ok1, e1 = await _run_tool("profile_dataset", {"path": str(DS)})   # file absent
   DS.write_text("v\n100\n200\n300\n")
   o2, ok2, e2 = await _run_tool("profile_dataset", {"path": str(DS)})   # same key
   o3, ok3, e3 = await _run_tool("profile_dataset", {"path": str(DS2)})  # copy, new key
   # -> ok1=False  ok2=False (identical error text)  ok3=True
   ```

   The control that makes both readings mean something is the *different key* case: the same
   bytes at a second path profile fine while the first path is still returning a stale or
   errored result. That isolates the cache as the cause and rules out the loader.

3. **Runbook: regenerating `_vendor` once the concurrent session lands.** This is the step
   §42(3) blocked on, written so it is executable rather than described. It mutates tracked
   files, which is why it was not run here, and it is the only thing standing between this
   lane and a green `ci.yml:75`.

   1. Confirm the other session has committed: `git status --short` must show no ` M` entries
      for `packages/evaluation/**`, and `git log --oneline -1` must be ahead of `9a085fd`.
      If it has not landed, stop — see step 5 for why.
   2. Re-measure the drift so the commit's scope is known before it is made, not after:
      `uv run python scripts/sync_vendor.py --check` (expect rc=1, and it prints the per-package
      counts; `--check` writes nothing).
   3. Regenerate: `uv run python scripts/sync_vendor.py` (bare invocation **writes**; the script's
      own message says "then commit the result").
   4. Stage the mirror **by directory, then verify it is only the mirror**:
      `git add src/data_science_agent/_vendor` followed by `git diff --cached --name-only`, and
      confirm every path starts with `src/data_science_agent/_vendor/`. Commit as its own
      `chore(vendor): resync _vendor after D-L1-02 tree fixes` — §R8 says a regeneration is its
      own explicit change, never folded into the source commit that caused it.
   5. Why the ordering in step 1 is not caution-for-its-own-sake: the writer is a **global
      synchroniser** — it copies every listed source tree from the *working tree*, so running it
      while another session's `external_validation.py` hunk is uncommitted bakes an unreviewed
      change into the mirror and into this lane's commit. That is the exact collision §41(4)
      predicted, arriving through a generated file instead of a source file.
   6. Then the two gates that were red become green and must be reported as such:
      `uv run python scripts/sync_vendor.py --check` → rc=0, and `uv run pytest -q --cov` stays
      rc=0. Pushing `06a22c6..9a085fd` **before** step 4 is a known-red range on `ci.yml:75`.

4. **What I did not do, and why.** Did not fix D-L3-04: it is one of §28's two allowed
   structural changes, L3's eight fixes are spent, and the shape of the key is a decision
   (may a cached tool result cross a run boundary?) rather than a defect with an obvious
   patch — §18's gate says surface it, so it is surfaced. Did not run the bare sync in (3):
   this lane's rails forbid it and the precondition in step 1 is not yet true. Did not push,
   tag, branch, or open a PR (§R14). Nothing under `_vendor` was hand-edited (§R3) — the probes
   import it only to compare line numbers. No `# noqa`, no new ignore, `fail_under` still 79.
   Working tree is exactly the other session's three files plus the untracked prompt document.

5. **Suggested order for whoever picks this up next.** (a) the four-line `(i)` in D-L3-04 —
   it is not structural, it is strictly more signal than today, and it removes the stuck-run
   failure mode immediately; (b) the `_vendor` resync per (3) once the evaluation session
   lands; (c) then `packages/evaluation`'s remaining 8 S110 sites, which is what closes
   D-L1-02 outright; (d) then the dead exclusions and the duplicated `"S110"` in the `tests/**`
   line from §42(6); (e) D-L3-04 `(ii)`/`(iii)` last, because they need a decision and a
   benchmark re-run, not a patch.

## §44 The exact blast radius of the blocked `_vendor` resync, measured read-only

**Why this section exists at all.** §43(3) step 2 tells the next person to "re-measure the
drift so the commit's scope is known before it is made", and the only tool for that is
`sync_vendor.py --check`, which reports **per-package counts** — enough to know a resync is
needed, not enough to review one. The inventory below came from a read-only `cmp` loop over
source-versus-mirror, so a reviewer can now check the regeneration's diff against a named
file list instead of a count. Nothing was written to produce it, and no gate was rerun for a
docs-only commit.

1. **Status of the two gates at `6b604f7`.** The concurrent session had **not** landed:
   `README.md`, `packages/evaluation/src/dsa_evaluation/external_validation.py` and
   `tests/evals/test_external_validation.py` were still ` M`, so §43(3) step 1's precondition
   fails and the resync is correctly still blocked. `origin/main` was still `06a22c6` with
   local `main` ahead 11, so pushing this range would publish a known-red `ci.yml:75`.

2. **The 14 files a resync would write — all of them mine, all of them pure copies of
   already-committed source.** `diff` line counts are source-vs-mirror, so they double-count
   each changed line (`<` and `>`); they size the review, they are not the commit's `+/-`.

   | mirror file | changed lines |
   |---|---|
   | `dsa_agent/langgraph_graph.py` | 55 |
   | `dsa_datasets/profiler.py` | 29 |
   | `dsa_jupyter/magic.py` | 21 |
   | `dsa_evidence/repro.py` | 20 |
   | `dsa_mcp/adapter.py` | 18 |
   | `dsa_api/routers/health.py` | 17 |
   | `dsa_agent/planner.py` | 16 |
   | `dsa_agent/graph.py` | 13 |
   | `dsa_jupyter/display.py` | 12 |
   | `dsa_tools/tools/evaluate_model.py` | 11 |
   | `dsa_llm/providers.py` | 10 |
   | `dsa_tools/tools/assumption_check.py` | 7 |
   | `dsa_api/routers/datasets.py` | 5 |
   | `dsa_tools/tools/run_sql.py` | 5 |

   Per-package this is `dsa_agent` 3, `dsa_api` 2, `dsa_jupyter` 2, `dsa_tools` 3,
   `datasets`/`evidence`/`llm`/`mcp` 1 each — identical to the counts `--check` prints, which
   is what makes the loop trustworthy rather than merely convenient. `pyproject.toml`,
   `AUDIT_LEDGER.md` and `tests/unit/test_metrics_rss_unit.py` appear nowhere, because the
   mirror covers only the shipped `src/` trees — so the resync cannot touch test or config
   surface, and a reviewer who sees either of those in the regeneration diff should stop.

3. **The one file that must not be taken yet.** `dsa_evaluation/external_validation.py` also
   differs, but its source side is the other session's **uncommitted** hunk. This is the whole
   reason §43(3) sequences the resync after their landing: `sync_vendor.py` is a global
   synchroniser that copies from the working tree, so running it now writes an unreviewed
   change into the mirror and into this lane's commit. When the regeneration happens, its diff
   should be exactly the 14 rows above; if it contains an `external_validation.py` hunk, it
   ran too early.

4. **The read-only check, for reuse.**

   ```bash
   git diff --name-only <lane-base>..HEAD | grep -E '^(packages|apps)/.*/src/.*\.py$' | while read src; do
     pkg=$(echo "$src" | sed -E 's#^(packages|apps)/([^/]+)/src/([^/]+)/.*#\3#')
     rel=$(echo "$src" | sed -E 's#^(packages|apps)/[^/]+/src/[^/]+/##')
     mir="src/data_science_agent/_vendor/$pkg/$rel"
     [ -f "$mir" ] && { cmp -s "$src" "$mir" && echo "in sync  $mir" || echo "DIFFERS  $mir"; }
   done
   ```

5. **Not done, deliberately.** `tests/**` still lists `"S110"` twice — §43(5)(d) proposed
   deleting that duplicate, and it is now recorded as **not** proposable: §41(6) names the
   `tests/**` line as an acceptance condition ("`tests/**` line 121 untouched (P-4's scope
   decision)"), so editing it, even to delete a redundant token, breaks this finding's own
   stated acceptance before `evaluation` has landed. It belongs to whatever lane decides to
   reopen P-4, not to a hygiene sweep. Likewise D-L3-04 `(i)` (do not cache failures) stays
   the next lane's first item: §28's ceiling is 8 fixes per session, L3 spent them on the
   eight trees, and landing a partial mitigation of an S0 while `(ii)`/`(iii)` remain open is
   how a ledger ends up claiming a finding is half-fixed.

## §45 D-L3-04 (i) landed as the maintainer-released ninth change, and what it pointedly does not fix

1. **Authorization, recorded because §28's ceiling is the point of the record.** §43(5)(a)
   and §44(5) both placed fix `(i)` in the *next* lane, on the grounds that L3's eight fixes
   were spent and that a partial S0 mitigation left the ledger holding a half-fixed finding.
   The maintainer released that constraint for this one change ("一并放开 D-L3-04 的 (i)
   修复"), so it landed as `2ed7a90` — ninth change of the session, first of D-L3-04, and the
   ceiling now stands released for exactly this item and nothing else.

2. **The change is four lines in `_run_tool`** (`graph.py:93-108`): a non-`ok` result returns
   the same `(None, False, error)` tuple to its caller but is no longer written to
   `_TOOL_CACHE`. Nothing about status semantics moved — the caller still sees `ok=False` —
   the failure simply stops being remembered. New test
   `tests/unit/test_tool_cache_failure_not_stored.py`, written and run red first:

   ```
   AssertionError: failure was cached: 'File not found: .../ds.csv'
   assert ('profile_dataset', 'cf921c53f33e7eb3bf30c33d') not in
     {('profile_dataset', 'cf921c53f33e7eb3bf30c33d'): (None, False, 'File not found: ...')}
   ```

   which is the mechanism, not an incidental break: the tuple is literally sitting under the
   success key. After the fix that test passes, and §43's independent probe now prints
   `cached: False`, `run2 (file now valid) ok=True`, `failure replayed …: False`.
   The test's final two assertions exist because of §44(5)'s objection to a partial fix in
   the other direction: a "fix" that deletes the cache entirely also turns the failure case
   green, so the test requires that a *success* is still cached and served by identity.

3. **Mode (a) is untouched, and that is the load-bearing line of this section.** Fix `(i)`
   addresses poisoned failures. It does nothing to stale successes: the key is still
   `(tool_name, sha256(inputs))` and `inputs` carries the dataset **path string**. Re-running
   §43's stale probe verbatim after this commit still reports

   ```
   mean reported run1   : [2.5]
   mean reported run2   : [2.5]   <-- served from cache, file already changed
   mean reported run3   : [250.0] <-- after evicting the key
   run2 == run1 (stale) : True
   ```

   So **D-L3-04 is now "partially mitigated", not fixed**: `(b)` closed, `(a)` open, `(iii)`
   (the dict is never evicted) open. `(ii)` — run or content identity in the key — is the one
   that closes (a); it is a signature change reaching all three `_run_tool` call sites
   (`graph.py:324`, `graph.py:439`, `langgraph_graph.py:91`) and it changes how many times
   tools execute in a notebook or benchmark run, so it needs a decision about whether a cached
   result may cross a run boundary at all. That is not a four-line change and it is not done
   here. Anyone reading only the table in §43(1) should read this paragraph with it.

4. **§44's blast-radius table is now stale in one row.** `dsa_agent/graph.py` measured 13
   changed source-vs-mirror lines at `6b604f7` and **21** at `2ed7a90`. The file count is
   unchanged — still exactly **14** files, still all of them this lane's committed source,
   still no `pyproject.toml` / ledger / test path, because the mirror covers only `src/`
   trees. The per-package totals `--check` prints are likewise unchanged (`dsa_agent` 3).
   The resync's acceptance test from §44(3) still applies: a regeneration diff containing an
   `external_validation.py` hunk ran too early.

5. **Gates, state, and what is still owed.** ruff rc=0, format rc=0 (184 files, +1 for the new
   test), mypy rc=0 (112 files), `pytest -q --cov` rc=0 at **80.52%** (7656 statements),
   `fail_under` 79 untouched, no `# noqa`, no new ignore entry, `_vendor` untouched (§R3 — this
   commit deepens the drift rather than papering over it). Re-measured: the concurrent session
   had still not landed at `2ed7a90`, so the §43(3) precondition for the resync remains false and
   `origin/main` is still `06a22c6` behind a local `main` that is now 13 commits ahead. **Not
   pushed.** Outstanding, in order: the `_vendor` resync once that session lands, then
   `packages/evaluation`'s 8 S110 sites (which is what closes D-L1-02), then D-L3-04 `(ii)` and
   `(iii)`, then D-L3-01's anti-leak pin and D-L3-03's `passed: True`-on-error sweep.

## §46 The resync and the push landed, and the reason `--check` was red is not the reason CI would be red

1. **Executed, under the maintainer's two authorizations** ("授权跑 sync_vendor.py"、"push"):
   `uv run python scripts/sync_vendor.py` → `Synced: dsa_agent, dsa_api, dsa_datasets,
   dsa_evaluation, dsa_evidence, dsa_jupyter, dsa_llm, dsa_mcp, dsa_tools`, then
   `git restore --source=HEAD -- src/data_science_agent/_vendor/dsa_evaluation`, committed
   as `dd8d3c9` with exactly 14 staged paths all under `_vendor/` (§44(2)'s predicted list,
   per package 3/2/3/2/1/1/1/1) and `dsa_evaluation` count 0. Pushed `06a22c6..dd8d3c9`,
   15 commits, fast-forward, no force; local and `origin/main` both `dd8d3c9`.
   Gates before that commit: ruff rc=0, format rc=0 (184 files — the mirror stays excluded by
   `pyproject.toml:113`, which is why the count did not move), mypy rc=0 (112 files),
   `pytest -q --cov` rc=0 at 80.52%, and the suite was confirmed to import
   `dsa_agent.graph` from `packages/agent/src/`, not from `_vendor`.

2. **The restore was the whole job, and it is checkable after the fact.** `sync()` is
   `rmtree` + `copytree` per differing package, so it copies **whatever is in the working
   tree** — including the concurrent session's still-uncommitted `external_validation.py`.
   Restoring that one directory returns it to HEAD's blob `014d6926439b7514…` (verified), and
   their source file is untouched (same md5 before and after). §44(3)'s acceptance test —
   "a regeneration diff containing an `external_validation.py` hunk ran too early" — is
   satisfied in the strong form: the commit contains none.

3. **A reasoning error of mine, caught before it became a claim: which red belongs to CI.**
   `sync_vendor --check` reads the working tree, so it mixes the session's own drift with
   anyone else's uncommitted edits. I began this turn suspecting §42(3)/§45 had overstated
   the push risk ("CI checks out a commit, not a worktree") — measuring showed **both** halves:
   - the evaluation drift I was reasoning about is invisible to CI (not in any commit), and
   - the 14-file drift is very much visible, so "pushing `06a22c6..ea25851` is red at
     `ci.yml:75`" was **right as written**. The ledger does not need correcting; my draft
     self-correction did.
   Settled with an instrument rather than by argument: compare the two sides as **committed
   blobs** at a chosen revision, which is what a clean checkout is.

   ```bash
   # run from the repo root; prints the same kind of report as sync_vendor --check, but
   # reads only <rev>'s objects, so a dirty worktree cannot move the verdict.
   V=src/data_science_agent/_vendor; rev=fc9485f
   for pkg in $(git ls-files "$V" | sed -n "s#^$V/\([^/]*\)/.*#\1#p" | sort -u); do
     src=$(git ls-files -- "packages/$pkg/src" "apps/$pkg/src" | head -1)   # see note
     a=$(git ls-tree -r --name-only $rev -- "${src%/*}/.." | sort)
     b=$(git ls-tree -r --name-only $rev -- "$V/$pkg" | sort)
     [ "$a" = "$b" ] || echo "DRIFT $pkg"
   done
   ```

   (Path-mapping detail matters, so the version actually used resolved each package's source
   prefix from `sync_vendor.SOURCES` rather than guessing it from directory names, and compared
   `git rev-parse <rev>:<path>` blob ids per file — names alone would miss a content change.)
   Verdicts, with exit codes taken unmasked: `OK at fc9485f`, rc=0 — the revision §40 records
   as pushed and CI-green, which is the instrument's negative control; `DRIFT at HEAD`, rc=1,
   14 files, before `dd8d3c9`; `OK at HEAD`, rc=0, after it. Post-commit, local `--check`
   reports exactly one drifting file (`dsa_evaluation`) — the intended divergence: the gate is
   red for the person holding that unreviewed edit, green for the tree that was pushed.

4. **Residual, and it transfers.** Once the other session commits `external_validation.py`,
   **their** commit will be red at `ci.yml:75` for the same reason mine was, and the fix on
   their side is the same two commands with the same one-directory caveat reversed: resync and
   let the evaluation mirror land with the evaluation source. This is not a defect to fix in
   advance; it is the normal cost of a generated mirror plus a shared worktree, and (3)'s
   blob view is how anyone tells the two situations apart in 30 seconds.

5. **What I proposed and then declined to commit.** A `scripts/check_vendor_ci_parity.py`
   wrapping (3) — useful, and it passed lint once written; it failed on `S603`/`S607` because
   no script in `scripts/` had ever shelled out, and the only cheap ways past that were a
   per-file-ignore for `scripts/` (§R11: exactly the widening this whole lane exists to stop)
   or relocating the check into `tests/`, where those two rules are already ignored — but that
   would install a **new blocking local gate**, which is a design decision, not a cleanup. The
   file is not in the tree (`scripts/` clean, verified) and nothing was suppressed. If you
   want the gate, the decision to record is: should `pytest` fail whenever `_vendor` trails a
   committed source? Say so and it is roughly 40 lines with a scratch-repo test.

6. **D-L1-02 status after the push: 27 of 35 closed, not closed.** The eight in-scope trees
   measure 0 S110 and 0 SIM105; `packages/evaluation`'s 8 remain (3 of them in the file that
   session still holds open), and §42(6)'s remaining items are unchanged: D-L3-04 `(ii)`/`(iii)`
   (mode (a), stale success across runs, still fully open — `dd8d3c9` changed nothing about the
   key), D-L3-01's anti-leak pin, D-L3-03's `passed: True`-on-error handlers, and the
   `plugins`/`execution` dead exclusions.

## §47 Completion record for the pushed lane

1. **What is now on the remote.** `06a22c6..dd8d3c9` pushed as a fast-forward — 15 commits,
   no force, no tag, no branch, no PR; `git rev-parse HEAD` and `git rev-parse origin/main`
   both `dd8d3c99947b50607eb2d710bb1a66b658c412a8`, and `git status -sb` reports no ahead/behind.
   Contents: 8 D-L1-02 tree fixes (`25443fd…ea25851`), one test correction (`a680b80`), one
   D-L3-04 fix (`2ed7a90`), four ledger sections (§42–§45), and the resync (`dd8d3c9`).

2. **Gates, as observed rather than as intended.** Before the last commit: ruff rc=0, format
   rc=0 (184 files), mypy rc=0 (112 files), `pytest -q --cov` rc=0 at 80.52%, `fail_under` 79
   untouched, zero `# noqa` added anywhere in the lane, and `dsa_agent.graph` confirmed to
   resolve from `packages/agent/src/` rather than `_vendor` during the suite.

3. **`ci.yml:75` is green for the pushed tree, and the local gate is still red — both correct.**
   Decided on committed blobs, not on argument: at `dd8d3c9` every vendored package matches its
   source (the same comparison reports `OK at fc9485f` — §40's pushed-and-green revision — as
   the instrument's negative control, and 14 files at the pre-resync `HEAD`). Meanwhile
   `sync_vendor.py --check` in *this* work tree still exits 1 naming one file,
   `dsa_evaluation`. That difference is the point of §46(3): the other session's uncommitted
   edit is not in anything pushed, and it will have to be resynced by their own commit, at
   which point the same restore caveat applies in reverse — their mirror should land with
   their source.

4. **D-L1-02 is not closed and this lane cannot close it.** 27 of 35 sites are fixed and the
   eight in-scope trees measure 0 S110 / 0 SIM105 with their ignore entries narrowed or
   removed; `packages/evaluation`'s 8 sites (3 inside the file that session still holds open)
   are outstanding, plus §42(6)'s list: D-L3-04 `(ii)`/`(iii)` — **mode (a), the stale-success
   half, is entirely unfixed by the push**; `dd8d3c9` changed generated copies, not the cache
   key, so the reproduction in §43(2) still reports `run2 == run1 (stale): True`. Then
   D-L3-01's anti-leak pin, D-L3-03's `passed: True`-on-error handlers, and the
   `plugins`/`execution` dead exclusions.

5. **One open design question, deliberately not answered here.** §46(5) recorded why a
   permanent CI-parity script was not committed (its lint hit was `S603`/`S607`, and the two
   cheap exits were a `scripts/` ignore — the §R11 widening this lane exists to oppose — or
   moving it under `tests/`, which would make `pytest` block on `_vendor` staleness). The
   question for the maintainer is exactly that: *should the local suite fail when `_vendor`
   trails a committed source?* If yes, it is ~40 lines plus a scratch-repo test; if no, the
   standing answer is that `ci.yml:75` is the only place the mirror is policed, and §46(3) is
   how to tell the two kinds of red apart.

## §48 The remote confirmed §46's prediction, and disagreed with the dispatch on one gate's scope

1. **Prediction tested against the thing itself.** §46(3) claimed `ci.yml:75` would be green
   on the pushed tree even though local `--check` is red; that was an inference from comparing
   committed blobs, so it was checked rather than kept. Run `36301971185` on `f8a2ad0` —
   `status=completed`, `conclusion=success`, jobs `ci` and `web-regression` both `success` —
   and the step's own line, verbatim from the remote log:

   ```
   Run uv run python scripts/sync_vendor.py --check
   OK: vendored dsa_* is in sync
   ```

   alongside `All checks passed!`, `Success: no issues found in 112 source files`, and
   `Required test coverage of 79.0% reached. Total coverage: 80.48%`. So the D-L1-02 lane is
   pushed and green on the remote, which is the first time in §41–§48 that the claim has an
   external witness rather than my own machine.
   Note the coverage number: 80.48% on Linux against 80.52% locally, same commit. That is not
   drift, it is platform-gated branches, and it is worth remembering when a lane quotes
   coverage as if it were a single number.

2. **A gap in the dispatch's own gate list, found by reading the remote's output.** §41(5)(d)
   and the L3 brief tell the lane to run
   `uv run ruff format --check packages apps/api tests src apps/jupyter` — **without**
   `scripts`. `ci.yml:85` runs it *with* `scripts`. Measured at `f8a2ad0`: the dispatch form
   reports 184 files, CI's form reports 195; both rc=0, so nothing shipped unformatted and no
   correction to §42–§47 is needed. The finding is about the instrument, not the tree: a lane
   that adds or edits a file under `scripts/`, follows the dispatch's command list to the
   letter, sees green, and pushes will get a remote red on a check it never ran. §46(5) is the
   live example of exactly that exposure — the parity script I wrote and removed was linted
   against `scripts` by luck of the `ruff check` line, and `ruff format --check scripts` was
   run only because I was checking whether to keep it.
   Cheapest fix, and it is a documentation edit rather than a code one: make the dispatch and
   any AGENTS-side gate list quote `ci.yml:84-86` verbatim, or have Appendix B's `# --- gates
   (§23) ---` block carry `scripts` on both ruff lines. Whoever owns that prompt document should
   do it; L3 did not edit `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` because it is another
   session's untracked file at this moment.

3. **One process error of mine, recorded because it cost the repo compute.** I pushed three
   times in a row (resync, §46, §47). `ci.yml`'s concurrency group cancels in-progress runs, so
   the first two runs were killed partway — `cancelled` shows in the run list for both — and the
   resync's CI verification had to be re-done by the third. The lane's own rule is "commit the
   ledger with the work": batching the ledger commit *before* pushing would have spent one CI
   run instead of three, and the second push was the one that actually destroyed the evidence
   the first push existed to produce.

4. **Where the lane stands, unchanged by the push.** D-L1-02 is 27 of 35, open; `packages/
   evaluation`'s 8 sites still sit behind another session's working copy. D-L3-04 remains
   partially mitigated — mode (b) closed by `2ed7a90`, mode (a) open, and the §43(2)
   reproduction still prints `run2 == run1 (stale) : True` against the pushed tree. D-L3-01's
   pin, D-L3-03's `passed: True`-on-error handlers, the `plugins`/`execution` dead exclusions,
   and §46(5)'s "should the local suite police the mirror?" question are all still open, and
   §47(5) still holds the decision on that last one.

## §49 The fact mechanism landed, and it immediately caught its own author twice

This is not a lane. It records the infrastructure the v2 prompt's §3/§4/§20.0
mandated, because the alternative was a mechanism with no written provenance.

**What shipped** (`git log --oneline -9`, one path per commit): `scripts/audit_facts.py`
(runtime collector, stdlib-only, ~0.8s, no subprocess), `docs/audit/facts.limits.json`
(14 ceilings + 1 floor + 11 excluded-with-reason), `tests/unit/test_debt_ratchet.py`
(11 tests, the second consumer), the `.gitignore` line for the derived snapshot, and the
rewritten `REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md` at 1128 lines against v1's 1129.

**Baseline for the next session, all from the collector, not typed from memory:**
run `uv run python scripts/audit_facts.py --check` and `--write`, and read
`docs/audit/facts.snapshot.json`. Every number this entry would otherwise have
frozen is in that snapshot with its `generatedAt` and ref — which is precisely the
mistake §49 would have repeated.

**Two findings about the instrument, both self-inflicted and both fixed:**

1. `D-INFRA-01` — the collector indicted its own source. Its regex literals scored as
   the repository's entire debt-marker count (reported 8, real 0) and it listed itself
   among the unwired checkers. Tier T0: `--seed` refused, then `command -v`-free reading
   of the shipped tree confirmed 0. Fixed by `SELF` exclusion, and the rule is now written
   into the prompt's §3 ("the instrument never measures itself").
2. `D-INFRA-02` — a ceiling whose only exits were "stop recording" or "delete other prose"
   (`debt.auditApparatusLines` = 3112 = ledger + prompt, seeded at the exact sum, so a
   mandated §6.2 ledger entry breached it on arrival). Approved as option A: the key now
   covers prompt/spec documents only; ledger volume is `debt.ledgerLines`, measured and
   reviewed but not gated. Ceiling moved 3112 → 1128, a tightening.

**Contamination caught before it could bite CI.** Re-seeding floors off this working tree
reported `debt.testFunctions` 423; a pristine `git archive` export of HEAD reads 420. The
gap is another session's uncommitted tests. A floor above what CI can check out is a
guaranteed false red, so it is pinned to 420 and the divergence is recorded in `_seedNote`
alongside `capabilities.packagesWithoutManifest` (1 here, 0 clean — untracked dir).
Method: `git archive HEAD | tar -x -C /tmp/x && cp scripts/audit_facts.py /tmp/x/scripts/`.

**Every guard here was shown capable of failing, per §11.3** — the prompt's own rule,
applied to the prompt's own author: mutating `evaluate_ratchet` to always return clean
turns 3 tests red; disabling `numeric_leaves` turns 4; emptying the seed-preservation
block turns exactly 1; redefining one ceiling reason in code only turns exactly the
register-drift test. Unmutated: 11 green.

**Deliberate non-actions.** `sync_vendor.py --check` is red (1 file under `dsa_evaluation`)
and I did **not** resync it — that is §7 class-(c) derived drift caused by another session's
uncommitted `packages/evaluation/.../external_validation.py`; resyncing would ship their
semantics under my message. No push (L10). No workflow edit (L7): the one-line CI wiring is
prepared and verified green against a clean export, and awaits its own approval.

**Open decisions.** (1) Wire `audit_facts.py --check` as the first step after `uv sync` in
`ci.yml` — until then the ratchet is local-plus-pytest only, and `debt.unwiredCheckers`
correctly still counts `scripts/check_public_claims.py` as the ledger's pre-existing finding.
(2) §46(5)'s "should the local suite police the mirror?" question, which this mechanism
reopens from the other side: it now can, if the mirror parity keys are wired in.

## §50 The ratchet is wired into CI, and §49's reason for waiting was false

`ci.yml` gained one step, `uv run python scripts/audit_facts.py --check`, placed after
`uv sync --dev` and before ruff/mypy/pytest/wheel/container builds. §49's open decision
(1) is therefore closed, and §49's stated reason for deferring was wrong:

- **Claimed in §49:** wiring it would make the first run red because `sync_vendor --check`
  is already rc=1.
- **Measured now:** that rc=1 is a *working-tree* artifact of another session's uncommitted
  `packages/evaluation/.../external_validation.py`. A pristine `git archive` export of HEAD —
  what the runner checks out — prints `OK: vendored dsa_* is in sync` at rc=0, because
  `dd8d3c9` already resynced the mirror. The premise for waiting did not survive contact
  with the export, so the wait was withdrawn rather than quietly dropped.

**Runner-shaped conditions actually exercised, not assumed.** A detached HEAD with a real
`.git/HEAD` (what `actions/checkout` produces) was simulated: head resolves, branch reports
`(detached)`, `commitStampAgeDays` degrades to `None` instead of raising, and `--check` exits
0 with 3 warnings against a ceiling of 4. `capabilities.packagesWithoutManifest` is empty
there — the runner cannot see an untracked directory — which is the divergence §49 recorded.

**Verified static:** the added step interpolates nothing, and no `run:` step in any workflow
here interpolates `github.event`, `inputs`, or dispatch payload values.

**Still a simulation, not the runner.** The remote witness arrives only on push, which has not
happened and needs its own approval.

**One gate derivation, one owner:** §26's derivation command now surfaces this gate
automatically, which is the point of deriving rather than copying — a prose gate list would
have silently gone stale again the moment this step landed.

## §51 Lane L2 — status and claim correctness (first run of this lane; census said 0 ids)

Census before enumerating (`grep -ohE 'D-L[0-9]+-[0-9]+' AUDIT_LEDGER.md | sort -u`): L1 16,
L3 5, **L2/L4/L5/L6/L7/L8 zero**. L2 was unexamined, not clean. Independent enumeration was
written before re-reading the prompt's §34; refutations of my own seeds are in 51.4.

### 51.1 Findings

### D-L2-01
| field | value |
|---|---|
| claim | Terminal status is computed from one check name, so a run whose evidence, claim and tool checks all failed still reports `COMPLETED`. |
| lane | L2 |
| evidence_tier | T0 |
| severity | S0 |
| location | `packages/agent/src/dsa_agent/graph.py:612-613` |
| mechanism | `has_hard_fail = any(not r.passed for r in state.validation_results if r.check == "budget")`. Shipped code emits **nine** distinct check names (`budget`, `completeness`, `evidence_bundle`, `evidence_coverage`, `langgraph_fallback`, `prompt_injection`, `resource_limits`, `tool_errors`, `unsupported_claim`); eight of them cannot influence status. So both halves of the product promise — evidence-verified claims and reproducible output — are computed, recorded, displayed in the report, and then never consulted at the single point where success is decided. |
| probe | enumerate `check="…"` across `packages/`+`src/` (excluding `_vendor`), then apply the shipped filter to real critic output |
| evidence_command | `uv run --frozen python` heredoc in this session: critic executed on three states |
| output_excerpt | `3 failing checks incl. bundle+claims+tools -> status: COMPLETED` (state carried `evidence_bundle`, `unsupported_claim`, `tool_errors` all `passed=False`); `PROBE_RC=0` |
| reproducible | deterministic |
| fix_sketch | Widen the filter to the hard-check set, or invert it (a result is hard unless the check declares itself advisory). Breaks: runs currently reported COMPLETED will report FAILED. |
| blast_radius | SDK + API + CLI + MCP + Jupyter status semantics; every benchmark/leaderboard run; `Analysis.status`; **measured: 2 of 5 real runs flip** (eda-01 `unsupported_claim`, eda-05 `tool_errors`) |
| verify_before | test asserting a run with a failing non-budget check yields FAILED — RED today (status COMPLETED) |
| expected_delta | benchmark `task_success` 1.0 → 0.6 at `--limit 5` if all hard checks gate status |
| ceiling_key | none — a behavioural invariant, not a quantity; needs a test, and §4's floor on test count guards its removal |
| status | open |

### D-L2-02
| field | value |
|---|---|
| claim | The `evidence_bundle` failure record added by `25443fd` has no consumer: it is appended and then ignored by the status computation. |
| lane | L2 |
| evidence_tier | T0 |
| severity | S1 |
| location | `packages/agent/src/dsa_agent/graph.py:597-607` vs `:612` |
| mechanism | The L3 lane converted a silent `except Exception: pass` into a recorded `ValidationResult(check="evidence_bundle", passed=False, …)`. Visibility without enforcement means a run with an unwritten `evidence_graph.json`/`experiment.json`/`reproduce.sh` still ends `COMPLETED`. The fix landed in §45 is therefore half a fix: the signal exists for a human reading the report and for nothing that decides status. |
| probe | read the appended check name, then the filter that consumes it |
| output_excerpt | `checks that cannot change status: [... 'evidence_bundle' ...]`, rc=0 |
| fix_sketch | fold into D-L2-01's widened filter; no separate change needed |
| blast_radius | one predicate; same status semantics as D-L2-01 |
| status | open — **crossover with L3 residual, report as the unfinished half of §45** |

### D-L2-03
| field | value |
|---|---|
| claim | `DSA_EVIDENCE_CRITIC=off` yields `validation_results == []` and `status == COMPLETED`, and the only record that the guarantee was skipped is on a field the public SDK object does not expose. |
| lane | L2 |
| evidence_tier | T0 |
| severity | S1 |
| location | `graph.py:464-471`, `critic.py:16-23`, `src/data_science_agent/sdk.py` (`Analysis` dataclass) |
| mechanism | The ablation is deliberate and documented ("stays enabled by default"), but the outward consequence is silent: `Analysis` fields are `['artifacts','error','evidence','insights','raw_state','report_markdown','run_id','status','tool_calls','validation']` — `agent_messages`, which holds "Evidence critic disabled for evaluation ablation", is **not** among them. A consumer sees `status=COMPLETED, validation=[], error=None`, and `[]` is a valid outcome shape rather than a labelled skip. |
| probe | run the graph path with the env var set, inspect `Analysis` dataclass fields |
| output_excerpt | `ablation flag honoured: True` / `validation_results on the ablated path: []` / `agent_messages exposed outward? False`, rc=0 |
| fix_sketch | emit one `ValidationResult(check="critic_ablated", passed=False)` (or a `skipped` marker) so the emptiness is labelled in the artifact, rather than deleting or hiding the ablation |
| blast_radius | evaluation harness + any caller that sets the env var; no change to default-on behaviour |
| status | open — needs a decision on whether an ablated run should report COMPLETED at all |

### D-L2-04 (instrument, L1/L2 crossover)
`benchmarks/**/raw_runs.json` records each run only under `run_result`; a first-pass script that
looked for a top-level `validation` key returned **"0 runs captured"** and would have reported a
blast radius of zero. The data is present as `run_result.validation_results`. A measurement that
silently returns an empty set instead of failing is the same class as a silent-pass gate.

### 51.2 Lead-register diff
- `critic.py` early-stage vacuous pass — **CONFIRMED but reclassified `PROTECTED`**: `check_evidence_coverage` returns `passed=True` only for `UNDERSTANDING`/`PLANNING`/`DATA_PROFILING`, and returns `passed=False` at `REPORTING` (executed: `evidence_coverage passed=False No evidence collected`). Correct by design; do not "fix".
- repro-bundle writes swallowed by `except Exception: pass` — **REFUTED as stated**: `25443fd` replaced it with a recorded result. Still defective, but as D-L2-02, not as a swallow.
- "the report never surfaces validation" — **REFUTED by my own probe**: `build_markdown_report` does mention `evidence_coverage` and "No evidence". My negative came from grepping `packages/reports/` while the builder lives in `dsa_agent/graph.py`. Wrong location, wrong conclusion.

### 51.3 Law liveness table (this lane)
| law | state | decider |
|---|---|---|
| N1 no excerpt → no severity | ACTIVE | every block above carries rc + excerpt |
| N2 baseline before change | ACTIVE | §20 baseline captured, no edit made |
| N3 red then green | ACTIVE, unexercised | no fix attempted — Phase 2 gate not passed |
| N9 enumerate before reading seeds | ACTIVE | 51.1 written first, 51.2 diffed after |
| §13 measure blast radius before proposing a status change | ACTIVE | 2/5 measured, not assumed |
| §7 tier-before-severity | ACTIVE | D-L2-01 T0→S0; D-L2-03 T0→S1 not S0 (no demonstrated user harm yet) |
| §3 reading-wins precedence | ACTIVE | refuted two of my own premises in 51.2 |

### 51.4 Deliberate non-actions
No file edited under this lane. D-L2-01's fix is a **public status-semantics change** and is
presented for approval, not implemented (§13, §22, anti-pattern A7). `packages/evaluation`
untouched (foreign). No push. Benchmark output written to `/tmp/ci-bench` only; `/tmp` scratch
removed afterwards.

## §52 D-L2-01 fix (a) implemented — verified, and it surfaced two real defects plus one scope limit

Working tree state, **not committed**: `packages/agent/src/dsa_agent/graph.py` + its vendored
mirror + the new test in `tests/integration/test_agent_analysis.py`. Held uncommitted because
the suite is red for a reason that is a decision, not a defect in this change (§52.3).

### 52.1 The change
`HARD_FAIL_CHECKS = frozenset({"budget","evidence_bundle","tool_errors","unsupported_claim"})`
applied at the **terminal** predicate only (`graph.py:612`). Line 474 — the mid-loop retry gate —
was deliberately left on `budget`, because widening it aborts the run *before any report exists*;
that is a larger behaviour change than (a) authorised. The verdict changes, the artifact survives.

### 52.2 Red then green, with exit codes taken from the commands themselves
| step | command | result |
|---|---|---|
| verify_before | `pytest -k flips_terminal_status` | **rc=1** `assert COMPLETED is FAILED` — the earlier `assert failing == ["unsupported_claim"]` and the report-present assertion had already passed, so the failure is my mechanism and not setup noise |
| verify_after | same | rc=0 |
| pinned ablation guard | `pytest tests/test_critic_ablation.py` | rc=0 — the `COMPLETED`-when-critic-off pin is preserved |
| lint / format / types | ruff check, ruff format --check, mypy | rc=0, rc=0 (197 files), rc=0 (112 files) |
| mirror | scoped regeneration of `dsa_agent` only | `sync_vendor --check` rc=1 naming **only** `dsa_evaluation` (foreign WIP); my package reports in sync |

Scoped regeneration was necessary, not convenient: `sync_vendor.py` exposes only `--check` and a
bare run `rmtree`s and recopies **every** package, which would have pulled another session's
uncommitted `dsa_evaluation` code into the shipped mirror under my commit message. **Finding
D-INFRA-05:** the tool has no per-package repair mode, so a one-package change cannot be
regenerated without adopting unrelated dirty state.

### 52.3 What the widened predicate surfaced (two real defects, one test that encoded the bug)
`tests/plugins/test_time_series_plugin.py::test_full_pipeline_..._integration` now fails:
`assert r.status in ("COMPLETED","REPORTING")` got `FAILED`. Reproduced against the live source
with the test's own dataset (`benchmarks/v2/datasets/sales.csv`, verified present, 17894 bytes):

- `tool_errors passed=False — 4 tool error(s)`, namely
  `train_model: Non-numeric features: float() argument must be a string or a real number` and
  `export_artifact: csv/xlsx export needs source with columns+rows`, each twice.
- `evidence_coverage`, `unsupported_claim`, `budget`, per-insight and per-evidence checks all passed.

So the status flip is **correct**: that flagship integration run has been failing four tool calls
all along, and the test passed only because nothing consulted the signal. Recorded as
`D-L2-05` (train_model on this dataset) and `D-L2-06` (export_artifact unresolved source), both
S1, both in `packages/tools`/`dsa_time_series` — outside the scope of (a).
The test itself was pinned on the bug; relaxing it is **not** taken here (§N6).

### 52.4 Correction to §51's numbers — my own instrument undercounted
§51 said "nine check names, eight cannot change status", derived from grepping `check="…"`
literals. An AST pass over `ValidationResult(...)` constructions gives **8 literal names and a
tail of names built at runtime**, and the executed run emitted `insight_evidence`,
`evidence_traceability` and `dataset_hash`, which appear nowhere as literals. So the real universe
is ≥11, and the honest statement is: after (a), four named checks gate status while
`evidence_coverage`, `dataset_hash`, `insight_evidence` and `evidence_traceability` still cannot —
including the reproducibility chain's own dataset identity.

**This is an argument for shape (b) (hard unless declared advisory) over the approved (a):** a
name list silently omits every check that does not exist yet, and dynamic names cannot be
enumerated from source at all.

### 52.5 Method errors of mine, recorded because they cost real detours
- Reported `PROBE_RC=0` for a selection that matched **zero tests**, then read `tail`'s exit code
  as pytest's — the exact pipe mask §26 names. Re-ran with the code taken from pytest itself.
- First reproduction passed `tests/fixtures/revenue.csv`, a path I invented, and reported its
  "File not found" tool errors as the repo's. The test's real dataset is
  `benchmarks/v2/datasets/sales.csv`; re-ran against it.
- A probe importing `data_science_agent` resolved `dsa_agent` from `_vendor` and reported
  `COMPLETED` for code I had already changed. In a shared tree with a demoted mirror, *which copy
  you imported is part of the measurement*, and I had not stated it.
- A `timeout` prefix was used on a host without it (rc=127), silently skipped.

## §53 D-L2-05 fixed and landed; D-L2-06 is a Proposed-ADR gap, not a bug I may close alone

### 53.1 D-L2-05 — landed as `c6e5e8b`
`train_model` selected every non-target column and then `astype(float)`, so an ordinary CSV
whose `date` column the loader parses as temporal failed the whole step. No existing test
covered mixed dtypes (`tests/unit/test_tools.py` used an all-numeric frame). Now numeric-only,
with dropped columns reported in `diagnostics.excluded_non_numeric` rather than quietly omitted.
Red first (`rc=1`, exactly the `datetime.date` message) then `rc=0`; 16 tools tests green
including the untouched all-numeric one; ruff/format/mypy rc=0; mirror regenerated for
`dsa_tools` alone. **The commit was verified in isolation**: a `git archive` export of HEAD
runs `tests/plugins` + `tests/unit/test_tools.py` at rc=0 and still contains zero
`HARD_FAIL_CHECKS`, proving the dtype fix does not depend on the held (a) change.

### 53.2 D-L2-06 — the root cause is a phantom capability, and it is not in `export_artifact`
`export_artifact` behaved **correctly**. Its contract says "Byte-identical relocation only —
never synthesizes content" (`export_artifact.py:50-52`), and it refuses a source lacking
`columns`+`rows`. Measured against the output models of everything the planner declares
tabular (`_TABULAR_TOOLS`):

| declared tabular | emits `columns`+`rows`? | note |
|---|---|---|
| `run_sql` | YES | the only conforming entry |
| `train_model` | no | fields: cv_mean, cv_scores, cv_std, diagnostics, features, model, n_rows |
| `evaluate_model` | no | confusion_matrix, metrics, task… |
| `forecast` | no | date_col, forecast, metrics, periods… |
| `feature_importance` | no | **emits base64_png — it is a chart tool, declared tabular** |
| `regression_analysis` | no | coefficients, intercept, metrics… |

Isolated from the dtype bug: an **all-numeric** dataset with a "predict y from a and b" query
still ends `FAILED`, with `export_artifact: csv/xlsx export needs source with columns+rows`,
because the hint `("predict","classif","churn","survival") → predictions.csv ← train_model`
pairs a filename with a source that can never satisfy it. Every plan matching
predict / evaluate-metrics / normalize keywords therefore carries a **guaranteed-failing step**.

Four sources disagree about this capability, and only the runtime tells the truth:
`docs/ADR/ADR-002-output-artifact-export-2026-09-08.md` is **Status: Proposed** and states the
gap plainly ("tool results stay in memory; only charts persist as files today"); the planner
behaves as if delivered; the tool output models say non-tabular; and
`tests/unit/test_export_artifact.py:143-144` **pins** the phantom pairing
(`by_name["predictions.csv"]["source"] == {"$from_tool": "train_model"}`).

### 53.3 Why (a) is held uncommitted
With `HARD_FAIL_CHECKS` active, that long-invisible failing step becomes a reported run failure
for predict / evaluate intents — which is exactly what the fix is for, and also a user-visible
status change beyond what §52 authorised. `tests/plugins/...integration` is red for this reason
alone. The three files stay modified in the working tree (`graph.py`, its mirror, the new
integration test) and are not committed, because §19.2 forbids clearing that red by relaxing the
pinned test or narrowing the predicate as a way to get green.

### 53.4 Decision required — three shapes, different cost
| option | what it is | what it costs |
|---|---|---|
| **I implement ADR-002's producing side** | the five tools gain tabular projections of results they already computed (a representation, not invented content) | largest change; touches five output models + their mirror; the ADR is still `Proposed`, so this is shipping a feature under a fix label |
| **II shrink `_TABULAR_TOOLS` to what conforms** | the planner stops emitting a step that can only fail; truth-telling, ~10 lines | removes an export that never worked; **requires editing a pinned assertion** at `test_export_artifact.py:143-144`, which is §N6 territory unless you rule that the pin encodes the defect; "predict and export" users get no CSV instead of a failing CSV step |
| **III land (a) now, accept the red plugin test** | status honesty first, D-L2-06 tracked as its own S1 | main's suite is red for a known, documented reason; contradicts §30's "only gates that actually ran are reported" |
My recommendation is **II**, because a declared-but-impossible capability is the defect this
document's L7 lane exists to catch, and deleting a step that cannot succeed restores the truth.
If you want the *feature* rather than the truth-correction, that is option I and should be
approved as ADR-002 implementation, not as a bug fix.

## §54 D-L2-06 and (a) both landed; the benchmark headline metric is the next honest gap

### 54.1 D-L2-06 — `a0dc728`
Derived rather than hand-curated: measured every registered tool's output model against
`_TABULAR_TOOLS`. Only `run_sql` emits `columns`+`rows`; `export_artifact` itself does but is
self-referential, and `feature_importance` was declared tabular while emitting `base64_png`.
Shrunk the list and removed the two hints that became unreachable, so no plan can carry a step
that only fails. `test_planner_export_steps_conventional_names` was updated because it pinned the
phantom pairing; the replacement asserts the invariant, exercises the tabular branch directly
through `_terminal_export_steps` (heuristics never emits `run_sql`, so routing it through the
planner would have left the assertion silently unrun — a vacuous guard), and adds the structural
test `test_declared_tabular_sources_really_are_tabular` that fails on any future non-conforming
entry. Red first: rc=1 naming `train_model`'s field list.

### 54.2 (a) — `4ba4c2f`
`HARD_FAIL_CHECKS = {budget, evidence_bundle, tool_errors, unsupported_claim}` at the terminal
predicate only. Line 474's retry gate deliberately unchanged: widening it aborts runs before any
report exists, which trades a wrong verdict for a missing artifact and was not what was approved.

### 54.3 The blast radius reversed, and what that means
| measurement | before the two tool fixes | after |
|---|---|---|
| benchmark runs flipping COMPLETED → FAILED at `--limit 5` | 2 / 5 | **0 / 5** |
| `task_success_rate` | 1.0 | 1.0 |
| eda-01 (genuine `unsupported_claim` failure) | reported COMPLETED | **reports FAILED** |

The 2/5 I reported in §51 was never "the predicate is too strict" — it was two real defects the
predicate had been ignoring. Fixing causes first, then tightening the verdict, produced honesty
without regression. That ordering is the reusable lesson: a blast-radius number measured over
unfixed defects argues for the wrong conclusion.

### 54.4 New finding, recorded not fixed
### D-L2-07
| field | value |
|---|---|
| claim | The benchmark's headline success metric never consults the run's status, so it reports 1.0 over a run the agent itself marks FAILED. |
| lane | L2 / L7 crossover |
| evidence_tier | T0 |
| severity | S1 |
| location | `packages/evaluation/src/dsa_evaluation/metrics.py:68-77` |
| mechanism | `status` is read at line 68 and assigned at 70, then never referenced again (the only other `status` reads are `c.get("status")` on individual tool calls, lines 72/161/172). `task_success = bool(has_ok and (has_report or tcalls))` therefore means "some tool worked and something came out", which is true of a failed run. `catalog.py:34` additionally defaults `task_success: bool = True`. |
| probe | run `dsa --limit 5`, compare `run_result.status` per task against `summary.json.task_success_rate` |
| output_excerpt | `eda-01 status=FAILED …` alongside `Task success rate: 1.0`, `BENCH_RC=0` |
| reproducible | deterministic |
| blast radius | `benchmarks/leaderboard/leaderboard.json` `task_success_rate`, `benchmarks/baseline/results.json`, the `benchmarks/baseline/README.md:26` CI tolerance ("any PR that drops task_success_rate … fails CI") — i.e. the tolerance rule guards a metric that cannot fall |
| fix_sketch | derive `task_success` from status (or add a separate `agent_status_ok` metric and keep both, stating which one the tolerance rule polices). Not taken: it changes published baseline/leaderboard numbers and touches `packages/evaluation`, which currently holds another session's uncommitted file. |
| status | open — needs a decision, and a re-baseline of `benchmarks/baseline/` if taken |
| ceiling_key | `floor.testTotal` style not applicable; needs the leaderboard's honest-by-design labelling (§32.3) preserved |

### 54.5 Deliberate non-actions
`packages/evaluation` untouched (foreign WIP). No push. Mirror regenerated per package only
(`dsa_tools`, `dsa_agent`), never wholesale. Commit `a0dc728` verified standalone on a
`git archive` export (49 tests rc=0, zero `HARD_FAIL_CHECKS`) before `4ba4c2f` was built on it.

## §55 Verifying on a pristine export caught three defects, two of them mine and one of them a repeat

Everything in §54 was asserted against the working tree. Re-running the same gates on
`git archive HEAD` — what the runner checks out — produced a different verdict, and the
difference was the point.

| failure on the export | real or harness | cause |
|---|---|---|
| `test_debt_ratchet::test_the_ratchet_is_currently_satisfied` rc=1 | **real, mine** | floor seeded to 426 in the dirty tree; a clean checkout reads 424. The +2 is the concurrent session's two uncommitted test functions |
| 18 ruff errors, 3 format diffs | harness | I ran pytest **before** ruff inside the export, and a `git archive` has no `.git`, so ruff could not honour `.gitignore` and linted ~3 generated notebooks my own test run created. CI is unaffected: `ci.yml` lints at :84-85, pytest runs at :87 |
| `test_fresh_clone_workspace_members_are_tracked`, `test_typescript_compiles` | harness | the first shells out to `git ls-files` (no `.git` in an export); the second needs `node_modules`, which `ci.yml:79` installs before pytest |

### 55.1 The floor trap, now caught three times
419 vs 423 in §53, then 424 vs 426 here — each time because `--seed` was re-run locally and
silently re-baked the working tree's reading. A clean measurement on top of a dirty tree is
still dirty. Two remedies, both landed: the floor is set to 400 with the divergence written into
`_floorPolicy`, and the prompt's §4 now states the rule, so the next session is not relying on
my having remembered it.

### 55.2 Mechanism fix, `b612882`
`capabilities.packagesWithoutManifest` counted `packages/artifacts/` — gitignored output the suite
itself writes (786 generated notebooks locally) — as a package missing a manifest, so any local
pytest run reddened the ratchet for a non-debt reason. It now requires the directory to hold
Python source. Falsified in an isolated `/tmp` tree rather than the shared one: a
`packages/zzpkg` with `__init__.py` and no manifest is reported; delete the `.py` and the same
tree reports nothing. `warnings.contradictions` also stopped being a ceiling — a composite counter
trips whenever anyone adds a probe, which is §4's own rule applied to me.

### 55.3 Final state on a clean checkout, in CI's step order
vendor rc=0 · npm lock rc=0 · ruff rc=0 · format rc=0 · mypy rc=0 · ratchet rc=0 **before and
after** the suite · pytest rc=0 (deselecting only the two tests that need `.git` / `node_modules`,
both of which CI provides). Locally all gates rc=0 except `sync_vendor --check`, which names only
`dsa_evaluation` — another session's uncommitted file, and HEAD itself is in sync.

### 55.4 Still open, unchanged by this section
D-L2-07 (benchmark `task_success` never reads status; `metrics.py:68-77`) remains a filed
decision, not a fix. L4-L8 have still never run (§6.4 census). No push at any point, so no remote
witness exists for the CI wiring added in §50 — `ci.yml`'s new step has never executed on a runner.

## §56 Remote witness obtained — the ratchet executed on the runner, in the intended position

Pushed `0a64a72..f9db412` as a **fast-forward** (23 commits, all authored in this session;
`git rev-list --left-right --count origin/main...HEAD` was `0 23` before and `0 0` after). No
force, no rebase, nothing from the concurrent session published.

`gh run watch --exit-status` returned 0: **run 36393018502 completed success**, jobs `ci` (32
steps) and `web-regression` (13 steps). The remote also reported `Required status check "ci" is
expected` — the new step is behind branch protection, so it can now block a merge rather than
merely report.

Evidence from the job's own log, in step order, with runner timestamps:

| log line | step | runner output |
|---|---|---|
| 404 | `uv lock --check` | `Resolved 192 packages in 1ms` |
| 405–416 | **`uv run python scripts/audit_facts.py --check`** | **`facts ratchet: OK`** @ `07:41:41.885Z` |
| 417–428 | `sync_vendor.py --check` | `OK: vendored dsa_* is in sync` @ `07:41:41.967Z` |
| 429–440 | `check_npm_workspace_lock.py` | `Root npm wor…` (matches all manifests) |
| 501–512 | `ruff format --check … scripts` | `197 files already formatted` |
| 513–524 | `mypy packages apps/api src apps/jupyter` | `Success: no issues found in 112 source files` |
| 525–664 | `pytest -q --cov` | `Required test coverage of 79.0% reached. Total coverage: 80.62%` |

Three claims this closes, each of which was previously only an inference of mine:

1. **The wiring is real.** §50's step is not merely present in the YAML — it ran, printed, and
   sat exactly where intended: after dependency install, before lint, types, tests, the wheel
   build and the container builds. A debt regrowth now fails in ~0.2 s of runner time.
2. **The ceilings are CI-valid, not local artefacts.** The floor-margin fix (§55) held on Linux:
   a tree that reads `debt.testFunctions` 424 there passed against a floor of 400. Had I shipped
   the seeded 426, this run would have been red and I would have been reporting a failure of my
   own making.
3. **`sync_vendor` rc=1 was never a repository condition.** Confirmed on the runner: in sync. The
   red I reported in §48/§49 existed only because of another session's uncommitted file.

New datum worth keeping: **coverage is 80.62% on Linux against 80.52% locally at the same
commit**. Not drift — platform-gated branches, which is precisely why §25.3 forbids citing
coverage as a single number without ref, platform and command. The `fail_under = 79` gate has
~1.6 pt of headroom on the runner and ~1.5 pt locally; both figures are readings, and §3 says to
re-measure rather than quote either.

Not done by this: D-L2-07 is unchanged and now sits on `origin/main`, so the published branch
carries a filed-but-open defect where the benchmark headline metric cannot fall. L4-L8 have still
never run.

## §57 D-L2-07 fixed — and the mirror told me my unit tests were measuring the wrong copy

`c1c7680`: `task_success` now requires the run's own verdict not to be a failure. Measured effect:
`dsa --limit 5` `task_success_rate` **1.0 → 0.8**, with eda-01 dropped on its merits — its
`unsupported_claim` check fails, and since `4ba4c2f` the run reports `FAILED` for it.

Semantics, stated rather than implied: a **present** status must not signal failure; an **absent**
status is not treated as failure (callers legitimately pass partial summaries, and inventing a
failure from missing data is the error direction this project exists to avoid).
`code_execution_success` still measures execution alone, so "a tool ran" and "the run succeeded"
remain separate claims instead of collapsing into one number.

### 57.1 The finding that matters more than the fix
Unit tests were green against live source while the `dsa` console script kept printing `1.0`. Cause,
demonstrated by order-sensitive import rather than by reading:

```
import data_science_agent, dsa_evaluation.metrics  ->  src/data_science_agent/_vendor/dsa_evaluation/metrics.py
import dsa_evaluation.metrics, data_science_agent  ->  packages/evaluation/src/dsa_evaluation/metrics.py
```

The façade inserts `_vendor` at `sys.path[0]`, so **the same import resolves to two different files
depending on who got there first**. Any fix to a workspace package is therefore inert for the
console-script and installed-wheel path until the mirror is regenerated — which is §13's and
§26's "reproduce the CI job, not your local habit" made concrete, and the reason
`sync_vendor --check` is the first CI step rather than a courtesy.

Mirroring had to be per-file: `sync_vendor` offers no `--package`/`--file` mode, and a bare run
would have copied another session's uncommitted `external_validation.py` into the shipped mirror.
Drift went 1 file → 2 → 1 as expected, and the rate moved the instant the mirror matched.
**D-INFRA-05 stands**: the tool needs a scoped repair mode; hand-copying is not a substitute.

### 57.2 Consequence I did not silently resolve
`benchmarks/baseline/summary.json` is frozen at `task_success_rate: 1.0` under the **old**
evaluator, and `tests/regression/test_regression_matrix.py::test_baseline_contract` asserts that
stored figure — it reads the snapshot, it does not recompute. So the test passes while the metric
it pins is now produced differently: the tolerance rule in `benchmarks/baseline/README.md` has gone
from "cannot fall" to "would fall if re-measured", and nothing re-measures it.

`docs/reproducibility.md:44` says these baselines are pinned and **changes require a version bump**,
which §27 lock **L7** puts out of my authority. So this is a decision, not a task:
(α) re-run the 50-task benchmark and re-freeze under a version bump — honest, and the published
number will drop; (β) leave the snapshot and annotate it as pre-§57-evaluator — cheap, and the
staleness is then at least declared; (γ) make the regression test recompute instead of reading the
file — that removes the freeze's purpose, so it needs its own argument.
Recommendation **(β) now, (α) with the next release**, because pinning a pre-change measurement and
saying so is honest, whereas silently re-freezing to a lower number under a fix commit is not.

### 57.3 State
Gates on the committed tree: ruff 0 · format 0 · mypy 0 · pytest 0 · ratchet 0 · vendor 1
(`dsa_evaluation`, the foreign file only). Lanes still unrun: L4–L8. Nothing pushed since §56's
witness, so `c1c7680` has no remote verdict yet — and it should, because it is the first change in
this series whose correctness depends on the mirror rather than on the source.

## §58 Remote witness for the metric fix; β landed; the exit-code trap fired twice on my own wrapper

### 58.1 `9754e8b` verified on the runner, not inferred
`gh run watch --exit-status` reported **0**, and independently the API reports `RUN completed
success` with both jobs `completed success`. Step evidence, with runner timestamps:

```
08:40:14.860  audit_facts --check      -> facts ratchet: OK
08:40:14.931  sync_vendor --check      -> OK: vendored dsa_* is in sync
08:40:36      ruff format / mypy       -> 197 files / no issues in 112 files
08:41:18      pytest --cov             -> coverage floor reached
08:41:23      Build wheel and sdist    -> Successfully built …whl
08:42:34      docker run dsa-api:ci .venv/bin/dsa --help
```

That is the first time this series' changes have been exercised through the **installed artifact and
containers**, not just the source tree — which is the only place the mirror semantics of §57 can
actually be falsified.

### 58.2 Two reporting errors of mine, both the same class
The earlier "CI came back green" was wrong, twice over:
1. I read the background task's reported exit code, which was my wrapper's **last** stage
   (`gh run view`, or `echo`) — not `gh run watch`'s. The watcher had actually died with rc=1 on a
   network read error (`can't assign requested address`, the proxy's fake-IP range) while `ci` was
   still in progress. A proxy failure was about to be reported as a pipeline verdict.
2. The fix is structural, not careful: every watcher now captures its own code into a named
   variable (`W5_REAL=$?`) and the authoritative conclusion is re-read from the API, so a green
   wrapper can no longer be mistaken for a green run.

Also caught in verification: I cited `docs/reproducibility.md §"Immutable baselines"` — the heading
is **§Immutability**. Wrong anchor, fixed before shipping.

### 58.3 β — `e86cb12`, pushed as `9754e8b..e86cb12`
`benchmarks/baseline/README.md` now declares which evaluator produced the frozen `1.0` and states
that a lower measured number is honesty rather than regression, with the command to reproduce it.
Existing claims were left intact, not softened — rewriting "fails CI" into something vaguer would
have been anti-pattern A8. Two scope limits verified rather than assumed: the regression test
compares the **stored** file and nothing in CI recomputes the snapshot; re-freezing needs a version
bump under §Immutability. mkdocs `--strict` rc=0, `pytest tests/regression` rc=0,
`check_public_claims` rc=0.

§58's own ledger entry is committed locally and deliberately **not pushed yet**: pushing now would
trip `ci.yml`'s `cancel-in-progress` and destroy the run watching `e86cb12`, which is the exact
mistake §48(3) recorded.

## §59 Lane L4 — architecture, boundaries, duplication (first run; census said 0 ids)

Census before enumerating: L1 16 · L3 5 · **L2 now 7, L4–L8 zero**. L4 was unexamined.
All findings below were derived from the tree by the probes named in each row; §34 was read after.

### D-L4-01
| field | value |
|---|---|
| claim | The installed and console-script runtime is entirely the vendored mirror, and which copy a module resolves to depends on import order — so a source edit can be inert while tests stay green. |
| lane | L4 | evidence_tier | T0 | severity | S1 |
| location | `packages/mcp/src/dsa_mcp/adapter.py:528`, `packages/evaluation/src/dsa_evaluation/cli.py:382,410`, `packages/evaluation/src/dsa_evaluation/external_benchmark.py:298` |
| mechanism | Four workspace modules import the published façade `data_science_agent`, whose import inserts `_vendor` at `sys.path[0]`. A workspace package therefore imports its own vendored duplicate. Measured in a façade-first process: `dsa_evaluation.cli`, `dsa_evaluation.metrics` and `dsa_agent.state` all resolve under `_vendor`. This is not a bug in the arrangement — the single-wheel install is the point (§13.1, `PROTECTED`) — it is the arrangement's cost, and §57 already paid it: a fix to `metrics.py` had zero effect on `dsa` until the mirror was regenerated. |
| probe | `uv run python -c "import data_science_agent, dsa_evaluation.metrics as m; print(m.__file__)"` vs the reverse order |
| output_excerpt | `cli -> VENDOR …/\_vendor/dsa_evaluation/cli.py`, `metrics -> VENDOR`, `dsa_agent.state -> VENDOR`; `AnalysisStatus is alt.AnalysisStatus -> False`; `isinstance(...) -> False`; `== -> True`; rc=0 |
| reproducible | deterministic |
| blast radius | every shipped path (wheel, `dsa`, Docker, Render runtime); no test-tree effect |
| fix_sketch | The identity half is currently latent: shipped code performs no `is`/`isinstance` comparison on these models (probe below returned nothing), so no behavioural bug to fix today. The actionable part is defence: mirror parity is guarded only by `sync_vendor --check` + the clean-install smoke, and **D-INFRA-05** (no scoped repair mode) makes the safe update path awkward. |
| status | open — recommendation is a §4 ceiling on the *gap*, not a redesign of vendoring |

### D-L4-02
| field | value |
|---|---|
| claim | `dsa_execution` and `dsa_tools` depend on each other at package level, because a shared leaf type lives inside one of the two cyclic members. |
| lane | L4 | evidence_tier | T0 | severity | S3 |
| location | `dsa_execution/sql_guard.py:5` and `python_sandbox.py:11` → `dsa_tools.errors.ToolExecutionError`; `dsa_tools/tools/run_sql.py:12` and `run_python.py:10` → `dsa_execution.{sql_guard,python_sandbox}` |
| mechanism | Package-granularity cycle, **not** an import cycle: `dsa_tools/errors.py` imports nothing (verified), so no deadlock is possible and none is observed. The seam that is missing is a leaf for the error type both sides need; today `dsa_execution` must reach "down" into `dsa_tools` for it, which is what closes the loop. |
| probe | grep the four edges above, then `grep -c dsa_execution packages/tools/src/dsa_tools/errors.py` → 0 |
| blast radius | any split or re-ordering of the two packages; dependency-direction docs |
| fix_sketch | move `ToolExecutionError` to a leaf module (own package, or an existing lower layer) and have both sides import the leaf. Behaviour-preserving, touches imports in ~5 files + both `pyproject` dependency lists. |
| status | open — Phase 4 candidate, not this run |

### D-L4-03
| field | value |
|---|---|
| claim | `langgraph_graph.py` is 513 lines of engine that nothing in `src/`, `apps/` or `packages/` can reach, yet it is a coverage source and is imported by one test — coverage bought from code no user executes. |
| lane | L4 | evidence_tier | T0 | severity | S1 (L1/L4 crossover) |
| location | `packages/agent/src/dsa_agent/langgraph_graph.py`; importer `tests/unit/test_langgraph.py:12,30` |
| mechanism | Zero references outside the file itself (grep over `src apps packages` returned none). Running its only test with `--cov=dsa_agent` attributes 228 statements and leaves 36% covered, with a contiguous `221-395` block never executed at all. So the file both occupies a coverage denominator and reports protection for a path no product surface can enter. |
| probe | `grep -rn 'run_analysis_langgraph\|build_graph' --include='*.py' src apps packages --exclude-dir=_vendor`; then `pytest tests/unit/test_langgraph.py --cov=dsa_agent --cov-report=term-missing` |
| output_excerpt | `langgraph_graph.py 228 142 30 6 36% … 221-395, 418, 443-490`; `FAIL Required test coverage of 79.0% not reached. Total coverage: 54.26%` — that rc=1 is the narrowed `--cov` scope tripping the global floor, not a test failure, and was checked rather than assumed |
| fix_sketch | either wire it as a real alternative engine behind a documented switch, or classify it as an experiment and move it out of the coverage source. **Deletion is `BLOCKED`** (L5 lock: coupled workspace/coverage/exclusion edits). |
| status | open — needs the question "is this a planned surface or dead mechanism?", which is a decision, not a fix |

### D-L4-04 / D-L4-05
Stub packages: `dsa_ml`, `dsa_reports`, `dsa_viz` ship 1 module each, `dsa_statistics` and `dsa_llm` 2 — all declared workspace members and coverage sources. `packages/artifacts/` holds 0 tracked files and is not a Python package. Largest shipped modules: `sdk.py` 680, `dsa_evaluation/cli.py` 665, `dsa_agent/graph.py` 625, `planner.py` 621, `dsa_mcp/adapter.py` 606. Recorded as S3 with no line-count-only finding: a split needs the seam named first (§15.3), which belongs to Phase 4.

### 59.1 Lead-register diff
- two engines, one possibly dead — **CONFIRMED and strengthened**: unreachable from any shipped surface, not merely "reached only by a test".
- `dsa_tools ↔ dsa_execution` cycle — **CONFIRMED but reclassified**: package-level only, no import cycle, so the honest severity is S3 not S1.
- stub packages — **CONFIRMED**.
- `_vendor` consequences — **CONFIRMED with a new mechanism** (§57's order-sensitive resolution) that v1 did not describe.
- "façade import triggers a bootstrap that breaks something" — **NOT REPRODUCED** as a failure; the bootstrap is what makes single-wheel install work. `PROTECTED`.

### 59.2 Self-review
My own `tests/integration/test_agent_analysis.py` asserts `state.status is AnalysisStatus.FAILED` — an identity comparison on a model class that has two possible identities. It is correct only because root `conftest.py` demotes `_vendor`; under the installed path it would be comparing a different class object. `==` is the safe comparison here; recorded so the next lane does not copy the pattern into shipped code.

### 59.3 Law liveness, this lane
| law | state | decider |
|---|---|---|
| §15.1 audit consequences, not existence of the mirror | ACTIVE | D-L4-01 kept `PROTECTED` for vendoring itself |
| §15.3 a line count is not a finding; name the seam | ACTIVE | D-L4-02 names the leaf-type seam; D-L4-05 explicitly deferred for lacking one |
| §9 tier before severity | ACTIVE | D-L4-02 downgraded to S3 once measured as non-import cycle |
| §7.2 attribute unexplained red before reporting it | ACTIVE | the `rc=1` above was proven to be the coverage floor, not a failure |
| §11.1 three strikes | ACTIVE, unused | every seed above resolved by first or second probe |

### 59.4 Non-actions
No file edited in this lane; all five findings stop at the Phase 2 gate. `packages/evaluation` and `tests/evals` read but untouched (foreign WIP). L5–L8 still unrun. No push in this turn.

## §60 L4 closed as diagnosis — one defence landed, one finding declined on cost, one awaiting a product answer

### 60.1 Landed
- **D-L4-01 defence** (`43c069c`): `tests/unit/test_vendor_parity.py` makes a stale mirror fail local
  `pytest`, not only the CI integrity step. Per-file scope; each case asserts it compared ≥1 file.
  Negative control by injecting drift into one mirror file → rc=1 naming `dsa_ml/__init__.py`, restored
  byte-identical from a `/tmp` copy (never `git checkout`; shared tree).
- **§59.2 self-review** (`29ab14c`): the status assertion I wrote last lane now compares by value.
  Negative control by narrowing `HARD_FAIL_CHECKS` to `{budget}` → rc=1, proving the rewrite still
  bites; `graph.py` restored byte-identical and clean.

Full gates after both: ruff 0 · format 0 · mypy 0 · pytest 0 · ratchet 0 · leaderboard 0.

### 60.2 Declined, with the price stated
**D-L4-02** — I recommended doing it, then measured the work instead of assuming it, and the
recommendation was wrong. `dsa_tools/errors.py` already imports nothing, so it *is* a leaf module;
the cycle exists only because package = distribution unit. Removing it means a new workspace
member (`[tool.uv.workspace]`, `[tool.uv.sources]`, both dependency lists, the coverage `source`
list, `sync_vendor.SOURCES`, and the coupled exclusions). Spending a ≤2-per-session structural
budget on an **S3 with no behavioural consequence** is a bad trade, so it is recorded as Phase 4
uplift, not fixed here. Cost of the deferral: the two packages cannot be split, versioned or
reasoned about independently, and any future reader re-derives the "is this a real cycle?"
question this lane just answered.

**D-L4-01 redesign** — rejected outright: vendoring is what makes the single-wheel install work
(`PROTECTED`, §27 L1-adjacent). The fixable part was the missing local guard, which is now in.

### 60.3 Still needs one word from the maintainer
**D-L4-03** `langgraph_graph.py`: unreachable from `src/`, `apps/`, `packages/`; 513 lines; its own
test leaves `221-395` never executed. Answering "planned surface" ⇒ wire it behind a documented
switch and it earns its coverage. Answering "experiment" ⇒ move it out of the coverage `source`
list so it stops inflating the denominator. **Not doing either** is also legitimate but must be
recorded, because the current state is the worst of both: dead to users, alive in the metric.
Deletion stays `BLOCKED` under lock L5 regardless.

### 60.4 Lane census after this session
L1 16 · L2 7 · L3 5 · **L4 5** · L5–L8 zero. `debt.unwiredCheckers` still names
`scripts/check_public_claims.py`; L5–L8 remain unexamined, not clean.

## §61 Lane L5 — documentation and public-claim consistency (first run)

### D-L5-01 — FIXED (`docs/agent.md`, guard in `tests/unit/test_imports.py`)
Claimed entry point `analyze_graph` does not exist anywhere in the code; claimed optional import of
`langgraph.graph.StateGraph` is in fact an unconditional top-level import. Both corrected, with the
reachability fact from §59 stated in the doc. This also settles **D-L4-03** the rule-compliant way:
the false part is gone from the docs; the module is left in place, no coverage exclusion is added
(§N6 / R11), and wiring-or-retiring remains a release decision rather than an audit-time edit.

Guard design note: the first version of the test was wrong and the failure was informative — it
rejected the token `langgraph`, which is a legitimate third-party module name in prose. Rule is now
"resolves to a `dsa_agent` attribute **or** an importable module", plus an in-test assertion that
the phantom name still does not resolve, so the guard cannot decay into vacuity. Red `rc=1` naming
`analyze_graph`, then green.

### D-L5-02 — BLOCKED, `SECURITY.md` names two files that do not exist
| line | names | tracked reality |
|---|---|---|
| 17 | `packages/execution/file_validator.py` | no such file. The described behaviour lives in `packages/execution/src/dsa_execution/mime_sniff.py` (`sniff_mime`, `is_allowed_mime`, `looks_like_zip_bomb`) plus `packages/datasets/src/dsa_datasets/validate.py` |
| 21 | `packages/agent/graph.py` | real path `packages/agent/src/dsa_agent/graph.py` |

Line 17 also names `sql_validator.py`, which does not exist either: the read-only SQL allowlist is
`packages/execution/src/dsa_execution/sql_guard.py`. A security policy pointing at nonexistent
modules is the specific case where "just fix the path" is still an approval item (§28): accuracy
fixes are welcome, but a security document is a public trust surface, so exact before/after is
required, not a drive-by edit. Proposed diff is ready; **needs your approval to apply.**

### D-L5-03 — BLOCKED, supported-versions table behind the release line
`SECURITY.md:43-44` lists `4.2.10` and `4.3.2`; `pyproject.toml` declares 4.4.0. Whether that is a
stale table or a deliberate support window is a policy question, not an accuracy fix — the table
*defines* what is supported, so widening or moving it changes a commitment. Reported, not changed.

### D-L5-04 — BLOCKED by file ownership
`README.md:16` still presents `v4.3.0` while the packaged version differs (v1's own lead, still
live). `README.md` is **another session's uncommitted file** in this shared tree, so it is
class-(b): I neither edit it nor commit it. Noted so it is not mistaken for my omission.

### D-L5-05 — measured, not gated
`docs/reproducibility.md` §Immutability and `benchmarks/baseline/README.md` were both re-read this
lane; §60's β annotation stands. The claims checker reports its own surface
(`scanned 14, skipped 51 as historical`), which is what §35's fix was for — it is now readable as
"these 14, not 'all docs'", so a clean exit can be interpreted correctly.

### 61.1 Non-findings and refutations
- Doc-stated tool budgets, critic/prompt-injection and sandbox file references (`guardrails.py`,
  `python_sandbox.py`, `dsa_agent/critic.py`) all resolve to tracked files: reviewed, correct.
- "MVP sequential engine" in the same section is **correct and current** — measured by the fact
  that `run_analysis` is what every shipped surface reaches. Left alone.
- The generic version of my phantom-symbol probe (all docs, all backticked names) returned 13
  hits of which 10 were builtins or third-party (`len`, `hasattr`, `astype`, `accuracy_score`) and
  it **missed the actual defect**, which is written without parentheses. Recorded as a rejected
  instrument: a gate that is 77% noise and blind to the real case is worse than the targeted check
  that fired. §4's CI-testability rule applied to my own probe design.

### 61.2 Law liveness
| law | state | decider |
|---|---|---|
| §16 STALE vs UNVERIFIABLE split | ACTIVE | D-L5-01/02 are stale-wrong and fixed-or-proposed; D-L5-03 is a policy definition, so not "stale" |
| §16 never reword to make a claim unfalsifiable | ACTIVE, honoured | the agent.md rewrite makes the claim narrower and truer, it does not delete it |
| §7.2 attribute every red before reporting | ACTIVE | the L5 guard's first failure was my rule being wrong, not the doc |
| §7 concurrency: foreign file is not a finding | ACTIVE | README.md untouched, D-L5-04 attributed |
| §11.3 guards must be shown to bite | ACTIVE | in-test self-check that `analyze_graph` stays unresolved |

### 61.3 State
Gates after the commit: ruff 0 · format 0 · mypy 0 · pytest 0 · ratchet OK · mkdocs --strict 0 ·
claims checker 0. Census: L1 16 · L2 7 · L3 5 · L4 5 · **L5 5** · L6–L8 zero. No push performed in
this lane yet; three local commits are queued.

## 62. D-L5-02 applied; two false controls found while verifying it; L8 opened

Scope authorised this turn: "apply the SECURITY.md patch and start lanes L6 through L8".

### 62.1 D-L5-02 — five corrections, not three
The proposed patch named three paths. Verifying each replacement target before pointing at it
turned up two more defects of the same class in the same section:

| claim as written | truth | evidence |
|---|---|---|
| `packages/execution/file_validator.py` | never existed; the MIME part lives in `dsa_execution/mime_sniff.py`, the allowlist/cap/traversal/archive-bomb parts in `dsa_datasets/validate.py` | `ALLOWED_EXTS` validate.py:9, `MAX_SIZE_BYTES` :18, traversal raise :29, archive guard :57 |
| `sql_validator.py` | never existed → `dsa_execution/sql_guard.py` | `_FORBIDDEN` :9, `_MAX_ROWS = 10000` :38, allowlist regex :57 |
| `PROMPT_INJECTION_PATTERNS` | **phantom symbol**, real names are `_INJECTION_PATTERNS` and `contains_prompt_injection` | guardrails.py:5, :20; zero hits repo-wide for the claimed name |
| `packages/agent/graph.py` for the budget numbers | wrong twice over: no such path, and the numbers are not in `graph.py` either | `Budget` in `dsa_agent/state.py`:94-97 |
| `dsa_agent/critic.py` | half-path — package-relative, not a repo path; widened the new guard and it caught this | guard output below |

`docs/security.md` carries neither phantom, so the defect did not replicate. Line 19's
`python_sandbox.py` claims were checked, not just re-pointed: `_DENY_IMPORTS`/`_DENY_ATTRS`/
`_DENY_NAMES` do deny all eight listed tokens and `_ALLOW_IMPORTS` does allow all nine listed
modules — that sentence is true.

### 62.2 Guard, and the gap it exposed in itself
`tests/unit/test_security_doc_claims.py`: path resolution for every backticked file claim, plus
AST- and field-level checks of the section's substantive claims. Falsified against the pre-patch
blob, not argued: **HEAD 19 cited / 4 unresolved → patched 20 cited / 0 unresolved.**

Two of my own instruments were wrong before they were right, and both were caught by running
them rather than by reading them:
- The first guard checked `hasattr(python_sandbox, "_safe_import")`. That function is nested, so
  the module has no such attribute — the assertion was red on a *true* doc claim. Replaced with
  an `ast.walk` over the module source, which finds nested defs.
- The first resolution regex required a known top-level directory, so bare `sql_validator.py`
  passed. Adding bare-name resolution is what surfaced the `dsa_agent/critic.py` half-path.
- My verification *probe* had the mirror-image bug: it returned the string `"bare->0"` for
  unmatched bare names, which is truthy, so it under-reported HEAD as 3 unresolved instead of 4.
  Re-measured before quoting the number.

### 62.3 D-L7-01 — `Budget.max_steps` is declared and never read (S1, BLOCKED)
`grep` for `max_steps` across `packages/ src/ apps/ tests/ scripts/` returns exactly one hit:
the field declaration at `state.py:95`. Zero readers. By contrast `max_tool_calls` and
`max_retries` are enforced at `graph.py`:408-446. The claim is nevertheless carried as fact by
`SECURITY.md`:21, `docs/architecture.md`:28, `docs/agent-system.md`:7,
`docs/portfolio/PROJECT_SUMMARY.md`:18, `research/paper/paper.md`:25, `:168` ("Budgets
**enforced**: `max_steps 20`") and `research/V3_RESEARCH_REPORT.md`:44, and it is baked into the
frozen `reproduction/v2/*/raw_runs.json` and `demo/runs/demo/state.json` payloads.

Not fixed beyond removing the false *location*. I dropped the word "enforced" by re-pointing to
the declaration site rather than deleting the knob, because the two honest resolutions are a
runtime behaviour change (wire it) and a seven-document rewrite (retract it) — a decision, not an
edit. **Recommendation: wire it** (`state.budget.max_steps` compared in the exec router), which
makes every existing claim true again with one change; it alters agent behaviour, so it is
blocked on approval.

### 62.4 D-L7-02 — the sandbox's 5 s wall-clock cannot interrupt anything (S1, BLOCKED)
`python_sandbox.py`:162 takes `timeout_ms: int = 5000`, but the check is *after* execution
(:194-199, `"error": "TimeoutError"` as a label on a completed run) and the comment at :176 says
so. No preemption exists anywhere in the chain: a grep for `wait_for|asyncio.timeout|signal.|
multiprocess|Pool(|concurrent.futures` across `packages/tools`, `packages/agent`,
`packages/execution` returns only that label line, and `run_python.py`:52 calls `execute_python`
synchronously.

Measured, T3, with a paired control under `ulimit -t 12`: `while True: i += 1` with
`timeout_ms=100` never returned and was killed by the CPU rlimit (rc 152 = 128+24 SIGXCPU); the
same probe with a 10-iteration loop returned in 0.00 s. So the 5 s bound is reporting, not
containment, and `SECURITY.md`:19 advertises it as a sandbox limit. Resolution is a code change
(subprocess or `RLIMIT_CPU` in a forked child) — behaviour-visible, needs approval, and would
have to be mirrored per §55's ordering hazard. Line 19 left in place for that reason: shrinking a
security guarantee in prose is not mine to do silently.

### 62.5 D-L8-01 — the LangGraph test could not tell the two engines apart (fixed)
`tests/unit/test_langgraph.py` asserts `status in ("COMPLETED", "FAILED")` and
`len(tool_calls) >= 1`. `run_analysis_langgraph` catches **any** exception from `graph.ainvoke`
and re-runs the non-LangGraph engine (:500-512), so those assertions are satisfied by the
hand-off — the test is green precisely when the feature is dead. langgraph is at **1.2.11** and
langgraph-checkpoint at **4.2.0**; nothing guarded the new shape.

Added `tests/unit/test_langgraph_engine_guard.py`: one test asserting no `langgraph_fallback`
result survives (the engine must answer) and one asserting `get_state(cfg)` still returns
populated thread state under the installed checkpoint major. Falsified by A/B in matched
conditions, both with an empty tool registry: **old file rc 0 (green), new guard rc 1** with
`ToolNotFoundError ... Available: []` quoted in the message. `langgraph_fallback` itself is
honest — it appends `passed=False` — which is why the fix is a test and not a code change.

### 62.6 D-L8-02 — checkpoints cannot be resumed across calls (S2, BLOCKED)
Measured with the same A/B pattern: `build_graph()` builds `MemorySaver()` inside the call
(:417) and never returns or stores it; no `get_state`/`update_state` call site exists outside
the new guard. After a run, `get_state` on **the same** graph returns 12 state keys; on a
**second** `build_graph()` with the identical `thread_id`, 0 keys. Pause/resume/replay/fork as
described by seven documents therefore has no mechanism, and the only entry point
(`run_analysis_langgraph`) is reached by tests alone — consistent with §60's finding that the
variant is unreleased.

Proposed, not applied: give `build_graph` an injectable checkpointer parameter (default keeps
today's behaviour) so the capability becomes both real and testable, or restate the documents as
"per-run checkpointing". Needs a decision.

### 62.7 Non-findings this turn
- pydantic 2.13.4: no `class Config:` blocks, no `.dict()`, no `parse_obj`, no `@validator` in
  `packages/`, `apps/`, `src/` outside the vendored mirror. Clean, reported as clean.
- SECURITY.md's supported-versions table is unchanged (D-L5-03 still open policy).
- `scripts/check_public_claims.py` has no reference anywhere in `.github/workflows/`, so the
  doc-claim guards that CI actually runs are the pytest ones.

### 62.8 State
Gates after this turn's edits: ruff 0 · format 0 · pytest 0 · ratchet OK · mkdocs --strict 0.
Collected tests 452 → **454** locally; CI's 450 denominator on `0b4c50a` still explains exactly.
Lanes L6 and L7 measured by three concurrent read-only agents; their reports land in
`/tmp/lane_reports/` and are integrated in §63 rather than merged into this entry.

## 63. L6 and L7 measured by three concurrent agents; two of their claims did not survive me

### 63.1 Method and safety
Three read-only agents ran L6.1 (frontend), L6.2 (repo integrity/search safety) and L7
(artifact reconciliation) concurrently against this tree. Reports: `/tmp/lane_reports/`
(`L6_frontend.md` 162 lines, `L6_repo_integrity.md` 465, `L7_artifacts.md` 507). Each was told
to write nothing in the repo; final `git status` from all three showed only the concurrent
session's three files, and `uv.lock`/`pyproject.toml` were byte-stable across their builds.
Two disclosed incidental side effects: two gitignored `.pyc` files from running the collector,
and six `artifacts/charts/*_forecast.png` plus `site/` and `apps/vscode/out/` that all predate
their first command by mtime. Both agents also recorded that **HEAD moved under them**
(`0b4c50a` → `f67dcdd`), and L7 verified that the intervening diff touches no file under
`packages/*/src`, `apps/*/src` or `_vendor` — so their measurements still hold.

Every headline claim below was re-opened by me. Nothing enters this ledger on an agent's word.

### 63.2 Verified in the source (T0-T1, my own eyes on the cited lines)
- **L6-FE-01 (S1).** `/benchmarks` reads `benchmarks/baseline/summary.json` and
  `benchmarks/v2/catalog.json` through `readFileSync` (`app/benchmarks/page.tsx:25,35`), and
  `docker/Dockerfile.web:5` copies only `apps/web`, so the files cannot exist in the web image.
  One detail the report missed and I added: the route is prerendered with
  `initialRevalidateSeconds: false` (measured in `.next/prerender-manifest.json`, 9 prerendered
  routes), so even in a layout where the read *succeeds* the figures are frozen at build time
  forever. `firstExisting`'s own comment at `:12-13` shows the author knew `process.cwd()`
  differs between layouts — this is a hedge, not an accident, and it cannot satisfy the split
  topology `docs/hosted-demo.md:14` asserts.
- **L6-FE-03 (S1).** HTTP failure is indistinguishable from absence:
  `app/failures/page.tsx:28` `if (!listRes.ok) return empty`, `:36 if (!r.ok) return`,
  `app/research/page.tsx:19` → `[]`, `app/analysis/[runId]/page.tsx:11` → `null`.
- **L6-FE-04 (S1, reachable via the docs).** Zero `Authorization`/`Bearer` tokens anywhere in
  `apps/web` source; `apps/api/.../security.py:122` gates `/api/*` on `DSA_AUTH_TOKEN`; and
  `docs/api.md:13` tells operators to set it. Setting it therefore yields a UI that reports
  "nothing exists" through FE-03 rather than "unauthorized". FE-03+FE-04 is the pair; neither
  is severe alone.
- **L7-AR-02 → fixed.** See §63.5.
- **L7-AR-04 → fixed.** See §63.5.

### 63.3 Where I corrected a sub-agent
- **L6-FE-17, numbers right, framing wrong.** `regression.mjs` was reported as "50 assertion
  points, 0 content assertions, 24 screenshots". My first check — counting `assert(`/`expect(`
  — returned 0 and 3, so I wrote the finding off as inflated. My instrument was the wrong one:
  the script hand-rolls `throw new Error` at `:118` (HTTP 200) and `:124` (overflow), 12 routes
  × 2 viewports = 48, plus 2 console checks = 50, and 24 screenshots at runtime. The counts
  stand. What changes the finding is the file's own header at `:8-10`: *"Intentionally
  backend-independent: with no API running, pages render their EmptyState/ErrorState (all HTTP
  200) — the tour guards layout, console hygiene, and 'old bundle' regressions, not live data"*,
  reinforced by `:119` waiting *so that* empty states render. So "a 200 with an empty body
  passes" is declared scope, not a bug. Restated: the repo's only browser-level net excludes
  content by design, therefore FE-01/02/03 have **no detector at all**, and the tour passes
  green on the broken production page. That is the finding.
- **L6-RI, "the real tree is never scanned" is false.** `tests/test_automation_scripts.py:215`
  does monkeypatch `ROOT` to `tmp_path`, but only inside one synthetic version-consistency test;
  `:223-224` reads `public_claims.ROOT` and asserts against the real tree. Narrowed to what is
  true: the *pattern* checks (identical text, stale version) run only on fixtures, so their
  numeric claims are never exercised against the repository they guard.
- **L6-RI, the README blind spot is misattributed.** `README.md` is **in** `SCAN_GLOBS`
  (`scripts/check_public_claims.py:42`); it is the *version-consistency* loop at `:194` that
  deliberately omits README, which is a defensible choice. The reason README's stale `v4.3.0`
  goes unseen is `:75` — `stale_version` matches only the literals `4.0.0|3.0.0|2.0.0`, so
  4.3.0 and 4.4.0 cannot be caught by construction. Verified directly.

### 63.4 Accepted at T2 (agent-measured, not re-opened by me) — do not treat as verified
L6-FE-02 (`/research` `readdirSync("research/results")`), the invented `RUNNING` status and
`tools.length || 19` fabrication, the orphan routes `/evaluations` `/failures` `/mcp`, the
"Checkpoint #12" replay claim, `/progress` polling without give-up, the absent fetch timeout,
`/failures` fanning out to 100 per-page requests, the hand-mirrored types dropping
`evidence.validation_status`; L7-AR-03 (VS Code claimed at `README.md:222` with no distributable
ever produced), L7-AR-05 (`ReproductionScore` not a symbol in the artifact), L7-AR-06
(`dsa-ml`/`dsa-reports`/`dsa-visualization` shipping a single `__version__` file each),
L7-AR-07 (`sync_vendor.SOURCES` never cross-checked against workspace members); the L6-RI
`git clean -ffdxy` analysis (94 entries vs 95, the one-line difference being the clone) and the
claim that 15 of the clone's dirty paths exist nowhere else in the tree. Each needs its own
red-first pass before it becomes a fix.

### 63.5 Landed this entry (3 commits, all red-first)
- **`docs/api.md` health table** promised `details:{db,duckdb,polars,llm}` on `GET /health`.
  The handler returns `details:{process}` (`health.py:39-43`, whose docstring names the split);
  `db` is on `/ready` (`:51-55`); `{duckdb,polars,llm}` is `/health/dependencies` (`:58-73`),
  which the table did not list at all. `ci.yml:156-159` asserts the code, so the documented and
  enforced contracts disagreed. New `tests/unit/test_health_contract_doc.py` compares the table
  to the handlers via `ast` — calling them is not an option, a TestClient request runs
  `init_db()` and writes SQLite into the tree. It arrived **red**, naming all three defects;
  and its first version filed `/ready` as undocumented, which was my regex matching only
  `/health*`, not a real finding.
- **`dsa --help`** advertised `MCP (§32): dsa mcp tools` (`dsa_evaluation/cli.py:259`) while that
  form exits 2 (`dsa: error: unrecognized arguments: tools`, rc taken from the command).
  Corrected in source and mirror. The guard's first design was wrong and its own negative
  control caught it: I appended `--help` to keep write-producing subcommands from executing,
  not realising argparse exits before it reports an unrecognised positional — the control came
  back `0 == 2`. Argument-form validation therefore needs a `build_parser()` seam; recorded as
  an uplift item instead of faked. Option-form assertions were deleted after measurement showed
  **zero** `dsa <sub> --flag` strings exist in the help today, i.e. an empty denominator that
  would pass forever.
- **Three live docs each carried a different wrong count.** Tool Layer "17" / mcp "18" /
  MCP_DESIGN "~13" against 18 tool modules on disk and 19 advertised entries; architecture.md
  "Next.js 15 / 13 routes" against a declared `16.3.4` and 16 `page.tsx` files (all four
  measured by me). Removed rather than corrected, per §3.
- **§17.2's own instruction was unsatisfiable** — it said to derive the pollution table "from
  the collector", and the collector emits no size or file-count leaf. Rewritten in place, one
  line for one line, because `debt.auditApparatusLines` is capped at exactly the current
  reading (1128 = 1128, measured), so any added line is a breach by construction.

### 63.6 Instrument limitations this lane exposed about my own mechanism
- `capabilities.navOrphanPages` ceiling is **23 and the measured value is 23** — zero headroom.
  The measured list mixes 11 `v4_3/` archive pages with 12 live ones, while §63's L7 adjudication
  rule says archive orphans are intended frozen history. Two owners now disagree about what the
  one number means, and the next genuinely new doc page trips CI regardless of nav care.
- `sync_vendor.py --check` is red in this working tree, and **not** because of my mirror edit:
  the only differing file is `external_validation.py`, the concurrent session's uncommitted work
  (`cmp` on the two HEAD blobs: identical, so CI is unaffected). Two consumers of the same fact
  diverged — `tests/unit/test_vendor_parity.py` stayed green because it deliberately skips
  git-dirty paths, which is also why it could not see my own `cli.py` mirror change; that parity
  was proved by `cmp` instead. The skip-on-dirty design tolerates other sessions at the cost of
  not covering the tree's in-flight files: worth naming as a trade-off, not a bug.
- L7's methodology correction to my own pitfall note: `-`/`_` normalisation is necessary but
  **not sufficient** — `dsa-visualization` ships import package `dsa_viz`, so joining member and
  artifact on the distribution name yields exactly one false "missing package". The only sound
  join key is each member's `[tool.hatch.build.targets.wheel] packages` entry.

### 63.7 Decisions still yours, ranked by what they cost to defer
1. **D-L7-01 wire `Budget.max_steps`** — smallest change, retracts nothing, makes seven
   documents and the frozen run payloads true again. Deferring keeps a false control in
   SECURITY.md.
2. **D-L7-02 preemptive sandbox timeout** — real containment (`RLIMIT_CPU` in a forked child or
   subprocess), needs mirror regeneration. Deferring keeps a 5 s figure that cannot interrupt.
3. **D-L8-02 injectable checkpointer** — makes pause/resume/fork exist and become testable;
   alternatively retract it in seven documents.
4. **FE-03 → FE-04 display state** — distinguish `unauthorized`/`serverError` from `empty`. The
   honest blocker: I cannot browser-verify here (no dev server without writing into a shared
   tree), so this needs either your local click-through or an explicit accept-unverified.
5. **FE-01/FE-02 data path** — serve the two frozen files through the API (matches
   `docs/hosted-demo.md:14`) or bind them into the web image and accept build-time freezing.
6. **D-L5-03 supported-versions table** and **α re-freeze of `benchmarks/baseline/`** unchanged.

### 63.8 Law liveness
| law | state | decider |
|---|---|---|
| §3 no derivable facts in prose | ACTIVE, now enforced on 3 live docs | counts I measured and deleted rather than corrected |
| §7.2 attribute every red before reporting | ACTIVE | three reds were my instruments, not the repo: `hasattr` on a nested def, the `/ready` regex, the `--help` blindener |
| §11.3 guards must be shown to bite | ACTIVE, and it fired on me | deleted the empty-denominator option test; kept `navOrphanPages` disagreement as a finding |
| §16 re-measure before quoting | ACTIVE | I re-ran the probe that reported 3 and returned 4 |
| §7 concurrency: foreign file is not a finding | ACTIVE | `external_validation.py` drift attributed, not touched; README v4.3.0 left to its owner |
| §17.2 "derive from the collector" | **VOID** | collector has no footprint leaf; the line was rewritten rather than left to mislead the next run |

### 63.9 State
Gates: ruff 0 · format 0 · full pytest 0 · ratchet OK · mkdocs --strict 0 with zero
ERROR/WARNING lines · `sync_vendor --check` 1 **from the concurrent session only** (proved
clean at HEAD). Collected tests 452 → **459** locally (CI's 450 on `0b4c50a` still explained
exactly by the two uncommitted foreign tests). Census: L1 16 · L2 7 · L3 5 · L4 5 · L5 5 ·
**L6 21+17 (agent-reported, 5 verified by me)** · **L7 11** · **L8 3 + 1 declined ceiling**.
Nothing pushed.

## 64. D-L7-01 closed — `Budget.max_steps` is now read, by both engines

Authorised turn: "开始接线 Budget.max_steps". TDD followed (skill loaded before implementation):
every assertion existed and failed before any production line changed.

### 64.1 What the wiring found, in the order it found it
- **The bound had to land in two places, not one.** Execution runs either through the sequential
  `for step in state.plan` loop or through the leading-independent-batch `gather` at
  `graph.py:405`, which fires whenever `len(indep_batch) > 1` and the whole batch fits the
  *tool-call* budget. That branch had no per-step check whatsoever: it handed the entire batch to
  `_asyncio.gather`. Proven by the red run — 21 steps executed under a limit of 20 on **both**
  paths (`profile_dataset` taking the sequential arm because it is not in `_PARALLEL_TOOLS`,
  `correlation_analysis` taking the batch arm). A single-site fix would have been another
  half-true control.
- **Truncating is not the same as reporting.** Cutting the plan short left the verdict
  `COMPLETED`, because the final status at `graph.py:623` is derived from hard-fail validation
  checks, not from `state.error`. Demonstrated by mutation: with `graph.py` enforcement present
  and only `critic.py` reverted, both engine tests failed with
  `assert COMPLETED == FAILED`. So the change extends the existing `check="budget"`
  hard-fail result (`critic.py:105`) to cover step exhaustion, reusing the check name the retry
  gate and `HARD_FAIL_CHECKS` already honour instead of minting a fourth signal.
- **`LGState` had no budget at all.** The LangGraph variant routes on `idx < len(plan)`
  (`langgraph_graph.py:145-150`) and its TypedDict carried no `budget` key, so wiring only the
  shipped engine would leave "tool budgets enforced" true in one engine and false in the other.
  Added `budget: Budget` to the state and bounded the router; 2 of 4 router tests were red first
  (stop-at-budget, honour-an-explicit-smaller-budget), and the other 2 are labelled
  green-on-arrival because they pin pre-existing behaviour (continue below budget, finish when
  the plan is exhausted) rather than new behaviour.
- **`max_tokens` is not a second dead knob** — read at `critic.py:146` into
  `guardrails.check_resource_limits`. All four `Budget` fields are now read somewhere.

### 64.2 Blast radius, measured structurally
My first comparison was invalid and I discarded it: a `--limit 5` run against the frozen
50-task baseline showed `task_success_rate 0.8 vs 1.0` and `unsupported_claim_rate 0.2 vs 0.06`,
which is a different task subset (and the §59/§60 verdict change), not this change. The real
question is whether the new bound can fire on that catalog at all, so it was measured directly:
running `heuristics_plan` over all 50 tasks gives plan lengths in {4,5,6,7,8}, **max 8, zero
plans over 20**. The guard cannot trigger there, so benchmark outcomes are untouched by
construction rather than by luck.

### 64.3 Doc claim restored, and now guarded by a parser
`SECURITY.md` went back to describing the budgets as enforced, with the enforcing file named and
the failure mode stated. `test_budget_enforcement_claim_is_backed_by_code` parses the engine with
`ast` and rejects any `max_*` the section cites that `graph.py` never reads — falsified by
adding `max_tokens` to the sentence, which produced exactly
`graph.py never reads ['max_tokens']`, then reverted from a `/tmp` copy and confirmed identical.
Substring counting would have passed on a comment mentioning the name; the AST cannot be fooled
that way.

### 64.4 Two mistakes of my own, both caught by running rather than reading
- An `Edit` whose anchor was a `def` line replaced that signature, silently grafting one
  function's body onto another. Detected by parsing the file for top-level `FunctionDef`s and
  seeing four with implausible sizes, not by eyeballing the diff — the same lesson as §62's
  nested-`_safe_import` failure, in the opposite direction.
- The new doc test called `_sandbox_section`, a helper from an earlier draft that the committed
  file no longer defines. `NameError` on the first run; the repair was to inline the split the
  way the sibling test already does it.

### 64.5 Law liveness
| law | state | decider |
|---|---|---|
| §11.3 watch the test fail first | ACTIVE | red run showed 21 executed on both paths; router tests 2-of-4 red |
| §12 no half-true controls | ACTIVE, drove scope | both execution branches + the unreleased engine wired, because one site would have re-created the same class of lie |
| §10 report the verdict, don't infer from error strings | ACTIVE | mutation B proved `COMPLETED` would have been reported |
| §7.2 attribute every red before reporting | ACTIVE | the invalid 5-vs-50 metric diff was discarded, replaced by a structural measurement |
| §55 mirror ordering hazard | ACTIVE | 3 modules re-copied to `_vendor` after each source/format change, verified with `cmp` |

### 64.6 State
Gates: ruff 0 · format 0 · mypy 0 (112 files) · full pytest 0 · ratchet OK · mkdocs --strict 0.
Collected tests 456 → **463** locally (+4 step-budget, +4 router, +1 doc-enforcement; note
`--collect-only` counts 463 vs the earlier 456 baseline including the foreign session's 2).
`sync_vendor --check` remains red solely from the concurrent session's `external_validation.py`.
D-L7-02 (sandbox preemption) and D-L8-02 (injectable checkpointer) stay BLOCKED awaiting
decisions; nothing pushed.

## 65. D-L7-02 closed — the sandbox timeout can interrupt now, and the ratchet policed my fix

### 65.1 Design chosen, and why the obvious one was rejected
Preemption was implemented as an `ast.NodeTransformer` that inserts a deadline call at the head of
every `For`/`AsyncFor`/`While` body, with the guard closing over a `time.perf_counter()` deadline.
`multiprocessing`/`RLIMIT_CPU` was rejected on a measured reason rather than taste: process spawn
costs hundreds of milliseconds per call and `mean_latency_ms` is a *gated* baseline number
(47.92 ms in `benchmarks/baseline/summary.json`), so the robust option would have moved a metric CI
compares. The transform's own cost was then measured instead of asserted — counterbalanced
A/B/A/B/A/B, 60 reps per arm, `execute_python` from HEAD (via `git show`, read-only) against the
new one on the same statement: **0.033 ms -> 0.083 ms per call, ratio 2.53, new slower in 6/6
paired observations**. Real 2.5x on the mechanism, 0.05 ms in absolute terms, and it cannot explain
the benchmark delta below.

`SandboxTimeout` inherits **BaseException**, not Exception: sandboxed code is allowed `try/except`,
so a deadline that is an `Exception` subclass can be swallowed by the very loop the guard is meant
to stop (`while True: try: ... except Exception: pass`). The conversion back into the normal result
dict happens at one boundary, so `run_python`'s contract is unchanged.

### 65.2 A false signal I did not act on
The paired benchmark run showed `mean_latency_ms 240.4 -> 404.8` with every quality metric identical.
One sample per arm on a host that earlier this session returned 15.4/18.3/26.5 s for identical
builds is not a regression, and the direct 6/6 A/B above bounds the true cost at +0.05 ms per call.
Reported as noise, not as a finding; the in-process measurement is the primary evidence.

### 65.3 The ratchet caught me adding "debt", and the ceiling did not move
`debt.swallowedExceptionSites` went 180 -> **181** and
`test_the_ratchet_is_currently_satisfied` failed, because `SWALLOW_RE` matches any line shaped like
`except X:` -- including my new `except SandboxTimeout:` clause, which *reports* rather than hides.
Two options: raise the ceiling, or change the code. Raising a debt ceiling is a policy loosening and
is explicitly a human decision, so I did not do it. Instead the handler was folded into the single
existing `except Exception as e:` line (now `except BaseException as e:` with an explicit
`if isinstance(e, (KeyboardInterrupt, SystemExit)): raise` first), which keeps interrupt semantics,
keeps the count at 180, and adds no suppression directive anywhere. The instrument is crude; the
response was to satisfy it honestly rather than edit it mid-audit.

### 65.4 Two of my own stale-path mistakes this unit
- I wrote `tests/test_sandbox.py` into a command from memory; it does not exist -- the existing
  coverage is `tests/security/test_adversarial_suite.py` and `tests/security/test_security_phase8.py`,
  found by `grep -rln execute_python tests/`.
- I re-ran a probe at `/tmp/probe_sandbox_preempt.py`, which was gone, and the resulting
  `Errno 2` looked at first like the sandbox failing. Rule honoured: a missing file is my error,
  not the subject's; recreated at `/tmp/probe_sb2.py` and it printed
  `returned_after=203ms error=TimeoutError stderr_tail=Timeout after 200ms > 200ms (interrupted)`.

### 65.5 Doc claim narrowed to what is measured
`SECURITY.md` now says the 5s budget is "interrupted at loop boundaries", quotes the measured
behaviour, and states the residual gap: a single long non-Python call can overrun and is reported
after the fact. The alternative was leaving "5s wall-clock" as an unqualified promise, which is the
class of defect this whole audit has been clearing.

### 65.6 Law liveness
| law | state | decider |
|---|---|---|
| §11.3 watch it fail first | ACTIVE | 2 of 3 tests red pre-implementation; the third (bounded loop unaffected) is green-on-arrival and labelled as pinning existing behaviour |
| §4 ceilings may only fall; loosening is human | ACTIVE, enforced on me | declined to move `swallowedExceptionSites`; restructured the code instead |
| §10 report paired signs, not seconds | ACTIVE | ratio 2.53 with 6/6 sign agreement reported; benchmark seconds rejected as noise |
| §12 no half-true controls | ACTIVE | coverage limit (non-Python overruns) written into the security doc, not left implied |
| §55 mirror ordering | ACTIVE | `python_sandbox.py` re-copied to `_vendor` after both the fold and the import-order autofix, verified with `cmp` |

### 65.7 State
Gates: ruff 0 · format 0 · mypy 0 (112 files) · full pytest 0 · ratchet OK (180 swallow sites,
unchanged) · `tests/security/` + deadline tests 39 passed. Nothing pushed; D-L8-02
(injectable checkpointer) is the next authorised item.

## 66. D-L8-02 half-closed — the checkpointer is now retainable, and the docs' remaining overstatement is a retraction decision

### 66.1 What landed
`build_graph(checkpoint=True, checkpointer=None)` and `run_analysis_langgraph(..., checkpointer=None)`:
an injected saver is compiled in, and without injection the previous behaviour is untouched. The
defect was that `MemorySaver()` was constructed inside `build_graph` and never returned or stored,
so `get_state` returned 12 keys on the graph that ran and 0 on a second graph with the identical
`thread_id` (measured in §62.6). Three tests, all red first with `TypeError: build_graph() got an
unexpected keyword argument 'checkpointer'`.

### 66.2 The mutation that made the pass-through real
The entry point could have accepted `checkpointer` and ignored it. Reverting only that one line
(`build_graph(checkpoint=True, checkpointer=checkpointer)` -> `build_graph(checkpoint=True)`) made
`test_entry_point_persists_into_the_callers_saver` fail with `assert {}` -- an empty restored state,
not an error. Restored and confirmed byte-identical before committing.

### 66.3 One test I deleted rather than keep
A fourth test asserted `build_graph(checkpointer=saver) is not build_graph(checkpoint=True)`. Two
compiles are always distinct objects, so it could never fail; it was removed after writing it, and
the file was then re-listed by parsing (`ast`) to confirm the remaining inventory -- including the
two `AsyncFunctionDef`s that my first printout had filtered out and briefly made me think the file
had lost a test.

### 66.4 Where the claim still overstates, and why I did not edit it
`docs/agent.md` -- the live product doc corrected in §61 -- turns out to carry **no** checkpoint,
MemorySaver or resume claim at all (grep over those terms: no matches). The overstatement lives in
six other documents: `docs/architecture.md`, `docs/agent-system.md`,
`docs/portfolio/PROJECT_SUMMARY.md`, `research/paper/paper.md`, `research/paper/V2_paper_draft.md`,
`research/V3_RESEARCH_REPORT.md` (plus `CHANGELOG.md`). After this change a caller *can* retain a
saver and read state back, so the primitive exists; what still does not exist is a shipped surface
that performs pause/resume/replay/fork, because the only entry point remains unreleased (§60).
Rewriting a research paper's capability claim is a retraction, not a typo fix, so it is presented
as a decision rather than performed here.

### 66.5 A number I could not reconcile, and how I resolved it
`--collect-only` reported 474 against my expectation of 469, and the snapshot I would have diffed
against was gone from `/tmp`. Rather than publish an unexplained number, the reconciliation came
from the maintained instrument: `debt.testFunctions = 438`, which is exactly §62's reading of 424
plus the 14 test functions added across §64-§66; the extra 36 in the collected count is
parametrisation. Lesson recorded where it belongs: quote the collector, and keep the snapshot you
intend to compare against.

### 66.6 State
Gates: ruff 0 · format 0 · mypy 0 (112 files) · full pytest 0 · mkdocs --strict 0 · ratchet OK
(`swallowedExceptionSites` still 180, `testFunctions` 438). Mirror re-copied for
`langgraph_graph.py` after formatting and verified with `cmp`. Nothing pushed.

## 67. One frontend claim promoted to T1, and the clone's unique work copied out before it could be lost

### 67.1 RUNNING does not exist (T1, verified by me)
`AnalysisStatus` has exactly 11 members (`state.py:10-21`): UNDERSTANDING, PLANNING,
DATA_PROFILING, ANALYSIS, MODELING, VALIDATION, SYNTHESIS, REPORTING, COMPLETED, FAILED,
HUMAN_REVIEW. There is no `RUNNING`, `PENDING`, `QUEUED` or `STARTED`. Yet the web layer treats
them as reachable:
- `apps/web/app/reports/ReportsTable.tsx:45` and `apps/web/app/runs/RunsTable.tsx:59` both offer
  `<option value="RUNNING">Running</option>` -- selecting it can only ever return an empty list.
- `apps/web/app/components/data/StatusBadge.tsx:16` classifies `RUNNING|PENDING|QUEUED|STARTED|HUMAN_REVIEW`
  as in-flight; four of the five names cannot arrive from the API.
- `apps/web/app/analysis/[runId]/RunInspector.tsx:534` computes the timeline step state with
  `i === 0 && run.status === "RUNNING" ? "active"` -- an unreachable branch, so the inspector can
  never show an active step.
The claim came from an agent at T2; it is T1 now because I opened all five sites and the enum.

### 67.2 Why I did not fix it in this turn
The correct repair is a UI-side mapping of the real in-flight members (ANALYSIS/SYNTHESIS/
VALIDATION/REPORTING) onto the "running" presentation, which changes no API contract -- adding
`RUNNING` to the enum would be a public status change on top of the L2 semantics already settled
in §56. Two things stopped me from doing even the UI mapping now: (a) it needs a browser to verify
and I will not claim a visual result I could not observe, and (b) `apps/web` is the other session's
active area -- §67.3 shows it is mid-restructure with a *different directory layout* -- so editing
those files now risks colliding with in-flight work that has no upstream copy.

### 67.3 The unique work is real, and my earlier remedy was wrong
Verified: `FRONTEND_REDESIGN_PROMPT.md`, `apps/web/components/` (12 files), `apps/web/lib/format.ts`
and `apps/web/lib/theme.tsx` exist **only** under `data-science-agent/`; the main tree has no
counterpart for any of them (its components live at `apps/web/app/components/`, which is why the two
trees can both contain a `StatusBadge.tsx` while being different files).
My §63 recommendation was `git bundle`. That is wrong for this case: all four paths are `??`
**untracked**, so a bundle would have captured none of them -- the exact loss scenario it was meant
to prevent. Corrected action taken instead, read-only against the clone and written outside it:

- `/tmp/clone-rescue-20260929-125612/untracked.tar` (105,984 bytes; contents listed and
  round-trip-extracted to prove readable content, e.g. `apps/web/components/ui/Button.tsx` = 101 lines)
- `/tmp/clone-rescue-20260929-125612/tracked-modified.patch` (409 lines; the 4 modified tracked files)
- `CHECKSUMS.sha256` for both

This is a mitigation for the §63 finding that `git clean -ffdxy` differs from `-fdxy` by exactly one
line -- `data-science-agent/` -- and would delete 1.1 GB that is unrecoverable and unpushed. It is
not a substitute for the owner committing the work; nothing in the clone was touched, staged or
moved.

### 67.4 Re-measured, because the agent's numbers had already decayed
The L6.2 report described 19 dirty paths of which 15 were `??`. `git -C data-science-agent status
--porcelain` now returns **8 entries (4 modified, 4 untracked)** -- the other session has been
committing while I worked. Any count quoted from a sub-agent's report needs re-measuring before it
is actionable; the direction of their finding held, the magnitude did not.

### 67.5 State
No source change in this entry (ledger only). Gates unchanged from §66: ruff 0 · format 0 · mypy 0 ·
full pytest 0 · ratchet OK · mkdocs --strict 0. Fourteen commits sit unpushed awaiting per-action
authorisation; the frontend batch (FE-03/04/05) is next in line but is blocked on either a
browser-verification step or your acceptance that I ship it unverified, and on the other session
finishing its `apps/web` restructure.

## 68. D-INFRA-05 closed — the only repair that existed was a bulk one, and bulk means "adopt someone else's work"

### 68.1 The hazard, stated correctly
My earlier framing ("`sync_vendor` has no scoped repair") understated it. There was no scoped
repair because there was no scope concept at all: `sync()` walked every package whose `_diff` was
non-None and did `shutil.rmtree(dst)` followed by `shutil.copytree(src, dst)`. In a shared
worktree, one bare run therefore rewrote **every** drifted package directory from whatever the
source tree happened to hold at that second -- including a concurrent session's uncommitted
edits -- into the mirror that ships inside the published wheel. The `--check` message made it
worse by recommending exactly that command as the remedy.

### 68.2 New contract
- `--check` -- audit, writes nothing (unchanged), but its hint now names the scoped command and
  says what `--all` would swallow.
- `--package NAME` (repeatable) and `--file SRC_PATH` (repeatable) -- per-**file** repair:
  byte-compare each source file to its mirror, write only the differing ones, unlink mirror files
  whose source is gone, and print every action. No directory is ever removed wholesale.
- `--all` -- the old bulk behaviour, now an explicit opt-in.
- bare run -- **refused**, exit 2, with the reason. A tool whose default is "rewrite everything"
  is a tool that will eventually be run on a shared tree by someone in a hurry.
- `--file` resolves the path and checks containment against each package root, so a `../../`
  argument cannot name a file inside a package. Implemented without shelling out, because
  `scripts/` forbids subprocess under the project's bandit rules (S603/S607) -- so the guard is
  path shape, not git inspection.

### 68.3 Red first, then live proof
7 of 12 assertions were red before the change (`--package`, `--file`, `--all` unknown; bare run
repairing two packages unasked; the check hint recommending the unscoped command). One is
**green-on-arrival and labelled as such**: `--file .../nope.py` is rejected today only because
argparse rejects the unknown flag, so it proves less than it appears to.

Then exercised against the real tree, never with `--all`:
- bare → `REFUSED: ...`, rc 2, and `git status` unchanged afterwards.
- `--check` → rc 1 with `Repair only what you changed: ... --package dsa_evaluation`, correctly
  attributing the drift to the concurrent session's uncommitted `external_validation.py` without
  copying it.
- `--package dsa_agent` and `--package dsa_execution` → `Already in sync`, which retro-verifies
  the manual mirror copies of §64/§65/§66 through the maintained instrument rather than my own
  `cmp` -- the tool agrees they are byte-exact.

### 68.4 Residual, not hidden
The tool still cannot tell whose source is whose; it can only force the operator to say which
packages they meant. `_diff` continues to report per-package counts rather than file names, so
`--check` output remains coarse -- the scoped commands are the precise surface now, and the
`tests/unit/test_vendor_parity.py` per-file skip-on-dirty design (§63.6) is unchanged.

### 68.5 State
Gates: ruff 0 · format 0 · full pytest 0 (12 in the sync_vendor suite) · ratchet OK. Tree holds
only my `scripts/sync_vendor.py` + `tests/test_sync_vendor_check.py` and the concurrent session's
three files. One commit queued locally; no push without a fresh per-action authorisation.

## 69. Phase 5 report produced, and writing it caught two errors in my own prose

`AUDIT_REPORT_PHASE5.md` (186 lines) implements §25.1–§25.6 against the recorded baseline `150b54f`
and the reporting commit `0a94a5a`.

- **Placement was a gate decision, not a tidy-up.** §25.4 asked "where does this go?" and the answer is
  forced: `capabilities.navOrphanPages` is capped at exactly its measured value (23), and the collector
  scans `docs/**/*.md` (`audit_facts.py:367-370`, `SCANNED` at :51). A new page under `docs/` would have
  become orphan #24 and turned CI red for the act of reporting. Root placement keeps it outside that scan,
  and `^[A-Z][A-Z_]*_(?:PROMPT|SPEC)\.md$` does not match its name, so `debt.auditApparatusLines` stays 1128.
  Verified after writing: apparatus 1128 · orphans 23 · todo markers 0 · claims checker `0 issues` ·
  ratchet `OK` · full pytest rc 0 · mkdocs --strict rc 0.
- **Two count errors, both caught against primary artefacts rather than by re-reading my draft.** The
  report's unverified-items bullet said "roughly thirteen"; `AUDIT_LEDGER.md` §63.4 actually carries
  **fifteen**, and I had also slipped `L7-AR-01` into the unverified set although §63.4 does not list it
  and the import-order mechanism was measured directly earlier -- understating known ground, the mirror
  image of over-claiming. Corrected in place, with the correction recorded here instead of silently
  rewritten. Likewise "twelve repairs" is now scoped honestly: twelve table rows covering the sixteen
  commits in `0b4c50a..0a94a5a`, out of 104 commits across the whole series; earlier-session repairs are
  referenced to §51–§60, not re-listed as mine.
- **`438` → `460` for `debt.testFunctions` explained, not smoothed.** §66 quoted 438. The reading came
  from a snapshot that `--check` never refreshes, and the `--write` that should have refreshed it ran with
  stdout and stderr redirected to `/dev/null`, so its failure was invisible. The value at `0a94a5a` is
  460. §66 stands as the historical record of what I saw; §25.3 carries the corrected figure with the
  mechanism, which is the family of my own suppression-hides-a-probe-failure trap.
- **Phase 4 is still not entered, by design.** §24's entry condition requires every S0/S1 to be
  `fixed`/`reverted`/`BLOCKED` with a recorded decision. The verified L6 S1s (FE-01/02/03/04) and the L7
  S1s are diagnosed but undecided, so uplift would be started over an open S1 -- the precise failure §24
  names. The report's §25.5 is therefore the prerequisite work, and its seven rows are the decision queue.
- **Self-audit outcome on my own laws:** §N10 is marked **VIOLATED** in the report (three batches
  committed code before the ledger entry), §34's per-lane probe inventory **NOT MET**, and §26's
  session-start gate derivation **PARTIAL**. These are reported as unchecked boxes rather than implied
  passes, per §30.

## 70. The fifteen T2 hypotheses adjudicated, and one of my own empty greps nearly fabricated a finding

Each row states the single command that decided it. Nothing in this section changed code.

| # | item | verdict | decider (command → observation) |
|---|---|---|---|
| 1 | FE-02 `/research` reads the filesystem | **CONFIRMED** | `grep -n readdirSync app/research/page.tsx` → `:1` imports `fs`, `:32` `readdirSync(dir).filter(startsWith("ablation_"))` |
| 2 | invented `RUNNING` status | **CONFIRMED** (promoted earlier, §67.1) | enum read `state.py:10-21` → 11 members, no RUNNING/PENDING/QUEUED/STARTED; UI uses it at 4 sites |
| 3 | fabricated `tools.length \|\| 19` | **CONFIRMED** | `grep -n "19" app/mcp/page.tsx` → `:39` renders `${tools.length \|\| 19} tools` |
| 4 | orphan routes `/evaluations` `/failures` `/mcp` | **CONFIRMED** | inbound-link grep per route excluding each page's own dir → **0, 0, 0** |
| 5 | "Checkpoint #12" invented referent | **CONFIRMED, and wider than reported** | `grep -rn Checkpoint apps/web/app` → `runs/[id]/replay/page.tsx:29` **and** `runs/[id]/page.tsx:79`; `grep -rn checkpoint apps/api/src/dsa_api/routers/` → no hits, so the referent cannot exist |
| 6 | `/progress` polls with no give-up | **CONFIRMED after relocating it** | the route does not exist (`find apps/web/app -name page.tsx` → 16 pages, none is `progress`); polling is `RunInspector.tsx:101 setInterval(tick, 3000)` with `:96-98 catch { }` labelled "Transient network blip — next tick retries" → a persistent failure retries forever and is silently swallowed |
| 7 | no fetch timeout anywhere | **CONFIRMED** | `grep -rn "AbortSignal\|signal:" apps/web` → no matches |
| 8 | `/failures` fans out up to 100 requests | **CONFIRMED with the number sourced** | `analysis.py:59 limit: int = Query(default=100 …)` × `failures/page.tsx:33 ids.map(async id => fetch(.../artifacts))` |
| 9 | mirrored types drop `validation_status` | **CONFIRMED for the drop only** | `grep -rn validation_status apps/web` → empty, while `state.py:66` defines `Literal["pending","verified","failed"]`. The agent's "verified evidence is a documented acceptance criterion" half was **not** re-verified and is not claimed here |
| 10 | L7-AR-03 VS Code surface with no artifact | **CONFIRMED, narrowed** | `README.md:214-222` table header is literally `Surface / Entry point`, and the VS Code row supplies a description where every other row supplies an entry point; `find -name "*.vsix"` → none; `grep -rln vsce .github/workflows scripts tests` → none. CI does run `npm --prefix apps/vscode ci`, so the source is installed and never packaged or checked |
| 11 | L7-AR-05 `ReproductionScore` | **SPLIT — half CONFIRMED, half REFUTED by me** | CONFIRMED: `docs/reproducibility.md:23` names `ReproductionScore {execution, numerical, statistical, evidence, semantic, overall}`; the real class is `ReproducibilityScore` with fields `level, score, details, dataset_sha256_match, tool_trajectory_match, conclusion_match` — different name, different shape, and `ReproductionScore` occurs in code only as a comment (`dsa_evaluation/cli.py:111`). REFUTED: the same sentence's `compare_runs` **exists** (`reproducibility.py:19`, imported and called at `cli.py:38,79`) |
| 12 | L7-AR-06 stub packages | **CONFIRMED** | `find packages/{ml,reports,visualization}/src -name '*.py'` → 1 each, `bytes=22`, contents `__version__ = "0.1.0"`; static-importer grep → no files outside their own package |
| 13 | L7-AR-07 `SOURCES` never cross-checked | **CONFIRMED** | `grep -rln "uv.workspace" tests/ scripts/ .github/` → empty |
| 14 | L6-RI `git clean -ffdxy` single-line risk | **CONFIRMED as an invariant; magnitude re-measured** | `git clean -fdxn \| wc -l` → **93**, `-ffdxn` → **94**, and `grep -c data-science-agent` in the latter → **1**. The earlier 94/95 pair decayed by one entry, exactly as §"audit premises decay fast" predicts; the asymmetry did not |
| 15 | clone's unique-paths claim | **DIRECTION CONFIRMED, magnitude REFUTED** | existence probes in both trees → the 4 untracked paths exist only under `data-science-agent/` (`FRONTEND_REDESIGN_PROMPT.md`, `apps/web/components/`, `apps/web/lib/{format.ts,theme.tsx}`); but `git -C data-science-agent status --porcelain` now returns **8** entries (4 M + 4 `??`), not "15 of 19" |

**Net:** 13 confirmed, 1 split (11), 1 direction-only (15); of the confirmations, three needed correcting in kind or location (#5 wider, #6 relocated, #10 narrowed) and two needed a magnitude refresh (#14, #15).

**The near-miss I should own.** Row 11's `compare_runs` first came back empty because I read the batch output wrong and nearly wrote "REFUTED — the doc's API does not exist". Re-running the narrow grep showed the definition plus two call sites. An empty result from a composite command is not a measurement — the same trap as the suppressed `--write` in §69, in the opposite direction: there, silence hid a failure to refresh; here, a misread silence would have invented a phantom.

**Effect on §25.4 / §34.** The fifteen are no longer hypotheses; the inventory above is the per-lane probe marking §34 asks for (`CONFIRMED`/`REFUTED`/`INCOMPLETE`), so the `NOT MET` line in the Phase 5 report's law table is now satisfied for L6/L7. Row 9's second half stays unverified and is marked as such rather than folded into the confirmation. None of these fifteen is yet a fix: they change the decision queue in §25.5 (rows 1-4 gain evidence, row 3 gains two more documents' worth of wording), not the code.

## 71. Four copy fixes, one new guard, and a correction to my own §70 verdict

### 71.1 §70 row 11 was wrong, and a second probe caught it
I wrote that L7-AR-05's surviving part was "name **and shape** mismatch". The shape part is false:
`packages/evaluation/src/dsa_evaluation/cli.py:112-118` assigns `reproduction_score = {"execution",
"numerical", "statistical", "evidence", "semantic", "overall", ...}` and `:120-123` emits
`by_level` over `L0..L5` — the document's six keys and its `by_level` clause match the code
verbatim, and `compare_runs` exists and is called. What is actually true is only that
`ReproductionScore` is not a Python class name, while a same-suffix class `ReproducibilityScore`
(with unrelated fields) does exist. So the item is **refuted as a factual defect** and demoted to a
naming ambiguity; `docs/reproducibility.md:23` now says "the CLI's `reproduction_score` object …
(the pydantic model in `dsa_evidence` is a different type, `ReproducibilityScore`)". Recording the
wrong verdict as written rather than quietly editing it: §70 said SPLIT, this says refuted-except-naming.

### 71.2 Landed (five one-line changes plus a guard)
- `apps/web/app/mcp/page.tsx:39` — `${tools.length || 19}` invented a tool count when the list is
  empty or unreachable; now renders the real count or "tool list unavailable".
- `apps/web/app/runs/[id]/replay/page.tsx:29` and `apps/web/app/runs/[id]/page.tsx:79` — both
  asserted a specific "`Checkpoint #12`" referent (and a `Run #124-Fork-A` identifier) that cannot
  exist: `grep -rn checkpoint apps/api/src/dsa_api/routers/` returns nothing. Now they state the
  absence instead of inventing an artefact.
- `docs/reproducibility.md:23` — as above.
- `tests/unit/test_vendor_sources_cover_workspace_members.py` — closes L7-AR-07: every workspace
  member's own `[tool.hatch.build.targets.wheel] packages` name must appear in
  `sync_vendor.SOURCES` and vice versa (15 ↔ 15, empty in both directions). It is **green on
  arrival** because the list is currently correct, so the file carries a functional control that
  removes one entry and asserts the diff reports exactly that package; without it the equality
  could not be shown to bite. The docstring also states why this is not the existing
  `capabilities.memberWithoutArtifactCopy` key: that one compares against `_vendor` **on disk**, so
  a hand-copied package satisfies it while remaining invisible to the repair tool.
- Not done deliberately: L7-AR-03's README row. `README.md` is one of the three files the
  concurrent session has uncommitted, and line 222 sits in its likely edit region; the accurate
  wording is recorded in §70 row 10 for whoever owns that file.

### 71.3 Verification actually performed
- `npm --prefix apps/web run typecheck` → `tsc --noEmit`, **rc 0**. This is the first time this
  session the web type-checker was run, and it is the evidence for the three `.tsx` edits.
- A candidate finding was refuted before being written up: `typecheck` is absent from
  `.github/workflows/` (only a comment mentions `tsc` for the VS Code compile), but
  `apps/web/next.config.mjs` sets no `ignoreBuildErrors`, so `next build` — which CI does run,
  twice — already type-checks. There is no unwired gate here.
- **VERIFICATION GAP, stated per §30.** The three `.tsx` edits are type-valid (`tsc --noEmit` rc 0)
  and the conditional logic is what the finding targeted, but no browser click-through was done:
  the repo's `next dev` was not started in this shared tree, and the claim "this sentence now renders
  as intended" is therefore argument, not observation. The edits replace a fabricated referent with a
  statement of absence in an existing `description=` string, so the rendering risk is the text itself,
  not layout or behaviour. Anyone with a running dev server should confirm the two replay/mcp cards
  read sensibly before this is called visually verified.

### 71.4 Effect on the Phase 4 entry condition
Two of the fifteen are now fixed as copy (#3, #5), one is resolved as naming-only (#11), one gained a
guard (#13), and one is parked on file ownership (#10). The items that genuinely block Phase 4 are
unchanged in kind: FE-01/02 data path, FE-03/04 auth and error presentation, FE-05 status
vocabulary, FE-06/07/08 fetch discipline, plus the §25.5 decision rows that need the maintainer.

## 72. The mechanism behind FE-01/FE-02, measured rather than inferred

While confirming what the runner would verify for the pushed web edits, the prerender set was read:
`apps/web/.next/prerender-manifest.json` contains 9 routes — `/_global-error`, `/_not-found`,
`/analysis`, `/benchmarks`, `/datasets`, `/datasets/compare`, `/evaluations`, `/icon.svg`,
`/runs/compare` — and **not** `/research`, `/failures` or `/mcp`. Cross-checked against the pages
themselves: those three call `fetch(..., { cache: "no-store" })` (`research/page.tsx:18`,
`failures/page.tsx:27,35`, `mcp/page.tsx:20`), which forces request-time rendering.

So the two filesystem-reading defects are **not the same defect**:
- **`/benchmarks` reads at build time and is then frozen forever.** It is prerendered with
  `initialRevalidateSeconds: false` (§67), so `readFileSync` runs during `next build`. In the web
  image the files do not exist (`Dockerfile.web` copies only `apps/web`), so an EmptyState is baked
  into static HTML; where the files *do* exist, the numbers are stale by construction and no
  revalidation ever refreshes them.
- **`/research` reads at request time.** Its `readdirSync` (`page.tsx:32`) runs per request inside
  the web container, where `research/results` was never produced, so it yields an empty list on
  every load — not frozen, simply always empty.

Both are host-locality failures, but they need different remedies: the first cannot be fixed by
serving data at request time unless the prerender/frozen flag is also addressed, while the second is
fixed by the same API-serving change on its own. Recorded so §25.5 row 1 is not decided on a merged
description of two different behaviours.

## 73. Runner verdict for `42ee536`, and the verification gap narrowed by evidence rather than assertion

**CI verdict: `completed / success`** per the API — both jobs green (`ci`, `web-regression`), plus
`CodeQL 42ee536 success` and `Secret Scan 42ee536 success`. All 26 steps of the `ci` job report
`success`, including `audit_facts --check`, `sync_vendor --check`, ruff, format, mypy,
`pytest --cov`, the SBOM step, `dsa --limit 5`, wheel+sdist, the clean-install smoke, and the
docker/compose/mkdocs steps.

**The watcher lied again, in the same way, third recurrence.** The background watcher wrote
`W10_REAL=1`, and its log's final line is
`failed to get run: Get "https://api.github.com/…/runs/36545318008…": unexpected EOF`
— a transport death against a run that had actually finished successfully. Had the rc been treated
as a verdict, a green pipeline would have been reported as red. The rule that keeps paying: the
watcher's exit code is only ever an observation about the watcher, and the conclusion comes from
`gh run view --json status,conclusion`.

**What the runner proved about the §71 web copy edits.** The `web-regression` job's tour printed
`regression: 24/24 checks passed`, and its route list includes `/mcp` and `/failures`. Since each
navigation requires HTTP 200, zero console errors and zero horizontal overflow at both viewports,
that is browser-level evidence the edited pages still render cleanly. §71's VERIFICATION GAP
therefore narrows rather than closes: **rendering is now machine-verified, textual correctness is
not** — the tour asserts no content, which is exactly §70's item-4 finding, so no runner step can
confirm the new sentences read as intended. Reporting the gap as partly closed on evidence is the
honest form; claiming it closed because the pipeline is green would be the failure mode this audit
exists to catch.

Unpushed at the time of writing: this section's predecessor §72 (`860208a`), docs-only.

## 74. The version detector now compares against the release line instead of a hand-kept blacklist

**Measured before designing.** Replacing `stale_version`'s literal triple with "any released
version that is not current" was implemented as a probe and rejected on its numbers: over the 14
scanned files it fires **160 times**, 150 of them `CHANGELOG.md` release records, plus
`CITATION.cff:1 cff-version: 1.2.0` (a metadata *format* version that happens to collide with a
project tag), `CITATION.cff:27 version: 4.2.0` (a `references:` entry, i.e. a citation *of* an old
release), and each sub-app's own `"version": "0.1.0"`. A rule that drowns in that is worse than the
blacklist it replaces, because its output stops being actionable.

**What went in instead: a declared-assertion table.** `CURRENCY_ASSERTIONS` names the places where a
document asserts *which release is current or upcoming* -- `README.md`'s `[**vX.Y.Z**]` release badge
and `ROADMAP.md`'s "next minor release through [vX.Y.Z" pointer -- and checks each against
`released_versions()` / `current_version()`. The cost is stated in the code: a new currency surface is
unchecked until someone adds a row. The benefit is that it cannot fire on version-shaped text that is
not a currency claim.

- `released_versions()` reads `.git/packed-refs` and `refs/tags` directly -- `scripts/` is under
  bandit S603/S607, so no `git` subprocess -- normalises `v`-prefixed and bare tags onto one key, and
  drops peeled `^{}` lines. The peeled-line and duplicate-name traps are both already recorded from
  the tag census, so they were designed out rather than rediscovered.
- If the tag set or the current version comes back empty, the check **returns an issue**
  ("currency check disabled") instead of returning no findings. A checker whose denominator can
  silently become zero reports clean while testing nothing, which is the most damaging failure mode
  available to it.
- `check_currency_claims()` is wired into `main()` as **high severity**, and the retired
  `stale_version` key is gone from `PATTERNS`. Its absence is asserted through the AST: my first
  version of that test grepped file text and failed on *my own explanatory comment* quoting the old
  literal, which was the test being wrong, not the code.

**Red first:** four tests failed with `AttributeError: module ... has no attribute
'check_currency_claims'` before any implementation existed; six pass after.

### 74.1 What it found on the real tree, and the one thing I did not fix

Two genuine defects, both pre-existing at HEAD:

- `ROADMAP.md:21` pointed "the next minor release" at v4.3.0, which shipped long ago. Fixed by
  removing the false currency claim and stating the actual position -- 4.4.0 is current, no
  readiness checklist exists for the next minor yet, and `docs/release-readiness-v4.3.md` remains
  the gate model. Reworded rather than retargeted because inventing a `v4.5.0 Release Readiness`
  link would have created a dangling reference; `mkdocs build --strict` still exits 0 after the edit.
- `README.md:16` advertises `[**v4.3.0**]` as the release badge. **This corrects my own earlier
  attribution**: §62 and §65 recorded D-L5-04 as "foreign-locked", but
  `git show HEAD:README.md | grep v4.3.0` returns the identical line, so it is repository history,
  not another session's in-flight work. I still do not edit it, for a narrower and sharper reason:
  the file is dirty in the working tree, so my one-line change would sit inside their unstaged
  edits and their next `git add README.md` would restage the old line and silently revert me. The
  fix is one token (`4.3.0` -> `4.4.0`, plus the tag URL) and belongs to whoever next owns that
  file's staged content.

Consequence stated rather than smoothed over: `check_public_claims.py` now exits **1** on a clean
checkout, by design. It is still the single unwired checker (`debt.unwiredCheckers: 1`), so nothing
in the pipeline changes today; §25.5 row 6's precondition is now concrete instead of hypothetical.

### 74.2 State
Gates: ruff 0 · format 0 (2 files reformatted before the run) · ratchet OK · full pytest 0 ·
mkdocs --strict 0 · `check_public_claims` 1 high-severity issue, the README line above.

## 74.3 A consequence of my own fail-closed guard: wiring the checker into `ci.yml` would break on its first run

Measured, not hypothesised: `ci.yml`'s two checkout steps (`:22`, `:54`) set only
`persist-credentials: false` -- **no `fetch-depth: 0`** -- while `publish.yml:27` does set it. A
default-depth checkout does not fetch tags, so inside the `ci` job `released_versions()` would read
an empty ref set, and the guard added in §74 returns "currency check disabled" as an **issue**
rather than reporting clean. Since `currency_claims` is classified high severity, the commit that
wires `check_public_claims.py` into `ci.yml` would go red **on its own wiring**, independent of any
stale claim in the tree.

This is the intended behaviour of a fail-closed check -- a detector with a silently zero denominator
reporting green is the worse outcome, and §74 chose that trade deliberately -- but it turns §25.5
row 6's precondition from one item into two, and both are now concrete:

1. fix `README.md:16` (`4.3.0` -> `4.4.0` plus the release URL), and
2. give the job tags (`fetch-depth: 0`, matching `publish.yml`) *or* pass the expected version in so
   the currency check can distinguish "no tags available" from "no stale claims".

Recording it here rather than at wiring time, because the person doing that work is likely not the
person who added the guard, and the failure mode otherwise reads as an unrelated CI breakage.

## 75. The trap §74.3 described is removed: the currency check degrades per-assertion instead of going dark

§74.3 ended with a check that reports "disabled" when a checkout has no tags, and named two
preconditions for ever wiring it into `ci.yml`. Only one was actually necessary, and the second was
an artefact of an all-or-nothing guard I had written an hour earlier.

**Change.** Each entry in `CURRENCY_ASSERTIONS` now carries a `needs_tags` flag. With no tag set: the
README badge is still checked (answering "is this the current release?" needs only the declared
version, which the old code had in hand and ignored -- its own disabled message printed
`current='4.4.0' tags=0`), while the ROADMAP "next release" check is skipped, because proving a
version already shipped genuinely requires the tag set. The skip is **reported**:
`currency_degradations()` contributes "no tags in this checkout: cannot test ROADMAP.md" to the
summary line, so narrowed coverage cannot be read as a clean run.

**Red first.** The new tagless test failed with exactly the predicted message,
`currency check disabled: current='4.4.0' tags=0`, before any implementation existed. The second new
test -- no current version at all still reports disabled -- is **green on arrival**: it pins the
fail-closed behaviour §74 chose, not new behaviour.

**A regression my own paired case caught.** The first rewrite dropped the `version in released`
predicate and flagged any non-current version as "already released", which turned the *positive*
case in `test_roadmap_must_point_at_an_unreleased_version` red (4.5.0, unreleased, was reported as
shipped). Restoring the predicate fixed it; had that test carried only the failure case, the bug
would have shipped as an over-broad detector -- the same lesson as §62's empty-denominator guards.

**One lint finding, fixed at the right level.** Folding the claim text into the branchy message left
`claim` unused (B007, which suggests renaming to `_claim`). Renaming would have silenced a real
signal that the rewrite had discarded a field worth keeping, so the field is now used to build the
message: `README.md:16 cites '4.3.0', advertised as the current release, which it is not (current
4.4.0)`.

**Effect on §74.3.** The wiring precondition list shrinks from two items to one: the `README.md:16`
token change. `fetch-depth: 0` is no longer needed to make the checker usable in the `ci` job -- it
is needed only to widen it to the ROADMAP half, and the tool now says which half it evaluated.

**State.** Gates: ruff 0 · format 0 (208 files) · ratchet OK · full pytest 0 · mkdocs --strict 0.
`check_public_claims.py` still exits 1 on a clean checkout for the one unowned README line, by
design. 8 currency tests pass. Nothing pushed in this section.

## 76. Measurement claims are now re-measured; the four typed number rules were already dead

The delegated choice was which count is canonical. **Chosen: `def test_` occurrences, as defined by
the collector's own `TEST_DEF_RE`, imported rather than restated.** Rationale, stated so it can be
argued with: it is derivable from the committed tree with no test run, is unaffected by
parametrisation and by platform-gated branches, and already has an owner (`debt.testFunctions`,
whose floor gates deletions). `collected` (481 locally) and `passed` in a CI log were rejected --
the first moves with plugin/platform, the second only exists after a run, and **both are currently
inflated by another session's uncommitted tests**: the collector now reads 475, up from 465 before
this section, of which my additions are 5 and the rest is theirs.

Consequence of choosing a structural rule over a prose sweep: a sentence is checkable only when it
names the path it counts (`pytest <target> ... # N tests`). That is deliberate. A blanket
"any number followed by 'tests'" rule was measured first, per §74's lesson: across the scanned
surface there are 6 such claims, 5 of them in `CHANGELOG.md` where quoting a superseded figure is
the file's job. So the derived check runs on the shape that carries a target, and CHANGELOG prose is
untouched by construction rather than by an exemption list.

**The four retired literals had no live coverage.** Measured per rule over the 14 scanned files:
`stale_mypy` 0 hits, `stale_coverage` 0, `stale_test_counts` 1 (CHANGELOG:503, a 4.3-era "86 tests"
record), `stale_routes` 1 (CHANGELOG:508). They could only ever catch numbers somebody had typed
once, and every current match was a false positive on a release record. Removed with those counts
attached; the naming rules (`old_package_pip`, `old_repo`, `old_package_import`) stay -- different
class, still live.

**What the new rule found immediately:** `apps/vscode/README.md:83` advertised
`uv run pytest tests/vscode -v  # 6 tests: manifest, commands, views, dsa wrapper, failure handling,
arch guard` while the directory defines **7** test functions. The enumeration was wrong in kind as
well as in count: it listed six concerns where one function covers three of them, omitted four
functions (6-step flow, tsc compile, contributes, no-stub), and named a "dsa wrapper" test that does
not exist. Corrected to the real seven. The file was clean in `git status`, so it was mine to fix;
`README.md:16` still is not, and remains the checker's one standing exit-1.

**An existing test broke, correctly.** `test_identical_text_is_flagged_only_outside_a_historical_prefix`
used `"The suite is 155 tests today."` as its payload and so depended on the retired
`stale_test_counts`. Its actual subject is path-keyed exclusion, not that literal, so the payload was
retargeted to a naming claim that survives, with the reason commented in place. The assertions are
unchanged -- both the scanned and the skipped copy must still produce findings.

**Two instrument faults worth recording, both mine.**
- My first blast-radius probe printed `f.name` instead of a relative path, so it labelled
  `apps/vscode/README.md` as `README.md` and I nearly wrote a fix against the wrong file. Re-ran
  with `relative_to(root)`.
- `README.md` is being edited live: between two of my commands, line 83 changed from the vscode test
  claim to "Python **3.12+** is required." and back to no match at all. A line number quoted from a
  shared tree is a snapshot, not a fact; and `git show HEAD:README.md | grep "[0-9] tests"` returning
  nothing was what finally located the claim in the other file.
- Added `measurement_claims_evaluated()` and assert it is >= 1 against the real repository, so the
  rule cannot go vacuous the way the four literals quietly had.

**State.** Gates: ruff 0 · format 0 (209 files) · ratchet OK · full pytest 0 · checker exits 1 on
the one unowned token. New: 5 tests in `tests/test_measure_claims.py`.

## 77. The version claim's standing red closes -- and the two shipped gate lists are narrower than CI

**Landed.** `README.md:16` advertised `[**v4.3.0**](.../releases/tag/v4.3.0)` while `pyproject.toml`
(`version = "4.4.0"`), `CITATION.cff` (`version: 4.4.0`) and the local tag set (`v4.4.0` present) all
say otherwise. §74.1 and §76 both declined to touch it because the file carries another session's
in-flight edits; the user then authorised this specific line ("帮我把 README 版本改成 4.4.0"), which is
the only bar that was in the way. The currency rule is green for the first time since it was wired,
in the checker's own words:

```
✓ No stale claims detected -- 0 issues (scanned 14 file(s); 51 skipped as historical)
```

That closes §74.3/§75's precondition argument from the other side: wiring `check_public_claims.py`
into CI now needs only `fetch-depth: 0` for the ROADMAP half, and no longer breaks on a clean
checkout. Still not wired -- that is a decision, not a discovery.

**Staged without taking the other session's work.** The version line sits five lines below that
session's anchor edit, so both changes land inside *one* hunk (`@@ -8,12 +8,12 @@`), while its
Quickstart rename and install-time note form a second hunk (`@@ -58,9 +58,10 @@`) with no change of
mine in it. `git add -p` needs interactive input this shell cannot provide, so the index was patched
directly: a one-line hunk built against `git show HEAD:README.md` and applied with
`git apply --cached`. Verified three ways before committing -- `git diff --cached -- README.md`
showed exactly the version line, the worktree file kept all three edits, and after the commit
`git status` still lists `M README.md` for the hunks that are not mine.

**A gate-scope defect that is live, and one that is retracted again.** Measured while checking this
commit, both by running the two commands and reading their own counts:

| surface | ruff check / format / mypy paths | `scripts`? | `--cov`? | `audit_facts --check`? |
| --- | --- | --- | --- | --- |
| `ci.yml:75,85-87` | `… tests src apps/jupyter scripts` / mypy `packages apps/api src apps/jupyter` | yes | yes (`:88`) | yes |
| `docs/contributing.md:19-22` | `packages apps/api tests src apps/jupyter`, mypy `packages apps/api src` | **no** | **no** | **no** |
| `CONTRIBUTING.md:10-12` | `packages apps/api tests`, mypy `packages apps/api` | **no** | **no** | **no** |

Both shipped contributor guides therefore tell a reader to run a *subset* of the remote's checks:
a contributor who edits `scripts/`, follows either list to the letter and pushes gets a CI red on a
check they were instructed to run; and `pytest -q` without `--cov` never evaluates the `fail_under
= 79` floor that `ci.yml:88` enforces. This is the same species as §48(2)'s dispatch-list gap, but
these are public documents rather than agent briefs, and there is no `AGENTS.md`/`CLAUDE.md` in the
repo root to carry a correct list (`ls` for both: no matches). Not fixed here: the user asked for one
version token, and rewriting two contributor guides is a separate decision. Cheapest correct fix is
to have both lists name `ci.yml:75,85-88` instead of restating paths -- a restated list is exactly
how it drifted.

**Re-retracted.** A root-scope `uv run ruff format --check .` reports `1 file would be reformatted`,
and the offender is `AUDIT_LEDGER.md:862` -- a fenced Python block inside this ledger
(`--> AUDIT_LEDGER.md:862:1`). So ruff 0.16.3 does format Python embedded in Markdown, and every
code block in the repo's `.md` files sits outside both style gates. §36 already recorded this and
declined to act ("There is no repo-root format gate, so there was nothing to fix"), and the
retraction holds: the ledger is quoted evidence, and reshaping it to satisfy a gate that does not
exist would edit the record to please the instrument. Noted here only because I re-triggered it and
should not file it twice.

**Two instrument faults, both mine, both caught by the child rather than the wrapper.**
- `… | tail -n ; echo rc=$?` measures `tail`. My first pass on this commit reported `fmt_rc=0` and
  `mkdocs_rc=0` that way. Re-ran with output redirected to a file and the code captured unpiped:
  `FORMAT_RC=0` (`209 files already formatted`), `MKDOCS_RC=0` with `grep -cE "WARNING|ERROR"` = 0,
  `RATCHET_RC=0` (`facts ratchet: OK`). Third time through the same trap in one session.
- The background-task layer sent `completed (exit code 0)` twice while pytest was still at 72%, and
  a third time after it had genuinely finished. `pgrep -fl bin/pytest` (empty) plus the log's own
  `PYTEST_RC=0` line are the verdict; the notification's is not. Note also that this run's `-q` log
  never prints an "N passed" summary line -- the count is the collector's (`testFunctions: 475`),
  not something to read off the terminal.

**State.** Gates on the committed tree: ruff check 0 · CI-exact format 0 (209 files) · mypy 0
(108 files) · mkdocs --strict 0 · ratchet OK · full pytest `PYTEST_RC=0`, coverage 80.82% against a
79 floor · `check_public_claims.py` 0. No new tests (documentation-only change). Push: still owed.

## 78. The gate lists the guides restate are pinned to `ci.yml` -- and one documented command could not run

**Authorised and scoped.** §77 left one open decision -- both contributor guides told readers to run
a *subset* of the remote's checks. The user delegated ("审阅无误，授权，我都听你的"), so this is that fix,
done test-first.

**RED, in the guard's own words** (`tests/test_ci_gate_integrity.py`, written before any doc edit):

```
CONTRIBUTING.md: mypy differs from ci.yml -- missing ['apps/jupyter', 'src'], extra []
CONTRIBUTING.md: pytest differs from ci.yml -- missing ['--cov', '--cov-report=term-missing'], extra []
CONTRIBUTING.md: never runs the ratchet gate CI runs (['--check', 'scripts/audit_facts.py'])
CONTRIBUTING.md: ruff-check differs ... / ruff-format differs ... -- missing ['apps/jupyter', 'scripts', 'src']
docs/contributing.md: mypy differs ... missing ['apps/jupyter'] / pytest ... missing the cov flags
docs/contributing.md: never runs the ratchet gate / ruff-check and ruff-format missing ['scripts']
```

**How the guard works, and what makes it non-vacuous.** `ci.yml`'s single-line run steps are parsed
with the file's existing `_single_line_run_steps`, each command classified into one of five gates
(`ruff-check`, `ruff-format`, `mypy`, `pytest`, `ratchet`), and the guide's fenced-block command is
compared as a *token set* after removing invocation scaffolding (`uv run python -m`), inline comments
and CI's `| tail` logging. Three things stop it going quietly green: `assert len(expected) == 5`
proves the parser still finds every gate; the guides are checked for gates they never run at all, not
only for wrong paths; and `test_gate_comparison_detects_a_shortened_list` is an in-test control that
feeds the comparator a list with `src apps/jupyter` removed and asserts it reports exactly those two
tokens. That control is green-on-arrival by design -- it tests the instrument, not the docs -- and is
labelled as such.

**Scope pin.** Only the two documents that present themselves as the pre-PR gate are compared. The
shorter "Development" (`README.md`, `## Development`) and "Quick Quality" (`docs/README.md:22-29`)
blocks are tasters: they may run a subset, and the reason is written into the guard's comment rather
than left for the next reader to guess.

**Searching for a second copy found two claims of a different class.** While checking that no other
doc restates the lists (a first-match comparator can hide a stale duplicate), `docs/README.md:25`
carried `# 257 passed (V4.1 live 2026-08-22; V1: 86+; V3.0: 155)` -- a typed measurement literal of
exactly the §76 class, the collector's real count being 475 test functions. It is *not* caught by
§76's `MEASURE_CLAIM`, and deliberately not taught to it: that rule requires the shape
`pytest <target> ... # N tests` and re-measures against `TEST_DEF_RE`, whereas "N passed" counts
collected instances, a different denominator. Making the guard accept that shape would have
installed a wrong equation, so the literal was removed and the line points at the binding list
instead. Same treatment for `docs/README.md:17`, which described `CHANGELOG.md` as `0.1.0 → 1.2.0`:
replaced with a non-numeric pointer, since re-typing `4.4.0` only re-arms the rot.

**A documented command that could not run on this tree.** `README.md:353` tells contributors
`uv run mypy .`. Measured: `MYPY_DOT_RC=2`, aborting with `Duplicate module named "dsa_api"` from
`data-science-agent/` -- the gitignored second clone (`.gitignore:55`). Because that directory is
gitignored, a fresh clone would pass, so the doc was not lying to contributors; the hazard is local
and real. The config was fixed rather than the doc: `data-science-agent/` joined `[tool.mypy] exclude`.
This is not a gate weakening -- the excluded tree is a duplicate copy of the same module names mypy
refuses to disambiguate, and nothing shipped leaves the checked set: after the change `mypy .`
reports `Success: no issues found in 114 source files` against the **112** CI's own list checks, i.e.
the documented command is now strictly *wider* than CI's, and it exits 0.

**Correction to §77, found by writing this.** §77's state line recorded "mypy 0 (108 files)" because
I ran `mypy packages apps/api src` -- the list `docs/contributing.md` was telling people to run, not
the one `ci.yml:87` runs. CI's list adds `apps/jupyter` and reports 112. The verdict (rc=0) was
right; the *surface* was under-stated by four files, which is the same under-scoping §78 exists to
stop. Re-measured on CI's exact command: `MYPY_RC=0`, 112 files.

**Instrument note (fourth this session).** In zsh `${PIPESTATUS[0]}` is empty -- arrays are
1-indexed and the variable is lowercase `$pipestatus` -- so my `echo "RC=${PIPESTATUS[0]}"` printed
`RC=` and read as a pass to anyone skimming. A blank exit code is not zero; the verdict came from the
test file's own assertion text.

**Decisions taken here, for the record.** `docs/contributing.md` was *not* given CI's
`sync_vendor.py --check` and `check_npm_workspace_lock.py` steps, and `CONTRIBUTING.md` keeps its
`dsa --limit 5` shorthand instead of CI's catalog-qualified form: the guard pins the five gates that
gate a PR's correctness, and widening it to every CI step would turn a style/coverage guide into a
transcript of the workflow file.

**State.** New: 2 tests in `tests/test_ci_gate_integrity.py` (guard + comparator control); the guard
was RED with the 10 offenders quoted above before any doc was touched, and is now green with them
aligned. Gates, each rc captured unpiped from its own child: `GATE_RC=0` (5 tests in the file) ·
ruff check 0 · CI-exact format 0 (209 files) · `MYPY_RC=0` (112 files, CI's list) · `PYTEST_RC=0`
with coverage 80.82% against the 79 floor · `RATCHET_RC=0` (`facts ratchet: OK`) · `CLAIMS_RC=0` ·
`MKDOCS_RC=0` with zero WARNING/ERROR lines · `MYPY_DOT_RC=0` (114 files) for the documented taster.
Collector: `testFunctions` 475 → **477**, proving the two new tests are defined;
`suppressionDirectives` unchanged at 42, so the new mypy exclude is not counted as a suppression --
and `--write` after the run dirtied no tracked file under `docs/audit/`. Nothing pushed.

## 79. The claims detector is wired into CI -- and wiring only counts if the gate cannot run blind

**Authorised scope.** §78's follow-up decision: give `check_public_claims.py` a CI step. §74.3 had
predicted it would break on its first run, and §77 softened that to "now needs only `fetch-depth: 0`
for the ROADMAP half". **Both halves were wrong**, and simulation -- not reading -- is what said so.

**Why a default checkout is red for the wrong reason.** `check_version_consistency()` shells out to
`git describe --tags --always` (the one `# noqa: S603` in `scripts/`). On a checkout with no tags that
returns the short SHA, so the rule emits `git tag mismatch: 188a09c base 188a09c != v4.4.0`, which is
high severity → exit 1. A step wired at default depth therefore fails every run on a plumbing
artefact rather than on a stale claim.

**Why `fetch-depth: 0` alone is not the answer.** Verified against the SHA the repo actually pins
(`actions/checkout@fbc6f399… # v5`): its `action.yml` declares `fetch-tags` with default **false**,
and `src/input-helper.ts` at that same commit applies "false" when the input is absent. (v5 no longer
has `src/git-manager.ts` -- that fetch 404s -- so the depth/tags command construction was not read.)
Relying on "fetch-depth 0 implies tags" would have been a guess about a runner I cannot execute
locally, so the design removes the guess instead: fetch both, and make the step self-attesting.

**The measured hazard, in a table.** Two clones made with `file://` -- `--depth 1` (0 tags readable)
and full (36 tags in `packed-refs`) -- running the same script:

| checkout | ref | `--require-released-tags` | rc | what it printed |
| --- | --- | --- | --- | --- |
| shallow, 0 tags | branch HEAD | no | 1 | `git tag mismatch: 188a09c …` -- red, but for plumbing |
| shallow, 0 tags | `release/v4.4.0-rc` | no | **0** | "✓ No stale claims … no tags in this checkout: cannot test ROADMAP.md" |
| shallow, 0 tags | `release/v4.4.0-rc` | yes | 1 | names the rule that never had a verdict |
| full, 36 tags | branch HEAD | yes | 0 | the gate actually ran |

Row two is the finding. `_is_release_candidate_ref()` legitimately skips the describe rule on a
`release/v<current>-rcN` ref, so on that ref a tagless checkout prints a *pass* while its strongest
assertion is inert -- D-L1-05's shape exactly (`--strict` with `links.not_found: ignore`). The flag
converts that caveat into a non-zero exit; without row two the flag would be dead weight.

**Landed.** `require_released_tags()` plus an argparse `--require-released-tags`; `ci.yml`'s `ci` job
checkout now carries `fetch-depth: 0` and `fetch-tags: true` with the reason in a comment, and the
step runs after the three integrity checks. `debt.unwiredCheckers` ceiling 1 → **0** (a fall, so
allowed): re-measured `[]`, and fed `1` back through `evaluate_ratchet()` in memory the ratchet
answers `{kind: ceiling, problem: debt_grew, actual: 1, limit: 0}` -- the tightened number bites, it
is not decoration. Both guides picked the new gate up too, because widening the guard to six gates
turned them red first, exactly as §78's design intends.

**A bonus the argparse switch bought by accident.** `main()` never parsed `argv`, so the script
silently accepted *any* flag: `check_public_claims.py --require-released-tagz` used to run the normal
check and exit 0. Measured after the change: rc 2, `error: unrecognized arguments`. A typo in a gate
flag was previously indistinguishable from omitting it.

**Cost, stated rather than assumed.** The `ci` job's clone goes from depth 1 to full history: 458
commits, 19 MB of objects measured locally. Job has 29 steps; the added step is stdlib-only Python.

**Two instrument faults of mine this round.**
- My first clone experiment concluded "the flag does nothing" (rc 0 with and without). The clones were
  made with `git clone`, which copies **commits**: my implementation was still uncommitted, so the
  tested script had no flag at all -- and, worse, an unparsed `argv` meant the flag was accepted and
  ignored. Re-copied the two scripts into the clones and the proof reversed. A working-tree edit is
  not in a clone until it is in a commit.
- The test's hand-rolled `_checkout_with` reported `{persist-credentials: false}` for a file that
  `yaml.safe_load` reads as three inputs: it treated the colon-less comment line I had just added
  inside `with:` as the end of the block. `yaml.safe_load` was used as the adjudicator, the reader now
  skips comments and keys off indentation, and `test_checkout_reader_sees_inputs_past_a_comment`
  pins that shape. The reader stays parser-free deliberately: PyYAML is transitive here (mkdocs pulls
  it, `pyproject.toml` never declares it), so a test importing it can ImportError on an unrelated bump.

**Not proven: the runner.** Everything above is a local simulation of the checkout contract. No CI
lane has executed this step, `actionlint` is not installed here (CI downloads it), and the `with:`
edit is unlinted by the workflow's own first step. Per the standing rule the lane gets shown on a
throwaway branch before `main`, which needs a push. Forward note while here: `publish.yml:27` and
`secret-scan.yml:26` already pass `fetch-depth: 0` without `fetch-tags`; nothing in them enumerates
local refs (`publish.yml` uses `gh api repos/.../releases/tags/$GITHUB_REF_NAME`), so they are not
broken today -- but any future step that reads `git tag --list` under `fetch-depth: 0` alone inherits
this same ambiguity.

**State.** New: 5 tests -- 3 for `require_released_tags` (empty set refused, populated set accepted,
the real checkout satisfies it) in `tests/test_currency_claims.py`, and the CI-wiring assertion plus
the `_checkout_with` comment control in `tests/test_ci_gate_integrity.py`; the guard's gate count went
5 → 6, which is what turned both guides red before they were updated. Collector:
`testFunctions` 477 → **482**, `unwiredCheckers` **0**, `suppressionDirectives` steady at 42 (the new
code adds no suppression), and the `facts.limits.json` diff is one line -- the ceiling itself. Gates,
each rc from its own child: `CHECK_RC=0` · `FORMAT_RC=0` · `MYPY_RC=0` (112 files) · `PYTEST_RC=0`,
coverage 80.82% over the 79 floor · `MKDOCS_RC=0` with zero WARNING/ERROR lines · `CLAIMS_RC=0` run
with `--require-released-tags` on the real checkout · `RATCHET_RC=0` after the tightening. The 458
commits / 19 MB figure and the four-row clone table are local measurements, not CI's. Nothing pushed,
and the workflow's own `actionlint` step has not seen this edit yet.

## 80. The branch run paid for itself immediately: my gate is green on the runner, my §76 tests were machine-bound

**What ran.** Pushed `ci-proof-79`, opened PR #78, and the `ci` job (run 36674978496, job
109757876596) came back `conclusion: failure`. Step-level, from the API rather than from a watcher's
exit code:

| step | conclusion |
| --- | --- |
| `Run actions/checkout@fbc6f399… # v5` | success |
| `Lint GitHub Actions workflows` (actionlint) | success |
| `Run uv run python scripts/audit_facts.py --check` | success -- with `unwiredCheckers` at 0 |
| `Run uv run python scripts/check_public_claims.py --require-released-tags` | **success** |
| `Run uv run pytest -q --cov --cov-report=term-missing` | **failure** |

So all three things §79 said only a runner could prove are proven: `fetch-tags: true` leaves
`git describe --tags` resolvable (the wired step exits 0 instead of dying on `git tag mismatch:
<sha>`), actionlint accepts the `with:` edit, and the tightened ceiling holds on the runner. The
merge state also read `BLOCKED` while that check was red, which is the required-check wiring working
as intended, not a bug.

**The failure was mine, from §76, and it is not about the new gate.** Five cases died on:

```
FAILED tests/test_measure_claims.py::test_a_stale_test_count_against_the_real_directory_is_flagged
  - FileNotFoundError: [Errno 2] No such file or directory: '/Users/jackson/Data agent/scripts/check_public_claims.py'
```

`REAL = Path("/Users/jackson/Data agent/scripts/check_public_claims.py")` plus two inline copies: a
test that hard-codes the authoring machine's absolute path. It passed ruff, mypy, the full local
suite and the ratchet because on *this* machine the path resolves.

**A limit of a method I lean on, recorded because it nearly hid this.** §78's discipline -- re-run a
suspect gate against a `git archive HEAD` export before blaming the repo -- did **not** catch it, and
could not have: the path is absolute, so an export anywhere on this disk still reads the original
repo and still passes. An export only falsifies *relative-path* assumptions. What finally exposes an
absolute-path bug is either another machine (here, the runner) or a *static* check, which is why the
guard below is static.

**Fix and guard.** The three literals became `REPO = Path(__file__).resolve().parents[1]`. New
`test_no_executed_code_hardcodes_a_developer_home_path` scans `tests/**` and `scripts/**` for a
quote immediately followed by `/Users/` or `/home/`, and carries `assert scanned >= 50` so a broken
walk cannot pass by finding nothing. Its red environment is genuine rather than synthetic: run in a
HEAD export that still contains the old file, it fires and names
`tests/test_measure_claims.py:23: REAL = Path("/Users/jackson/Data agent/…` ; run in the fixed repo,
8/8 pass. It also matches its own docstring text nowhere, because the guard looks for a quote *before*
the slash and the prose form has none.

**Blast radius, measured instead of assumed.** `git grep -c /Users/jackson` over tracked files,
excluding the nested clone: **40 files**. Split by whether anything executes them:

- executed (`tests/`, `scripts/`, `packages/`, `apps/`, `src/`): **1 file**, `tests/test_measure_claims.py` -- fixed here.
- not executed: `case-studies/0*/outputs/*.{json,md}` (28 files), `benchmarks/external/datascibench/results/raw_runs.json`,
  `research/external/datascibench_results.json`, three `research/results/ablation_*.json`,
  `research/v4_3/results/manifests/phase_f_manifest.json`, and two `AUDIT_LEDGER.md` quotes.

The second group cannot break CI, but it does bake the author's filesystem path into committed
evidence artifacts -- a portability wart and a small disclosure of a personal path in anything
published from `case-studies/` or the benchmark results. Not rewritten here: those files are
generated records, and silently editing committed evidence to scrub a path is a different decision
from fixing a test. Filed, with the count attached, so whoever regenerates them can decide.

**Instrument note.** `gh run list --branch ci-proof-79` returned `[]` while the same head SHA had five
runs queued. For `pull_request` events the branch filter does not match; `gh api
repos/.../actions/runs?head_sha=$(git rev-parse <ref>)` is the query that sees them. A first check
that returns nothing is not evidence that nothing was triggered.

**State.** Local re-verification of the fix: `CHECK_RC=0` · `FORMAT_RC=0` (209 files) · `MYPY_RC=0`
(112 files) · `PYTEST_RC=0`, coverage 80.82% over the 79 floor · `MKDOCS_RC=0` with zero WARNING/ERROR
lines · `RATCHET_RC=0` · `CLAIMS_RC=0` with `--require-released-tags` · guard file 8/8 ·
`testFunctions` 482 → **483**. Re-pushed to the same throwaway branch for runner confirmation -- same
ref, same PR, nothing touching `main`, inside the verification already authorised. Merge remains a
separate decision and is not taken here.

## 81. Thirteen resume claims tightened, and the guard that first tried to gag the honest sentences

**The premise, measured before anything was rewritten.** A sub-agent supplied the claim inventory;
the load-bearing fact -- that no shipped path uses the LangGraph engine -- was re-verified here rather
than borrowed. `MemorySaver()` is constructed in exactly one place, `packages/agent/src/dsa_agent/`
`langgraph_graph.py:427`, and grepping `build_graph(`/`run_analysis_langgraph` across `packages`,
`apps`, `src`, `scripts`, `examples` returns one hit: `:440`, inside the same module. The four
entry points that actually run analyses -- `apps/api/.../analysis_service.py:34`,
`src/data_science_agent/sdk.py:321`, `dsa_evaluation/runner.py:145`, `external_validation.py:146` --
all import `dsa_agent.graph.run_analysis`, the sequential engine. `apps/web/app/runs/[id]/page.tsx`
contains zero occurrences of `Checkpoints`. So the docs describe a seam that exists and is tested,
presented as a capability a user can invoke.

**What changed (13 sites, all wording).** `docs/architecture.md:48` said `StateGraph` with
`MemorySaver`, `checkpoint` for pause/resume/replay/fork; it now names the sequential engine as what
ships and the checkpointer parameter as a seam with no shipped caller. Same treatment for
`docs/architecture.md:28` (roles line), `docs/agent-system.md:7`, `docs/portfolio/PROJECT_SUMMARY.md:18`
(`MemorySaver` checkpoints for replay), `docs/portfolio/ONE_MINUTE_PITCH.md:9`,
`research/V3_RESEARCH_REPORT.md:44`, `research/paper/paper.md:34` and `:59`,
`research/paper/V2_paper_draft.md:15` and `:39`,
`apps/web/app/runs/[id]/replay/page.tsx:15` (the header promised "Select checkpoint, Replay or Fork"
two lines above its own empty state saying no checkpoint API exists -- the page contradicted itself),
`apps/web/app/runs/page.tsx:30` (listed a Checkpoints section the route does not render), and
`README.md:222` (the VS Code row advertised "analysis replay" while `extension.ts` registers seven
commands, none of them replay).

**Two statements deliberately kept, and a guard that had to learn the difference.** The first red run
of `tests/test_checkpoint_claims.py` named three *honest* disclaimers -- "Replay and fork need a
checkpoint API that does not exist in this build", "under construction", "not wired in this build" --
because the pattern matched on shape, not on intent. A gate that punishes truthful hedges trains the
next editor to write vaguer prose, so `_DISCLAIMER` now clears any line that denies the capability,
and `test_the_guard_fires_on_the_shape_it_exists_to_stop` asserts both directions fire *and* the three
real UI sentences stay green. `test_the_working_benchmark_checkpoint_stays_described` protects the one
resume that genuinely works -- `run_eval.py` appends each finished task to `raw_runs.partial.jsonl`
and skips those ids on restart -- so a future sweep cannot delete a true statement, which is why
`CHANGELOG.md:115` and `DATASCIBENCH_REPORT.md:143` were left alone, and `CHANGELOG.md:541` is
exempted by prefix as a historical release record rather than edited into a lie about the past.

**Exemptions declared in the test, with reasons, not as silence**: `site/` (generated mirror),
`docs/v3`//`docs/v4_3` (historical), `CHANGELOG.md`, the audit documents themselves, `benchmarks/`
(its checkpoint is real), `data-science-agent/` (a second clone). `assert len(files) >= 20` fails the
test if the globs ever stop finding anything.

**Not fixed here, named for the record.** `docs/portfolio/PROJECT_SUMMARY.md:18` and
`research/paper/V2_paper_draft.md:15` still carry `Next.js 13 routes`, `17 tools` and `Next.js 15` --
the same retired-literal family as §76, reachable now that `stale_routes` no longer exists. They were
left because the fix is a re-count of the current surface (apps/web is Next.js 16.3.4) and folding an
unverified new number into a wording change replaces one stale claim with another.

**State.** 4 new tests in `tests/test_checkpoint_claims.py`; `testFunctions` 483 → **487**. Gates,
rc from each child: `TSC_RC=0` (`npm --prefix apps/web run typecheck`, needed because two `.tsx`
strings changed) · `CHECK_RC=0` · `FORMAT_RC=0` · `MYPY_RC=0` (112 files) · `PYTEST_RC=0`, coverage
80.82% · `MKDOCS_RC=0` with zero WARNING/ERROR lines (these files are nav-served) · `RATCHET_RC=0` ·
`CLAIMS_RC=0` with `--require-released-tags`. The second run of the verification lane,
36675826804, is `completed success` with both jobs green and `check_public_claims.py
--require-released-tags` and `pytest --cov` each recorded `success` step-by-step -- §79's gate and
§80's fix are now proven on `ubuntu-latest`, not just here. Nothing merged; `main` untouched.

## 82. The portfolio's unowned counts are gone -- and a first red list that proved the guard was wrong, not the docs

**Precedent followed, not reinvented.** §63 already ruled on this class: `AUDIT_REPORT_PHASE5.md:43`
records "counts removed, not corrected (§3 rule)" after measuring 18 modules, 19 entries,
`next 16.3.4` and 16 pages. §81 left two portfolio lines carrying the same numbers, so this is the
completion of that ruling rather than a new policy.

**Measured first.** `find apps/web/app -name "route.ts*"` returns nothing and `page.tsx` counts 16,
with `apps/web/package.json` declaring `next: 16.3.4` -- so "`Next.js 13 routes`" is false under any
denominator. `grep -c "add_parser("` gives 12 where the doc claimed 11 subcommands, i.e. the number
was not even re-derivable by a consistent count. That ambiguity is itself the argument for deleting
instead of correcting: whoever typed 11 and whoever would type 12 are both guessing at a definition.

**Landed.** `docs/portfolio/ONE_MINUTE_PITCH.md:9` and `docs/portfolio/PROJECT_SUMMARY.md:18`,`:30`
lost their surface census (11 subcommands / 17-18 tools / 13 routes / 18 tools + 5 resources /
7 commands + 2 views); the qualitative claim reads better without them. Editing `:30` exposed two
more of the same species: the wheel was advertised as `jack-data-science-agent 4.2.10` while
`pyproject.toml` says 4.4.0, and `SBOM 192` cited a number no check recomputes. Both now name their
owner instead (`version owned by pyproject.toml`, `generated by scripts/generate_sbom.py`), and the
PEP 740 sentence keeps `4.2.10` because there it is a dated fact about a past release, not a currency
claim -- the distinction §76 established for measurement literals.

**The guard took three tries and the red lists are the record of why.**
`tests/test_doc_census_claims.py`, 3 tests:
1. First cut scanned `apps/**/*.md` and reached `apps/web/node_modules/next/dist/docs/**`, reporting
   ~40 "offences" in third-party documentation -- a probe counting dependency output, the same error
   family as the gitignored `packages/artifacts/` notebook trap. `SKIP_SEGMENTS` now prunes
   `node_modules`, `dist`, `build`, `.next`, `.venv`, `_vendor`, `site`.
2. Second cut widened the nouns to `tests|tasks|metrics|modules|datasets|pages` and its red list came
   back containing **McNemar 6:2, a Wilson interval, a verified run's "1.33 s, 6 evidence items",
   catalog sizes from `docs/benchmark.md`, and an ADR's dated "(7 tests)"**. That is a ban on numbers,
   not a rule about ownership, and it would have taught the next author to write "several" instead.
   Narrowed to the product-surface nouns §63 actually demonstrated drifting.
3. Third cut still matched `321 tool calls` and `6 tool calls` -- a run's tool-call count, not the
   tool census. Diagnosed by printing the exact matched token per line rather than re-reading the
   prose, then a `(?! calls)` lookahead.

So the test suite now pins both directions: the shape fires on "11 subcommands" and "16 routes", and
a cited derived figure, an instruction line, and spelled-out prose all stay clear. The exemption list
is asserted too (`test_exempt_surfaces_are_what_they_claim`), because a carve-out for a directory that
no longer exists silently widens what the guard ignores.

**Deliberately not touched.** `research/**` keeps its counts and is exempt with a stated reason -- a
paper describes the release it was written against, and rewriting a submission's numbers to today's
tree is falsifying a record. That covers `research/paper/paper.md:25`,`:58`,
`research/paper/V2_paper_draft.md:15`,`:39`, `research/V3_RESEARCH_REPORT.md:45`,
`research/related-work.md:27` and the two claim-evidence tables. If any of those documents is being
resubmitted, its census needs the same treatment as a deliberate author decision. `docs/ADR/` is
exempt for the same dating reason.

**State.** 3 new tests; `testFunctions` 487 → **490**. Gates, rc from each child: `CHECK_RC=0` ·
`FORMAT_RC=0` · `MKDOCS_RC=0` (the two portfolio files are nav-served, so this is the check that
matters) · `RATCHET_RC=0` · `CLAIMS_RC=0` with `--require-released-tags` · `PYTEST_RC=0`, coverage
80.82%. No runner has seen this change yet: §81's tightening was verified as run 36678529947
(`completed success`), and this entry will only claim a runner result after one exists for it.

### 82.1 The runner result §82 declined to predict, and a watcher that polled nothing for 37 minutes

The run exists now: 36696729612 on head `74355bf`, `completed success`, `ci` and `web-regression` both
green, and step-level in its own words -- `audit_facts.py --check => success`,
`check_public_claims.py --require-released-tags => success`, `pytest -q --cov => success`,
`mkdocs build --strict => success`. So the portfolio edits are confirmed by the docs gate on
`ubuntu-latest`, which is the only gate that matters for them. Three green runs on this lane now
(36675826804, 36678529947, 36696729612), all of them following the one red run 36674978496 that caught
§80's machine-bound path -- the sequence the branch protocol exists to produce.

Two instrument faults were needed to get there, both worth keeping:
- The first watcher resolved its run id with `--jq '... .databaseId'` against the **REST** listing,
  where the field is `id` (`databaseId` belongs to the GraphQL node). The id was therefore an empty
  string, `gh run view ""` became a request to `/actions/runs/`, and every one of 50 polls returned
  `HTTP 404` -- while the wrapper reported `completed (exit code 0)` at the end. A poller that never
  observed anything is not a poller that observed nothing: the fix is to echo the resolved id before
  trusting any loop, and to log a line when a read returns neither in-progress nor completed instead
  of letting an empty string through. §79's premature notification and this are the same lesson twice
  more: the wrapper's exit code is never the child's verdict.
- `NO_PROXY="*"`, which this session needed for `gh api` and log fetches, **broke `git push`**:
  `LibreSSL SSL_connect: SSL_ERROR_SYSCALL in connection to github.com:443`, in the same shell where
  gh calls had just succeeded. Unsetting `NO_PROXY`/`no_proxy` made the identical push work. The
  bypass is per-client, not per-shell -- saved to memory so the next session does not re-derive it by
  failing a push first.
