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

`release/v4.3.0/manifest.json` records the immutable **source candidate SHA** above. It does not attempt to embed the SHA of the commit that contains the manifest itself, which would be a self-reference. The final `v4.3.0` tag should point to the merged release commit only after the PR head has passed every release-critical gate.

## Verified gate evidence

Three evidence layers are retained for the release candidate:

- Distribution CI run `33287733264` on candidate head `3e34b07549a1f9912dbf235255fdcda9cad57167` passed the complete repository CI, including wheel + sdist build, clean-wheel installation, public SDK import/version checks, installed `dsa --help`, API/Web Docker builds, container CLI smoke, Next production build, Compose, and MkDocs strict.
- Historical clean-checkout release-verification run `33288208568` on candidate head `e87eecccdfaed1f8e0e995f95ea1d2553d7a339f` passed the then-current aggregate verifier at **14/14 gates**. Its report is retained as Actions artifact `9725134640` with artifact digest `sha256:48bfc019f982ff1753bda8a2bd1e2ebc63859becf45e51eb381e5816c37f8e63` through 2026-09-29. It is supporting historical evidence, not a substitute for final-head checks.
- Final pre-metadata candidate head `3f6b184eb9f62baf14a4a6fb84898932b63f384e` passed CI run `33289287375`, Dependency Review, Secret Scan, both CodeQL language jobs, and the SonarQube Quality Gate. SonarQube reported **4 non-blocking new issues and 0 security hotspots**; the Quality Gate passed.

The current `dsa verify-release` implementation is deliberately narrower and safer: it performs deterministic validation of retained release evidence, accepts only an explicitly supported static manifest path, and has no external-process execution capability. Tests, builds, package installation, containers, CodeQL, secret scanning, dependency review, and SonarQube remain independently executed gates. Compose declares the developer `.env` file optional (`required: false`) so validation remains read-only when that local file is absent.

## Current gates

| Gate | State | Evidence / requirement |
|---|---|---|
| Scope frozen | ✅ PASS | `v4.2.10...fcb98f455dff644ebd0e525083fd0f1d7e344369`, 103 commits |
| Package/version surfaces | ✅ PASS | Canonical runtime/citation/test surfaces set to `4.3.0` |
| Changelog | ✅ PASS | Entry derived from the frozen 103-commit diff |
| Release manifest | ✅ PASS | Records the source candidate and evidence without self-referential SHA claims |
| uv lock / vendored sources / SBOM | ✅ PASS | Regenerated and checked by CI |
| Ruff / formatting | ✅ PASS | Repository CI |
| mypy | ✅ PASS | Repository CI |
| full pytest | ✅ PASS | Repository CI |
| benchmark smoke | ✅ PASS | Repository CI |
| API + Web Docker | ✅ PASS | Both images pass; packaged/container `dsa` CLI also passes |
| Web production build | ✅ PASS | Next.js production build passes |
| Compose / MkDocs strict | ✅ PASS | Both pass in final candidate CI |
| Dependency Review / Secret Scan | ✅ PASS | GitHub security workflows green |
| CodeQL Python + JavaScript | ✅ PASS | Both language jobs completed successfully |
| SonarQube Quality Gate | ✅ PASS | Quality Gate passed; 4 non-blocking new issues, 0 security hotspots |
| Wheel + sdist build | ✅ PASS | Umbrella distribution built successfully in CI |
| Clean-wheel install smoke | ✅ PASS | Fresh venv import + SDK version + CLI smoke passed |
| Current release evidence verification | ✅ PASS | Deterministic retained-evidence verifier passed in final candidate CI |
| Historical clean-checkout verification | ✅ PASS | Earlier aggregate verifier: 14/14 PASS; artifact retained as supporting evidence |
| Final PR-head checks | REQUIRED | The exact PR head merged to `main` must have a green required check set |
| Tag / PyPI / GitHub Release | BLOCKED UNTIL MERGE | Create only from the verified merged commit |

## Real-model reporting boundary

The code supports a controlled four-way real-model comparison and validates its artifacts. The release does **not** depend on publishing a benchmark score: `OPENAI_API_KEY` still has to be configured manually in GitHub Actions, and credentialed smoke artifacts must be reviewed before any comparative result is promoted to README or the leaderboard.

## Non-blocking adoption tasks

These improve discovery but do not hold the package release hostage:

- set the GitHub About description and Topics;
- publish and verify the hosted demo, then set the Website field;
- upload the prepared repository Social Preview;
- enable/expand community promotion after the release is verifiably published.

## Release procedure

1. Keep the source scope frozen; only release-verification and metadata corrections belong in the RC.
2. Run the complete repository check set on the exact final PR head.
3. Merge the release candidate only after that head is green.
4. Verify the merged `main` commit.
5. Create tag `v4.3.0` only from the verified merged commit; let Trusted Publishing publish that exact tagged commit.
6. Verify PyPI, GitHub Release assets, attestations, and the release announcement before closing the release issue.

## Release decision

**READY TO MERGE WHEN THE CURRENT PR HEAD IS GREEN.** All functional, packaging, security, and release-verification gates have passed with retained evidence. The remaining condition is that the exact metadata-corrected PR head complete its required check set successfully.
