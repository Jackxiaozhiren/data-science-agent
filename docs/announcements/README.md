# Release Announcements

This directory contains shareable release announcements generated from verified GitHub Releases.

For future tagged releases, the publish workflow will generate:

- `<tag>.md` — immutable, version-specific announcement copy;
- `latest.md` — a pointer-style copy for the newest published version.

Each announcement links back to the canonical GitHub Release and PyPI package. Release notes remain the source of truth for detailed changes and artifacts.

`latest.md` is a copy of the newest announcement that release workflow actually produced — it is written by
`scripts/generate_release_announcement.py` when a release is published, not looked up live. If the version it
names is older than `pip install -U jack-data-science-agent` gives you, the generator has not run for the newer
tag; [GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) is the authoritative list.

That failure mode is what left the copy at v4.2.10 for five releases: the `Publish` runs for v4.3.x and v4.4.0
reached PyPI and then died at *Attach distributions to GitHub Release safely*, so the announcement step behind
it was skipped. The v4.4.0 copy here was produced by running that script's own `render()` against the published
release, which the workflow's content comparison treats as already up to date, so a future run for the same tag
overwrites nothing.

- 2026-10-08: `v4.4.0.md` added and `latest.md` regenerated from the v4.4.0 GitHub Release (published
  2026-09-11) — `AUDIT_LEDGER.md` §135.

[View all GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) · [PyPI](https://pypi.org/project/jack-data-science-agent/)
