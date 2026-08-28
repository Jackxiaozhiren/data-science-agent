"""Render CONTRIBUTORS.md from GitHub contributor data.

This script is designed for GitHub Actions and uses only the Python standard
library. Bot accounts are excluded. It writes CONTRIBUTORS.md locally; the
workflow is responsible for committing the file if it changed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
OUT = Path("CONTRIBUTORS.md")


def api_get(path: str) -> Any:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "data-science-agent-contributor-recognition",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(f"{API}{path}", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {body}") from exc


def fetch_contributors(repository: str) -> list[dict[str, Any]]:
    contributors: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = api_get(f"/repos/{repository}/contributors?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise RuntimeError("GitHub contributors endpoint did not return a list")
        contributors.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < 100:
            break
    return contributors


def render(repository: str, contributors: list[dict[str, Any]]) -> str:
    humans = [
        item
        for item in contributors
        if item.get("login")
        and item.get("type") != "Bot"
        and not str(item.get("login")).endswith("[bot]")
    ]
    humans.sort(key=lambda item: (-int(item.get("contributions") or 0), str(item["login"]).lower()))

    if humans:
        rows = "\n".join(
            f"| [@{item['login']}](https://github.com/{item['login']}) | {int(item.get('contributions') or 0)} |"
            for item in humans
        )
    else:
        rows = "| _No human contributors discovered yet_ | — |"

    owner, repo = repository.split("/", 1)
    return f"""# Contributors

Data Science Agent is built by people who improve code, documentation, benchmarks, reproducibility, plugins, case studies, and community workflows.

This page is maintained automatically from GitHub's contributor data. Bot accounts are excluded.

> Contribution counts below are GitHub commit counts on the repository. They are a maintenance signal, **not a ranking of contribution value**.

<!-- contributors-table:start -->

| Contributor | GitHub commit contributions |
|---|---:|
{rows}

<!-- contributors-table:end -->

## Ways to be recognized

Contributions that can become part of the project include:

- code and bug fixes;
- benchmark tasks and evaluation improvements;
- reproducibility investigations;
- documentation and examples;
- plugins and integrations;
- case studies and datasets with clear licensing;
- issue triage and high-quality technical review.

Start with the [Contributing Guide](CONTRIBUTING.md) or browse [good first issues](https://github.com/{owner}/{repo}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
"""


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository or "/" not in repository:
        raise RuntimeError("GITHUB_REPOSITORY must be set to owner/repo")

    content = render(repository, fetch_contributors(repository))
    OUT.write_text(content, encoding="utf-8")
    print(f"Rendered {OUT} for {repository}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
