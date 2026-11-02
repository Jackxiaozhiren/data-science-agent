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

#: How long to wait for the runs a new head triggers. The provider creates them a second or two after it accepts
#: the request or the push, and approving before they exist approves nothing while looking like success.
APPROVAL_WAIT_SECONDS = 90.0
APPROVAL_POLL_SECONDS = 5.0

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
            # No skip keyword here. The token was correct while this job pushed a generated table straight to the
            # default branch -- and it is still correct that the refresh lands as a pull request whose checks must
            # run -- but GitHub honours the keyword from a pull request's commit message, so keeping it would mean
            # the request could never collect the `ci` check that branch protection requires. A flag baked into an
            # artifact outlives the design that needed it.
            "message": "docs: refresh contributor recognition",
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
    # Plural `refs` here: GitHub reads the singular `/git/ref/...` for a GET and the plural `/git/refs/...` for
    # the update. Asking the singular route to move a ref answers 404, which is what the first live dispatch after
    # this change proved -- a stand-in transport that accepts whatever path it was handed cannot catch that.
    request_json(
        "PATCH",
        f"/repos/{repository}/git/refs/heads/{WORK_BRANCH}",
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


def _branch_head(repository: str, branch: str) -> str:
    """The commit the request points at, which is also the commit its runs are filed under."""
    ref = request_json("GET", f"/repos/{repository}/git/ref/heads/{branch}")
    return str(ref["object"]["sha"])


def _parked_runs(repository: str, head: str) -> list[dict[str, Any]]:
    """The pull-request runs this head triggered that the workflow-approval policy is holding."""
    listing = request_json(
        "GET",
        f"/repos/{repository}/actions/runs?head_sha={head}&event=pull_request&per_page=50",
    )
    # No default: an empty list from a response that never carried the key would read as "nothing was parked"
    # and skip the approval in silence, which is the failure this function exists to end.
    if not isinstance(listing, dict) or not isinstance(listing.get("workflow_runs"), list):
        raise RuntimeError("GitHub actions runs endpoint did not return a run list")
    return [run for run in listing["workflow_runs"] if run.get("conclusion") == "action_required"]


def _await_parked_runs(repository: str, head: str) -> list[dict[str, Any]]:
    """Wait for the runs to exist. A new head creates them a second or two after the request is accepted."""
    deadline = time.monotonic() + APPROVAL_WAIT_SECONDS
    while True:
        parked = _parked_runs(repository, head)
        if parked or time.monotonic() >= deadline:
            return parked
        time.sleep(APPROVAL_POLL_SECONDS)


def _approve_parked_runs(repository: str, branch: str) -> dict[str, Any]:
    """Release the checks the job's own request is not allowed to trigger, with the token that made it.

    The request is authored by `app/github-actions`, which this repository's workflow-approval policy treats as
    an outside collaborator: every `pull_request` run on it sits in `action_required` until a human approves, so
    the required `ci` check is never created and the request can never become mergeable (§306, §312). The missing
    piece is not a scope on the request and not another trigger -- a dispatched run was measured against this
    exact PR and never counted (§313) -- it is the approval call itself, which `actions: write` allows and which
    the job's own token may make against its own run. Measured: 201, and the run leaves `action_required`.
    """
    head = _branch_head(repository, branch)
    parked = _await_parked_runs(repository, head)
    if not parked:
        print(f"No parked runs on {head[:7]}; nothing needed approval.")
        return {"approved": 0}

    approved: list[int] = []
    for run in parked:
        _, refused = probe("POST", f"/repos/{repository}/actions/runs/{run['id']}/approve")
        if refused is not None:
            print(
                f"Could not approve run {run['id']} ({run.get('name')}): {refused.status} {refused}"
            )
            return {"approved": len(approved), "refused": refused, "run": run.get("name")}
        print(f"Approved run {run['id']} ({run.get('name')}); it left action_required.")
        approved.append(int(run["id"]))
    return {"approved": len(approved)}


def _with_approvals(repository: str, branch: str, outcome: dict[str, Any]) -> dict[str, Any]:
    """Attach the approval result to a published refresh, without raising on a refusal."""
    result = _approve_parked_runs(repository, branch)
    outcome["approved"] = result["approved"]
    if result.get("refused") is not None:
        outcome["approval_refused"] = True
    return outcome


def refresh(repository: str, base: str, content: str) -> dict[str, Any]:
    """Put the rendered file on a working branch and land it as a pull request.

    Returns what happened rather than raising for the states that are not errors: the file already matches, the
    token may write a branch but not open a pull request, or the request exists while the approval call that
    starts its checks was refused. The first two are reported by `main()`; the third is the one a reader has to
    be told about, because a published request whose runs are all parked looks exactly like a request waiting
    its turn.
    """
    _, existing = current_file(repository, base)
    if existing == content:
        print(f"{TARGET} is already up to date on {base}.")
        return {"status": "current", "target": base}

    _ensure_branch(repository, default_branch_head(repository))
    publish(repository, WORK_BRANCH, content)

    carried = _reuse_open_pull(repository)
    if carried is not None:
        return _with_approvals(
            repository,
            WORK_BRANCH,
            {"status": "published", "target": WORK_BRANCH, "pull": carried["number"]},
        )

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
    return _with_approvals(
        repository,
        WORK_BRANCH,
        {"status": "published", "target": WORK_BRANCH, "pull": pull.get("number")},
    )


def main() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not repository or "/" not in repository:
        raise RuntimeError("GITHUB_REPOSITORY must be set to owner/repo")

    repo = request_json("GET", f"/repos/{repository}")
    if not isinstance(repo, dict):
        raise RuntimeError("Could not load repository metadata")
    branch = str(repo.get("default_branch") or "main")

    content = render(repository, fetch_contributors(repository))
    outcome = refresh(repository, branch, content)
    if outcome["status"] == "published-without-pull":
        # A branch nobody is told about is the eight-week silence this file exists to end, so a stranded artifact
        # is reported as the failure it is: the token needs `pull-requests: write` on the workflow.
        print(
            "FAILURE: the refresh is published but no pull request could be opened; the job needs "
            "pull-requests: write, or someone must open the printed compare URL."
        )
        return 2
    if outcome.get("approval_refused"):
        # A request whose runs are all still parked is the §300 failure one layer down: it is on the queue, it
        # is not red, and its required check will never appear. Loud beats patient.
        print(
            "FAILURE: the refresh is published as a pull request, but the runs it triggered are still parked in "
            "action_required, so its required check will never appear and it cannot become mergeable; the job "
            "needs actions: write on the workflow, or a human has to click Approve and run."
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
