# V4.2.1 Post-Release Reconciliation — Phase A (V4.3 W1 §26)

> **Spec:** `DATA_SCIENCE_AGENT_V4_3.md` §10-26 (W1 — Post-Release Reconciliation).
> **Date:** 2026-08-25.
> **Baseline:** `v4.2.0` (`f24be10`) — historical immutable release.
> **Chain:** `v4.2.0` (historical) → **`v4.2.1` (this reconciliation)** → `v4.3.0` (future: external scientific validation).

---

## 1. Release Identity

| Field | Value |
|-------|-------|
| Previous release | `v4.2.0` — tag `f24be10`, published 2026-08-22 (untouched) |
| This release | `4.2.1` (patch — no breaking public API change) |
| Version controls updated | `pyproject.toml`, `src/data_science_agent/__init__.py`, `sdk.py`, `packages/plugins/src/dsa_plugins/manifest.py`, `apps/jupyter/src/dsa_jupyter/metadata.py`, `CITATION.cff`, `README.md`, `CHANGELOG.md`, version-assert tests |
| SemVer decision (§20) | `PATCH` — bug fix (mypy gate), verification completion (CS03-08), documentation correction, case-study artifact completion; **no public API change** → `4.2.1` |

---

## 2. Diff Audit (§11)

Baseline commands run before staging (`git status --short`, `git diff --stat`, `git diff`, `git ls-files --others --exclude-standard`). Full classification in [V4_2_1_CHANGESET_AUDIT.md](V4_2_1_CHANGESET_AUDIT.md).

**Diff shape (modified):** 24 files across 6 groups:
- `INTENDED_FIX` (2): `packages/evaluation/src/dsa_evaluation/{human_eval.py, cli.py}` — mypy regression fix.
- `CASE_STUDY_ARTIFACT` (7 READMEs + index): CS02-08 documentation + CS03-08 committed `outputs/`.
- `DOCUMENTATION_RECONCILIATION` (5 + 1 new audit + 1 new report): `docs/v4_2/PRODUCT_EVIDENCE.md`, `research/v4_2/*`, `docs/v4_3/V4_2_FINAL_TRUTH.md` + new docs.
- `GENERATED_BUT_REQUIRED` (3): `demo/runs/demo/*` — fresh real `dsa demo` output.
- `VERSION` (10): version bump + changelog + citation.
- **Restored / EXCLUDED** (5): benchmark result smoke-overwrites + garbled SBOM regeneration (below).

**New files (untracked → staged):** `case-studies/03-08/outputs/` (36 files) + `docs/v4_3/` (3 files).

---

## 3. Files Included / Excluded

**Included (staged):** every row marked Include in [V4_2_1_CHANGESET_AUDIT.md](V4_2_1_CHANGESET_AUDIT.md) — 24 modified + 36 case-study output JSONs/MD + 3 v4_3 docs.

**Excluded — smoke-run ephemera restored to baseline:**
- `benchmarks/ds-agent-benchmark/results/{raw_runs,results,summary}.json` — restored to the canonical **50-task `50/50 @1.00`** run (a `dsa --limit 5` smoke had overwritten it to `n=5`). The canonical internal-benchmark evidence is preserved; nothing staged.
- `release/sbom.json`, `release/sbom.cyclonedx.json` — SBOM regeneration in this environment picked up a stale installed `jack-data-science-agent 4.2.0` dist alongside local `4.2.1`, producing a duplicated entry. **Reverted.** SBOM regeneration for `4.2.1` is `PENDING OWNER ACTION` (clean env) per §128.

**Excluded — unrelated to v4.2.1 scope:** none remaining; all changes classified.

---

## 4. Full Release Gates (§19, §123)

All gate commands re-executed live on 2026-08-25 (`Python 3.12.13`, `uv 0.11.7`, `Node v24.15.0`, `Docker 29.7.2`, `.venv`).

