# v4.3.0 Release Readiness and Final Verification

This document records the completed release gate and post-release verification for Data Science Agent v4.3.0.

## Release identity

- Release: `v4.3.0`
- Theme: **Adoption, Verifiable Evaluation & Project Reliability**
- Previous release tag: `v4.2.10`
- Previous release commit: `ecf16d0dcef229e38094a853310dd4acd347419b`
- Frozen source candidate: `fcb98f455dff644ebd0e525083fd0f1d7e344369`
- Final tagged commit: `80d5c077d91143a219eb36ff1baa1a952fa4857b`
- Release date: 2026-08-30

The final tag points to the exact commit that passed the post-merge release checks. The Docker base jumps to Python 3.14 and Node 26 are not part of v4.3.0; they remain deferred to a dedicated compatibility cycle.

## Release-manifest semantics

`release/v4.3.0/manifest.json` records the immutable source-candidate SHA used during release preparation. It intentionally does not attempt to embed the SHA of the commit that contains the manifest itself, which would be self-referential. The final release identity is therefore established by the `v4.3.0` tag and its exact commit above.

## Verified pre-release evidence

Three retained evidence layers supported the release decision:

- Distribution CI run `33287733264` on candidate head `3e34b07549a1f9912dbf235255fdcda9cad57167` passed the complete repository CI, including wheel + sdist build, clean-wheel installation, public SDK import/version checks, installed `dsa --help`, API/Web Docker builds, container CLI smoke, Next production build, Compose, and MkDocs strict.
- Historical clean-checkout release-verification run `33288208568` on candidate head `e87eecccdfaed1f8e0e995f95ea1d2553d7a339f` passed the then-current aggregate verifier at 14/14 gates. Its retained artifact remains supporting historical evidence rather than a substitute for final-head checks.
- Final pre-metadata candidate head `3f6b184eb9f62baf14a4a6fb84898932b63f384e` passed CI, Dependency Review, Secret Scan, both CodeQL language jobs, and the SonarQube Quality Gate. SonarQube reported 4 non-blocking new issues and 0 security hotspots; the Quality Gate passed.

A post-merge test-only regression in the release-candidate ref test was then fixed by PR #49 without weakening the stricter branch-name-based RC policy. The final `main` commit `80d5c077d91143a219eb36ff1baa1a952fa4857b` passed the complete repository CI, both CodeQL language jobs, and gitleaks before tagging.

## Final published release verification

GitHub Release `v4.3.0` was published from the exact tagged commit above and is not a prerelease.

Publish workflow run `33290267914` executed from tag `v4.3.0` and verified the tagged tree again before publication:

- mypy: PASS
- Ruff: PASS
- full pytest: PASS
- wheel + sdist build: PASS
- fresh-wheel CLI and SDK smoke: PASS
- PyPI Trusted Publishing: PASS
- digital publish attestations: generated for both distributions

Published PyPI artifacts:

- `jack_data_science_agent-4.3.0-py3-none-any.whl`
  - SHA256: `c7064fa29fd6667bfdab17dd25e2680e1541cc17b74a42310caa9e2467bbeca3`
- `jack_data_science_agent-4.3.0.tar.gz`
  - SHA256: `31ca4d0c35b040608d2835b5ed83f6d76fe296e3505003d7ede3e9934ff96267`

Both PyPI uploads returned HTTP 200 from the production PyPI upload endpoint.

## Immutable GitHub Release boundary

The GitHub Release was already published and marked immutable when the Publish workflow reached its optional binary-asset attachment step. GitHub correctly rejected post-publish asset uploads because immutable releases only permit assets to be added before publication.

This does not affect the integrity or availability of the Python package:

- PyPI is the canonical wheel/sdist distribution channel.
- PyPI publication and attestations succeeded before the GitHub asset step.
- GitHub provides source-code archives for the immutable `v4.3.0` tag.
- No package, tag, or release metadata needs to be rewritten to compensate for the missing duplicate GitHub binary attachments.

The post-release workflow has been hardened so future immutable GitHub Releases do not turn a successful PyPI publication into a failed overall Publish job solely because duplicate post-publish binary attachments are prohibited.

## Final gates

| Gate | State | Evidence / requirement |
|---|---|---|
| Scope frozen | ✅ PASS | v4.2.10 to frozen v4.3.0 source scope |
| Package/version surfaces | ✅ PASS | Canonical runtime/citation/test surfaces set to `4.3.0` |
| Changelog | ✅ PASS | Entry derived from the frozen release diff |
| Release manifest | ✅ PASS | Source-candidate evidence recorded without self-referential SHA claims |
| uv lock / vendored sources / SBOM | ✅ PASS | Checked by CI |
| Ruff / formatting | ✅ PASS | Final main CI |
| mypy | ✅ PASS | Final main CI and Publish workflow |
| full pytest | ✅ PASS | Final main CI and Publish workflow |
| benchmark smoke | ✅ PASS | Final main CI |
| API + Web Docker | ✅ PASS | Final main CI |
| Web production build | ✅ PASS | Final main CI |
| Compose / MkDocs strict | ✅ PASS | Final main CI |
| Dependency Review / Secret Scan | ✅ PASS | Release PR security workflows |
| CodeQL Python + JavaScript | ✅ PASS | Final main checks |
| SonarQube Quality Gate | ✅ PASS | Release-candidate Quality Gate passed; 0 security hotspots |
| Wheel + sdist build | ✅ PASS | Final main CI and Publish workflow |
| Clean-wheel install smoke | ✅ PASS | Final main CI |
| Fresh-wheel publish smoke | ✅ PASS | Publish workflow |
| Tag identity | ✅ PASS | `v4.3.0` → `80d5c077d91143a219eb36ff1baa1a952fa4857b` |
| PyPI Trusted Publishing | ✅ PASS | Production uploads returned HTTP 200 |
| Publish attestations | ✅ PASS | Generated for wheel and sdist |
| GitHub Release | ✅ PASS | Published, immutable, not prerelease |
| GitHub duplicate binary assets | ℹ️ NOT REQUIRED | Immutable release prohibits post-publish uploads; PyPI is canonical |

## Real-model reporting boundary

The code supports a controlled four-way real-model comparison and validates its artifacts. v4.3.0 does not publish or imply comparative real-model benchmark scores without reviewed credentialed artifacts. Deterministic/stub benchmark results remain harness validation rather than evidence of real-model quality.

## Release procedure for future versions

1. Freeze the source scope and run the complete repository check set on the exact final PR head.
2. Merge only after the release PR is green, then verify the exact merged `main` commit.
3. Create the version tag only from that verified merged commit.
4. Let Trusted Publishing rebuild, smoke-test, attest, and publish the exact tagged package to PyPI.
5. Treat PyPI as the canonical wheel/sdist distribution channel.
6. Treat the GitHub Release as immutable publication metadata plus source archives; do not require post-publish duplicate binary attachments.
7. Verify the tag SHA, PyPI artifact hashes, attestations, GitHub Release state, and release announcement before closing the release issue.

## Release decision

**RELEASED AND VERIFIED.** v4.3.0 is published from the intended exact commit, PyPI Trusted Publishing succeeded with attestations, the tagged package passed fresh-wheel smoke testing, and the immutable GitHub Release correctly preserves the release metadata and source archives.
