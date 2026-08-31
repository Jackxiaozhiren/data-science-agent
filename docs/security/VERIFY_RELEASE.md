# Verify a Data Science Agent Release (V4.3 W8 §60)

> **Spec:** V4.3 §60 — Attestation Verification · §58 PyPI Attestations · §59 GitHub
> Artifact Attestations · §91 Supply-Chain Gate.
> **Status (2026-08-30, local Spec branch):** Trusted Publishing (OIDC) is **live** and the
> **PyPI PEP 740 attestation for 4.2.10 is present and digest-verified** (found during this
> audit). **GitHub** build provenance (`attest-build-provenance`) is **NOT yet implemented**
> (Phase H scope). The digest + PyPI-attestation chains are verifiable today; the GitHub-build
> chain is documented as the target.
> **Date:** 2026-08-30 · **Branch note:** this tree tracks the `DATA_SCIENCE_AGENT_V4_3.md`
> Spec (external benchmarking) at `v4.2.10-*`; the published `v4.3.0` on PyPI/GitHub follows
> a different release lineage (see `docs/v4_3/SUPPLY_CHAIN_SECURITY.md` §0).

---

## 1. What you get from PyPI

`pip install jack-data-science-agent==4.2.10` (or `pipx`). Published via **Trusted
Publishing (OIDC)** — no long-lived token (`.github/workflows/publish.yml`:
`permissions.id-token: write`, `environment: pypi`, `pypa/gh-action-pypi-publish@v1.14.2`).

```bash
pip download jack-data-science-agent==4.2.10 --no-deps -d /tmp/dsa-verify
ls /tmp/dsa-verify          # jack_data_science_agent-4.2.10-py3-none-any.whl + sdist
sha256sum /tmp/dsa-verify/*.whl
```

## 2. Verify the artifact ↔ release chain (§60: artifact → attestation → repository → workflow → commit)

```text
wheel / sdist
   ↓ digest
PyPI release metadata (the JSON you downloaded came from PyPI, which received the
   wheel from the gh-action-pypi-publish step)
   ↓
GitHub release v4.2.10  (immutable; attached dist/* from the same workflow)
   ↓
.github/workflows/publish.yml  (the workflow that attaches `dist/*` via
   softprops/action-gh-release; build + test gates run first: mypy/ruff/pytest)
   ↓
release/v4.2.10/manifest.json  (recorded commit `ecf16d0`, tag v4.2.10,
   gates 12/12 PASS) and `git rev-parse v4.2.10` → commit `ecf16d0`
```

**Commands to walk the chain today (digest path):**

```bash
# 1. PyPI says the artifact exists and its digest
curl -s https://pypi.org/pypi/jack-data-science-agent/4.2.10/json |
  python3 -c "import json,sys; d=json.load(sys.stdin); [print(u['filename'], u['digests']['sha256']) for u in d['urls']]"
# 2. GitHub release attaches the same artifacts (immutable)
gh release view v4.2.10 --json assets --jq '.assets[].name'
# 3. The release manifest records the commit + gates
git show v4.2.10:release/v4.2.10/manifest.json
# 4. The tag resolves to the release commit
git rev-parse v4.2.10
```

## 3. Attestation chain

The **PyPI publish attestation is real and verifiable for 4.2.10** (found 2026-08-30): the
GitHub release `v4.2.10` carries `jack_data_science_agent-4.2.10-*.whl.publish.attestation`
and `*.tar.gz.publish.attestation` — PEP 740 format (`version: 1`, `verification_material`
with certificate + Rekor transparency log), DSSE envelope, predicateType
`https://docs.pypi.org/attestations/publish/v1`, and the statement **subject sha256 matches
the distributed wheel** (`4fc8cbff…db57`). GitHub **build** provenance (`attest-build-provenance`,
`gh attestation verify` with GitHub issuer) is NOT yet wired.

**Verify the PyPI attestation (today, offline):**

```bash
gh release download v4.2.10 --pattern "jack_data_science_agent-4.2.10-py3-none-any.whl" -p "*.publish.attestation" --dir /tmp/dsa-verify
sha256sum /tmp/dsa-verify/*.whl                                   # → wheel digest
python3 - <<'PY'
import json, base64
d = json.load(open('/tmp/dsa-verify/*.publish.attestation'))
st = d['envelope']['statement']
st = json.loads(base64.b64decode(st)) if isinstance(st, str) else st
print(st['predicateType'])
for s in st['subject']:
    print(s['name'], s['digest']['sha256'])
# compare the subject sha256 to the wheel sha256 above — must match
PY
```

**GitHub build-provenance chain (target, not yet shipped):** add `actions/attest-build-provenance`
for wheel + sdist + SBOM, then `gh attestation verify dist/*.whl --repo Jackxiaozhiren/data-science-agent`.

**Status table for 4.2.10 (recorded 2026-08-30):**

| Check | 4.2.10 status | Evidence |
|---|---|---|
| Trusted Publishing (OIDC) | ✅ IMPLEMENTED | `publish.yml` `id-token: write`; PyPI 4.2.10 present |
| wheel/sdist in GitHub release | ✅ IMPLEMENTED | `gh release view v4.2.10` assets |
| Release manifest (commit, gates) | ✅ IMPLEMENTED | `release/v4.2.10/manifest.json` |
| PyPI attestation (PEP 740) | ✅ IMPLEMENTED — VERIFIED | `.publish.attestation` assets; subject digest == wheel sha256 |
| GitHub build provenance | ❌ NOT IMPLEMENTED | no `attest-build-provenance` in workflows |
| SBOM verified on release | ✅ PARTIAL | SBOM generated; not cryptographically attested |
| `docs/security/VERIFY_RELEASE.md` | ✅ THIS FILE | §60 deliverable |

**Honesty gate (§91):** do not claim a "verifiably produced package" until the attestation
items above land. Until then the project is a *published package with OIDC provenance*, which
is what the tables in §2 verify.