| Gate | Command | Result | Status |
|------|---------|--------|--------|
| Full test suite | `.venv/bin/python -m pytest -q` | **257 passed** (exit 0; 257 collected) | ✅ PASS |
| mypy (release gate) | `.venv/bin/python -m mypy packages apps/api src --ignore-missing-imports` | **`Success: no issues found in 104 source files`** | ✅ PASS |
| mypy `mypy .` (§19 wording) | `.venv/bin/python -m mypy . --ignore-missing-imports` | 230 errors in 36 files (checked 168) — all in `tests/` (untyped mocks); **pre-existing**, never the release gate | ⚠️ Gap (documented §6) |
| ruff | `.venv/bin/python -m ruff check packages apps/api tests src apps/jupyter` | **`All checks passed!`** | ✅ PASS |
| ruff format | `.venv/bin/python -m ruff format --check ...` | **154 files already formatted** | ✅ PASS |
| Web build | `npm ci --prefix apps/web --legacy-peer-deps && npm --prefix apps/web run build` | **PASS** (Next.js routes generated; frozen `next@15`/`react@19.0.0` peer conflict resolved via legacy flag — no lockfile change) | ✅ PASS |
| Docker | `docker compose config` | **valid** | ✅ PASS |
| Docs | `.venv/bin/python -m mkdocs build --strict` | **`Documentation built`** (no warnings) | ✅ PASS |
| Doctor | `uv run dsa doctor` | `warn` (LLM warn = expected stub fallback) | ✅ PASS |
| Demo | `uv run dsa demo` | `COMPLETED` (exit 0) | ✅ PASS |
| **verify-release** | `uv run dsa verify-release v4.2.0` | **`12/12 PASS`** (pytest, mypy, ruff, npm, docker, security, MCP, benchmark smoke, demo, tables, figures, docs) | ✅ PASS |
| Security | `pytest tests/security` | 34 passed | ✅ PASS |
| MCP | `pytest tests/mcp` | 13 passed | ✅ PASS |
| SDK | `pytest tests/sdk` | 31 passed | ✅ PASS |
| Plugins | `pytest tests/plugins` | 24 passed | ✅ PASS |
| Jupyter | `pytest tests/jupyter` | 10 passed | ✅ PASS |
| VS Code | `pytest tests/vscode` | 7 passed | ✅ PASS |
| Evals | `pytest tests/evals` | 20 passed | ✅ PASS |
| Perf | `pytest tests/perf` | 6 passed | ✅ PASS |

**Combined accessory suites: 145 passed** (security 34 + MCP 13 + SDK 31 + plugins 24 + Jupyter 10 + VS Code 7 + evals 20 + perf 6). *Note: live SDK collection is 31 vs 32 recorded in the 2026-08-23 audit — a param/collection drift, non-blocking.*

---

## 5. Case-Study Verification (§15-16, §134)

All 8 case studies now satisfy the verification contract (§16): dataset source + license + **dataset hash (verified live via `sha256sum`. matches README)** + question + analysis plan + real execution + tool trajectory + evidence + report + reproduction metadata + exit status.

| Case | Run ID | Status | Evidence | Tool calls | Failures (real, preserved) | Report (bytes) |
|------|--------|--------|--------:|--------:|--------:|--------:|
| CS01 Sales | `run-008a1531cf` | `COMPLETED` | 6 | 6 | 0 | 3890 |
| CS02 Churn | `run-44043c60a0` | `COMPLETED` | 3 | 7 | 4 (`train_model`×2, `causal_check`×2) — now documented | 2983 |
| CS03 Time Series | `run-1c70a7896a` | `COMPLETED` | 5 | 9 | 4 (`correlation_analysis` `DuplicateError`×2, `train_model` CV×2) | 4526 |
| CS04 Marketing | `run-0c004191b2` | `COMPLETED` | 5 | 5 | 0 | 2896 |
| CS05 Financial | `run-d1f43414f1` | `COMPLETED` | 5 | 7 | 2 (`train_model` non-numeric×2) | 3330 |
| CS06 Public Stats | `run-cd71ab4f39` | `COMPLETED` | 3 | 7 | 4 (`hypothesis_test` group<2×2, `train_model`×2) | 2525 |
| CS07 Data Quality | `run-9c943b40b5` | `COMPLETED` | 3 | 5 | 2 (`causal_check` `DuplicateError`×2) | 2669 |
| CS08 Classification | `run-e569d4141d` | `COMPLETED` | 5 | 7 | 2 (`causal_check` `DuplicateError`×2) | 3470 |

