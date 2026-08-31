# OpenSSF Scorecard Report (V4.3 W8 §62)

> **Spec:** V4.3 §62 — OpenSSF Scorecard: record `score`, `failed checks`, `warnings`,
> `recommended improvements`. Do not optimize only for the badge; fix substantive problems.
> **Date:** 2026-08-31 · **Command:** `scorecard --repo=Jackxiaozhiren/data-science-agent --format=json`
> (Scorecard 5.5.0) · **Scope:** the GitHub repository as configured/pushed (this is what the
> scorecard audits — remote repo config + pushed workflows). **Local Spec-branch caveat §8.**
> **Score: 4.6 / 10.**

---

## 1. Result (2026-08-31)

```text
scorecard --repo=Jackxiaozhiren/data-science-agent --format=json --show-details
Score: 4.6/10
Checks: 18 (10 pass-normalized, 8 flagged below)
Repository: github.com/Jackxiaozhiren/data-science-agent
```

## 2. Checks (score / 10)

| Check | Score | Reason (Scorecard) | Genuine gap or detection blind spot? |
|-------|-------|--------------------|--------------------------------------|
| **Binary-Artifacts** | 10/10 | no binary artifacts detected | ✅ healthy |
| **Dangerous-Workflow** | 10/10 | no dangerous workflow patterns | ✅ healthy |
| **Dependency-Update-Tool** | 10/10 | update tool detected | ✅ healthy |
| **License** | 10/10 | license file detected | ✅ healthy |
| **Vulnerabilities** | 10/10 | no known vulns (fresh) | ✅ healthy |
| **SAST** | 9/10 | SAST tool detected but not run on all commits | minor — CodeQL runs on push+PR+weekly; the "-1" is schedule-only paths |
| **CI-Tests** | 6/10 | 10/16 merged PRs checked by CI | **genuine** — not every merged PR passed CI (mostly docs/CI-only PRs) |
| **Pinned-Dependencies** | 5/10 | dependency not pinned by hash | **genuine** — several `action@vN/tag` references instead of pinned SHA |
| **Security-Policy** | 4/10 | security policy file detected (partial) | honest — `SECURITY.md` exists but some sections stale (§2 caveat) |
| **Contributors** | 3/10 | 1 contributing org | honest — single-maintainer project (not a defect, but real) |
| **Branch-Protection** | 0/10 | branch protection not enabled on dev/release branches | **genuine** — no required status checks / PR review rules enforced |
| **Code-Review** | 0/10 | 0/30 approved changesets | **genuine** — no review-approved PRs in window (solo maintainer workflow) |
| **Maintained** | 0/10 | "created within last 90 days" | **Scorecard artifact** — repo/repos rewritten recently (History reset); not a maintenance-problem signal |
| **Token-Permissions** | 0/10 | workflow tokens with excessive permissions | **genuine** — `ci.yml` has no explicit job `permissions:` block (§ H gap #4) |
| **Fuzzing** | 0/10 | project not fuzzed | honest — no fuzzing harness (low priority for this project type) |
| **CII-Best-Practices** | 0/10 | no best-practices badge effort | honest — §63 not yet evaluated (do not display badge before earning) |
| **Packaging** | **−1/10** | "packaging workflow not detected" | **Scorecard blind spot** — `publish.yml` + PyPI artifacts exist (4.2.10/4.3.0 published, verified §58); Scorecard's heuristic did not match this workflow layout |
| **Signed-Releases** | 0/10 | "has not signed or included provenance with any releases" | **Scorecard blind spot** — **v4.2.10 ships PEP 740 PyPI attestations** (`*.publish.attestation`, subject digest verified, `docs/security/VERIFY_RELEASE.md` §3). Scorecard only recognizes Sigstore-built-in release signing, not PyPI publish attestations |

## 3. Warnings / notes (honest, not badge-chasing)

- **Packaging −1 and Signed-Releases 0 are detection false-negatives**, not true gaps. This
  report records the Scorecard verdict **and** the counter-evidence so neither is over-claimed.
- **Maintained 0** reflects a recent history reset (repo rewritten to core artifacts), not
  abandonment — evidenced by active 2026-08-30 releases.
- **4.6/10 is a floor**, not a ceiling claim. It is the Scorecard number for repo config as
  pushed; local-Spec-branch-only files are not what Scorecard scores.

## 4. Recommended improvements (by genuine-impact, §62 — fix substantive, don't chase badge)

1. **Branch protection on `main`** (Branch-Protection 0): enable required status checks
   (`ci`, `dependency-review`, `secret-scan`, `codeql`) + require PR for pushes; at minimum
   require status checks. **Highest-leverage security fix.**
2. **Least-privilege CI tokens** (Token-Permissions 0): add explicit job-level
   `permissions: contents: read` to `ci.yml` (publish.yml already scoped).
3. **Pin GitHub Actions by SHA** (Pinned-Dependencies 5): replace `action@tag` refs with
   pinned commit SHAs in `ci.yml` / `publish.yml` / `codeql.yml` / `secret-scan.yml` /
   `dependency-review.yml` (Dependabot keeps them updated via `update-types`).
4. **Code review** (Code-Review 0, CI-Tests 6): document a making-a-PR-from-a-branch workflow
   so reviews + CI can gate every change (single-maintainer: use `/approve` or a second
   reviewer account — honest, not fabricated approval).
5. **CII Best Practices self-assessment** (§63): evaluate eligibility and record outcome in
   this doc — but do **not** display the badge until actually obtained.
6. **SAST on all commits** (SAST 9): add CodeQL to the release-tag push path (it already runs
   on push/PR/weekly; tighten scheduling).
7. **Fuzzing** — low priority for this project (parser surface minimal); note as future, not planned.

## 5. How this stays honest

- Re-run `scorecard --repo=… --format=json` after each change set and update the table.
- Do **not** inflate by scoring only the good checks; the two blind-spot rows carry explicit
  counter-evidence rather than being silently zeroed or silently relabeled.
- No fabricated approval count, no fake contributors, no claimed badge (§63, §108).

## 6. Cross-refs

- GitHub build provenance / attest-build-provenance gap: `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §4#1.
- SECURITY.md stale "not yet enabled" line: `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §2.
- PyPI attestation verification commands: `docs/security/VERIFY_RELEASE.md` §3.
- Release lineage caveat (local Spec branch vs published origin/main v4.3.0): `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §0.