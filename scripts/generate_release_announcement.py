"""Generate and publish a shareable release announcement from GitHub Release data.

The GitHub Release remains the source of truth. This script uses the standard
library and the workflow-provided GITHUB_TOKEN to upsert announcement Markdown
on the repository default branch.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.github.com"


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

    request = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            return None
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {body}") from exc


def render(tag: str, release: dict[str, Any]) -> str:
    notes = str(release.get("body") or "").strip() or "_No release notes supplied._"
    highlights = notes if len(notes) <= 1800 else notes[:1800].rstrip() + "\n\n…"
    published = str(release.get("published_at") or "")[:10] or "unknown date"
    release_url = str(release.get("html_url") or "")

    return f"""# Data Science Agent {tag}

> Released {published} · Evidence-grounded autonomous data science, from natural-language questions to reproducible analysis.

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

This announcement is generated from the canonical GitHub Release. The release page remains the source of truth for artifacts and full notes.
"""


def upsert(repository: str, branch: str, path: str, content: str, tag: str) -> None:
    quoted_path = urllib.parse.quote(path, safe="/")
    current = request_json("GET", f"/repos/{repository}/contents/{quoted_path}?ref={urllib.parse.quote(branch)}")
    payload: dict[str, Any] = {
        "message": f"docs: publish {tag} announcement [skip ci]",
        "branch": branch,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if isinstance(current, dict) and current.get("sha"):
        payload["sha"] = current["sha"]
    request_json("PUT", f"/repos/{repository}/contents/{quoted_path}", payload)


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    tag = os.environ.get("RELEASE_TAG") or os.environ.get("GITHUB_REF_NAME")
    if not repository or "/" not in repository:
        raise RuntimeError("GITHUB_REPOSITORY must be set to owner/repo")
    if not tag:
        raise RuntimeError("RELEASE_TAG or GITHUB_REF_NAME must be set")

    repo = request_json("GET", f"/repos/{repository}")
    if not isinstance(repo, dict):
        raise RuntimeError("Could not load repository metadata")
    branch = str(repo.get("default_branch") or "main")

    release = request_json("GET", f"/repos/{repository}/releases/tags/{urllib.parse.quote(tag, safe='')}")
    if not isinstance(release, dict):
        raise RuntimeError(f"Release {tag!r} was not found")

    announcement = render(tag, release)
    upsert(repository, branch, f"docs/announcements/{tag}.md", announcement, tag)
    upsert(repository, branch, "docs/announcements/latest.md", announcement, tag)
    print(f"Published announcement for {tag} on {branch}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
