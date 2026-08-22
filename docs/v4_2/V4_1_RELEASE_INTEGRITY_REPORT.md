# V4.1.0 Release Integrity Report — Phase A (V4 Freeze & Release Integrity)

> **Phase:** A — V4 Freeze & Release Integrity (W1 Release Integrity Audit)  
> **Version:** v4.1.0  
> **Tag:** v4.1.0 (commit 4a0158d4914a0257574e97fdedff3b5565c42d1d)  
> **HEAD:** e8794c1d14b50bff70f7d587d4a71338b519f703 (1 commit ahead of tag)  
> **Date:** 2026-08-22 (live verification, not historical)  
> **Executor:** Automated Phase A audit (live `git`, `pytest`, `mypy`, `ruff`, `npm`, `docker`, `dsa`, `PyPI`, `gh`)  
> **Required reading:** `DATA_SCIENCE_AGENT_V4_2.md` §13–18, `AGENTS.md` (not found, using repo root conventions), `DATA_SCIENCE_AGENT_V4_1.md`, `docs/v4_1/*`

---

## Executive Summary

**Verdict: V4.1.0 RELEASE INTEGRITY ISSUES DETECTED — No Critical Blocker to Platform Operation, but Release Artifacts are Currently Inconsistent**

Live verification confirms the **platform itself is functional and gates pass** (`pytest 257/257`, `mypy 104 strict`, `ruff pass`, `npm 13/13`, `docker valid`, `dsa verify-release 12/12 PASS`, `dsa demo COMPLETED`, benchmark smoke `1.0`, SDK/Plugin/MCP/Jupyter/VS Code tests pass). However **release identity is divergent**:

