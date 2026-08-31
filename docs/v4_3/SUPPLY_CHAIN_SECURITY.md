# Software Supply-Chain Security Report (V4.3 W8 §55-64)

> **Spec:** V4.3 W8 §55-64 — Supply-Chain Provenance · §91 Supply-Chain Gate · §112
> Software Principle ("Can users verify where this package came from?").
> **Date:** 2026-08-30 · **HEAD:** local Spec branch, `git describe → v4.2.10-10-gfba2ae1`.
> **Method:** live inspection of `.github/workflows/*`, release artifacts, PyPI/GitHub state,
> `SECURITY.md`, SBOM. No number here is asserted without a command/line reference.
> **Verdict at a glance:** `published package via trusted (OIDC) publishing with **PyPI
> attestations present and digest-verified for v4.2.10**` — **still missing** GitHub
> build provenance (attest-build-provenance), Scorecard, Best Practices, SBOM attestation,
> and CI least-privilege hardening → not yet the full §91 gate, but materially ahead of
> "no attestations".

---

## 0. Release lineage caveat (read first)

There are **two release lineages** carrying the "v4.3.0" label:

- **Published lineage (origin/main, GitHub + PyPI):** `v4.3.0` (released 2026-08-30) with
  its own release manifest, `research/paper`, real-model smoke, etc. It has exported the
  wheel to PyPI (`jack-data-science-agent` latest = **4.3.0**).
- **This Spec branch (local, external-benchmark lineage):** tracks `DATA_SCIENCE_AGENT_V4_3.md`
  (W1-W12) at `v4.2.10`, with `docs/v4_3/*`, `benchmarks/external/`, `research/external/`
  that the published lineage does **not** contain.

Both share the same `.github/workflows/publish.yml` OIDC mechanism and SBOM scripts. The
classifications below apply to the mechanism **and** to the 4.2.10 artifacts on this branch.
A future merge/re-sync must re-run every check below on the merged tree before claiming audit
coverage (`docs/v4_3/V4_2_FINAL_TRUTH.md §0.0` records the same caveat).

---

## 1. Classification summary (§105 vocabulary)

| # | Check (V4.3 §) | Status | Evidence (this tree) |
|---|----------------|--------|----------------------|
| 1 | PyPI Trusted Publishing / OIDC (§56) | **IMPLEMENTED** | `.github/workflows/publish.yml:9-16`: `environment: pypi`, `permissions: id-token: write`, `pypa/gh-action-pypi-publish@v1.14.2`. Live: PyPI `jack-data-science-agent` releases include `4.2.10` (and `4.3.0` from the published lineage). |
| 2 | No long-lived release token (§57) | **IMPLEMENTED** | `grep -r PYPI_API_TOKEN .github/ → 0`; `SECURITY.md` "No PyPI credentials exist in this repository's history or CI" (§:38). |
| 3 | PyPI attestations (PEP 740) (§58) | **IMPLEMENTED — v4.2.10 EMPIRICALLY VERIFIED** | GitHub release `v4.2.10` assets include `jack_data_science_agent-4.2.10-py3-none-any.whl.publish.attestation` (10,198 B) + `.tar.gz.publish.attestation`. Inspected 2026-08-30: PEP 740 (`version: 1`, `verification_material.certificate` + Rekor `transparency_entries` w/ `inclusionProof`), DSSE `envelope` (`statement` predicateType `https://docs.pypi.org/attestations/publish/v1`), and the statement **subject digest matches the actual wheel** (`sha256 4fc8cbff…db57` == downloaded artifact). A truely verifiable public provenance for 4.2.10. |
| 4 | GitHub artifact attestations (attest-build-provenance) (§59) | **NOT IMPLEMENTED** | `grep -r attest-build-provenance .github/ → 0`. The `.publish.attestation` assets are **PyPI publish attestations** (PEP 740, issuer = PyPI trust root), **not** GitHub build provenance — `gh attestation verify` (Sigstore w/ GitHub issuer) is not wired. |
| 5 | Attestation verification doc (§60) | **IMPLEMENTED — THIS FILE + `docs/security/VERIFY_RELEASE.md`** | `docs/security/VERIFY_RELEASE.md` created 2026-08-30 (PyPI-attestation path now verifiable; GitHub-build-provenance path documented as target). |
| 6 | SBOM (§61) | **IMPLEMENTED** (Partial: un-attested) | `release/sbom.json` (CycloneDX 1.4, **192 components**, version 4.2.10, generated 2026-08-27) by `scripts/generate_sbom.py`; `ci.yml` runs `--check`. |
| 7 | OpenSSF Scorecard (§62) | **NOT IMPLEMENTED** | `grep -r scorecard .github/ docs/ → 0`; no `SCORECARD.md`. |
| 8 | OpenSSF Best Practices / OSPS (§63) | **NOT IMPLEMENTED** | no badge evaluation; README has no badge (correctly — §63 do not display unearned). |
| 9 | CodeQL (§) | **IMPLEMENTED** | `.github/workflows/codeql.yml` (Python+JS, `security-and-quality`, weekly). |
| 10 | Dependency Review | **IMPLEMENTED** | `.github/workflows/dependency-review.yml` (`fail-on-severity: high`). |
| 11 | Secret Scanning | **IMPLEMENTED** | `.github/workflows/secret-scan.yml` (gitleaks, `fetch-depth: 0`) + GitHub push protection. |
| 12 | Dependabot | **IMPLEMENTED** | `.github/dependabot.yml` (npm/pip/docker). |
| 13 | Dependency Pinning | **IMPLEMENTED** | `uv.lock` committed; `ci.yml` `uv lock --check`. |
| 14 | Vendor sync guard | **IMPLEMENTED** | `ci.yml` `scripts/sync_vendor.py --check`. |
| 15 | Release permissions (least privilege) | **PARTIAL** | `publish.yml` job-permission fine; `ci.yml` has **no explicit job `permissions:` block** (defaults grant wider than needed). |
| 16 | Security provenance report (§64) | **IMPLEMENTED — THIS FILE** | §64 deliverable. |

