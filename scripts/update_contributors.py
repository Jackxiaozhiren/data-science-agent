"""Render and publish CONTRIBUTORS.md from GitHub contributor data.

The script uses only the Python standard library. Bot accounts are excluded.
Updates go through the GitHub Contents API with a bounded retry on SHA conflicts,
so concurrent pushes to ``main`` do not cause non-fast-forward failures.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.github.com"
TARGET = "CONTRIBUTORS.md"


def request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "data-science-agent-contributor-recognition",
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
        error = RuntimeError(f"GitHub API request failed ({exc.code}): {body}")
        error.status = exc.code  # type: ignore[attr-defined]
        raise error from exc


def fetch_contributors(repository: str) -> list[dict[str, Any]]:
    contributors: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = request_json("GET", f"/repos/{repository}/contributors?per_page=100&page={page}")
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


def current_file(repository: str, branch: str) -> tuple[str, str]:
    path = urllib.parse.quote(TARGET, safe="/")
    current = request_json("GET", f"/repos/{repository}/contents/{path}?ref={urllib.parse.quote(branch)}")
    if not isinstance(current, dict) or not current.get("sha") or not current.get("content"):
        raise RuntimeError(f"Could not load {TARGET}")
    existing = base64.b64decode(str(current["content"])).decode("utf-8")
    return str(current["sha"]), existing


def publish(repository: str, branch: str, content: str) -> None:
    path = urllib.parse.quote(TARGET, safe="/")
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

    for attempt in range(1, 4):
        sha, existing = current_file(repository, branch)
        if existing == content:
            print(f"{TARGET} is already up to date.")
            return

        payload = {
            "message": "docs: refresh contributor recognition [skip ci]",
            "branch": branch,
            "sha": sha,
            "content": encoded,
        }
        try:
            request_json("PUT", f"/repos/{repository}/contents/{path}", payload)
            print(f"Updated {TARGET} on {branch}.")
            return
        except RuntimeError as exc:
            if getattr(exc, "status", None) not in {409, 422} or attempt == 3:
                raise
            print(f"Concurrent update detected; retrying {TARGET} ({attempt}/3).")
            time.sleep(attempt)

    raise RuntimeError(f"Could not update {TARGET} after retries")


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository or "/" not in repository:
        raise RuntimeError("GITHUB_REPOSITORY must be set to owner/repo")

    repo = request_json("GET", f"/repos/{repository}")
    if not isinstance(repo, dict):
        raise RuntimeError("Could not load repository metadata")
    branch = str(repo.get("default_branch") or "main")

    content = render(repository, fetch_contributors(repository))
    publish(repository, branch, content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
