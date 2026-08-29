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

The open Dependabot proposals that jump the Docker bases to Python 3.14 and Node 26 are **not** part of v4.3.0. They are major runtime changes and should be evaluated separately after this release candidate.

## Release-manifest semantics

`release/v4.3.0/manifest.json` records the immutable **source candidate SHA** above. It does not attempt to embed the SHA of the commit that contains the manifest itself, which would be a self-reference. The final `v4.3.0` tag should point to the release-metadata commit only after that commit has passed every release-critical gate.

## Current gates

| Gate | State | Requirement |
|---|---|---|
| Scope frozen | ✅ PASS | Actual `v4.2.10...source-candidate` diff reviewed and bounded |
| Package/version surfaces | 🟡 IN RC | Canonical runtime/citation/test surfaces set to `4.3.0` |
| Changelog | 🟡 IN RC | Entry derived from the frozen 103-commit diff |
| Release manifest | 🟡 IN RC | Records source candidate and pending final gates |
| uv lock / vendored sources / SBOM | 🟡 IN RC | Regenerated from candidate metadata |
| Ruff / formatting | ⏳ PENDING | Must pass on the release PR head |
| mypy | ⏳ PENDING | Must pass on the release PR head |
| full pytest | ⏳ PENDING | Must pass on the release PR head |
| benchmark smoke | ⏳ PENDING | Must pass on the release PR head |
| API + Web Docker | ⏳ PENDING | Both images plus packaged `dsa` CLI must pass |
| Web production build | ⏳ PENDING | Next.js production build must pass |
| Compose / MkDocs strict | ⏳ PENDING | Both must pass |
| Dependency Review / Secret Scan | ⏳ PENDING | Both must pass |
| CodeQL Python + JavaScript | ⏳ PENDING | Both must pass |
| SonarQube Quality Gate | ⏳ PENDING | Must pass with no unresolved new security issues |
| Wheel + sdist build | ⏳ PENDING | Build only the umbrella distribution |
| Clean-wheel install smoke | ⏳ PENDING | Fresh environment import + SDK + CLI smoke |
| Final release verification | ⏳ PENDING | Release verification must pass for the final candidate |
| Tag / PyPI / GitHub Release | ⛔ BLOCKED | Only after every release-critical gate above is PASS |

## Real-model reporting boundary

The code now supports a controlled four-way real-model comparison and validates its artifacts. The release does **not** depend on publishing a benchmark score: `OPENAI_API_KEY` still has to be configured manually in GitHub Actions, and the credentialed smoke artifacts must be reviewed before any comparative result is promoted to README or the leaderboard.

## Non-blocking adoption tasks

These improve discovery but do not hold the package release hostage:

- set the GitHub About description and Topics;
- publish and verify the hosted demo, then set the Website field;
- upload the prepared repository Social Preview;
- enable/expand community promotion after the release is verifiably published.

## Release procedure

1. Commit the version/changelog/manifest/generated-metadata candidate on `release/v4.3.0-rc`.
2. Run the full repository gate set on the release PR.
3. Build wheel + sdist from the exact release PR head.
4. Install the wheel in a clean environment and run import, SDK version, and CLI smoke checks.
5. Record final gate evidence in the manifest/readiness document and rerun gates after any metadata change.
6. Only then merge the release candidate, create tag `v4.3.0`, and let Trusted Publishing publish the exact tagged commit.
7. Verify PyPI, GitHub Release assets, attestations, and release announcement before marking the release issue complete.

## Release decision

**Current decision: NOT READY TO TAG.** The source scope is frozen and release formalization is in progress; final candidate verification remains mandatory.
