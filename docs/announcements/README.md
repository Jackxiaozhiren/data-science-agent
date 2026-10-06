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

[View all GitHub Releases](https://github.com/Jackxiaozhiren/data-science-agent/releases) · [PyPI](https://pypi.org/project/jack-data-science-agent/)
