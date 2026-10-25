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

#: Where the refresh writes. `main` requires the `ci` status check (strict), and a commit created through the
#: Contents API cannot already carry a check that has not run yet -- so publishing to the default branch is
#: refused with a 409 every week. A normal branch has no such rule, and the result lands as a pull request.
WORK_BRANCH = "chore/contributor-recognition"

#: A 409 that will still be true on the third attempt. Measured verbatim from seven consecutive weekly failures:
#: `Could not update file: Required status check "ci" is expected.`
UNRETRYABLE_HINTS = (
    "required status check",
    "branch protection",
    "protected by a branch",
    "not allowed to push",
)


class GitHubAPIError(RuntimeError):
    """GitHub API error with the HTTP status and body preserved for retry decisions."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"GitHub API request failed ({status}): {body}")
        self.status = status
        self.body = body


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

    request = urllib.request.Request(  # noqa: S310 - API=https hardcoded above, path internal
        f"{API}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - https only, no file: scheme
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise GitHubAPIError(exc.code, body) from exc


def probe(
    method: str, path: str, payload: dict[str, Any] | None = None
) -> tuple[Any, GitHubAPIError | None]:
    """Call the API and hand back (result, error) instead of raising, for the two calls whose failure is a fact.

    Existence of a branch ref and the token's pull-request permission are both *expected* to fail some of the
    time, and the debt ratchet counts every `except` in this tree. One probe, one handler, no `try` sprinkled
    through the callers.
    """
    try:
        return request_json(method, path, payload), None
    except GitHubAPIError as exc:
        return None, exc


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


def is_bot(item: dict[str, Any]) -> bool:
    login = str(item.get("login") or "")
    normalized = login.lower()
    return item.get("type") == "Bot" or normalized.endswith("[bot]") or normalized.endswith("bot")


def render(repository: str, contributors: list[dict[str, Any]]) -> str:
    humans = [item for item in contributors if item.get("login") and not is_bot(item)]
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
    current = request_json(
        "GET", f"/repos/{repository}/contents/{path}?ref={urllib.parse.quote(branch)}"
    )
    if not isinstance(current, dict) or not current.get("sha") or not current.get("content"):
        raise RuntimeError(f"Could not load {TARGET}")
    existing = base64.b64decode(str(current["content"])).decode("utf-8")
    return str(current["sha"]), existing


def is_retryable_conflict(exc: GitHubAPIError) -> bool:
    """Is this 409 a race worth re-reading the sha for, or a rule that will be true on attempt three too?"""
    if exc.status not in {409, 422}:
        return False
    body = (exc.body or "").lower()
    return not any(hint in body for hint in UNRETRYABLE_HINTS)


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
        except GitHubAPIError as exc:
            if not is_retryable_conflict(exc) or attempt == 3:
                raise
            print(f"Concurrent update detected; retrying {TARGET} ({attempt}/3).")
            time.sleep(attempt)

    raise RuntimeError(f"Could not update {TARGET} after retries")


def default_branch_head(repository: str) -> str:
    """The commit the working branch is reset to, so the pull request contains the file and nothing else."""
    owner, repo = repository.split("/", 1)
    meta = request_json("GET", f"/repos/{owner}/{repo}")
    name = str(meta.get("default_branch") or "main")
    ref = request_json("GET", f"/repos/{owner}/{repo}/git/ref/heads/{name}")
    return str(ref["object"]["sha"])


def _ensure_branch(repository: str, head_sha: str) -> None:
    """Point the working branch at the base head, so the pull request carries the file and nothing else."""
    _, missing = probe("GET", f"/repos/{repository}/git/ref/heads/{WORK_BRANCH}")
    if missing is not None:
        if missing.status != 404:
            raise missing
        request_json(
            "POST",
            f"/repos/{repository}/git/refs",
            {"ref": f"refs/heads/{WORK_BRANCH}", "sha": head_sha},
        )
        return
    request_json(
        "PATCH",
        f"/repos/{repository}/git/ref/heads/{WORK_BRANCH}",
        {"sha": head_sha, "force": True},
    )


def _pull_body(repository: str, base: str) -> dict[str, Any]:
    return {
        "title": "docs: refresh contributor recognition",
        "head": WORK_BRANCH,
        "base": base,
        "body": (
            "Rendered by the `Contributor Recognition` job from GitHub's contributor data (bot accounts "
            "excluded). Counts are GitHub commit counts, not a ranking of contribution value."
        ),
    }


def _reuse_open_pull(repository: str) -> dict[str, Any] | None:
    """The branch is reused week to week, so an open request on it is refreshed rather than duplicated."""
    owner, _ = repository.split("/", 1)
    head = f"{owner}:{WORK_BRANCH}"
    found = request_json(
        "GET", f"/repos/{repository}/pulls?state=open&head={urllib.parse.quote(head)}"
    )
    if isinstance(found, list) and found:
        first = found[0]
        print(f"An open pull request already carries this refresh: #{first.get('number')}")
        return {"number": first.get("number"), "html_url": first.get("html_url")}
    return None


def refresh(repository: str, base: str, content: str) -> dict[str, Any]:
    """Put the rendered file on a working branch and land it as a pull request.

    Returns what happened rather than raising for the two states that are not errors: the file already matches,
    or the token may write a branch but not open a pull request.
    """
    _, existing = current_file(repository, base)
    if existing == content:
        print(f"{TARGET} is already up to date on {base}.")
        return {"status": "current", "target": base}

    _ensure_branch(repository, default_branch_head(repository))
    publish(repository, WORK_BRANCH, content)

    carried = _reuse_open_pull(repository)
    if carried is not None:
        return {"status": "published", "target": WORK_BRANCH, "pull": carried["number"]}

    pull, refused = probe("POST", f"/repos/{repository}/pulls", _pull_body(repository, base))
    if refused is not None:
        if refused.status != 403:
            raise refused
        compare = f"https://github.com/{repository}/compare/{base}...{WORK_BRANCH}?expand=1"
        print(
            f"The token cannot open a pull request (403). Branch {WORK_BRANCH} is published; open it: {compare}"
        )
        return {"status": "published-without-pull", "target": WORK_BRANCH, "compare": compare}

    print(
        f"Updated {TARGET} on {WORK_BRANCH}; pull request #{pull.get('number')}: {pull.get('html_url')}"
    )
    return {"status": "published", "target": WORK_BRANCH, "pull": pull.get("number")}


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository or "/" not in repository:
        raise RuntimeError("GITHUB_REPOSITORY must be set to owner/repo")

    repo = request_json("GET", f"/repos/{repository}")
    if not isinstance(repo, dict):
        raise RuntimeError("Could not load repository metadata")
    branch = str(repo.get("default_branch") or "main")

    content = render(repository, fetch_contributors(repository))
    refresh(repository, branch, content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
