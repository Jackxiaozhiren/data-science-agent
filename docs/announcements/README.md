# Release Announcements

This directory holds shareable release announcements. Each copy is rendered by
`scripts/generate_release_announcement.py` and committed like any other file in the repository; nothing in
the release pipeline writes here after the fact.

## How a copy gets here

On the release branch, alongside the version bump:

```bash
python scripts/generate_release_announcement.py --preview v4.6.0 --repository <owner>/<repo>
```

That writes `docs/announcements/v4.6.0.md` and `docs/announcements/latest.md` from the `## 4.6.0` section of
`CHANGELOG.md`, and the release PR carries both. A pre-tag copy states no publication date, because at that
moment there is none to observe; it links to the release URL, which is derivable from the tag. `--from-release
v4.6.0` renders the other way -- from a published GitHub Release, date and all -- and exists for backfilling a
release that shipped without a copy. It writes files, never a branch.

`publish.yml` then only verifies the tree it checked out: the tag's own copy must exist and open with
`# Data Science Agent <that tag>`, and `latest.md` must say the same. If the release PR forgot the copy, the
release goes red with the command to prepare it.

## Why the workflow stopped writing here

Until §151 the announcement step committed both copies to the default branch through the contents API. That
write cannot succeed while `main` is protected with `ci` required and `strict: true`:

- **v4.3.x and v4.4.0 — the run died before the announcement step.** Those `Publish` runs reached PyPI and then
  failed at *Attach distributions to GitHub Release safely*, so the step behind it was skipped. The v4.4.0 copy
  here was produced by running the script's own `render()` against the published release.
- **v4.5.0 — the run reached the step and GitHub refused the write.** `Publish` run 37919265633 passed steps 1-20
  (PyPI 4.5.0, immutable GitHub Release with four assets) and failed at *Generate release announcement* with
  `409: Could not create file: Required status check "ci" is expected.` The tag names `39fe318`, and the `ci` run
  on that commit — 37913590449 — had already finished **failure** 54 minutes before the publish run started, at
  `Run uv run python scripts/check_public_claims.py --require-released-tags`, printing two findings:
  `git tag mismatch: v4.4.0-228-g39fe318 base v4.4.0 != v4.5.0` and `README.md:16 cites '4.5.0', advertised as
  the current release, but the newest release tag is '4.4.0'`.

Those two findings are correct assertions: a commit that declares 4.5.0 while the newest tag is 4.4.0 does claim
a release that does not exist yet. The cost was structural. The commit a version tag may name is exactly the
commit whose `ci` had to run while the tag was still missing, and pushing a tag triggers no `ci` for that SHA
(`ci.yml` triggers on `push: branches: [main]` and `pull_request`, not on tags), so the parent of any
post-publish commit is red by construction and the write is refused -- on every release, not only this one.

Two alternatives were considered and rejected on measured grounds. Having the workflow open a PR instead needs
`pull-requests: write`, but GitHub documents that *"when you use the repository's GITHUB_TOKEN to perform
tasks, events triggered by the GITHUB_TOKEN will not create a new workflow run"*
([docs](https://docs.github.com/en/actions/concepts/security/github_token)), so such a PR carries no `ci`
check and could only be merged by an admin override -- a manual step in a different place. Relaxing protection
would remove the gate that §148 showed decides the whole pipeline's shape. So the copy moved upstream in time
instead of downstream: prepared before the tag, merged with the release PR, verified by the release itself.

## Reading the copies

`latest.md` is the copy of the newest release this repository carries -- rendered by the script, not looked up
live. If the version it names is older than `pip install -U jack-data-science-agent` gives you, a release was
cut without its copy; [GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) is the
authoritative list. Each copy links back to the canonical GitHub Release and the PyPI package, and release
notes remain the source of truth for detailed changes and artifacts.

- 2026-10-08: `v4.4.0.md` added and `latest.md` regenerated from the v4.4.0 GitHub Release (published
  2026-09-11) — `AUDIT_LEDGER.md` §135.
- 2026-10-11: `v4.5.0.md` added and `latest.md` regenerated from the v4.5.0 GitHub Release (published
  2026-10-09) after run 37919265633 step 21 was refused by branch protection — `AUDIT_LEDGER.md` §149.
- 2026-10-11: the pipeline changed. Copies are prepared by `--preview` on the release branch, `publish.yml`
  verifies the tree it builds, and the newest tag is no longer exempt from the copy-coverage rule —
  `AUDIT_LEDGER.md` §151.

[View all GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) · [PyPI](https://pypi.org/project/jack-data-science-agent/)
