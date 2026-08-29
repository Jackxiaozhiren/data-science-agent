from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def replace(path: str, old: str, new: str, *, count: int = -1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{path}: expected text not found: {old!r}")
    target.write_text(text.replace(old, new, count), encoding="utf-8")


def main() -> None:
    replace("pyproject.toml", 'version = "4.2.10"', 'version = "4.3.0"', count=1)
    replace(
        "src/data_science_agent/__init__.py",
        '__version__ = "4.2.10"',
        '__version__ = "4.3.0"',
        count=1,
    )
    replace(
        "src/data_science_agent/sdk.py",
        'version == "4.2.10"',
        'version == "4.3.0"',
        count=1,
    )
    replace(
        "src/data_science_agent/sdk.py",
        '``"4.2.10"`` string.',
        '``"4.3.0"`` string.',
        count=1,
    )
    replace(
        "src/data_science_agent/sdk.py",
        'self._version = "4.2.10"',
        'self._version = "4.3.0"',
        count=1,
    )
    replace(
        "apps/jupyter/src/dsa_jupyter/metadata.py",
        'sdk_version = "4.2.10"',
        'sdk_version = "4.3.0"',
        count=1,
    )
    replace("CITATION.cff", "version: 4.2.10", "version: 4.3.0", count=1)
    replace(
        "CITATION.cff",
        "date-released: 2026-08-26",
        "date-released: 2026-08-29",
        count=1,
    )
    replace(
        "packages/plugins/src/dsa_plugins/manifest.py",
        'CURRENT_DSA_VERSION = "4.2.10"',
        'CURRENT_DSA_VERSION = "4.3.0"',
        count=1,
    )
    replace(
        "scripts/check_public_claims.py",
        '"version": "4.2.10"',
        '"version": "4.3.0"',
        count=1,
    )
    replace(
        "tests/api/compatibility/test_sdk_compat.py",
        'a.version == "4.2.10"',
        'a.version == "4.3.0"',
        count=1,
    )
    replace(
        "tests/jupyter/test_jupyter_integration.py",
        'meta["sdk_version"] == "4.2.10"',
        'meta["sdk_version"] == "4.3.0"',
        count=1,
    )
    replace(
        ".github/DISCUSSION_TEMPLATE/q-a.yml",
        "placeholder: e.g. 4.2.10",
        "placeholder: e.g. 4.3.0",
        count=1,
    )

    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    title = "## 4.3.0 — Adoption, Verifiable Evaluation & Project Reliability"
    if title not in text:
        marker = "# Changelog\n\n"
        if not text.startswith(marker):
            raise SystemExit("CHANGELOG.md: unexpected header")
        entry = """## 4.3.0 — Adoption, Verifiable Evaluation & Project Reliability

### Added

- **Auditable real-model execution** via an explicit OpenAI Responses API path. Offline/stub execution remains the deterministic default; real calls require explicit opt-in and never silently substitute the stub provider.
- **Four controlled evaluation variants** under one provenance model: full DSA, DSA without the evidence critic, vanilla LLM + tools, and an LLM-only control.
- **Credentialed four-way smoke evaluation workflow** that is manual-only, accepts no dispatch inputs, fixes the first smoke to one model/task/pricing snapshot, scopes the API key to execution steps, uploads per-row artifacts, and fails if any row or the matrix-integrity validator fails.
- **Publication-integrity validator** for four-way artifacts, including provider/model/call-count, task/catalog/dataset snapshot, baseline-control, critic-state, pricing, commit, and cross-row consistency checks.
- **Adoption and contributor paths**: Windows PowerShell quickstart, benchmark-task contribution walkthrough, executable hello-world plugin walkthrough, structured issue/discussion templates, public roadmap, contributor recognition, and richer project automation.
- **Case-study discovery improvements** with a visual gallery and three flagship workflows surfaced near the README demo.

### Changed

- Repositioned the project around **verifiable, reproducible AI data science**: claim-level evidence, inspectable artifacts, and explicit separation between deterministic harness validation and real-model comparative results.
- Made hosted-demo frontend/backend boundaries configurable for cross-origin deployment and documented the verified launch sequence without advertising an unverified backend URL.
- Hardened repository operations with actionlint, lock/vendor drift checks, dependency review, secret scanning, CodeQL, SonarQube quality gates, and reproducible leaderboard/contributor automation.

### Security

- Upgraded the web runtime to **Next.js 16.3.3**, **React/ReactDOM 19.2.8**, and **Sharp 0.35.4**, raised the PostCSS floor, and documented upstream license obligations.
- Added a permanent `npm audit --audit-level=high` CI gate so High/Critical web dependency advisories cannot hide in install logs.
- Kept real-model workflow permissions least-privilege, checkout credentials non-persistent, actions pinned by commit SHA, and credentials out of artifacts and repository content.

### Fixed

- Fixed the packaged `dsa` console bootstrap so vendored `dsa_*` aliases initialize before the evaluation CLI imports.
- Fixed the API Docker image so the root `src/` package is present; CI now verifies the packaged/container CLI path.
- Added a root npm workspace lock drift guard and corrected Dependabot's Docker update directory.

### Evaluation integrity

- The existing `stub/small` result remains **harness validation**, not a real-model leaderboard claim.
- v4.3.0 ships the execution and validation machinery for a credible four-way comparison, but **does not claim comparative real-model scores until credentialed artifacts pass publication review**.

### Compatibility

- No intentional breaking change to the Stable public SDK surface.
- Python **3.12+** remains the supported baseline for this release; the separate Python 3.14 and Node 26 base-image Dependabot proposals are intentionally excluded from this candidate and require independent review.

"""
        changelog.write_text(marker + entry + text[len(marker) :], encoding="utf-8")

    readiness = """# v4.3.0 Release Readiness

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
"""
    (ROOT / "docs/release-readiness-v4.3.md").write_text(readiness, encoding="utf-8")

    manifest = {
        "version": "4.3.0",
        "release_tag": "v4.3.0",
        "status": "release-candidate",
        "theme": "Adoption, Verifiable Evaluation & Project Reliability",
        "previous_tag": "v4.2.10",
        "previous_release_commit": "ecf16d0dcef229e38094a853310dd4acd347419b",
        "source_candidate_commit": "fcb98f455dff644ebd0e525083fd0f1d7e344369",
        "commits_since_previous_release": 103,
        "release_metadata_commit": None,
        "python_requires": ">=3.12",
        "real_model_publication_status": (
            "execution-and-validation-ready; no credentialed comparative score published"
        ),
        "excluded_open_runtime_updates": [
            "#45 python 3.12-slim -> 3.14-slim",
            "#46 node 20-alpine -> 26-alpine",
        ],
        "gates": {
            "ci": "pending",
            "dependency_review": "pending",
            "secret_scan": "pending",
            "codeql": "pending",
            "sonarqube": "pending",
            "wheel_sdist_build": "pending",
            "clean_wheel_install": "pending",
            "sdk_smoke": "pending",
            "cli_smoke": "pending",
            "release_verification": "pending",
        },
        "notes": [
            "Manifest records the frozen source candidate rather than attempting a self-referential metadata commit SHA.",
            "Do not create v4.3.0 tag until all release-critical gates are PASS on the final metadata commit.",
            "No deterministic stub result is represented as real-model comparative quality.",
        ],
    }
    out = ROOT / "release" / "v4.3.0" / "manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
