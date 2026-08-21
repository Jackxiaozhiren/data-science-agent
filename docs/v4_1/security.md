# Security & Supply Chain — V4.1 §41-47

**GitHub (§41):** `Dependabot Alerts/Security Updates` (weekly `pip` `/`, `npm` `apps/web`, `docker` `/`) + `Dependency Review` (PR) + `Secret Scanning` + `Push Protection` + `CodeQL` (python+javascript) — `SECURITY.md` + `.github/workflows`.

**CodeQL (§42):** `.github/workflows/codeql.yml` `python` + `javascript`, `security-and-quality`, push/PR weekly.

**Dependency Review (§43):** `.github/workflows/dependency-review.yml` `fail-on-severity high`, `allow-licenses MIT/Apache-2.0/...`.

**Secret Protection (§44):** `gitleaks` via `.github/workflows/secret-scan.yml` scans full Git history for `API keys/tokens/passwords`; no secrets in `repository/Git history/CI artifacts/logs` (verified via grep, `test_secret_protection_no_hardcoded`).

**Plugin Supply Chain (§45):** `PluginManifest.validate_manifest()` checks `malicious plugin` (suspicious entrypoint `os.`, `eval`), `dependency confusion` (`dsa-` not in `WORKSPACE_PACKAGES`), `typosquatting` (Levenshtein ≤2 vs `POPULAR_PYPI`), `malicious dependency`, `arbitrary code`.

**Pinning (§46):** `uv.lock` 4231 lines committed, `uv lock --check` in `ci.yml`, `pyproject.toml` versioned (`polars>=1.0`), `dependencies` vs `dependency-groups.dev` separated, auditable.

**SBOM (§47):** `release/sbom.json` 192 components (package, version, license, source, purl) + `release/sbom.cyclonedx.json` (CycloneDX 1.4) via `scripts/generate_sbom.py` (from `uv.lock` + `importlib.metadata`).

**Tests:** `tests/security/test_w7_supply_chain.py` 11 (codeql, review, secret, SBOM, typosquat, entrypoint, confusion, pinning, secret grep).

See `SECURITY.md` + `W7_SECURITY.md`.
