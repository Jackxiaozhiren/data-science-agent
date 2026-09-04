# OSPS Baseline Assessment (V4.3 W9 §92)

> **Spec:** `DATA_SCIENCE_AGENT_V4_3.md` §92 — evaluate the OpenSSF Open Source
> Project Security (OSPS) Baseline and record each item as
> `PASS / PARTIAL / FAIL / NOT APPLICABLE / NOT VERIFIED`.
> **Date:** 2026-09-04 · **Repo:** `Jackxiaozhiren/data-science-agent` · **HEAD:** `5892870` (`v4.3.1`).
> **Method:** live inspection of `.github/workflows/*`, repo-root governance files,
> release artifacts, `gh api repos/…/branches/main` (branch protection), plus the
> committed evidence in `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` and
> `docs/v4_3/SCORECARD.md` (OpenSSF Scorecard 4.6/10, 2026-08-31).
> Items that require repository-owner console access are marked `NOT VERIFIED`
> rather than guessed (§128, §130).

---

## 1. Access Control

| # | Item | Status | Evidence |
|---|------|:------:|---|
| AC-1 | Branch protection on primary branch | **PASS** | Live check 2026-09-04: `gh api …/branches/main → protected: true`; remediation commit `efa3bca` ("harden CI + branch protection"). |
| AC-2 | Least-privilege CI/CD permissions | **PASS** | Explicit `permissions:` blocks in all five workflows (`ci.yml:3,8`, `publish.yml:8,15`, `codeql.yml:15`, plus dependency-review/secret-scan); `publish.yml` uses `environment: pypi` + `id-token: write` only. |
| AC-3 | 2FA for all with write access | **NOT VERIFIED** | GitHub account/org setting; not visible via API without owner scope. Owner to confirm (§128). |
| AC-4 | Release-environment approval rules (manual approval on `pypi` env) | **NOT VERIFIED** | Environment protection rules are console-only configuration. |

## 2. Build & Release

| # | Item | Status | Evidence |
|---|------|:------:|---|
| BR-1 | Automated CI on every change | **PASS** | `.github/workflows/ci.yml` (pytest, mypy, ruff, web build, docker config, SBOM check, vendor sync check, `uv lock --check`). |
| BR-2 | Reproducible builds / pinned dependencies | **PASS** | `uv.lock` committed + CI `uv lock --check`; npm lockfile committed; `scripts/sync_vendor.py --check` guards vendoring drift. |
| BR-3 | Releases produced by a dedicated workflow | **PASS** | `publish.yml` (PyPI Trusted Publishing, OIDC, no long-lived token — `grep PYPI_API_TOKEN .github/ → 0`). |
| BR-4 | Release provenance / attestations | **PARTIAL** | PEP 740 PyPI publish attestations **empirically digest-verified** for 4.2.10 (`docs/security/VERIFY_RELEASE.md`; DSSE subject digest == wheel). GitHub **build** provenance (`attest-build-provenance`) NOT IMPLEMENTED — `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` item 4. |
| BR-5 | SBOM shipped with releases | **PASS** | `release/sbom.json` (CycloneDX, 193 components at 4.3.1), CI enforces currency via `--check`. |
| BR-6 | Signed release artifacts (Sigstore/GH build attestation) | **FAIL (open item)** | Only the PyPI publish-attestation path exists; GitHub-issued build provenance absent (see BR-4). |

## 3. Documentation

| # | Item | Status | Evidence |
|---|------|:------:|---|
| DOC-1 | LICENSE present and stated | **PASS** | `LICENSE` at repo root. |
| DOC-2 | README with project purpose & usage | **PASS** | `README.md` (install, quickstart, version banner). |
| DOC-3 | Contribution guide | **PASS** | `CONTRIBUTING.md` (+ `docs/contributing.md`). |
| DOC-4 | Code of Conduct | **PASS** | `CODE_OF_CONDUCT.md`. |
| DOC-5 | Security policy | **PASS** | `SECURITY.md` — private reporting via GitHub Security Advisories, 3-business-day response expectation. |
| DOC-6 | Governance / maintainer model | **FAIL (open item)** | No `GOVERNANCE.md` / `MAINTAINERS.md`; single-maintainer project. Recommendation: add a minimal governance statement. |
| DOC-7 | Citation metadata | **PASS** | `CITATION.cff` (version 4.3.1 lineage; audited in Phase I, commit `40d6e71`). |

