# v4.3.0 Release Readiness

This document is the public release gate for the next Data Science Agent minor release.

It exists to prevent a version tag from becoming the mechanism that decides whether a change set is ready. The release should happen **after** the candidate commit satisfies the evidence below.

## Candidate theme

**v4.3.0 — Adoption, Community Reliability, and Verifiable Project Operations**

Compared with `v4.2.10`, the current candidate line adds substantial public-project infrastructure without intentionally changing the stable core analysis API:

- conversion-oriented README, hero, and executable-looking product demo surface;
- eight visual case studies with three flagship workflows;
- structured issue and discussion contribution routes;
- contributor recognition, triage, stale management, and PR/issue labeling;
- deterministic benchmark leaderboard generation and validation;
- automated release announcements;
- public roadmap and contributor pathways;
- GitHub Actions hardening with concurrency, least-privilege permissions, timeouts, and `actionlint`;
- tests for repository automation and conflict-safe GitHub Contents API writes.

The release theme is therefore **adoption + operational reliability**, not a claim of a new core modeling architecture.

## Current evidence

Baseline hardening commit: `6ebfbe27b8a6ba287fa5b54f11649df280d7694a`

| Gate | Current state | Evidence / requirement |
|---|---|---|
| GitHub Actions syntax | ✅ PASS | `actionlint 1.7.12` runs as the first CI quality gate with a pinned archive checksum |
| Ruff | ✅ PASS | lint and formatting checks passed on the hardening run |
| mypy | ✅ PASS | strict project type-check gate passed |
| pytest + coverage gate | ✅ PASS | full test command passed, including repository automation tests |
| Benchmark smoke | ✅ PASS | CI benchmark smoke passed |
| API Docker image | ✅ PASS | image build passed |
| Web Docker image | ✅ PASS | image build passed |
| Web production build | ✅ PASS | build passed |
| Docker Compose config | ✅ PASS | config validation passed |
| MkDocs strict build | ✅ PASS | documentation build passed |
| CodeQL Python | ✅ PASS | latest hardening run completed successfully |
| CodeQL JavaScript | ✅ PASS | latest hardening run completed successfully |
| Secret Scan | ✅ PASS | latest hardening run completed successfully |
| Contributor Recognition | ✅ PASS | conflict-safe Contents API workflow completed successfully |
| Package version | ❌ NOT READY | still `4.2.10`; bump only when the final candidate is frozen |
| `CHANGELOG.md` v4.3.0 entry | ❌ NOT READY | write from the final diff, not from planned work |
| v4.3 release manifest | ❌ NOT READY | generate from the final candidate SHA and gate results |
| Fresh-wheel install smoke | ⏳ FINAL GATE | build the final candidate wheel, install in a clean environment, run SDK + CLI smoke |
| Final candidate CI | ⏳ FINAL GATE | rerun all release-critical checks after version/changelog/manifest changes |
| Tag / PyPI publish | ⛔ BLOCKED | do not tag until every required gate above is PASS |

## Release blockers

The following conditions block `v4.3.0`:

1. The package version is still `4.2.10`.
2. There is no final `4.3.0` changelog section derived from the frozen diff.
3. There is no `release/v4.3.0/manifest.json` tied to the final candidate commit.
4. The final wheel has not yet been built and smoke-tested from a clean environment.
5. Any CI, CodeQL, secret-scan, benchmark, docs, packaging, or reproduction regression on the final candidate blocks the tag.

## Scope reconciliation

Historical internal `docs/v4_3` material was intentionally removed during the 4.2.2 repository-hygiene cleanup. Therefore the public repository must not imply that an old internal v4.3 specification has automatically been completed.

For the public release, the canonical scope is the **actual diff from `v4.2.10` to the frozen candidate commit**, summarized in the changelog and this gate.

If a separate private/internal v4.3 specification contains additional product requirements, those requirements must be reconciled before the version bump; they should not be inferred from historical deleted files.

## Final release procedure

When the scope is frozen:

1. Ensure no unrelated feature work is still entering `main`.
2. Review `git diff v4.2.10...<candidate>` and classify every material change.
3. Update `pyproject.toml` and all canonical version surfaces to `4.3.0`.
4. Add the `4.3.0` changelog entry from the actual diff.
5. Generate `release/v4.3.0/manifest.json` with the final commit and gate metadata.
6. Run full CI, CodeQL, secret scan, benchmark, docs, Docker, and automation tests on the candidate.
7. Build the wheel/sdist from the candidate.
8. Install the wheel in a clean environment and run SDK + CLI smoke tests.
9. Run the project's release verification command for `v4.3.0` if applicable to the final release configuration.
10. Only after every release-critical gate is green, create tag `v4.3.0` and let Trusted Publishing perform the release.
11. Verify the GitHub Release, PyPI artifacts, attestations, and generated release announcement.

## Non-blocking adoption tasks

These improve discoverability but should not hold the package release hostage:

- enable GitHub Discussions in repository settings;
- populate repository About description and Topics;
- upload the prepared Social Preview image;
- expand external community promotion after the release is verifiably published.

## Release decision

**Current decision: NOT READY TO TAG.**

The engineering baseline is green. The remaining work is release formalization and final-candidate verification, not emergency CI repair.
