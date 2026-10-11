"""Render a release announcement from data the repository already holds.

Two modes, and neither writes to a remote branch. The pipeline used to render the copy from the
*published* release and commit it to the default branch from inside ``publish.yml``, and that write
cannot succeed: ``main`` is protected with ``ci`` required and ``strict: true``, the commit a version
tag may name is exactly the commit whose ``ci`` ran while the tag was still missing, and pushing a
tag triggers no ``ci`` for that SHA (§149, run 37919265633 → 409 on *Generate release announcement*).

    --preview v4.6.0        Render the copy for the release this tree is preparing, from the
                            CHANGELOG section for that version, and write both copies into the
                            working tree. This is the pipeline path: the copy rides the release PR,
                            so it is on the default branch before the tag is cut (§151).

    --from-release v4.4.0   Render the copy from a published GitHub Release instead, for backfilling
                            a release that shipped without one. Needs a token to read the release;
                            committing the result stays the operator's step.

A copy says only what its mode can observe. ``--from-release`` prints the publication date because
the release reports it; ``--preview`` prints none, because at preview time there is no publication
date to know.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"

#: Every copy opens with this line, and `check_public_claims` reads the announced version back out
#: of it -- the two must agree on one spelling, so it lives here once.
TITLE_PREFIX = "# Data Science Agent"

PITCH = (
    "Evidence-grounded autonomous data science, from natural-language questions to "
    "reproducible analysis."
)

PROVENANCE = (
    "This announcement is rendered by `scripts/generate_release_announcement.py` from the "
    "repository's release record -- the CHANGELOG section for the version, or the published "
    "GitHub Release. The release page remains the source of truth for artifacts and full notes."
)

#: The highlights of a published release are truncated to this, because the release body is prose
#: written for a release page rather than for a one-page announcement.
MAX_HIGHLIGHTS = 1800


class GitHubAPIError(RuntimeError):
    """GitHub API error with the HTTP status preserved for retry decisions."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"GitHub API request failed ({status}): {body}")
        self.status = status


class SectionNotFound(RuntimeError):
    """The CHANGELOG holds no section for the version being prepared."""


