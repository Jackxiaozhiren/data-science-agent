# V4.2.1 Changeset Audit — Phase A (V4.3 W1 §11-13)

> **Purpose:** Classify every modified / untracked file in the working tree before staging, per `DATA_SCIENCE_AGENT_V4_3.md` §11-13 (change classification, protect unrelated changes, no blind `git add -A`).
> **Baseline:** `v4.2.0` tag (`f24be10`) — historical immutable release.
> **Audited:** 2026-08-25 (live `git status --short`, `git diff --stat`, `git diff`, `git ls-files --others --exclude-standard`).
> **Decision rule:** No file is staged without a category and reason; files whose ownership is unclear are kept out (`NOT INCLUDED — OWNERSHIP UNCERTAIN`).

---

## 1. Change Classification (§12)

| # | File | Category | Include? | Reason |
|---|------|----------|:---:|---|
| 1 | `packages/evaluation/src/dsa_evaluation/human_eval.py` | `INTENDED_FIX` | ✅ Include | mypy regression fix (H1): `krippendorff_alpha` / `agreement_summary` type-narrowed through guarded loops; no new `# type: ignore`, behavior-preserving. Restores `104 clean` / `12/12 PASS`. |
| 2 | `packages/evaluation/src/dsa_evaluation/cli.py` | `INTENDED_FIX` | ✅ Include | mypy fix (H1): `_reproduce_benchmark` `per_task` retyped `dict[str, Any]`, stale `# type: ignore[arg-type,misc]` removed. Behavior-preserving. |
| 3 | `case-studies/03-time-series/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS03 marked `✅ Verified` with real run `run-1c70a7896a`; honest 4 tool-failure note. |
| 4 | `case-studies/04-marketing/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS04 `✅ Verified` (`run-0c004191b2`); dataset-schema honesty note (§18) with malformed table **fixed** during reconciliation. |
| 5 | `case-studies/05-financial/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS05 `✅ Verified` (`run-d1f43414f1`); dataset-schema honesty note (§18) with malformed table **fixed**. |
| 6 | `case-studies/06-public-statistics/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS06 `✅ Verified` (`run-cd71ab4f39`); honest 4 tool-failure note. |
| 7 | `case-studies/07-data-quality/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS07 `✅ Verified` (`run-9c943b40b5`); honest 2 tool-failure note. |
| 8 | `case-studies/08-classification/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | CS08 `✅ Verified` (`run-e569d4141d`); honest 2 tool-failure note. |
| 9 | `case-studies/02-churn/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | Pre-existing gap fixed: CS02's 4 real tool failures (`train_model`×2, `causal_check`×2) now documented in Limitations (§17). |
| 10 | `case-studies/README.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | Index updated to 8/8 `✅ Verified` (real Agent, no mock); CS02 row notes 4 tool failures. |
| 11 | `docs/v4_2/PRODUCT_EVIDENCE.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | Case-study table 8/8 with per-case run ids + honest failure counts. |
| 12 | `research/v4_2/V4_2_RESEARCH_REPORT.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | `N=2 → N=8` case-study limitation updated; 18 failures + gap counts; no fabricated adoption. |
| 13 | `research/v4_2/benchmark_vs_real_world.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | Gap analysis expanded with live failures → 1 covered / 7 underrepresented / 6 missing; benchmark v3 `0.4.0` evidence bar met (plan only, do not modify frozen `v2`). |
| 14 | `demo/runs/demo/manifest.json` | `GENERATED_BUT_REQUIRED` | ✅ Include | Fresh real `dsa demo` output (`run-fd3f41582d` → re-run 2026-08-25T11:26Z), same dataset/question, `r=-0.057`; reproducible via `dsa demo`. |
| 15 | `demo/runs/demo/report.md` | `GENERATED_BUT_REQUIRED` | ✅ Include | Same run's report (`REPORTING`, evidence + validation). Real, regenerated. |
| 16 | `demo/runs/demo/state.json` | `GENERATED_BUT_REQUIRED` | ✅ Include | Same run's full trace. Real, regenerated. |
| 17 | `case-studies/03-time-series/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | Real execution artifacts (`evidence.json`, `insights.json`, `report.md`, `summary.json`, `tool_calls.json`, `artifacts.json`) — `COMPLETED`, 5 evidence, 9 tool calls, 4 errors preserved. |
| 18 | `case-studies/04-marketing/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | `COMPLETED`, 5 evidence, 5 tool calls, 0 errors. |
| 19 | `case-studies/05-financial/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | `COMPLETED`, 5 evidence, 7 tool calls, 2 errors preserved. |
| 20 | `case-studies/06-public-statistics/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | `COMPLETED`, 3 evidence, 7 tool calls, 4 errors preserved. |
| 21 | `case-studies/07-data-quality/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | `COMPLETED`, 3 evidence, 5 tool calls, 2 errors preserved. |
| 22 | `case-studies/08-classification/outputs/` (6 files) | `CASE_STUDY_ARTIFACT` | ✅ Include | `COMPLETED`, 5 evidence, 7 tool calls, 2 errors preserved. |
| 23 | `docs/v4_3/V4_2_FINAL_TRUTH.md` | `DOCUMENTATION_RECONCILIATION` | ✅ Include | Historical v4.2.0 truth audit (2026-08-23 + 2026-08-25 closure) — preserved as the audit record (§22). |
| 24 | `docs/v4_3/V4_2_1_CHANGESET_AUDIT.md` | `GENERATED_BUT_REQUIRED` | ✅ Include | This document (§12 required output). |
| 25 | `docs/v4_3/V4_2_1_RECONCILIATION.md` | `GENERATED_BUT_REQUIRED` | ✅ Include | Reconciliation report (§26 required output). |
| 26 | `CHANGELOG.md` | `VERSION` | ✅ Include | `## 4.2.1` entry added (templates §22); `4.2.0` historical entry preserved. |
| 27 | `CITATION.cff` | `VERSION` | ✅ Include | `version: 4.2.1`, `date-released: 2026-08-25`. |
| 28 | `README.md` | `VERSION` | ✅ Include | Title `v4.2.1`. |
| 29 | `pyproject.toml` | `VERSION` | ✅ Include | `version = "4.2.1"`. |
| 30 | `src/data_science_agent/__init__.py` | `VERSION` | ✅ Include | `__version__ = "4.2.1"`. |
| 31 | `src/data_science_agent/sdk.py` | `VERSION` | ✅ Include | `Agent._version = "4.2.1"` + docstrings. |
| 32 | `packages/plugins/src/dsa_plugins/manifest.py` | `VERSION` | ✅ Include | `CURRENT_DSA_VERSION = "4.2.1"`. |
| 33 | `apps/jupyter/src/dsa_jupyter/metadata.py` | `VERSION` | ✅ Include | fallback `sdk_version = "4.2.1"`. |
| 34 | `tests/sdk/test_sdk_contract.py` | `VERSION` | ✅ Include | Version-assert tests updated to `4.2.1` (tracked current release). |
| 35 | `tests/api/compatibility/test_sdk_compat.py` | `VERSION` | ✅ Include | Version-assert test updated to `4.2.1`. |

