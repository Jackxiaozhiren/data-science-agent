# Verify a PyPI Release — V4.3 W9 §86

> **Spec:** V4.3 §86 (PyPI provenance verification) — how a user walks
> Package → Attestation → Publisher Identity → Source Repository.
> **Full chain doc:** `docs/security/VERIFY_RELEASE.md` (digest path + GitHub
> release path). This file is the **PyPI-focused entry point** required by §86.
> **Verified state (2026-08-30 audit, still current for mechanism):**
> Trusted Publishing (OIDC) **live**; PyPI PEP 740 attestation for **4.2.10
> present and digest-verified**; GitHub build-provenance attestations
> **NOT yet implemented** (no `attest-build-provenance` in `.github/workflows/`).

---

## 1. The chain (§86)

```text
Package (wheel/sdist on PyPI)
  ↓ digest (sha256)
Attestation (PEP 740 *.publish.attestation)
  ↓ issuer = PyPI trust root, statement subject == wheel digest
Publisher Identity (GitHub OIDC → PyPI trusted publisher)
  ↓ .github/workflows/publish.yml (environment: pypi, id-token: write)
Source Repository (tag → commit → workflow run)
```

## 2. Walk it (commands)

```bash
# 1. Package — download and hash
pip download jack-data-science-agent==4.2.10 --no-deps -d /tmp/dsa-verify
sha256sum /tmp/dsa-verify/*.whl
# expected wheel digest (2026-08-30 verified): sha256 4fc8cbff…db57

# 2. Attestation — fetch from the GitHub release assets
gh release view v4.2.10 --json assets --jq '.assets[].name'
# includes: jack_data_science_agent-4.2.10-py3-none-any.whl.publish.attestation
# check the statement subject digest inside the attestation == step-1 digest
# (PEP 740: version 1, DSSE envelope, Rekor transparency_entries)

# 3. Publisher identity — the workflow that published it
sed -n '1,20p' .github/workflows/publish.yml
# environment: pypi + permissions id-token: write, no PYPI_API_TOKEN anywhere:
grep -r PYPI_API_TOKEN .github/  # → 0 results

# 4. Source repository — tag resolves to the release commit
git rev-parse v4.2.10
git show v4.2.10:release/v4.2.10/manifest.json 2>/dev/null || \
  cat release/v4.3.0/manifest.json | head -30
```

## 3. What is NOT claimed

- **GitHub artifact attestations** (`gh attestation verify`, Sigstore GitHub
  issuer): not wired — `grep -r attest-build-provenance .github/` → 0.
  Documented as the target in `VERIFY_RELEASE.md` §3, not as done.
- **Per-release re-verification required:** the `.publish.attestation` asset is
  only meaningful if the statement digest matches the distributed artifact —
  re-run steps 1–2 after every publish (§91 supply-chain gate).
- **SBOM** (`release/sbom.json`, CycloneDX) is present but **not cryptographically
  attested** to the wheel — the SBOM half of §91 is done, attestation half open.

## 4. Pointers

- Mechanism + gaps table: `docs/v4_3/SUPPLY_CHAIN_SECURITY.md`
- Scorecard: `docs/v4_3/SCORECARD.md` (4.6/10 with blind-spot annotation)
- OSPS baseline: `docs/security/OSPS_BASELINE.md`
