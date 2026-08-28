# External Validation History — V4.2 W5 Evidence Pointer (V4.3 Phase A, §103)

> **Purpose:** `reproduction/external/` was trimmed from the working tree at `82bb1a3`
> (2026-08-26, `chore: trim repository to core artifacts`) and `.gitignore` excludes
> `reproduction/`. A fresh clone at HEAD therefore cannot `ls reproduction/external/`.
> This document restores **provenance** (commit, hashes, retrieval commands) for the
> V4.2 external-validation evidence, per V4.3 §103 and the Phase A truth report
> (`V4_2_FINAL_TRUTH.md` §5, §16 Medium #2).
>
> **Date:** 2026-08-28 · **HEAD at writing:** `c8903d4` (`v4.2.10-1-gc8903d4`)

---

## 1. What the evidence is (honest description, §49-54 / §103)

Three external reproduction runs of the V4.2 install → demo → SDK → CLI → plugin →
case-study → reproduction pipeline, produced by the harness from `edabd8b`
(`feat: Phase E blind reproduction harness — W5 §34-39`):

- **Environment A (macOS, arm64): REAL run** (`is_real: true` semantics — actual
  install/executed checks on the developer machine).
- **Environment B (Linux) and C (Container): SIMULATED, honestly labeled** in
  `summary.json` (`"is_real": "1 real (A) + 2 simulated honest (B/C)"`).
- All three report `10/10 PASS` on the shared metric set (`3/3` per metric),
  3–5s time-to-first-success, `0/3` manual intervention.

**Correct §103 description:** these are **one developer across three environments
(1 real + 2 simulated)** — NOT three independent humans. No independent human
evaluation has been conducted; V4.3 W7 (Phase G) governs that distinction.

## 2. Provenance

| Field | Value |
|-------|-------|
| Last commit containing the directory | `bf8d176fa4a9f55df8754709e9471a027764953f` — `fix(release): reconcile v4.2 case studies and release gates` (2026-08-25 19:35:34 +0800) |
| Original introduction | `edabd8b` (harness) → `cf6e561` (`docs: Phase E external reproduction — W5 §34-39 (3 envs, blind, 10/10 PASS)`) |
| Removed from working tree | `82bb1a3` — `chore: trim repository to core artifacts; repoint kept docs` (2026-08-26) |
| Why not restorable by checkout alone | `.gitignore` line `reproduction/` excludes the path at HEAD |

## 3. File inventory at `bf8d176` (git blob + sha256 content hashes)

| File | Git blob | sha256 (content) |
|------|----------|------------------|
| `reproduction/external/README.md` | `9e0f49b221bfb454e0b60590d012032be9684675` | `781377864ad3255486d6157229600ab971805afcffe6e3ab0313ae3d36ed081b` |
| `reproduction/external/run.sh` | `4dd6ada0b18c006e8a8ef8736378190a2575c005` | `e81981d165fbad184ff48ffeb635af21468e42a0dff84248e7636382a043be2d` |
| `reproduction/external/summary.json` | `25280c9c2bea8bec3cf98ed4f2726ac8730d75bb` | `5edfae34c7f349852ab12fe4078a69aa00e116f6d9ce7598bb4aeef717618621` |
| `reproduction/external/evaluator-A.json` | `03db4b77094c0543467d999fe0b64d717f59b922` | `50f56ccbeb197bd24465b8fc9307e0f6f1861162cdbdf6de8a43fd76c8629c56` |
| `reproduction/external/evaluator-B.json` | `3f9a4f42955ca5a0a8107b6364d7585f0eda1f5b` | `abc5d96da3c8af482d66895a6136d16629e7113616080914bc525f1fe1b81804` |
| `reproduction/external/evaluator-C.json` | `5801c6ab34b162680b907a49662bcfd201480563` | `fd9f8e830af6ed9c4398ba3344c0fb77ae4e1cefd40146bf62e94e4fdbad685b` |

## 4. Retrieval commands (no working-tree files required)

```bash
# Read any artifact straight from history
git show bf8d176:reproduction/external/summary.json
git show bf8d176:reproduction/external/evaluator-A.json

# Verify content hash of a retrieved file
git show bf8d176:reproduction/external/summary.json | shasum -a 256
# → 5edfae34c7f349852ab12fe4078a69aa00e116f6d9ce7598bb4aeef717618621

# Restore the full directory into the working tree (optional; .gitignore'd)
git checkout bf8d176 -- reproduction/external/

# List the directory at that commit
git ls-tree bf8d176 reproduction/external/
```

## 5. `summary.json` content (recorded verbatim essentials)

```json
{
  "version": "v4.1.1",
  "commit": "edabd8b",
  "date": "2026-08-22",
  "evaluators": 3,
  "all_pass": true,
  "environments": ["macOS", "Linux (sim)", "Container (sim)"],
  "metrics": {
    "install_success": "3/3", "demo_success": "3/3", "sdk_success": "3/3",
    "cli_success": "3/3", "plugin_success": "3/3", "case_study_success": "3/3",
    "reproduction_success": "3/3",
    "time_to_first_success": "3-5s (macOS 3s, Linux 4s, Container 5s)",
    "manual_intervention": "0/3", "documentation_clarity": "High"
  },
  "windows_supported": false,
  "is_real": "1 real (A) + 2 simulated honest (B/C) — per §39 anonymous, no fabricated identities"
}
```

## 6. Status for V4.3 purposes

- **Classification:** `VERIFIED IN HISTORY`, `NOT AT HEAD WORKING TREE`.
- Per V4.3 §103 / §50: the honest public phrasing is *"environment replication
  (1 real host + 2 simulated environments), not independent human validation."*
- V4.3 W7 (Phase G) requires genuinely independent evaluators or an explicit
  `NOT CONDUCTED` — do not upgrade this evidence's wording.
- If a future patch wants the files back at HEAD, restore via `git checkout
  bf8d176 -- reproduction/external/` and either `git add -f` (overriding
  `.gitignore`) or narrow the `.gitignore` rule to `reproduction/*` with an
  exception for `reproduction/external/`.
