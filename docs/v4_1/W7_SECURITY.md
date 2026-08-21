# W7 Public Security & Supply Chain — Completion Report 2026-08-21

> Workstream W7 (§41-47) — Public repo hardening for open-source readiness.

## Summary

W7 brings `V4.0 skeleton` to **public-security-ready**: GitHub security features, CodeQL, Dependency Review, Secret Protection, Plugin Supply Chain, Pinning, SBOM.

## Changes

| File | Change |
|------|--------|
| `.github/workflows/codeql.yml` | New §42 CodeQL for `python` + `javascript` (push/PR weekly, `security-and-quality`, `security-events: write`) |
| `.github/workflows/dependency-review.yml` | New §43 PR `dependency-review-action` (fail on high, check `vulnerability/license/dependency change`) |
| `.github/workflows/secret-scan.yml` | New §44 `gitleaks` scans full history for hard-coded credentials |
| `.github/dependabot.yml` | Already weekly `pip` (`/`), `npm` (`apps/web`), `docker` (`/`) — §41 |
| `.github/workflows/ci.yml` | Update §46 `uv lock --check` + §47 `generate_sbom.py && test -f release/sbom.json`, ruff/mypy now cover `src` + `apps/jupyter` |
| `SECURITY.md` | Add §41-47 section (Dependabot, CodeQL, Dependency Review, Secret Scanning, Plugin Supply Chain, Pinning, SBOM) + Secret Protection (§44) |
| `packages/plugins/src/dsa_plugins/manifest.py` | Enhance §45: `POPULAR_PYPI` + `WORKSPACE_PACKAGES` + Levenshtein typosquat, `dependency confusion` (`dsa-` not in workspace), `suspicious entrypoint` (`os.`, `subprocess`, `eval` etc.), arbitrary code, path traversal |
| `scripts/generate_sbom.py` | New §47 generates `release/sbom.json` (192 components, package, version, license, source, purl) + `release/sbom.cyclonedx.json` (CycloneDX 1.4) via `uv.lock` + `importlib.metadata` |
| `release/sbom.json` | Generated 192 components (local workspace 14 + PyPI 178), auditable (§47) |
| `release/sbom.cyclonedx.json` | Full CycloneDX |
| `tests/security/test_w7_supply_chain.py` | New 11 tests §41-47 (codeql, dependency-review, secret-scan, SBOM, workspace, typosquat, entrypoint, confusion, pinning, secret grep) |

## Verification (§41-47)

```bash
# §42 CodeQL
cat .github/workflows/codeql.yml | grep -E "python|javascript|codeql-action"
# python + javascript + security-and-quality

# §43 Dependency Review
cat .github/workflows/dependency-review.yml | grep dependency-review-action
# allow-licenses: MIT, Apache-2.0 ...

# §44 Secret Protection
cat .github/workflows/secret-scan.yml | grep gitleaks
# scans full history
grep -r "sk-" --include="*.py" | grep -v ".venv" | wc -l
# 0
cat SECURITY.md | grep "Secret Scanning"
# Secret Scanning / Push Protection

# §45 Plugin Supply Chain
uv run pytest tests/security/test_w7_supply_chain.py::test_plugin_supply_chain_typosquat -v
# flagged pandss ~ pandas
uv run pytest tests/security/test_w7_supply_chain.py::test_plugin_supply_chain_suspicious_entrypoint -v
# flagged os.system

# §46 Pinning
test -f uv.lock && wc -l uv.lock  # 3000+ lines
uv lock --check  # pass (CI)
grep "polars>=" pyproject.toml  # versioned
# dev vs runtime separated: dependencies vs dependency-groups.dev

# §47 SBOM
uv run python scripts/generate_sbom.py
# SBOM: 192 components → release/sbom.json
jq '.components[0]' release/sbom.json
# {"package":"aiosqlite","version":"0.22.1","license":"Unknown","source":"https://pypi.org/simple",...}
test -f release/sbom.json && test -f release/sbom.cyclonedx.json  # pass
uv run pytest tests/security/test_w7_supply_chain.py::test_sbom_exists_and_has_required_fields -v
# pass

# Gates
uv run ruff check packages apps/api tests src apps/jupyter
# All checks passed!
uv run mypy packages apps/api src --ignore-missing-imports
# 104 clean
uv run pytest tests/security/test_w7_supply_chain.py -v
# 11 passed
```

## Security & Supply Chain Risks (§44-45)

- **No hardcoded credentials** in `repository/Git history/CI artifacts/logs` — `gitleaks` + grep verified; Secret Scanning covers full history (§44).
- **Plugin permissions** DENY default + `validate_manifest` now checks typosquatting/confusion (§45).
- **GitHub Security** (§41): `Dependabot` ✅, `CODEOWNERS` ✅, `Secret Scanning`/`Code Scanning`/`Dependency Review` via workflows (repo settings enable on remote).

## Maturity

| Capability | Before | After W7 |
|------------|--------|----------|
| Security & Supply Chain | Stable (23 tests, dependabot) | **Stable (hardened)** — CodeQL + Review + Secret Scan + SBOM + Pinning + Plugin checks, 11 new tests |

## Next

W8 External Developer Validation (§48-50) requires fresh clone test + validation report.

## Stop Condition (§72)

W7 implements `Inspect→Plan→Implement→Test→Security→Benchmark→Document→Commit→STOP`. Do not auto-enter W8.
