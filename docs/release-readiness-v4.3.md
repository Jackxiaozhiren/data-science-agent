# v4.3.0 Release Readiness

This document is the public release gate for Data Science Agent v4.3.0. A tag is the result of release readiness, not the mechanism that decides whether the release is ready.

## Candidate theme

**v4.3.0 — Adoption, Verifiable Evaluation & Project Reliability**

The release combines public-project adoption work with a materially stronger evaluation and security story, while preserving the Stable SDK contract.

## Frozen source scope

- Previous release tag: `v4.2.10`
- Previous release commit: `ecf16d0dcef229e38094a853310dd4acd347419b`
- Frozen source candidate: `fcb98f455dff644ebd0e525083fd0f1d7e344369`
- Commits in frozen diff: `103`
- Canonical diff: `v4.2.10...fcb98f455dff644ebd0e525083fd0f1d7e344369`

The frozen source candidate includes the real-model provider/provenance path, critic ablation, LLM baselines, secure four-way smoke workflow, publication validator, web security upgrades, contributor/adoption workflows, flagship case studies, Windows quickstart, benchmark contribution guide, and plugin walkthrough.

The Docker base jumps to Python 3.14 and Node 26 are **not** part of v4.3.0. They were deferred to a dedicated compatibility cycle rather than mixed into this release.

## Release-manifest semantics

`release/v4.3.0/manifest.json` records the immutable **source candidate SHA** above. It does not attempt to embed the SHA of the commit that contains the manifest itself, which would be a self-reference. The final `v4.3.0` tag should point to the merged release-metadata commit only after that exact head has passed every release-critical gate.

## Verified gate evidence

Two independent layers were used before finalizing this metadata:

- Distribution CI run `33287733264` on candidate head `3e34b07549a1f9912dbf235255fdcda9cad57167` passed the complete repository CI, including wheel + sdist build, clean-wheel installation, public SDK import/version checks, installed `dsa --help`, API/Web Docker builds, container CLI smoke, Next production build, Compose, and MkDocs strict.
- Clean-checkout release-verification run `33288208568` on candidate head `e87eecccdfaed1f8e0e995f95ea1d2553d7a339f` passed `dsa verify-release v4.3.0` at **14/14 gates**. Its report is retained as Actions artifact `9725134640` with artifact digest `sha256:48bfc019f982ff1753bda8a2bd1e2ebc63859becf45e51eb381e5816c37f8e63` through 2026-09-29.
- The same candidate line passed Dependency Review, Secret Scan, CodeQL Python + JavaScript, and SonarQube Quality Gate with 0 new issues and 0 security hotspots.

The release verifier was hardened during this process so it can run from a clean checkout: it prepares the VSCode/Web Node dependencies itself, while Compose declares the developer `.env` file optional (`required: false`) so validation remains read-only when that local file is absent.

## Current gates

| Gate | State | Evidence / requirement |
|---|---|---|
| Scope frozen | ✅ PASS | `v4.2.10...fcb98f455dff644ebd0e525083fd0f1d7e344369`, 103 commits |
| Package/version surfaces | ✅ PASS | Canonical runtime/citation/test surfaces set to `4.3.0` |
| Changelog | ✅ PASS | Entry derived from the frozen 103-commit diff |
| Release manifest | ✅ PASS | Records the source candidate and evidence without self-referential SHA claims |
| uv lock / vendored sources / SBOM | ✅ PASS | Regenerated and checked by CI |
| Ruff / formatting | ✅ PASS | Repository CI and release verifier |
| mypy | ✅ PASS | Repository CI and release verifier |
| full pytest | ✅ PASS | Repository CI and release verifier |
| benchmark smoke | ✅ PASS | Repository CI and release verifier |
| API + Web Docker | ✅ PASS | Both images pass; packaged/container `dsa` CLI also passes |
| Web production build | ✅ PASS | Next.js production build passes |
| Compose / MkDocs strict | ✅ PASS | Both pass from clean release verification |
| Dependency Review / Secret Scan | ✅ PASS | GitHub security workflows green |
| CodeQL Python + JavaScript | ✅ PASS | Both languages green with no new alerts |
| SonarQube Quality Gate | ✅ PASS | Quality Gate passed; 0 new issues / 0 security hotspots on verified candidate code |
| Wheel + sdist build | ✅ PASS | Umbrella distribution built successfully in CI |
| Clean-wheel install smoke | ✅ PASS | Fresh venv import + SDK version + CLI smoke passed |
| Final release verification | ✅ PASS | `dsa verify-release v4.3.0`: 14/14 PASS; artifact retained |
| Final metadata-head checks | ⏳ PENDING | This metadata + clean-Compose update must itself finish green before merge |
| Tag / PyPI / GitHub Release | ⛔ BLOCKED | Only after the final head is green and the RC is merged |

## Real-model reporting boundary

The code supports a controlled four-way real-model comparison and validates its artifacts. The release does **not** depend on publishing a benchmark score: `OPENAI_API_KEY` still has to be configured manually in GitHub Actions, and the credentialed smoke artifacts must be reviewed before any comparative result is promoted to README or the leaderboard.

## Non-blocking adoption tasks

These improve discovery but do not hold the package release hostage:

- set the GitHub About description and Topics;
- publish and verify the hosted demo, then set the Website field;
- upload the prepared repository Social Preview;
- enable/expand community promotion after the release is verifiably published.

## Release procedure

1. Keep the source scope frozen; only release-verification and metadata fixes belong in the RC.
2. Run the full repository gate set on the final release PR head.
3. Confirm wheel + sdist, clean-wheel SDK/CLI smoke, security scans, and `dsa verify-release v4.3.0` remain green.
4. Merge the release candidate only after the final metadata head is green.
5. Create tag `v4.3.0` only from the verified merged commit; let Trusted Publishing publish that exact tagged commit.
6. Verify PyPI, GitHub Release assets, attestations, and the release announcement before closing the release issue.

## Release decision

**Current decision: READY FOR FINAL METADATA CHECKS; NOT YET READY TO TAG.** All functional and packaging release gates have passed with retained evidence. The remaining pre-merge requirement is a completely green check set on this final metadata head.