---

## 2. Documentation contradiction found (2026-08-30)

`SECURITY.md:41` states:

> **Status:** PyPI publish is **not yet enabled** (no OIDC trust configured on the project).

This **contradicts** the live state:

- `.github/workflows/publish.yml` already implements OIDC, and **PyPI hosts 4.2.10** (this
  lineage) **and 4.3.0** (published lineage) — both uploaded, so OIDC trust is in fact
  configured and used.
- The `SECURITY.md` wording predates the first successful OIDC publish and was not updated.

**Action:** update `SECURITY.md:41-43` to reflect that Trusted Publishing is live; attestations
remain the gap. **Status: OPEN** (documented here rather than silently fixed so the edit is
reviewable). No functional impact — the workflow + PyPI state are authoritative.

---

## 3. SBOM detail

```text
release/sbom.json              → 192 components, version 4.2.10, generated 2026-08-27T11:59:48
release/sbom.cyclonedx.json    → bomFormat CycloneDX 1.4, component jack-data-science-agent 4.2.10
scripts/generate_sbom.py       → source (+ --check in ci.yml)
```

SBOM is generated per-release and stored under `release/`, but is **not cryptographically
attested** to the published wheel. §91 gate asks for `SBOM + Artifact Attestation`; the SBOM
half is done, the attestation half is the outstanding item.

---

## 4. Honest gaps to close before claiming full "verifiably produced package" (§91)

1. **GitHub build provenance** — add `actions/attest-build-provenance` for wheel + sdist +
   SBOM, so `gh attestation verify` (Sigstore, GitHub issuer) works alongside the existing
   PyPI PEP 740 attestations (§58 now ✗→✅; this §59 remains the gap).
2. **OpenSSF Scorecard** — run `scorecard` against the repo, record score/failed checks in
   `docs/v4_3/SCORECARD.md` (do not optimize for badge only, §62).
3. **Best Practices / OSPS evaluation** — assess eligibility; don't display badges before earned.
4. **Least-privilege CI** — add explicit job-level `permissions:` to `ci.yml`.
5. **SECURITY.md contradiction** (§2) — update the stale "not yet enabled" status line.
6. **Re-verify PyPI attestation after each publish** — the `.publish.attestation` asset is
   production-y only if the wheel digest in its statement matches the distributed artifact
   (verify command in `docs/security/VERIFY_RELEASE.md`).

None of these is a functional blocker for local development or for the DataSciBench benchmark
track; all are Phase H (W8) items that Phase L (release certification §91) will gate on.

## 5. How to keep this honest

- Re-run each evidence command after any workflow/SBOM/pyproject change; update the table.
- The **published lineage's v4.3.0** may already carry some of these (its release manifest
  cites distribution CI with immutable releases) — the audit here is for **this branch's**
  artifacts and mechanism; a merge must re-verify (§0).
- No fabricated attestation URLs, badge claims, or Scorecard numbers — each row maps to a
  command or file line above.