---

## 2. Restored / Excluded Files (GENERATED_EPHEMERAL)

These were modified by gate executions in the working tree but are **ephemeral smoke-run side effects**; the working tree was restored to the committed baseline and **no net change is staged**.

| File | Cause | Resolution |
|------|-------|------------|
| `benchmarks/ds-agent-benchmark/results/raw_runs.json` | `dsa --limit 5` (smoke) overwrote the canonical 5-task → 50-task results | **Restored to HEAD** (50-task canonical `50/50 @1.00` preserved as the release's Internal Benchmark evidence) |
| `benchmarks/ds-agent-benchmark/results/results.json` | same | **Restored to HEAD** (50-task) |
| `benchmarks/ds-agent-benchmark/results/summary.json` | same | **Restored to HEAD** (50-task) |
| `release/sbom.json` | SBOM regeneration for 4.2.1 picked up a stale installed `jack-data-science-agent 4.2.0` dist alongside local `4.2.1`, producing a duplicated component entry | **Reverted to HEAD**; SBOM regeneration for 4.2.1 is `PENDING OWNER ACTION` in a clean environment (§128) |
| `release/sbom.cyclonedx.json` | same | **Reverted to HEAD**; see above |

> **Net effect of restore:** the released repo keeps the canonical 50-task v1 benchmark results and the v4.2.0 SBOM baseline; the 5-task smoke result was never intended to be committed.

---

## 3. Ownership Check (§13)

- **UNKNOWN / `NOT INCLUDED — OWNERSHIP UNCERTAIN`:** none. Every remaining change is attributable (Phase D case-study execution 2026-08-25, `dsa verify-release` gate side effects, or deliberate reconciliation edits made during this audit).
- **PRE_EXISTING_UNRELATED_CHANGE:** none left unclassified. The benchmark-result and demo modifications were confirmed as gate-runbyproducts (see `verify_release.py` — `dsa --limit 5` + `dsa demo` write into the working tree).

---

## 4. Integrity Rules Applied

- No `git add -A` was used; files were staged explicitly (§11, §121).
- `v4.2.0` tag/commit/history and `release/v4.2.0/manifest.json` are **untouched** (§2, §25).
- No historical release claim was rewritten: `docs/v4_2/*`, `research/v4_2/*`, and `docs/v4_3/V4_2_FINAL_TRUTH.md` retain their v4.2.0 timestamps and are updated only where a live-fact change (8/8 executed) required it.

*Generated: 2026-08-25 — companion to `docs/v4_3/V4_2_1_RECONCILIATION.md`.*