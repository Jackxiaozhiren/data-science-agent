# Release Announcements

This directory contains shareable release announcements generated from verified GitHub Releases.

On tagged releases the publish workflow renders two copies:

- `<tag>.md` — immutable, version-specific announcement copy;
- `latest.md` — a pointer-style copy for the newest published version.

Rendering is not the same as landing: the workflow commits both to `main` through the contents API, and that write
is refused while `main` is protected as described below.

Each announcement links back to the canonical GitHub Release and PyPI package. Release notes remain the source of truth for detailed changes and artifacts.

`latest.md` is a copy of the newest announcement that the publish pipeline actually produced — it is rendered by
`scripts/generate_release_announcement.py`, not looked up live. If the version it names is older than
`pip install -U jack-data-science-agent` gives you, the generator did not land its commit for the newer tag;
[GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) is the authoritative list.

Two different reasons the generator has failed to land that commit, both measured rather than assumed:

- **v4.3.x and v4.4.0 — the run died before the announcement step.** Those `Publish` runs reached PyPI and then
  failed at *Attach distributions to GitHub Release safely*, so the announcement step behind it was skipped. The
  v4.4.0 copy here was produced by running that script's own `render()` against the published release, which the
  workflow's content comparison treats as already up to date, so a future run for the same tag overwrites nothing.
- **v4.5.0 — the run reached the step and GitHub refused the write.** `Publish` run 37919265633 passed steps 1-20
  (PyPI 4.5.0, immutable GitHub Release with four assets) and failed at *Generate release announcement* with
  `409: Could not create file: Required status check "ci" is expected.` The tag names `39fe318`, and the `ci` run
  on that commit — 37913590449 — had already finished **failure** 54 minutes before the publish run started, at
  `Run uv run python scripts/check_public_claims.py --require-released-tags`, printing two findings:
  `git tag mismatch: v4.4.0-228-g39fe318 base v4.4.0 != v4.5.0` and `README.md:16 cites '4.5.0', advertised as
  the current release, but the newest release tag is '4.4.0'`. Main is protected with `ci` required and
  `strict: true`, so a contents-API commit whose parent has no *green* `ci` is refused.

Those two findings are the pending-tag assertions, and they are right: a commit that declares 4.5.0 while the
newest tag is 4.4.0 does claim a release that does not exist yet. What that costs the pipeline is structural --
step 21 cannot land on the commit as the pipeline leaves it. The commit a version tag may name is exactly the
commit whose `ci` had to run while the tag was still missing, and pushing the tag does not re-trigger `ci` on that
SHA (`ci.yml` triggers on `push: branches: [main]` and `pull_request`, not on tags), so by the time the release
exists the parent's red `ci` is already recorded and immutable unless someone re-runs it. So the announcement
write needs either a PR opened by the workflow (`pull-requests: write`, whose checks then run with the tag
present), an admin bypass, or a `gh run rerun` of the tagged commit's `ci` before step 21 -- and §146's
replacement, which fixed a different circularity (the gate demanding a copy no release had produced yet), does
not lift this one. Until one of those is chosen, the copies below are written by hand from the same `render()`,
which the workflow's content comparison then treats as up to date.

- 2026-10-08: `v4.4.0.md` added and `latest.md` regenerated from the v4.4.0 GitHub Release (published
  2026-09-11) — `AUDIT_LEDGER.md` §135.
- 2026-10-11: `v4.5.0.md` added and `latest.md` regenerated from the v4.5.0 GitHub Release (published
  2026-10-09) after run 37919265633 step 21 was refused by branch protection — `AUDIT_LEDGER.md` §149.

[View all GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) · [PyPI](https://pypi.org/project/jack-data-science-agent/)