- **18 real tool-call failures preserved** across CS01-08 (counted from `outputs/tool_calls.json`), matching the audit claim and §17. Each is visible in its `outputs/tool_calls.json` (`status: error`), in the case-study README Limitations, and in `research/v4_2/benchmark_vs_real_world.md` gap analysis. **Not deleted / hidden / rewritten.**
- **Reproduction packages** (`artifacts/reports/<runId>/`: `report.md`, `evidence_graph.json`, `reproduce.sh`, `analysis.ipynb`, `experiment.json`) exist on-disk for all 6 new runs, but `artifacts/` is `.gitignore`d — the durable committed evidence is the `outputs/` dirs. Noted as limitation M1.

---

## 6. Known Limitations (§26, §134)

1. **External validation remains `1 real + 2 simulated honest` on the same host** — NOT "3 independent human reviewers" (§74). Unchanged; cannot be fabricated.
2. **`mypy .` (168 files) fails on `tests/` typing** — the release gate is the canonical 104-file set (`mypy packages apps/api src` = clean). §19 lists `mypy .`; this repo has never been clean on the full tree. Documented here and left for V4.3.
3. **`npm run build` requires `--legacy-peer-deps`** — frozen `next@15.0.0` / `react@19.0.0` peer mismatch in the committed lockfile. No dependency change made in this patch. Gate passes in this environment with the legacy flag; a clean install path is a V4.3/upstream item.
4. **SBOM for 4.2.1 not regenerated in this commit** (`PENDING OWNER ACTION`) — see §3. `release/sbom.json` stays at the v4.2.0 baseline until a clean-env regeneration.
5. **Dataset semantic honesty (§18):** `marketing.csv` / `financial.csv` remain `sales.csv`-generator schema (not channel/OHLC). Retained with explicit limitation and fixed tables — **not** silently relabeled.
6. **`dsa verify-release` / `dsa --limit 5` inherently re-dirties** `benchmarks/ds-agent-benchmark/results/` and `demo/runs/demo/` on every run; benchmark results are restored to the canonical 50-task baseline before commit.
7. **Case-study `outputs/` are committed but reproduction packages are on-disk only** (gitignored) — fresh clones get the evidence + `reproduce.sh`-style regeneration, not the archived bundle (M1, unchanged).
8. **Human-eval agreement pending** (no real human review) — unchanged, `NOT CONDUCTED` until V4.3 W7/W8.

---

## 7. Version Transition (§20-21, §25)

```text
v4.2.0 (f24be10) ──historical immutable──▶ v4.2.1 (this commit) ──▶ v4.3.0 (future)
```

- `v4.2.0` tag, commit history, `release/v4.2.0/manifest.json`, CHANGELOG `4.2.0` entry, and docs/v4_2 + research/v4_2 content are **preserved unchanged** where historical.
- Patch bump `4.2.0 → 4.2.1` applied to all current-version pointers + version-assert tests.

---

## 8. Artifact Status

| Artifact | Status |
|----------|--------|
| `pyproject.toml` / `__version__` / `Agent._version` | `4.2.1` |
| `CITATION.cff` | `version: 4.2.1`, `date-released: 2026-08-25` |
| `CHANGELOG.md` | `## 4.2.1` entry added; `4.2.0` preserved |
| `README.md` | `v4.2.1` |
| Internal benchmark v1 results | canonical `50/50 @1.00` preserved (restored from smoke overwrite) |
| Case-study evidence | 8/8 committed `outputs/` (real Agent, 18 failures preserved) |
| `docs/v4_3/` | `V4_2_FINAL_TRUTH.md` (audit) + `V4_2_1_CHANGESET_AUDIT.md` + `V4_2_1_RECONCILIATION.md` |
| SBOM | v4.2.0 baseline; 4.2.1 regeneration `PENDING OWNER ACTION` |
| PyPI | `jack-data-science-agent 4.2.1` publish `PENDING OWNER ACTION` (existing release mechanism; §24, §128) |

---

*Generated: 2026-08-25 — output of V4.3 Phase A; STOP after this per §120, §126 (no automatic continuation into Phase B).*