## 4. Bug Reporting

| # | Item | Status | Evidence |
|---|------|:------:|---|
| BUG-1 | Public issue tracker open to users | **PASS** | Issues enabled; `docs/v4_3/COMMUNITY_STATUS.md` (2026-08-31: 7 open issues via live `gh api`). |
| BUG-2 | Issue templates | **PASS** | `.github/ISSUE_TEMPLATE/` incl. `user-feedback.yml` (Phase J). |
| BUG-3 | Documented response process for non-security issues | **PARTIAL** | Security SLA documented (3 business days); general-issue triage SLA not yet written down. |

## 5. Maintenance

| # | Item | Status | Evidence |
|---|------|:------:|---|
| M-1 | Active maintenance / release cadence | **PASS** | `v4.2.0` (2026-08-22) → `v4.2.1` → … → `v4.3.0` (2026-08-30) → `v4.3.1` (2026-08-31), all with GitHub Releases + CHANGELOG entries. |
| M-2 | Dependency update strategy | **PASS** | `.github/dependabot.yml` (npm/pip/docker); `uv lock --check` in CI. |
| M-3 | Archived/status banner | **PASS** (active) | No archival banner; actively released. |

## 6. Vulnerability Management

| # | Item | Status | Evidence |
|---|------|:------:|---|
| VM-1 | Private vulnerability reporting channel | **PASS** | `SECURITY.md` (GitHub Security Advisories preferred). |
| VM-2 | Static analysis (SAST) | **PASS** | `.github/workflows/codeql.yml` — Python + JavaScript, `security-and-quality`, weekly. |
| VM-3 | Dependency vulnerability gate | **PASS** | `.github/workflows/dependency-review.yml` (`fail-on-severity: high`). |
| VM-4 | Secret scanning in CI | **PASS** | `.github/workflows/secret-scan.yml` (gitleaks, `fetch-depth: 0`). |
| VM-5 | GitHub-native push protection / secret alerting | **NOT VERIFIED** | Recorded as enabled in `docs/v4_3/SUPPLY_CHAIN_SECURITY.md`; the account-level setting itself needs owner-console confirmation. |
| VM-6 | Documented fix/release process for vulnerabilities | **PARTIAL** | Coordination rule documented in `SECURITY.md`; patch → release flow demonstrated in practice (e.g. `v4.3.1`); no explicit VM runbook beyond that. |

---

## 7. Summary

| Status | Count | Items |
|---|---:|---|
| PASS | 21 | AC-1, AC-2, BR-1, BR-2, BR-3, BR-5, DOC-1..5, DOC-7, BUG-1, BUG-2, M-1..3, VM-1..4 |
| PARTIAL | 3 | BR-4 (PyPI attestations verified; GH build provenance absent), BUG-3, VM-6 |
| FAIL | 2 | BR-6 (GitHub build attestation absent), DOC-6 (no governance doc) |
| NOT VERIFIED | 3 | AC-3 (2FA), AC-4 (env approval), VM-5 (native push protection) |
| NOT APPLICABLE | 0 | — |

*29 items assessed; counts match the per-section rows above.*

**Open items, in priority order (substantive fixes first, per §91/§92 — never badge-chasing):**

1. **BR-6:** add `actions/attest-build-provenance` to the release workflow so
   `gh attestation verify` works for repo-built artifacts (the PyPI path already works).
2. **DOC-6:** add `GOVERNANCE.md` (roles, release authority, security-response owner).
3. **BUG-3:** document a general issue-triage SLA in `CONTRIBUTING.md`.
4. **NOT VERIFIED trio (owner action, §128):** confirm 2FA, `pypi` environment
   approval rules, and GitHub push protection in the repository settings console;
   update this file with the confirmation date.

**Cross-references:** `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` (per-check classification),
`docs/v4_3/SCORECARD.md` (OpenSSF Scorecard 4.6/10 with honest blind spots),
`docs/security/VERIFY_RELEASE.md` (attestation verification procedure).

*Generated: 2026-09-04 — every status above cites a command, file, or live API check;
unverifiable rows are `NOT VERIFIED`, not assumed (§130).*