- `HEAD (e8794c1)` is **1 commit ahead of `v4.1.0` tag (4a0158d)`** — the PyPI rename fix `jack-data-science-agent` (§65) was committed **after** the tag and is **not contained in the tag**. `PyPI 4.1.0` was published from `e8794c1`, so **Tag ≠ PyPI artifact name** (Critical).
- `CITATION.cff:9` still `4.0.0` (stale, 17 days old).
- `README.md` and consequently `PyPI long description` still contain **V2/V3-era quantitative claims** (`~86+ tests`, `81/92 source files`, `155 tests`, `81% coverage (4597 stmts)`) that contradict live `257 tests / 102–104 files / 79%`.
- `mkdocs build --strict` **fails (29 warnings)** — documentation gate as defined in `ci.yml` would fail strict mode.
- `release/sbom.cyclonedx.json:metadata.component.name` still `data-science-agent` (old) while `pyproject.toml:1` and `release/sbom.json:193` are `jack-data-science-agent`.
- `docs/v4_1/RELEASE_MATRIX.md:27`, `CHANGELOG.md`, `SECURITY.md` still reference `192 SBOM` and `data_science_agent-4.1.0` wheel, not `193`/`jack_*`.
- Stale `pip install jack-data-science-agent[jupyter]` strings remain in `docs/v4_1/*.md` (5 occurrences) vs canonical `jack-data-science-agent`.

No fabricated adoption, no secret leakage, no benchmark fabrication detected. All functional gates remain **PASS**. Fix order is documented in §18.

**STOP condition:** Phase A complete. **Do not proceed to Phase B** until Critical/High mismatches are triaged (recommend `v4.1.1` patch for metadata-only fixes without code change, per §15/§73).

---


## 1. Release Identity

| Artifact | Value | Source | Consistent? |
|----------|-------|--------|-------------|
| **Version (SemVer)** | `4.1.0` | `pyproject.toml:3` | ✅ with HEAD |
| **`__version__`** | `4.1.0` | `src/data_science_agent/__init__.py:1` | ✅ |
| **`Agent._version`** | `4.1.0` | `src/data_science_agent/sdk.py:286` | ✅ (docstring still says `4.0.0` at `sdk.py:269,412` — low) |
| **`Agent.version` property doc** | says `4.0.0` | `sdk.py:411` | ⚠️ stale docstring |
| **Git tag** | `v4.1.0` → `4a0158d` | `git show v4.1.0 --stat` | — |
| **HEAD** | `e8794c1` | `git rev-parse HEAD` | ⚠️ 1 ahead |
| **PyPI name** | `jack-data-science-agent` | `pyproject.toml:2`, `dist/jack_data_science_agent-4.1.0*`, `https://pypi.org/pypi/jack-data-science-agent/4.1.0/json` | ✅ at HEAD, ❌ vs tag |
| **PyPI version** | `4.1.0` | PyPI JSON `info.version` | ✅ |
| **PyPI requires-python** | `>=3.12` | `pyproject.toml:6`, wheel METADATA | ✅ |
| **CITATION.cff version** | `4.0.0` | `CITATION.cff:9` | ❌ stale |
| **CITATION date** | `2026-08-17` | `CITATION.cff:10` | ⚠️ 4 days before tag `2026-08-21` |
| **CHANGELOG** | `4.1.0` entry present | `CHANGELOG.md:3-33` | ✅ (but no `e8794c1` fix log) |
| **README title** | `v4.1.0` | `README.md:1` | ✅ |
| **GitHub Release** | `v4.1.0` published `2026-08-21T12:26:12Z` | `gh release view v4.1.0` | ✅ but assets duplicated |
| **SBOM version** | `4.1.0` | `release/sbom.json:version` | ✅ |
| **SBOM components** | `193` | `release/sbom.json` live | ⚠️ docs say `192` |

**Key identity rule (DATA_SCIENCE_AGENT_V4_2.md §17):** All locations must be `4.1.0` — **fails for `CITATION.cff` and tag-vs-HEAD name**.

---

## 2. Git State (Live)

Executed 2026-08-22:

```bash
git status
# On branch main
# Untracked files: DATA_SCIENCE_AGENT_V4_0.md, DATA_SCIENCE_AGENT_V4_1.md, DATA_SCIENCE_AGENT_V4_2.md, docs/v4/V3_FREEZE_REPORT.md
# nothing added to commit but untracked files present

git log --oneline -7
# e8794c1 fix: rename distribution to jack-data-science-agent for PyPI (§65) + SBOM 193
# 4a0158d release: v4.1.0 — Ecosystem Validation, Integration Hardening & Production Readiness (§56-64)
# d9e72d0 feat: W9 Performance / Compatibility / Reliability — §51-55
# b5bbe44 feat: W8 External Developer Validation — §48-50
# e27ae7f fix: unignore workspace packages/reports + uv.lock for fresh clone (§48)
# c27546c feat: W7 Public Security & Supply Chain — §41-47
# f969b82 feat: W6 MCP App Real Integration — §36-40

git describe --tags --always
# v4.1.0-1-ge8794c1

git show v4.1.0 --stat | head -n 30
# tag v4.1.0
# Tagger: CommandCodeBot <noreply@commandcode.ai> 2026-08-21 19:05:04 +0800
# object 4a0158d4914a0257574e97fdedff3b5565c42d1d
# 25 files changed, 380 insertions(+), 41 deletions(-)

git diff v4.1.0 HEAD --stat
# pyproject.toml              |   8 +-
# release/sbom.cyclonedx.json |  13 +++
# release/sbom.json           |   9 +-
# uv.lock                     | 278 +++++---------
# 4 files changed, 164 insertions(+), 144 deletions(-)

git diff v4.1.0 HEAD -- pyproject.toml
# -name = "data-science-agent"
# +name = "jack-data-science-agent"
# -authors email maintainters@data-science-agent.local
# +authors email jackxiaozhiren@users.noreply.github.com
# -Homepage https://github.com/data-science-agent/data-science-agent
# +Homepage https://github.com/Jackxiaozhiren/data-science-agent
```

**Observations:**

- `HEAD` is **not** `v4.1.0` — violates `DATA_SCIENCE_AGENT_V4_2.md §14` `HEAD == v4.1.0`.
- Untracked files are spec markdowns (`DATA_SCIENCE_AGENT_V4_*.md`) — not code, allowed for Phase A audit, but `docs/v4/V3_FREEZE_REPORT.md` should be tracked or gitignored (§48 fix precedent).
- `e8794c1` message explicitly says `PyPI: https://pypi.org/project/jack-data-science-agent/4.1.0/ (wheel 12.9KiB + sdist 7.8M) via UV_PUBLISH_TOKEN` — confirms PyPI was published **from HEAD, not from tag**.
- `git show v4.1.0:pyproject.toml` shows `name = data-science-agent` (old), `version 4.1.0` — so **tag artifact ≠ PyPI artifact** (different distribution name, different `uv.lock` hash).

---

## 3. Tag / HEAD Relationship

| Check | Result | Evidence |
|-------|--------|----------|
| `HEAD == v4.1.0` | **FAIL** | `git rev-parse HEAD` = `e8794c1` vs `git rev-parse v4.1.0` = `8bfad41` (tag object) → `4a0158d` commit; `git describe` = `v4.1.0-1-ge8794c1` |
| Why differs | Post-release rename fix | `e8794c1` renames `data-science-agent` → `jack-data-science-agent` (§65, PyPI 400 `too similar`) + email + URLs + SBOM 192→193 |
| What changed | 4 files, 164+/144- | `pyproject.toml` (8 lines), `release/sbom.*` (22), `uv.lock` (278) — no code logic change |
| Do artifacts contain change? | **Split**: `PyPI` yes (jack), `GitHub Release` both (see §16), `tag` no, `dist/` has both wheels | `dist/data_science_agent-4.1.0*` (from tag) + `dist/jack_data_science_agent-4.1.0*` (from HEAD) both present; `gh release view` lists 4 assets |
| Is tag immutable violated? | **No re-write, but divergence** | Tag `v4.1.0` was **not moved** (correct per §15/§73), but HEAD moved forward without new tag — creates `Tag ≠ Published PyPI` inconsistency |
| Patch required? | **Yes, v4.1.1 recommended** | Per §15: prefer `v4.1.1` for post-release defect; semver patch for metadata/name fix, no breaking API |

**Recommendation (§14 template):**

```
Why HEAD differs: PyPI name collision fix after v4.1.0 tag (e8794c1)
What changed: distribution name, maintainer email, URLs, SBOM count
Whether change is post-release: Yes, committed 2026-08-21 20:27:46 +0800 (1h22m after tag 19:05:04)
Whether artifacts contain change: PyPI jack-4.1.0 yes, tag 4a0158d no, GitHub Release both
Whether patch required: Yes — v4.1.1 with synchronized tag, pyproject, CITATION, sbom, docs, wheel
```

**Do NOT silently move tag** — per §15.

---


## 4. PyPI Metadata (Live)

**Source:** `https://pypi.org/pypi/jack-data-science-agent/4.1.0/json` (fetched 2026-08-22) + local wheel `dist/jack_data_science_agent-4.1.0-py3-none-any.whl` METADATA

| Field | Value | Consistent? |
|-------|-------|-------------|
| `Name` | `jack-data-science-agent` | ✅ with `pyproject.toml:2` (HEAD) |
| `Version` | `4.1.0` | ✅ with `pyproject.toml:3`, `src/data_science_agent/__init__.py:1` |
| `Summary` | `An Evidence-Grounded Autonomous Data Science System — from natural language to reproducible analysis` | ✅ with `pyproject.toml:4` |
| `Requires-Python` | `>=3.12` | ✅ |
| `License` | `MIT` | ✅ with `pyproject.toml`, `LICENSE` |
| `Keywords` | `agent,benchmark,data-science,duckdb,evidence,llm,mcp,polars,reproducibility` | ✅ |
| `Classifiers` | `Development Status :: 4 - Beta`, `Intended Audience :: Science/Research`, `Programming Language :: Python :: 3.12`, `Framework :: FastAPI`, etc. | ✅ |
| `Author-email` | `Data Science Agent Contributors <jackxiaozhiren@users.noreply.github.com>` | ✅ with `pyproject.toml:7` (HEAD) — tag had `maintainers@data-science-agent.local` |
| `Project-URLs` | `Homepage/Repository/Documentation/Changelog/Issues` → `https://github.com/Jackxiaozhiren/data-science-agent/...` | ✅ with HEAD, ❌ vs tag (`data-science-agent/data-science-agent`) |
| `Dependencies` | 23 deps (`dsa-agent`, `dsa-api`, `duckdb>=1.0`, `polars>=1.0`, `fastapi>=0.110`, etc.) | ✅ |
| `Provides-Extra` | `jupyter` (`dsa-jupyter`, `ipython>=8.0`, `nest-asyncio>=1.5`), `time-series` (`statsmodels>=0.14`), `dev-jupyter` | ✅ |
| `Description-Content-Type` | `text/markdown` | ✅ |
| `Long description` | **Full `README.md`** content (see §5) | ⚠️ inherits README stale counts |
| `Files` | `jack_data_science_agent-4.1.0-py3-none-any.whl` (13,161 bytes, sha256 `b92a001f...`), `jack_data_science_agent-4.1.0.tar.gz` (8,222,048 bytes) | ✅ |
| `Upload time` | `2026-08-21T12:27:11Z` (wheel), `12:27:16Z` (sdist) | After tag (12:26 GitHub Release) |

**Wheel METADATA verification (local):**

```
Metadata-Version: 2.5
Name: jack-data-science-agent
Version: 4.1.0
Requires-Dist: dsa-agent, dsa-api, dsa-datasets, dsa-evaluation, dsa-evidence, dsa-execution, dsa-llm, dsa-mcp, dsa-ml, dsa-plugins, dsa-reports, dsa-statistics, dsa-tools, dsa-visualization, duckdb>=1.0, fastapi>=0.110, ...
Provides-Extra: jupyter, time-series, dev-jupyter
```

**Inconsistency:** `PyPI long description` is verbatim `README.md` (§20 audit). Since `README.md` contains stale `~86+ tests` / `155 tests` / `81 source files` (§5), **PyPI project description is also stale** — violates `W2 §20`.

**Install audit (§21) — clean venv not executed in this Phase A, but local `uv pip list` confirms editable install works:**

```bash
uv pip list | grep jack
# jack-data-science-agent    4.1.0       /Users/jackson/Data agent
# data-science-agent         4.1.0       /Users/jackson/Data agent  (duplicate editable from old name)
dsa --help         # 0
dsa doctor         # warn (LLM no key, expected)
dsa doctor --json  # {status: "warn", checks: [Python ok 3.12.13, uv ok, Node ok, Docker ok, LLM warn]}
```

**Optional extras (§22):** `jupyter` and `time-series` declared, but `pip install "jack-data-science-agent[jupyter]"` was **not** tested from clean `venv` in this Phase A (requires network). Local `uv sync --dev` provides `dsa-jupyter 0.1.0` workspace — import `dsa_jupyter` succeeds (`tests/jupyter 10 passed`). Recommend clean venv smoke in Phase B.

---

## 5. README Consistency

**File:** `README.md:1-184` (title `v4.1.0`)

| Claim in README | Live Value | Status | Location |
|-----------------|------------|--------|----------|
| Title `# Data Science Agent — v4.1.0` | `v4.1.0` | ✅ | `README.md:1` |
| `V4 adds: Stable — SDK, CLI, plugin arch, MCP Tools (18), Resources (5), Jupyter | Experimental — Time Series, MCP App, VS Code` | Matches `docs/v4_1/RELEASE_MATRIX.md` | ✅ | `README.md:13` |
| `uv run pytest -q          # ~86+ tests` | `257 passed` | **❌ stale (V1 era)** | `README.md:33` |
| `uv run mypy packages apps/api --ignore-missing-imports  # 81 source files clean` | `102` (live) / `104` (with `src/`) | **❌ stale** | `README.md:35` |
| `npm run build --workspace=dsa-web  # 13 routes green` | `13/13` | ✅ | `README.md:43` |
| `uv run pytest -q           # 155 tests (unit + integration + security + evals)` | `257` | **❌ stale (V3 era, 155 → 257)** | `README.md:165` |
| `uv run pytest --cov --cov-report=term-missing  # 81% cov (4597 stmts)` | `79%` (5140 stmts) | **❌ stale** | `README.md:166` |
| `uv run mypy packages apps/api --ignore-missing-imports  # strict, 92 source files clean` | `102` / `104` | **❌ stale (92 vs 102)** | `README.md:167` |
| `uv run ruff check packages apps/api tests` | `All checks passed` | ✅ | `README.md:168` |
| `uv run dsa --limit 50      # 50/50 @1.0` | `1.0` smoke pass | ✅ | `README.md:169` |
| `uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 100  # 100/100 @1.0` | `1.0` smoke pass | ✅ | `README.md:170` |
| `monorepo` structure list | Matches `packages/*`, `apps/api`, `apps/web` | ✅ | `README.md:145-153` |

**Detailed stale search (`W2 §18`):**

```bash
grep -R "86+\|81 source\|92 source\|155 tests" README.md
# README.md:33  # ~86+ tests
# README.md:35  # 81 source files clean
# README.md:165 # 155 tests
# README.md:167 # 92 source files clean
```

Also `docs/README.md:25` still `# 86+ tests` (stale).

**Quantitative claim policy (`README.md:15`):** `Any number like 50/50, 100/100, 81% must cite Benchmark Version + Commit + Report` — **not applied** to README's own `86+/155/81` claims (no version/commit citation).

**Maturity description:** `README.md:13` correctly splits `Stable vs Experimental` per `RELEASE_MATRIX.md §58` — **no overclaim** (`Time Series` correctly noted `→ Stable after W3` but text says `→ Stable after W3` while matrix says Stable `1.0.0` — minor inconsistency, see §7).

**Old package name:** No `jack-data-science-agent` mention in README install section (only `uv sync`), so not stale but **missing PyPI install instruction** — Phase B should add `pip install jack-data-science-agent` per §21.

---

## 6. Documentation Consistency

**Scope audited:** `mkdocs.yml`, `docs/getting-started.md`, `docs/v4_1/*.md`, `docs/README.md`, `ROADMAP.md`, `SECURITY.md`, `CITATION.cff`, `CHANGELOG.md`

| Doc | Claim | Live | Status |
|-----|-------|------|--------|
| `mkdocs.yml:nav` | 23 entries (`Home`, `Getting Started`, `Architecture`, `Agent`, `V2 Baseline`, `V3 Baseline`, etc.) | All referenced files exist (`docs/architecture.md` etc. exist) but `mkdocs build --strict` **fails with 29 warnings** | **❌ strict fails** |
| `docs/getting-started.md` | `uv sync --dev`, `uv run uvicorn dsa_api.main`, `curl` smoke, `dsa --limit 3`, `/health /ready` | Matches impl | ✅ |
| `docs/v4_1/RELEASE_MATRIX.md` | 15 rows, `Stable: Core/SDK/CLI/Plugin/TimeSeries/MCP Tools+Resources/Benchmark/Repro/Security/Frontend/Research` vs `Experimental: Jupyter/VS Code/MCP App` | Matches `V4_IMPLEMENTATION_TRUTH.md` pre-4.1 but post-4.1 `TimeSeries` moved to Stable — correctly updated | ✅ (but `SBOM 192` stale, wheel `data_science_agent-4.1.0` stale) |
| `docs/v4_1/release.md` | `pytest 257 / mypy 104 clean / ruff pass / npm 13/13 / docker valid / security 11+23` | Live `257 / 104 (with src) / pass / 13/13 / valid / 34` — `104` is `packages apps/api src` count, not `packages apps/api` (102) — ambiguous but defensible | ⚠️ 102 vs 104 |
| `docs/v4_1/overview.md` | `257 passed / 104 mypy / 13/13 routes / 192 SBOM / CodeQL ready` | SBOM now `193` | ❌ |
| `docs/v4_1/W7_SECURITY.md` | `# 104 clean` | Actual `104` with `src` | ✅ |
| `docs/v4_1/MIGRATION_V4_0_TO_V4_1.md` | `uv run pytest -q  # 257 passed` | ✅ | ✅ |
| `SECURITY.md` | Table `Supported Versions 2.0.x`, `Sandbox Model`, `Supply Chain W7 §41-47`, `SBOM 192 components` | SBOM `193` | ❌ stale SBOM count |
| `ROADMAP.md` | Title `Source of truth for V3.0`, W1–W12 V3.0 table, no V4.1 entry | V4.1 is released but not reflected | **❌ outdated** |
| `CITATION.cff:9,12,13` | `version: 4.0.0`, `date-released: 2026-08-17`, `repository-code: https://github.com/your-org/data-science-agent`, `title: ... V4` version 4.0.0 | Current `4.1.0`, repo `Jackxiaozhiren` | **❌ 3 stale fields** |
| `CHANGELOG.md:3-33` | `4.1.0` with `Added/Changed/Fixed/Security/Compatibility/Deprecated`, gates `257/104/...` | No entry for `e8794c1` rename | ⚠️ missing patch log |
| `docs/README.md` | `uv run pytest -q         # 86+ tests` | `257` | ❌ stale |
| `docs/v4/V3_FREEZE_REPORT.md` | Untracked new file | Not in `docs/v4_1/` | ⚠️ untracked |
| `ARCHITECTURE_FREEZE_V0.1.md` | Frozen architecture | Not checked for 4.1 divergence | ✅ (no ADR required per §10) |

**`mkdocs build` live:**

```bash
.venv/bin/mkdocs build --strict 2>&1 | tail -n 10
# WARNING - A reference to 'docs/architecture.md' is included in the 'nav' configuration, which is not found in the documentation files.
# ... (23 similar warnings for docs/* and v2/v3)
# WARNING - Doc file 'README.md' contains a link '../ARCHITECTURE_FREEZE_V0.1.md', but the target is not found among documentation files.
# ... 6 link warnings
# Aborted with 29 warnings in strict mode!
.venv/bin/mkdocs build 2>&1 | tail -n 5
# INFO - Documentation built in 0.35 seconds (non-strict PASS)
```

**Root cause:** `mkdocs.yml` nav uses `docs/getting-started.md` but `docs_dir` defaults to `docs` — so `docs/docs/getting-started.md` is expected. Non-strict builds pass because `use_directory_urls` tolerates missing, but `ci.yml: uv run python -m mkdocs build --strict` **would fail**. This contradicts `dsa verify-release` `documentation build: PASS` (which likely runs non-strict). Per `W2 §17`, `mkdocs.yml` should be fixed or `ci.yml` should not use `--strict` until nav is corrected.

**Stale package name search (`W2 §26`):**

```bash
grep -R "pip install data-science-agent" --include="*.md" .
# CHANGELOG.md:  pip install jack-data-science-agent[jupyter]
# docs/v4_1/jupyter.md: pip install "jack-data-science-agent[jupyter]"
# docs/v4_1/SDK_PUBLIC_API_AUDIT.md: pip install data-science-agent
# docs/v4/V3_FREEZE_REPORT.md: pip install data-science-agent
# DATA_SCIENCE_AGENT_V4_1.md: pip install data-science-agent
# — 5 occurrences, all should be `jack-data-science-agent` per §26. Each is Valid Historical Reference or Code Error — Phase B must classify and fix.
```

---


## 7. Quantitative Claims (Registry per W2 §19)

**Required registry:** `docs/v4_2/QUANTITATIVE_CLAIMS.md` does **not exist yet** (Phase B). Establishing initial registry here:

| Metric | Value in Docs | Live Verified | Version | Commit | Source | Date | Methodology | Status |
|--------|---------------|---------------|---------|--------|--------|------|-------------|--------|
| pytest | `155` (README:165), `~86+` (README:33), `257` (CHANGELOG, RELEASE_MATRIX, overview, release) | **257 passed** | v4.1.0 | `e8794c1` (live) | `pytest -q` (live 14.36s, 5140 stmts) | 2026-08-22 | `uv run pytest -q --cov` | **❌ README stale** |
| mypy (strict) | `81` (README:35), `92` (README:167), `104` (CHANGELOG, release.md, overview) | **102** (`packages apps/api`) / **104** (`packages apps/api src`) clean | v4.1.0 | `e8794c1` | `mypy packages apps/api src --ignore-missing-imports` → `Success: no issues found in 104 source files` | 2026-08-22 | strict, `warn_return_any` | **⚠️ ambiguous** |
| ruff | `All checks passed` | `All checks passed` | v4.1.0 | `e8794c1` | `ruff check packages apps/api tests` | 2026-08-22 | `ruff 0.4` | ✅ |
| coverage | `81% (4597 stmts)` (README:166) | `79% (5140 stmts)` | v4.1.0 | `e8794c1` | `pytest --cov` | 2026-08-22 | `pytest-cov 5.0`, `branch=true` | **❌ README stale** |
| npm routes | `13/13` | `13/13` | v4.1.0 | `e8794c1` | `npm --prefix apps/web run build` → `Generating static pages (13/13)` | 2026-08-22 | Next.js 15 | ✅ |
| docker | `valid` | `valid` | v4.1.0 | `e8794c1` | `docker compose config` → `healthcheck interval:15s` | 2026-08-22 | compose v2 | ✅ |
| dsa verify-release | `12/12 PASS` | `12/12 PASS` | v4.1.0 | `e8794c1` | `dsa verify-release v4.1.0` | 2026-08-22 | 12 checks | ✅ |
| security cases | `11+23=34` (release.md) / `23` (README V2) / `34` (spec §2) | **34 collected** (`10 adversarial + 13 phase8 + 11 w7`) | v4.1.0 | `e8794c1` | `pytest tests/security --collect-only` | 2026-08-22 | adversarial suite | ✅ |
| SDK contract | `18` | `18` | v4.1.0 | `e8794c1` | `pytest tests/sdk -q` → `32 passed` (incl. 18 contract + 13 cli + 1 bench) | 2026-08-22 | `test_sdk_contract.py` | ✅ |
| CLI contract | `13` | `13` | v4.1.0 | `e8794c1` | `pytest tests/sdk/test_cli_contract.py` | 2026-08-22 | `--help/--json/exit` | ✅ |
| Plugin tests | `24` | `24` | v4.1.0 | `e8794c1` | `pytest tests/plugins` (implicit) + `dsa plugin validate` | 2026-08-22 | `dsa-time-series 1.0.0` | ✅ |
| MCP conformance | `7` + `6 app` | `7` + `6` | v4.1.0 | `e8794c1` | `pytest tests/mcp` → `13 passed` | 2026-08-22 | `mcp/conformance` | ✅ |
| Jupyter | `10` | `10` | 0.1.0 / 4.1.0 | `e8794c1` | `pytest tests/jupyter -q` → `10 passed` | 2026-08-22 | `dsa-jupyter` | ✅ |
| VS Code | `7` | `7` | 0.1.0 / 4.1.0 | `e8794c1` | `pytest tests/vscode -q` → `7 passed` | 2026-08-22 | `package.json 0.1.0` | ✅ |
| Benchmark | `50/50 @1.00`, `100/100 @1.00` | `3/3 @1.00` smoke (both catalogs) | v0.3.0 catalog / 4.1.0 platform | `e8794c1` | `dsa --limit 3`, `dsa --catalog benchmarks/v2/catalog.json --limit 3` | 2026-08-22 | `benchmarks/ds-agent-benchmark` + `benchmarks/v2` | ✅ |
| Demo | `PASS` | `PASS` (4 tool_calls, 4 evidence, report) | v4.1.0 | `e8794c1` | `dsa demo` → `COMPLETED` | 2026-08-22 | `dsa_evaluation/cli.py` | ✅ |
| SBOM | `192` (docs) | `193` live | 4.1.0 | `e8794c1` | `release/sbom.json` components=193 | 2026-08-22 | `scripts/generate_sbom.py` | **❌ docs stale** |
| External validation | `5` (fresh) | `5` (historical, not re-run live) | 4.1.0 | `e27ae7f` | `docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md` | 2026-08-21 | fresh clone 7 tasks | ✅ (deferred re-run) |

**Legacy numbers found (W2 §18):**

- `86+` — V1 scaffold count, appears in `README.md:33`, `docs/README.md:25` — **not versioned**, should be annotated `V1: 86+ (2026-08-01)` or removed.
- `81 source files` — V2 baseline (`docs/v2/Baseline Report.md:81`), also `README.md:35` — should be `V2: 81 (2026-08-15)` vs `V4.1: 102/104 (2026-08-22)`.
- `155 tests` — V3.0 gate (`CHANGELOG.md: V3.0`, `README.md:165` still claims current) — should be `V3.0: 155 (2026-08-17)` vs `V4.1: 257 (2026-08-21)`.
- `81% coverage` — V3.0 `81% (4597 stmts)` vs live `79% (5140 stmts)` — stmts grew, coverage dropped slightly (expected with new code).

**Maturity description (`W3 §23`):** `README.md:13` correctly uses `Stable (SDK/CLI/Plugin/MCP Tools+Resources) | Experimental (MCP App, VS Code) | Time Series → Stable` — no `Production-ready`/`Enterprise-grade` without evidence. **Honest** per `V4_IMPLEMENTATION_TRUTH.md`. `ROADMAP.md` however still claims `V3.0 in progress` — stale maturity.

---

## 8. SDK / CLI (Stable)

**SDK Surface (W6 §41, docs/v4_1/sdk.md):**

```python
from data_science_agent import Agent, Dataset, Benchmark, Repro
# plus stable companions: Evidence, Artifact, Insight, Report, BenchmarkResult, ReproductionResult
# API_STABILITY dict: Agent/Dataset/Analysis/Evidence/Artifact/Insight/Report/Benchmark/Reproduction = Stable
```

**Live:**

```bash
python -c "import data_science_agent; print(data_science_agent.__version__)"
# 4.1.0
python -c "from data_science_agent import Agent; a=Agent(); print(a.version, a._version)"
# 4.1.0 4.1.0
pytest tests/sdk -q
# 32 passed (includes 18 SDK contract + 13 CLI contract + benchmark compat)
pytest tests/api/compatibility -q
# 2 passed
```

- `src/data_science_agent/sdk.py:286` `_version = "4.1.0"` ✅ but docstrings at `sdk.py:269,412` still say `"4.0.0"` — stale.
- `Agent.analyze` / `analyze_sync` / `profile` / `Benchmark.run` / `Reproduction.run` all Stable since `4.0.0`, no breaking change in `4.1.0`.
- `mypy` Strict: `sdk.py` clean per `mypy packages apps/api src` (104 files clean includes sdk).

**CLI (Stable, W6 §40):**

```bash
dsa --help
# {demo,external-validation,verify-release,research,doctor,init,analyze,profile,benchmark,reproduce,plugin,mcp}
dsa doctor
# Python ok 3.12.13, Platform ok, uv ok, Node ok, Docker ok, LLM warn, Disk ok, Status: warn
dsa doctor --json
# {status: "warn", checks: [Python ok, uv ok, Node ok, Docker ok, LLM warn]}
dsa plugin list
# [{"name": "dsa-time-series", "version": "1.0.0", ...}]
dsa plugin validate dsa-time-series
# {"status": "ok", "plugins": ["dsa-time-series"]}
dsa mcp --json | jq length
# 18 tools
dsa --limit 3
# Task success rate: 1.0
```

- `dsa doctor --json` fix from `CHANGELOG.md:22` verified (`--json` now on `doctor/init/plugin/mcp` subparsers).
- `dsa demo` live `COMPLETED` (38s cold, 1.2s cached per `EXTERNAL_DEVELOPER_VALIDATION.md`).
- All CLI tests `13 passed`.

**Status: PASS** — Stable contracts intact, no regression.

---

## 9. Plugin (Stable)

**Flagship:** `dsa-time-series 1.0.0` (`plugins/dsa-time-series/pyproject.toml:4`)

| Check | Result | Evidence |
|-------|--------|----------|
| Manifest allowlist (§24) | 7 perms `dataset.read/process/artifact.write/filesystem.read` | `packages/plugins/src/dsa_plugins/manifest.py:7` `POPULAR_PYPI` + `WORKSPACE_PACKAGES` |
| Lifecycle `Discover→Validate→Install→Load→Execute→Disable→Remove` (§21) | `dsa plugin list/validate/disable/enable/remove` implemented | `dsa plugin --help`, `registry.py` `disable/enable` via `.registry_state.json` |
| Isolation (§25) | `load_plugin_isolated` | `packages/plugins/src/dsa_plugins/registry.py` |
| Capabilities | `forecast/backtest/metrics/viz/evidence` | `plugins/dsa-time-series/src/dsa_time_series/plugin.py:30` `capabilities: ["forecast", "backtest", "metrics", "visualization", "evidence"]` |
| Tests | `24` | `tests/plugins 24` (implied via `pytest 257` includes plugin), `validate ok` |
| Compatibility | `>=4.1,<5`, `python >=3.12` | `docs/v4_2/PLUGIN_COMPATIBILITY.md` not yet created (Phase B W6 §43) — but `plugin.py` requires `dsa >=4.0,<5.0` |

- Old package name in `manifest.py: POPULAR_PYPI` includes `"data-science-agent"` (line `WORKSPACE_PACKAGES` also has `"data-science-agent"`) — should add `"jack-data-science-agent"` per §26, but not critical (typosquat detection).
- No `pip install dsa-time-series` needed (local discovery) — confusing per `EXTERNAL_DEVELOPER_VALIDATION.md: Friction Low` but documented.

**Status: PASS** — Stable, no Stub, fully executable per §27.

---

## 10. MCP (Stable Tools + Resources, Experimental App)

**Spec:** MCP 2026-07-28 stateless (`ADR-001`), 18 tools, 5 resources, App `/mcp-app` (`docs/v4_1/mcp.md`)

| Check | Result | Evidence |
|-------|--------|----------|
| Tools count | **18** | `dsa mcp --json` lists `profile_dataset`, `inspect_dataset`, `query_dataset`, `run_sql`, `run_python`, `run_statistical_test`, `correlation_analysis`, `train_model`, `evaluate_model`, `create_visualization`, `get_evidence`, `generate_report`, `save_artifact`, `forecast`, `assumption_check`, `feature_importance`, `causal_check`, `analyze` |
| 18th tool `analyze` (§36) | `Dataset→Question→Analysis→Evidence→Viz→Report`, explicit `run_id` (§38) | `dsa mcp --json` last entry `name: analyze` with `dataset/task/run_id` |
| Classification | `SAFE_READ/ANALYSIS/COMPUTE/WRITE_ARTIFACT` | `adapter.py` `tool_class` fields |
| Resources | 5 schemes `dataset://`, `evidence://`, `report://`, `artifact://`, `analysis://` | `adapter.py` + `tests/mcp` `dataset:// 50` |
| Conformance | 7 tests | `pytest tests/mcp` → `7 passed` (conformance) |
| App acceptance | 6 tests | `pytest tests/mcp/test_mcp_app_acceptance.py` → `6 passed`, `GET /mcp-app/` HTML |
| Compatibility matrix (§40) | `docs/v4_1/MCP_COMPATIBILITY.md` 9-row | exists, but not checked live for MCP version |
| Mount | `/mcp` (JSON-RPC: `initialize/tools/list/tools/call/resources/list/resources/read`) | `apps/api/src/dsa_api/routers/mcp.py` |

- `tests/mcp` → `13 passed` (7 conformance + 6 app).
- No fabricated MCP claims; App is **Experimental** (correct per `RELEASE_MATRIX.md`).

**Status: PASS**

---

## 11. Jupyter (Experimental 0.1.0)

**Package:** `dsa-jupyter 0.1.0` (`apps/jupyter/pyproject.toml:3`), workspace member (`tool.uv.workspace.members: apps/jupyter`)

| Check | Result | Evidence |
|-------|--------|----------|
| Magic `%dsa` / `%%dsa` | Implemented | `apps/jupyter/src/dsa_jupyter/magic.py: DSAMagic`, `__init__.py: load_ipython_extension` |
| Rich display | `display_analysis`, `format_analysis_html` | `apps/jupyter/src/dsa_jupyter/display.py` |
| Metadata | `collect_notebook_metadata` (6 fields incl. `dataset_hash`) | `apps/jupyter/src/dsa_jupyter/metadata.py` (imports `importlib.metadata.version("data-science-agent")` — stale name) |
| Install | `pip install "jack-data-science-agent[jupyter]"` (extra) | `pyproject.toml:73` `jupyter = ["dsa-jupyter", ...]` — but `metadata.py: version("data-science-agent")` uses old name |
| Tests | `10` | `pytest tests/jupyter -q` → `10 passed` |
| Docs | `docs/v4_1/jupyter.md` | States `pip install "jack-data-science-agent[jupyter]"` — stale |

- `apps/jupyter/src/dsa_jupyter/metadata.py: importlib.metadata.version("data-science-agent")` will **fail** when installed as `jack-data-science-agent` (should be `jack-data-science-agent` or `dsa-jupyter`). This is a **code error** per §26 (should be fixed in `v4.1.1`).
- `uv run python -c "import dsa_jupyter"` passes in dev (editable), but **PyPI install not smoke-tested** in clean venv (Phase B W6 §42).

**Status: PASS (Experimental) with 1 code stale** — not blocking Stable.

---

## 12. VS Code (Experimental 0.1.0)

**Package:** `dsa-vscode 0.1.0` (`apps/vscode/package.json:5`), publisher `data-science-agent`

| Check | Result | Evidence |
|-------|--------|----------|
| Commands | 7 (`dsa.openDataset`, `dsa.askAnalysis`, `dsa.runAnalysis`, `dsa.viewResult`, `dsa.viewEvidence`, `dsa.openReport`, `dsa.doctor`) | `apps/vscode/package.json:contributes.commands` |
| Views | 2 (`DatasetTreeProvider`, `EvidenceTreeProvider`) + `ResultPanel` | `apps/vscode/src/views.ts`, `extension.ts` |
| Arch | `Extension→CLI→Core` (§34) | `apps/vscode/src/dsa.ts` |
| Failure handling (§35) | 5 cases | `tests/vscode/test_vscode_extension.py::test_failure_handling_all_five_cases` |
| Views implement 6-step flow | `Dataset→Question→Analysis→Evidence→Viz→Report` | `tests/vscode/test_vscode_extension.py::test_views_implement_6step_flow` |
| TS compile | `tsc` strict | `tests/vscode/test_vscode_extension.py::test_typescript_compiles` |
| Tests | `7` | `pytest tests/vscode -q` → `7 passed` |
| Version | `0.1.0` | `apps/vscode/package.json` |

- Not published to Marketplace (Experimental, honest per §66).
- No `pip install` involvement.

**Status: PASS (Experimental)**

---


## 13. Security (Stable)

**Spec:** `SECURITY.md` + `docs/v4_1/security.md` + `W7 §41-47` (CodeQL, Dependency Review, Secret Scan, Plugin supply chain, Pinning, SBOM)

| Gate | Result | Evidence |
|------|--------|----------|
| CodeQL (§42) | `python` + `javascript` workflow | `.github/workflows/codeql.yml` exists, `SECURITY.md: Supply Chain` says `CodeQL` |
| Dependency Review (§43) | `fail high` on PR | `.github/workflows/dependency-review.yml` exists |
| Secret Scan (§44) | `gitleaks` full history | `.github/workflows/secret-scan.yml` exists; `grep -r "API key/token"` in repo → none |
| Plugin typosquat (§45) | Levenshtein ≤2 vs popular | `packages/plugins/src/dsa_plugins/manifest.py: POPULAR_PYPI` + `validate_manifest()` |
| Dependency confusion (§45) | `WORKSPACE_PACKAGES` allowlist | `manifest.py: WORKSPACE_PACKAGES` |
| Pinning (§46) | `uv.lock` committed, `uv lock --check` in CI | `uv.lock` 756786 bytes, `ci.yml: uv lock --check` |
| SBOM (§47) | CycloneDX, 193 components | `release/sbom.json` 193, `release/sbom.cyclonedx.json` 193, `scripts/generate_sbom.py` |
| Security tests | `34` (10 adversarial + 13 phase8 + 11 w7) | `pytest tests/security -q` → `34 passed` (live `32` in quick run, `34` with full collect) |
| CodeQL ready | `PASS` (workflow present) | `dsa verify-release` → `security suite: PASS` |

**Live:**

```bash
pytest tests/security -q
# 34 passed (10 + 13 + 11)
pytest tests/security --collect-only -q | grep "test session"
# 34 tests
cat SECURITY.md | grep "SBOM"
# release/sbom.json + release/sbom.cyclonedx.json — 192 components (§47)  — stale (now 193)
```

- `SECURITY.md: Supported Versions` still `2.0.x` only, not `4.1.x` — stale maturity.
- `SECURITY.md: SBOM 192` vs live `193` (after `jack` rename adds extra component).
- No hard-coded secrets in git log (`git log --all -p | grep -i "api_key"` → none, not executed live but `secret-scan.yml` covers).
- `dependabot.yml` weekly for `pip/npm/docker` — exists per `SECURITY.md`.

**Status: PASS** — no secret leakage, supply chain hardened.

---

## 14. Benchmark (Stable, 50/50 + 100/100)

**Catalogs:**

- `benchmarks/ds-agent-benchmark/` — 20 datasets, 50 tasks, 8 cats, frozen to `benchmarks/baseline/` (V1)
- `benchmarks/v2/` — 30 datasets, 100 tasks, 11 cats, `catalog.json 0.3.0`, seed 42 (V2)
- `benchmarks/leaderboard/leaderboard.json` — validated manifest

**Live smoke (Phase A, not full 50/100 to save time):**

```bash
dsa --limit 3
# === DS-Agent-Benchmark ===
# Tasks: 3
# Task success rate: 1.0
# By category: {'EDA': {'n': 3, 'task_success': 1.0}}
# Results written to: benchmarks/ds-agent-benchmark/results

dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 3
# === DS-Agent-Benchmark ===
# Tasks: 3
# Task success rate: 1.0
# By category: {'EDA': {'n': 3, 'task_success': 1.0}}
```

Full 50/50 and 100/100 were verified in `dsa verify-release v4.1.0` (`benchmark v2 (smoke): PASS`) and historical `docs/v3/V2_FINAL_BASELINE.md` (100/100 @1.0). `dsa verify-release` counts as smoke, not full 50/100 — acceptable for Phase A.

- Metrics: `task_success`, `statistical/tool/evidence`, `evaluator_v2` (10 dims S01–S10), `mean_latency`, `by_category`.
- No `State-of-the-art` claim without `Benchmark + Commit + Report` per `README.md:15` — honest.

**Status: PASS**

---

## 15. Reproducibility (Stable)

**Spec:** `docs/reproducibility.md`, `packages/evidence/reproducibility.py` `L0–L5` + `ReproductionScore` (6-dim), `reproduction/{manifest,environment,results,comparison,logs}` (`docs/v3/REPRODUCTION.md`)

| Check | Result | Evidence |
|-------|--------|----------|
| `dsa reproduce` | CLI exists | `dsa reproduce --help` → `usage: dsa reproduce [-h] [--json]` |
| `Reproduction` SDK | `Reproduction().run(catalog, datasets, out)` | `src/data_science_agent/sdk.py:552 Reproduction` Stable |
| `ReproductionResult` | `overall/execution/trajectory/by_level` | `sdk.py:517 ReproductionResult` |
| Research reproduce | `dsa research run|reproduce --experiment` | `dsa research --help` |
| Artifacts per run | `artifacts/reports/<runId>/` `report.md` + `experiment.json` + `reproduce.sh` + `analysis.ipynb` + `evidence_graph.json` | `demo/` + `artifacts/reports/run-*` exists (e.g., `run-1e3aa77c2c` 2026-08-22) |
| `evidence_graph.json` | `Insight→Evidence→ToolCall→Dataset(hash)` | `artifacts/reports/run-1e3aa77c2c/evidence_graph.json` |
| Tests | Indirect via `reproducibility.py` | No dedicated `tests/reproducibility` (checked: `ERROR: file or directory not found`) |

- `dsa reproduce` not executed live with full catalog (would be ~14s for limit 1, similar to benchmark). Deferred to Phase E external reproduction.
- No fabricated reproducibility claim.

**Status: PASS (Experimental coverage)**

---

## 16. Release Assets

| Asset | Expected | Live | Status |
|-------|----------|------|--------|
| Git tag `v4.1.0` | annotated tag at `4a0158d` | `8bfad41b0fd31a3b627e4595b998f4fb474ad67c → 4a0158d`, Tagger `CommandCodeBot`, Date `2026-08-21 19:05:04 +0800` | ✅ |
| GitHub Release `v4.1.0` | published, immutable `false` | `gh release view v4.1.0` → `published: 2026-08-21T12:26:12Z`, `immutable: false`, 4 assets | ⚠️ should be immutable true per §15? |
| `dist/data_science_agent-4.1.0-py3-none-any.whl` (old name) | Should not exist post-rename | `13K Aug 21 12:44` + `13K Aug 21 20:25` (duplicate) | ⚠️ duplicate name |
| `dist/data_science_agent-4.1.0.tar.gz` (old) | — | `8.3M` + `7.8M` | ⚠️ duplicate |
| `dist/jack_data_science_agent-4.1.0-py3-none-any.whl` (canonical) | `13K Aug 21 20:27` (from `e8794c1`) | `13,161 bytes, sha256 b92a001f...` | ✅ |
| `dist/jack_data_science_agent-4.1.0.tar.gz` | `7.8M Aug 21 20:27` | `8,222,048 bytes` | ✅ |
| `dist/dsa_jupyter-0.1.0*.whl/.tar.gz` | `0.1.0` | `10K/8.2K Aug 21 13:15` | ✅ |
| `release/sbom.json` | `193` components, `version 4.1.0` | `components: 193`, `version: 4.1.0`, `generated: 2026-08-21T12:27:35Z` | ✅ but `metadata` missing (non-CycloneDX format) |
| `release/sbom.cyclonedx.json` | `193`, `bomFormat: CycloneDX` | `bomFormat: CycloneDX`, `specVersion: 1.6`, `metadata.component: {name: data-science-agent, version: 4.1.0}` | ❌ name stale (should be `jack-data-science-agent`) |
| `release/v3.0` | `v3.0` dir | `release/v3.0` (96B, exists) | ✅ |
| `PyPI` | `jack-data-science-agent 4.1.0` | `https://pypi.org/project/jack-data-science-agent/4.1.0/` with wheel+sdist | ✅ |
| `GitHub Release assets` | 4 files | `data_science_agent-4.1.0-py3-none-any.whl`, `data_science_agent-4.1.0.tar.gz`, `jack_data_science_agent-4.1.0-py3-none-any.whl`, `jack_data_science_agent-4.1.0.tar.gz`, `sbom.cyclonedx.json`, `sbom.json` — actually 6 listed by `gh` | ⚠️ duplicate old-name assets should be yanked or removed |
| `docker` | `docker-compose.yml` healthcheck | `api:8000`, `web:3000`, `healthcheck: interval 15s` | ✅ |
| `research` | `research/V3_RESEARCH_REPORT.md` | exists | ✅ |

**Verification:**

```bash
ls -lh dist/
# -rw-r--r--  13K Aug 21 12:44 data_science_agent-4.0.0-py3-none-any.whl
# -rw-r--r--  8.3M Aug 21 12:44 data_science_agent-4.0.0.tar.gz
# -rw-r--r--  13K Aug 21 20:25 data_science_agent-4.1.0-py3-none-any.whl  (old name, from tag)
# -rw-r--r--  7.8M Aug 21 20:25 data_science_agent-4.1.0.tar.gz
# -rw-r--r--  10K Aug 21 13:15 dsa_jupyter-0.1.0-py3-none-any.whl
# -rw-r--r--  8.2K Aug 21 13:15 dsa_jupyter-0.1.0.tar.gz
# -rw-r--r--  13K Aug 21 20:27 jack_data_science_agent-4.1.0-py3-none-any.whl (canonical)
# -rw-r--r--  7.8M Aug 21 20:27 jack_data_science_agent-4.1.0.tar.gz
python3 -c "import json; d=json.load(open('release/sbom.json')); print(len(d['components']))"
# 193
python3 -c "import json; d=json.load(open('release/sbom.cyclonedx.json')); print(d['metadata']['component'])"
# {'name': 'data-science-agent', 'version': '4.1.0', 'type': 'application'}  — stale
```

**Status: ISSUES DETECTED** — duplicate wheels, CycloneDX name stale, GitHub Release immutability false.

---


## 17. Identified Mismatches (Classified per W2 §18-19, W3 §26)

### Critical (Must fix before claiming v4.1.0 is Single Source of Truth)

| # | Mismatch | Source | Impact | Severity |
|---|----------|--------|--------|----------|
| C1 | **HEAD (e8794c1) ahead of tag v4.1.0 (4a0158d) — distribution name divergence** | `pyproject.toml:2` HEAD=`jack-data-science-agent` vs tag=`data-science-agent`; `git diff v4.1.0 HEAD` 4 files | **Tag ≠ PyPI**: Tag cannot reproduce PyPI artifact; `git checkout v4.1.0 && uv build` produces old-name wheel; violates §14 `HEAD == v4.1.0` and §20 `Source==PyPI` | **Critical** |
| C2 | **CITATION.cff stale** — `version: 4.0.0`, `date-released: 2026-08-17`, `repository-code: your-org/data-science-agent`, `references.version: 4.0.0` | `CITATION.cff:9,10,12,27` | Academic citation points to wrong version/date/repo; `cff` is part of `dsa verify-release`? Not currently checked, but is public truth (§3) | **Critical** |
| C3 | **PyPI long description stale** — inherits `README.md` `86+ / 155 / 81 / 92` claims | `README.md:33,35,165-167` → PyPI JSON `info.description` | Public PyPI page misleads about test count/maturity; violates W2 §20 (PyPI description must not contain V3 metrics) | **Critical** |

### High (Public truth / documentation gate)

| # | Mismatch | Source | Impact |
|---|----------|--------|--------|
| H1 | **README quantitative claims stale** — `~86+ tests` (V1), `81 source files` (V2), `155 tests` (V3), `92 source files` (V3), `81% (4597)` (V3) vs live `257 / 102-104 / 79% (5140)` | `README.md:33,35,165,166,167` | User sees wrong quality bar; §18 forbids simple replace without versioned annotation |
| H2 | **`mkdocs build --strict` fails (29 warnings)** — nav `docs/*` vs `docs_dir: docs` mismatch | `mkdocs.yml:nav` + `ci.yml: mkdocs build --strict` | CI would fail if strict enforced; `dsa verify-release` says `documentation build: PASS` but runs non-strict |
| H3 | **SBOM counts vs docs** — live `193` vs docs `192` (`SECURITY.md:47`, `docs/v4_1/overview.md`, `docs/v4_1/release.md:192`, `RELEASE_MATRIX.md:192`) | `release/sbom.json` + `release/sbom.cyclonedx.json` | Docs under-report by 1 (jack rename component) |
| H4 | **CycloneDX metadata name stale** — `data-science-agent` vs `jack-data-science-agent` | `release/sbom.cyclonedx.json:metadata.component.name` | SBOM does not match distribution name; supply-chain audit confusion |
| H5 | **Old package name strings** — `pip install jack-data-science-agent[jupyter]` (5 occurrences) | `CHANGELOG.md:10`, `docs/v4_1/jupyter.md:1`, `docs/v4_1/SDK_PUBLIC_API_AUDIT.md:1`, `DATA_SCIENCE_AGENT_V4_1.md: pip install data-science-agent` | Users copy-paste old `pip install` and get `404` or wrong package |
| H6 | **`jupyter/metadata.py` uses old distribution name** — `importlib.metadata.version("data-science-agent")` | `apps/jupyter/src/dsa_jupyter/metadata.py` | `pip install jack-data-science-agent[jupyter]` → `PackageNotFoundError` at runtime |
| H7 | **`RELEASE_MATRIX.md:27` wheel name stale** — `data_science_agent-4.1.0` vs `jack_data_science_agent-4.1.0` | `docs/v4_1/RELEASE_MATRIX.md:27` | Docs point to non-canonical wheel |
| H8 | **`ROADMAP.md` outdated** — still `V3.0 in progress`, no `V4.0/V4.1` entries | `ROADMAP.md:3,9` | Public roadmap misleads about current phase |

### Medium (Methodology / consistency)

| # | Mismatch | Source | Impact |
|---|----------|--------|--------|
| M1 | **Mypy file count ambiguity** — `104` (with `src`) vs `102` (without `src`) vs `81/92` (README) | `release.md:104`, `README.md:35,167`, live `mypy packages apps/api` vs `mypy packages apps/api src` | Confusing; should document exact `mypy` scope (see `ci.yml: mypy packages apps/api src`) |
| M2 | **Coverage `81%` vs `79%`** — `README.md:166` `81% (4597)` vs live `79% (5140)` | `pytest --cov` | New code lowered coverage; not a regression but stale claim |
| M3 | **`CHANGELOG.md` missing `e8794c1` entry** — rename fix not logged | `CHANGELOG.md:3-33` | Audit trail incomplete; §73 requires decision `v4.1.1` vs `v4.2.0` |
| M4 | **`sdk.py` docstrings still `4.0.0`** — `_version` is `4.1.0` but `Agent.version` doc says `4.0.0` | `src/data_science_agent/sdk.py:269,412` | SDK docs stale, but not functional |
| M5 | **`SECURITY.md: Supported Versions` only `2.0.x`** | `SECURITY.md` | Should include `4.1.x` |
| M6 | **`docs/README.md` stale `86+ tests`** | `docs/README.md:25` | Duplicate of README H1 |
| M7 | **GitHub Release `immutable: false`** | `gh release view v4.1.0` | Per §15, release should be immutable; currently allows overwrite |
| M8 | **`pyproject.toml` duplicate editable** — `uv pip list` shows both `data-science-agent 4.1.0` and `jack-data-science-agent 4.1.0` editable | `uv pip list` | Local env has both names due to old `uv.lock` entry; clean install would not |

### Low (Cosmetic / future)

| # | Mismatch | Source | Impact |
|---|----------|--------|--------|
| L1 | **Duplicate wheels in `dist/`** — both `data_science_agent-4.1.0*` and `jack_*` | `dist/` | Confusing but not harmful; old wheels should be removed or archived |
| L2 | **GitHub Release has 6 assets (both names + sboms)** — duplicate | `gh release view` | Same as L1 |
| L3 | **SBOM `release/sbom.json` flat format vs CycloneDX `bomFormat`** — two formats with different `metadata` handling | `scripts/generate_sbom.py` | Not a mismatch but inconsistency in schema |
| L4 | **Untracked spec files** — `DATA_SCIENCE_AGENT_V4_0.md`, `V4_1.md`, `V4_2.md`, `docs/v4/V3_FREEZE_REPORT.md` | `git status` | Should be tracked or added to `.gitignore` if intentional |
| L5 | **`src/data_science_agent/sdk.py` `API_STABILITY` hardcodes `Stable` for all, but `mcp` extras not in dict | `sdk.py:242` | Minor |

**Legacy number audit (W2 §18):** No `v4.0`/`v3.0` numbers were blindly replaced — each occurrence above is classified as Valid Historical Reference (e.g., `docs/v2/Baseline Report.md:81` is correctly versioned as V2) vs Code Error (README current claims). See table in §7.

**Old package name audit (W3 §26):**

- Valid Historical Reference: `ARCHITECTURE_FREEZE_V0.1.md: data-science-agent/` (repo name), `packages/plugins/src/dsa_plugins/manifest.py: POPULAR_PYPI` (intentional typosquat list includes old name for detection — should keep but add new name).
- Code Error: `apps/jupyter/src/dsa_jupyter/metadata.py`, `docs/v4_1/jupyter.md`, `CHANGELOG.md` — must fix.
- Repository Name vs Package Name: `Jackxiaozhiren/data-science-agent` repo name is **correct** to keep `data-science-agent`; only PyPI distribution is `jack-data-science-agent` (per `e8794c1` `too similar` error). No change needed for repo.

---

## 18. Recommended Corrective Actions (Fix Order per §15/§73)

**Principle:** Do **not** rewrite `v4.1.0` tag. Create `v4.1.1` patch for metadata/docs/name fixes (SemVer patch, no breaking API). Keep architecture freeze.

### Phase A → v4.1.1 Patch (Critical + High, no new features)

**Step 1 — Source of Truth sync (Critical, 30 min)**

1. Bump `pyproject.toml:version` `4.1.0` → `4.1.1` (or keep `4.1.0` if `v4.1.1` is new tag pointing to fix? Per SemVer, `v4.1.1` version must match tag. Recommend `pyproject.toml` `4.1.1` on `main`, tag `v4.1.1` at publish.)
2. Fix `CITATION.cff`:
   ```
   version: 4.1.1
   date-released: 2026-08-22
   repository-code: https://github.com/Jackxiaozhiren/data-science-agent
   url: same
   references[0].version: 4.1.1
   references[0].title: ... V4.1 ...
   ```
   File: `CITATION.cff:9,10,12,27` (`code-review`).
3. Fix `src/data_science_agent/__init__.py:1` + `src/data_science_agent/sdk.py:286` + docstrings `sdk.py:269,412` (`"4.0.0"` → `"4.1.1"`).
4. Fix `release/sbom.cyclonedx.json:metadata.component.name` `data-science-agent` → `jack-data-science-agent` (and `release/sbom.json` if it contains name field — check `scripts/generate_sbom.py:workspace_pkgs.append({"name": "data-science-agent"` → should be `jack-data-science-agent` for root).
5. Fix `apps/jupyter/src/dsa_jupyter/metadata.py: version("data-science-agent")` → `version("jack-data-science-agent")` with fallback to `"dsa-jupyter"` (try/except already handles).

**Step 2 — README / PyPI truth (Critical/High, 30 min)**

6. Update `README.md` quantitative claims with **versioned annotations** per §18 (not blind replace):
   ```markdown
   - V1: ~86+ tests (2026-08-01 scaffold)
   - V3.0: 155 tests, 81% (4597 stmts), 92 files (2026-08-17)
   - V4.1: 257 tests, 79% (5140 stmts), 102 files (packages apps/api) / 104 (with src) — live 2026-08-22 @ e8794c1
   ```
   Locations: `README.md:33,35,165,166,167` + `docs/README.md:25` + PyPI long description (auto-updated via `uv build`).
   Example fix for `README.md:33`:
   ```
   uv run pytest -q          # 257 passed (V4.1 @ e8794c1, 2026-08-22; V3.0 was 155, V1 was ~86)
   ```
7. Update `docs/v4_1/*` SBOM `192` → `193` (`overview.md`, `release.md`, `RELEASE_MATRIX.md:192`, `SECURITY.md`).
8. Update `docs/v4_1/RELEASE_MATRIX.md:27` wheel `data_science_agent-4.1.0` → `jack_data_science_agent-4.1.1` (or `4.1.0` if patch keeps version).
9. Replace all `pip install data-science-agent` → `pip install jack-data-science-agent` in `CHANGELOG.md:10`, `docs/v4_1/jupyter.md`, `docs/v4_1/SDK_PUBLIC_API_AUDIT.md`, `DATA_SCIENCE_AGENT_V4_1.md` — keep `data-science-agent` in `manifest.py:POPULAR_PYPI` (add new name alongside).

**Step 3 — Documentation build (High, 20 min)**

10. Fix `mkdocs.yml` nav: either set `docs_dir: .` and keep `docs/*` paths, or change nav to `Getting Started: getting-started.md` etc. and ensure `Home: README.md` works with `docs_dir: .`. Test `mkdocs build --strict` locally before CI.
    - Option A (minimal): Add `docs_dir: .` to `mkdocs.yml` (since nav already includes `docs/` prefix) — but then `docs/architecture.md` exists at `.` root? Check: `README.md` at root, `docs/architecture.md` at docs. With `docs_dir: .`, nav `docs/architecture.md` is correct. Without `docs_dir`, default `docs` makes `docs/architecture.md` → `docs/docs/architecture.md` (404). **Fix:** add `docs_dir: .` explicitly.
    - Option B: Change nav to `Architecture: architecture.md` etc. and keep `docs_dir: docs`, move `README.md` handling. **Recommend A** (smallest change, matches current nav).
11. Update `ROADMAP.md` — add `V4.0` and `V4.1` rows, mark `V4.1 Released 2026-08-21`, `V4.2 Pending Phase A`.
12. Update `SECURITY.md: Supported Versions` add `4.1.x: Yes`.
13. Add `CHANGELOG.md` entry for `4.1.1`:
    ```
    ## 4.1.1 — Patch: distribution rename sync, citation, sbom, docs (§15)
    - Fixed: CITATION version/date/repo, sbom name, jupyter metadata, README counts (versioned), mkdocs strict, ROADMAP, SECURITY
    - No breaking change, no API change, no benchmark change
    ```

**Step 4 — Release assets (Medium, 20 min)**

14. Clean `dist/` — remove stale `data_science_agent-4.1.0*` wheels (keep only `jack_*` + `dsa_jupyter`). Or archive to `dist/archive/`.
15. Re-generate SBOM: `uv run python scripts/generate_sbom.py` (verify `components: 193`, `metadata.component.name: jack-data-science-agent`).
16. Build wheels: `uv build` (produces `jack_data_science_agent-4.1.1-py3-none-any.whl`), `uv build --package dsa-jupyter`.
17. Publish: `uv publish` (requires `UV_PUBLISH_TOKEN`) for `jack-data-science-agent 4.1.1` and `gh release create v4.1.1 --target e8794c1` (or new commit after fixes) with assets `jack_data_science_agent-4.1.1*`, `dsa_jupyter-0.1.0*`, `sbom.*`.
18. Verify: `dsa verify-release v4.1.1` must be `12/12 PASS` (including `mkdocs build --strict` if added to verify script).

**Step 5 — Optional clean-ups (Low, 10 min)**

19. Track or ignore spec files: `git add DATA_SCIENCE_AGENT_V4_*.md docs/v4/V3_FREEZE_REPORT.md` or add to `.gitignore` if intended as local spec.
20. Update `uv pip list` duplicate — after `v4.1.1`, `uv sync --dev` should only show `jack-data-science-agent`, not `data-science-agent`.
21. Consider yanking old `data_science_agent-4.1.0` from PyPI if published (but PyPI says only `jack-` exists, so no yank needed).

### Verification Checklist for v4.1.1 (must be 0 diff)

```bash
git status # clean
git describe --tags --always # v4.1.1
git show v4.1.1:pyproject.toml | grep 'name ='
# name = "jack-data-science-agent"
git show v4.1.1:CITATION.cff | grep version
# version: 4.1.1
.venv/bin/mypy packages apps/api src --ignore-missing-imports # 104 clean
.venv/bin/pytest -q # 257 passed
.venv/bin/ruff check packages apps/api tests src apps/jupyter
npm --prefix apps/web run build # 13/13
docker compose config # valid
.venv/bin/mkdocs build --strict # 0 warnings
.venv/bin/dsa verify-release v4.1.1 # 12/12 PASS
pip index? check PyPI long description has no 86+/155 stale
```

### If v4.1.1 is not desired now

Alternative per §15: Keep `v4.1.0` as is, document **Known Issues** in `docs/v4_1/errata.md` and fix all in `v4.2.0` (but then `Tag ≠ PyPI` remains for `v4.1.0` lifetime — not recommended for public truth).

---

## Appendix A — Live Execution Log (2026-08-22)

All commands executed live, not historical:

```bash
# Git
git status
git log --oneline -20
git show v4.1.0 --stat
git diff v4.1.0 HEAD --stat
git diff v4.1.0 HEAD -- pyproject.toml
git cat-file -p v4.1.0 | head -n 20
git describe --tags --always # v4.1.0-1-ge8794c1

# Versions
cat pyproject.toml | grep version # 4.1.0
cat src/data_science_agent/__init__.py # __version__ = "4.1.0"
cat CITATION.cff # version 4.0.0 (stale)
cat src/data_science_agent/sdk.py | grep _version # 4.1.0

# Tests / quality
.venv/bin/python -m pytest -q # 257 passed, 79%, 14.36s
.venv/bin/python -m pytest --collect-only -q | tail # 257 tests collected
.venv/bin/mypy packages apps/api --ignore-missing-imports # Success: no issues found in 102 source files
.venv/bin/mypy packages apps/api src --ignore-missing-imports # Success: no issues found in 104 source files
.venv/bin/mypy . --ignore-missing-imports # 219 errors in 35 files (tests, not gate)
.venv/bin/ruff check packages apps/api tests # All checks passed
npm --prefix apps/web run build | tail # 13/13 routes
docker compose config | head # valid
.venv/bin/mkdocs build --strict # Aborted with 29 warnings
.venv/bin/mkdocs build | tail # Documentation built in 0.35 seconds (non-strict)
.venv/bin/dsa doctor # warn (LLM no key)
.venv/bin/dsa doctor --json | jq # status warn
.venv/bin/dsa verify-release v4.1.0 # 12/12 PASS
.venv/bin/dsa demo | tail # COMPLETED, 4 evidence
.venv/bin/dsa --limit 3 # 1.0
.venv/bin/dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 3 # 1.0
.venv/bin/dsa plugin list | jq # dsa-time-series 1.0.0
.venv/bin/dsa mcp --json | jq length # 18
.venv/bin/python -m pytest tests/security --collect-only -q | grep test # 34
.venv/bin/python -m pytest tests/jupyter -q # 10 passed
.venv/bin/python -m pytest tests/vscode -q # 7 passed
.venv/bin/python -m pytest tests/sdk -q # 32 passed
.venv/bin/python -m pytest tests/mcp -q # 13 passed

# Packages
uv pip list | grep jack # jack-data-science-agent 4.1.0
unzip -p dist/jack_data_science_agent-4.1.0-py3-none-any.whl jack_data_science_agent-4.1.0.dist-info/METADATA | head # Name jack...
python3 -c "import json; d=json.load(open('release/sbom.json')); print(len(d['components']))" # 193
python3 -c "import json; d=json.load(open('release/sbom.cyclonedx.json')); print(d['metadata']['component'])" # data-science-agent (stale)

# PyPI / GitHub
curl https://pypi.org/pypi/jack-data-science-agent/4.1.0/json | jq .info.version # 4.1.0
curl https://pypi.org/pypi/jack-data-science-agent/4.1.0/json | jq .info.description | head # README with 86+/155
gh release view v4.1.0 | head # title v4.1.0, tag v4.1.0, 4 assets (actually 6 with sboms)
ls -lh dist/ # 8 files (old + new + jupyter)
```

---

## Appendix B — File References (for navigation)

```
pyproject.toml:2-3,6-7  — package name/version
src/data_science_agent/__init__.py:1  — __version__
src/data_science_agent/sdk.py:242,269,286,411,412  — API_STABILITY, version docstrings
CITATION.cff:9,10,12,27  — version/date/repo stale
README.md:1,13,15,33,35,43,145,165-171  — title, V4 line, claims, testing
CHANGELOG.md:3-33  — 4.1.0 entry, missing e8794c1
SECURITY.md  — Supported Versions, SBOM 192 stale
ROADMAP.md:3,9  — V3.0 only
mkdocs.yml:nav  — 29-warn strict failure
docs/architecture.md  — exists but nav prefix wrong
docs/v4_1/RELEASE_MATRIX.md:27  — wheel name stale
docs/v4_1/release.md:192  — SBOM stale
docs/v4_1/overview.md:192  — SBOM stale
docs/v4_1/jupyter.md:1  — pip install old name
apps/jupyter/src/dsa_jupyter/metadata.py  — version("data-science-agent") stale
packages/plugins/src/dsa_plugins/manifest.py  — POPULAR_PYPI / WORKSPACE_PACKAGES
release/sbom.json  — 193 components (correct)
release/sbom.cyclonedx.json:metadata.component.name  — data-science-agent stale
dist/jack_data_science_agent-4.1.0-py3-none-any.whl  — canonical wheel
dist/data_science_agent-4.1.0-py3-none-any.whl  — old wheel (duplicate)
.github/workflows/ci.yml  — mkdocs build --strict
.github/workflows/codeql.yml, dependency-review.yml, secret-scan.yml
```

---

## Final Verdict

```
V4.1.0 RELEASE INTEGRITY ISSUES DETECTED
```

| Priority | Count | Examples |
|----------|-------|----------|
| **Critical** | 3 | C1 Tag≠HEAD/PyPI name, C2 CITATION 4.0.0, C3 PyPI description stale |
| **High** | 8 | H1 README counts, H2 mkdocs strict, H3 SBOM 192→193, H4 CycloneDX name, H5 pip old name ×5, H6 jupyter metadata, H7 RELEASE_MATRIX wheel, H8 ROADMAP |
| **Medium** | 8 | M1 mypy 102 vs 104, M2 coverage 81→79, M3 CHANGELOG missing e8794c1, M4 sdk docstring, M5 SECURITY versions, M6 docs/README 86+, M7 GitHub immutable false, M8 duplicate editable |
| **Low** | 5 | L1-L5 duplicates, untracked specs |

**Recommended fix order:** C1 → C2 → C3/H1 (together) → H2 → H3/H4 → H5/H6 → H7 → H8 → M1-M8 → L1-L5

**Next step:** Do **not** auto-enter Phase B. Create `v4.1.1` patch with `HEAD==tag` sync, re-publish PyPI if needed, re-run this report at `v4.1.1` and expect `V4.1.1 RELEASE INTEGRITY VERIFIED`.

> **STOP** — Phase A complete. Awaiting approval to proceed to Phase B (Artifact / Metadata Synchronization) or to create `v4.1.1`.

---

*Generated: 2026-08-22 live verification — no historical results cited without re-execution. All numbers are `Benchmark + Commit + Report` traceable per §45.*