class LatestIsNewer(RuntimeError):
    """`latest.md` announces a newer release than the copy being written."""


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "data-science-agent-release-announcement",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(  # noqa: S310 - API=https hardcoded above, path internal
        f"{API}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - API=https hardcoded above, path internal
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            return None
        raise GitHubAPIError(exc.code, body) from exc


def _template(tag: str, highlights: str, *, release_url: str, released_line: str | None) -> str:
    lead = f"> {released_line} · {PITCH}" if released_line else f"> {PITCH}"
    return f"""{TITLE_PREFIX} {tag}

{lead}

## Install or upgrade

```bash
pip install -U jack-data-science-agent
```

## Highlights

{highlights}

## Verify the release

- [GitHub Release]({release_url})
- [PyPI](https://pypi.org/project/jack-data-science-agent/)
- Inspect the attached wheel/sdist and publishing attestations on the release page.

## Share-ready summary

> Data Science Agent {tag} is available: evidence-grounded autonomous data science with reproducible reports, claim-level provenance, benchmarks, and multiple interfaces. Release: {release_url}

---

{PROVENANCE}
"""


def _bounded(highlights: str, limit: int = MAX_HIGHLIGHTS) -> str:
    """Keep the copy shareable: cut at a line boundary and name where the rest lives.

    A CHANGELOG section runs to hundreds of lines -- rendering v4.5.0 from its own produced 58,971
    characters before this bound existed -- and an announcement page that long is a mirror, not a
    summary. The ellipsis is the last character so the cut is visible rather than silent.
    """
    if len(highlights) <= limit:
        return highlights
    cut = highlights[:limit].rstrip()
    boundary = cut.rfind("\n")
    if boundary > 0:
        cut = cut[:boundary]
    return cut.rstrip() + "\n\nFull entries: `CHANGELOG.md` and the release notes.\n\n…"


def render(tag: str, release: dict[str, Any]) -> str:
    """The published-release form: the date and the notes come from the release itself."""
    notes = str(release.get("body") or "").strip() or "_No release notes supplied._"
    highlights = (
        notes if len(notes) <= MAX_HIGHLIGHTS else notes[:MAX_HIGHLIGHTS].rstrip() + "\n\n…"
    )
    published = str(release.get("published_at") or "")[:10] or "unknown date"
    return _template(
        tag,
        highlights,
        release_url=str(release.get("html_url") or ""),
        released_line=f"Released {published}",
    )


def changelog_highlights(changelog: str, version: str) -> str:
    """The `## <version>` section of the changelog, ending at the next level-two heading.

    Sliced by heading level, not searched for a substring: `### ` subsections belong to the section
    and the following `## ` does not.
    """
    heading = re.compile(rf"^## {re.escape(version)}(?:\s|$)")
    lines = changelog.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if start is None:
            if heading.match(line):
                start = index + 1
        elif line.startswith("## "):
            return "\n".join(lines[start:index]).strip()
    if start is None:
        raise SectionNotFound(
            f"CHANGELOG.md has no `## {version}` section. Move this release's entries out of "
            "`## Unreleased` and under that heading before preparing the announcement copy: the "
            "copy is rendered from them, so a missing section leaves nothing honest to render."
        )
    return "\n".join(lines[start:]).strip()


def release_url_for(repository: str, tag: str) -> str:
    """The URL this release will have. Derivable before the tag exists, so nothing is invented."""
    return f"https://github.com/{repository}/releases/tag/{tag}"


def preview(tag: str, changelog: str, repository: str) -> str:
    """The pre-tag form: curated highlights, a derivable URL, and no publication date."""
    return _template(
        tag,
        _bounded(changelog_highlights(changelog, tag.removeprefix("v"))),
        release_url=release_url_for(repository, tag),
        released_line=None,
    )


def title_version(text: str) -> str | None:
    """The version a copy announces, read from its title line."""
    match = re.match(rf"^{re.escape(TITLE_PREFIX)} v(\d+\.\d+\.\d+)\s*$", text.splitlines()[0])
    return match.group(1) if match else None


def _key(version: str) -> tuple[int, int, int]:
    major, minor, patch = (int(part) for part in version.split("."))
    return (major, minor, patch)


def write_copies(root: Path, tag: str, text: str) -> list[Path]:
    """Write `docs/announcements/<tag>.md` and `latest.md`, refusing to move the pointer backwards.

    `latest.md` is what a reader installs, so a run for an older tag must not overwrite a newer one.
    The version being prepared is the only one allowed to lead the tags, which is the state this
    flow creates on purpose.
    """
    version = tag.removeprefix("v")
    directory = root / "docs" / "announcements"
    latest = directory / "latest.md"
    if latest.is_file():
        current = title_version(latest.read_text(encoding="utf-8"))
        if current is not None and _key(current) > _key(version):
            raise LatestIsNewer(
                f"docs/announcements/latest.md already announces v{current}; refusing to replace "
                f"it with v{version}. A copy may lead the tags only for the version being prepared."
            )
    directory.mkdir(parents=True, exist_ok=True)
    written = [directory / f"{tag}.md", latest]
    for path in written:
        path.write_text(text, encoding="utf-8")
    return written


def load_release(tag: str, repository: str) -> dict[str, Any]:
    release = request_json(
        "GET", f"/repos/{repository}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    )
    if not isinstance(release, dict):
        raise GitHubAPIError(404, f"Release {tag!r} was not found on {repository}")
    return release


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a release announcement into the tree.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--preview",
        metavar="TAG",
        help="render the copy for a release that has not been tagged yet, from CHANGELOG.md",
    )
    mode.add_argument(
        "--from-release",
        metavar="TAG",
        help="render the copy from the published GitHub Release (backfill; writes no remote branch)",
    )
    parser.add_argument(
        "--repository",
        required=True,
        help="owner/repo, for the release URL; required because a wrong slug ships in the copy",
    )
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--root", default=".", help="repository root to write into")
    parser.add_argument("--stdout", action="store_true", help="print the copy instead of writing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tag = args.preview or args.from_release
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise SystemExit(f"Tag must look like v1.2.3, got {tag!r}")
    if not args.repository:
        raise SystemExit(
            f"{tag} needs --repository owner/repo: the copy links to the release, and inventing a "
            "slug is not the same as deriving one."
        )

    if args.preview:
        text = preview(tag, Path(args.changelog).read_text(encoding="utf-8"), args.repository)
    else:
        text = render(tag, load_release(tag, args.repository))

    if args.stdout:
        print(text, end="")
        return 0
    for path in write_copies(Path(args.root), tag, text):
        print(f"wrote {path} ({len(path.read_text(encoding='utf-8'))} chars)")
    print(
        f"Prepared {tag}. Commit both files on the release branch so the copy is on the default "
        "branch before the tag is cut; publish.yml verifies the tree it builds."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
