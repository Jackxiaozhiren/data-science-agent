"""§124, Phase 4 target 5 and 7: the runtime versions the README-ish page states are derived, not remembered.

`docs/getting-started.md` advertises a Python floor and a Node floor. Those numbers were typed from
someone's screen: nothing connected them to `pyproject.toml`, `.github/workflows/ci.yml` or
`docker/Dockerfile.web`, which are the four places that actually decide which runtimes this project
supports, tests, and ships. Reading them side by side is itself the finding recorded as D-L4-14 -- CI
installs Node **22** while the web image is `node:20-alpine`, so the container ships a runtime the
dashboard build has never been proven on. The doc now states all of it, and this file keeps the doc
honest by re-deriving it from the same sources.

The rule is a pure function over four texts, so the falsification half is not theoretical: each
mismatch is planted in a fixture and must be reported.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = "docs/getting-started.md"


def _declared_python_floor(pyproject: str) -> int | None:
    match = re.search(r'requires-python\s*=\s*">=\s*(\d+)\.(\d+)"', pyproject)
    if not match:
        return None
    return int(match.group(2))


def _ci_python_minor(ci: str) -> int | None:
    match = re.search(r'python-version:\s*"?3\.(\d+)"?', ci)
    return int(match.group(1)) if match else None


def _ci_node_major(ci: str) -> int | None:
    match = re.search(r'node-version:\s*"?(\d+)"?', ci)
    return int(match.group(1)) if match else None


def _web_image_node_major(dockerfile: str) -> int | None:
    match = re.search(r"FROM node:(\d+)-", dockerfile)
    return int(match.group(1)) if match else None


def runtime_version_issues(*, doc: str, pyproject: str, ci: str, dockerfile: str) -> list[str]:
    """Every way the page's stated runtimes disagree with the files that decide them."""
    issues: list[str] = []

    floor = _declared_python_floor(pyproject)
    if floor is None:
        issues.append('pyproject.toml: no `requires-python = ">=3.x"` to derive the floor from')
    else:
        if f"Python ≥ 3.{floor}" not in doc:
            issues.append(f"{DOC}: does not state the declared floor Python ≥ 3.{floor}")
        tested = _ci_python_minor(ci)
        if tested is None:
            issues.append("ci.yml: no python-version to compare against the floor")
        elif tested != floor:
            issues.append(
                f"{DOC}: claims the only tested version is the floor 3.{floor}, "
                f"but CI runs 3.{tested}"
            )

    node_ci = _ci_node_major(ci)
    node_image = _web_image_node_major(dockerfile)
    if node_ci is None:
        issues.append("ci.yml: no node-version declared")
    if node_image is None:
        issues.append("docker/Dockerfile.web: no `FROM node:<major>-` base image declared")
    if node_ci is not None and f"Node **{node_ci}**" not in doc:
        issues.append(
            f"{DOC}: never names the Node CI builds and tests the dashboard on ({node_ci})"
        )
    if node_image is not None and f"`node:{node_image}-alpine`" not in doc:
        issues.append(f"{DOC}: never names the web image's Node ({node_image}-alpine)")
    if node_ci is not None and node_image is not None and node_ci != node_image:
        if "has never been proven" not in doc:
            issues.append(
                f"{DOC}: CI tests Node {node_ci} but the image runs {node_image}; "
                "the page must state that divergence"
            )
    return issues


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_the_stated_runtimes_match_the_files_that_decide_them() -> None:
    issues = runtime_version_issues(
        doc=_read(DOC),
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml"),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert issues == [], "\n".join(issues)


def test_the_derivations_are_not_reading_nothing() -> None:
    """A guard whose four probes all returned None would report zero issues forever."""
    pyproject, ci, dockerfile = (
        _read("pyproject.toml"),
        _read(".github/workflows/ci.yml"),
        _read("docker/Dockerfile.web"),
    )
    assert _declared_python_floor(pyproject) == 12, _declared_python_floor(pyproject)
    assert _ci_python_minor(ci) == 12, _ci_python_minor(ci)
    assert _ci_node_major(ci) is not None
    assert _web_image_node_major(dockerfile) is not None


def test_every_mismatch_is_reported_and_a_matching_page_is_not() -> None:
    good = runtime_version_issues(
        doc=_read(DOC),
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml"),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert good == []

    stale_floor = runtime_version_issues(
        doc=_read(DOC).replace("Python ≥ 3.12", "Python ≥ 3.10"),
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml"),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert any("Python ≥ 3.12" in i for i in stale_floor), stale_floor

    untested_claim = runtime_version_issues(
        doc=_read(DOC),
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml").replace(
            'python-version: "3.12"', 'python-version: "3.13"'
        ),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert any("CI runs 3.13" in i for i in untested_claim), untested_claim

    silent_image = runtime_version_issues(
        doc=_read(DOC).replace("`node:20-alpine`", "an older Node image"),
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml"),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert any("20-alpine" in i for i in silent_image), silent_image

    # ... and the four probes still have to fire on an empty page, not just on edited ones.
    blank = runtime_version_issues(
        doc="# Getting Started\n",
        pyproject=_read("pyproject.toml"),
        ci=_read(".github/workflows/ci.yml"),
        dockerfile=_read("docker/Dockerfile.web"),
    )
    assert len(blank) >= 4, blank
