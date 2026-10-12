"""§160 item 5, authorized in §164: the benchmark and research artifacts are served, not read in place.

The measured defect (`AUDIT_LEDGER.md` §160, table row 5): `docker/Dockerfile.web` copies only `apps/web`,
while the two pages opened `benchmarks/baseline/summary.json`, `benchmarks/v2/catalog.json` and
`research/results/ablation_*` off the filesystem. In a container every one of those reads misses, so the
deployment renders "Baseline not frozen yet" for a baseline that exists in the repository -- the exact
shape §167 made visible as a *distinct* failure rather than silence.

The picked shape serves all three from `dsa_api.routers.artifacts`, which is why the tests below are split
the way they are: a payload must equal the artifact it claims to expose, the route must sit inside the
authenticated `/api/` family (these are repository files, not public data), and the two pages must ask the
API instead of the filesystem.

Every expected value here is re-derived from the artifacts on disk rather than typed into this file, so
re-freezing a baseline or regenerating a catalog cannot silently make a stale literal pass.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]

ROUTER_MODULE = "dsa_api.routers.artifacts"
ROUTER_SOURCE = ROOT / "apps/api/src/dsa_api/routers/artifacts.py"
DOCKERFILE_API = ROOT / "docker" / "Dockerfile.api"
API_DOCS = ROOT / "docs" / "api.md"

#: The pages that used to read artifacts off disk, and the endpoint each now calls.
PAGE_TO_ENDPOINT = {
    "apps/web/app/benchmarks/page.tsx": "/api/v1/benchmarks/baseline",
    "apps/web/app/research/page.tsx": "/api/v1/research/experiments",
}

#: The shapes `dsa_api.core.security.AuthMiddleware` treats as unauthenticated.
PUBLIC_PROBE_PATHS = frozenset({"/health", "/ready", "/version"})

FS_READ = re.compile(
    r"""\b(?:readFileSync|readdirSync|readFile|readdir)\s*\(|from\s+["'](?:node:)?fs["']"""
)


def _router():
    from dsa_api.routers.artifacts import router

    return router


def _disk_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- payload == artifact


def test_baseline_endpoint_returns_the_committed_summary_verbatim():
    from dsa_api.routers.artifacts import BASELINE, read_baseline

    assert BASELINE == "benchmarks/baseline/summary.json"
    assert read_baseline() == _disk_json(BASELINE)


def test_catalog_endpoint_aggregates_reconcile_with_the_catalog_file():
    from dsa_api.routers.artifacts import CATALOG, read_catalog

    catalog = _disk_json(CATALOG)
    expected: dict[str, int] = {}
    for task in catalog["tasks"]:
        name = str(task["category"])
        expected[name] = expected.get(name, 0) + 1

    payload = read_catalog()
    assert payload["source"] == CATALOG
    assert payload["tasks"] == len(catalog["tasks"])
    assert payload["by_category"] == expected
    assert sum(payload["by_category"].values()) == payload["tasks"]
    assert payload["datasets"] == catalog["datasets"]


def test_research_endpoint_lists_the_capped_prefix_and_the_full_total():
    from dsa_api.routers.artifacts import (
        RESULTS_DIR,
        RESULTS_LIMIT,
        RESULTS_PREFIX,
        read_experiments,
    )

    directory = ROOT / RESULTS_DIR
    on_disk = sorted(p.name for p in directory.iterdir() if p.name.startswith(RESULTS_PREFIX))

    payload = read_experiments()
    assert payload["experiments"] == on_disk[:RESULTS_LIMIT]
    assert payload["total"] == len(on_disk)
    assert payload["experiments"] == sorted(payload["experiments"])


def test_repo_root_points_at_the_checkout_not_at_the_package_directory():
    """`parents[5]` is the one path expression that has to work in an image and a checkout alike."""
    from dsa_api.routers.artifacts import REPO_ROOT

    assert REPO_ROOT == ROOT, (
        f"{ROUTER_SOURCE.relative_to(ROOT)} resolves its artifacts from {REPO_ROOT}; "
        f"the repository root is {ROOT}"
    )


# ---------------------------------------------------------------- absence is a 404 that names the file


@pytest.mark.parametrize(
    "route,expected_name",
    [
        ("read_baseline", "benchmarks/baseline/summary.json"),
        ("read_catalog", "benchmarks/v2/catalog.json"),
        ("read_experiments", "research/results"),
    ],
)
def test_a_missing_artifact_answers_404_naming_it(
    monkeypatch, tmp_path: Path, route: str, expected_name: str
):
    """The page must be able to say *which* artifact is absent, not merely "no data" (§167's vocabulary)."""
    import dsa_api.routers.artifacts as artifacts

    monkeypatch.setattr(artifacts, "REPO_ROOT", tmp_path)
    handler: Callable[[], dict[str, Any]] = getattr(artifacts, route)
    with pytest.raises(HTTPException) as caught:
        handler()
    assert caught.value.status_code == 404
    assert expected_name in str(caught.value.detail)


def test_a_directory_that_exists_but_holds_no_ablation_answers_an_empty_list(
    tmp_path: Path, monkeypatch
):
    """Empty and absent are different answers; conflating them is the §167 defect."""
    import dsa_api.routers.artifacts as artifacts

    (tmp_path / artifacts.RESULTS_DIR).mkdir(parents=True)
    monkeypatch.setattr(artifacts, "REPO_ROOT", tmp_path)
    assert artifacts.read_experiments() == {"experiments": [], "total": 0}


# ---------------------------------------------------------------- the route surface


def test_every_artifact_route_is_inside_the_authenticated_api_family():
    from dsa_api.core.security import _AUTH_PUBLIC_PATHS

    assert _AUTH_PUBLIC_PATHS == PUBLIC_PROBE_PATHS
    paths = [route.path for route in _router().routes]
    assert len(paths) == 3, f"expected the three §164 endpoints, found {paths}"
    for path in paths:
        assert path.startswith("/api/"), f"{path} is outside the prefix AuthMiddleware gates"
        assert path not in _AUTH_PUBLIC_PATHS, (
            f"{path} would leak repository files to unauthenticated callers"
        )


def test_every_artifact_route_is_documented():
    documented = API_DOCS.read_text(encoding="utf-8")
    for route in _router().routes:
        row = f"| GET | `{route.path}` |"
        assert row in documented, (
            f"{route.path} is served but missing from {API_DOCS.relative_to(ROOT)}"
        )


def _dockerfile_copies(text: str) -> dict[str, list[str]]:
    """``{destination: [sources]}`` for every ``COPY`` in a Dockerfile, in order, last wins on repeats."""
    copies: dict[str, list[str]] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[0].upper() == "COPY" and not fields[1].startswith("--"):
            copies[fields[-1]] = fields[1:-1]
    return copies


def test_the_api_image_copies_exactly_the_artifacts_the_router_reads():
    """Each path constant in the router must land at the same repository-relative location in the image.

    Derived from the module rather than retyped, so a fourth endpoint added without its ``COPY`` line is
    reported here instead of returning 404 in the deployment. The whole-tree form is refused on purpose:
    ``benchmarks/`` is 2.8 GB on disk (9 tracked files under ``benchmarks/external/``) and the artifacts
    these three endpoints read are ~153 KB.
    """
    import dsa_api.routers.artifacts as artifacts

    copies = _dockerfile_copies(DOCKERFILE_API.read_text(encoding="utf-8"))
    for relative in (artifacts.BASELINE, artifacts.CATALOG, artifacts.RESULTS_DIR):
        dest = f"./{relative}"
        assert copies.get(dest) == [relative], (
            f"{relative} is read by the router but copied as {copies.get(dest)}"
        )

    benchmark_dests = {dest for dest in copies if dest.startswith("./benchmarks")}
    assert benchmark_dests == {f"./{artifacts.BASELINE}", f"./{artifacts.CATALOG}"}, (
        f"the image copies {sorted(benchmark_dests)} under benchmarks/, not just the artifacts it serves"
    )


def test_the_copy_check_can_fail():
    """Negative control: the directory-wide form this change deliberately avoided must be reported."""
    whole_tree = (
        "WORKDIR /app\nCOPY benchmarks ./benchmarks\nCOPY research/results ./research/results\n"
    )
    copies = _dockerfile_copies(whole_tree)
    assert "./benchmarks" in copies and "./research/results" in copies
    assert {d for d in copies if d.startswith("./benchmarks")} != {
        "./benchmarks/baseline/summary.json"
    }


# ---------------------------------------------------------------- the pages stopped reading files


def fs_read_issues(source: str) -> list[str]:
    """Every way a page reads an artifact off the filesystem instead of asking the API."""
    return [match.group(0) for match in FS_READ.finditer(source)]


def test_the_converted_pages_read_no_artifact_from_the_filesystem():
    problems: list[str] = []
    for relative, endpoint in PAGE_TO_ENDPOINT.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for offender in fs_read_issues(text):
            problems.append(f"{relative}: still touches the filesystem via {offender}")
        if endpoint not in text:
            problems.append(f"{relative}: never calls {endpoint}")
    assert problems == [], "; ".join(problems)


def test_the_research_page_keeps_an_absent_results_dir_apart_from_an_empty_one():
    """``total: 0`` on 200 means "no ablation has run"; a 404 means the deployment has no results dir.

    Those two readings need different remedies -- run the ablation, or ship ``research/results`` -- so the
    page may not send both to the same copy. Asserted on the branch text, and the earlier
    ``expsFailure !== "notFound"`` shape is refused, because that form routed 404 to the empty state.
    """
    text = (ROOT / "apps/web/app/research/page.tsx").read_text(encoding="utf-8")
    assert '!== "notFound"' not in text, "the 404 arm is folded back into the generic failure test"

    anchor = 'expsFailure === "notFound"'
    assert anchor in text, "the page has no dedicated notFound branch"
    start = text.index(anchor)
    branch = text[start : text.index(") :", start)]
    assert "deployment" in branch, (
        "the 404 branch does not say the artifact is missing from the deployment"
    )
    assert "404" in branch
    assert "ablation runner" not in branch, "the 404 branch tells the reader to do the wrong thing"
    assert "No results yet" not in branch, "the 404 branch reuses the genuinely-empty copy"


def test_the_filesystem_read_check_can_fail():
    """Negative control: the detector above must report the pre-§168 shape it was written to catch."""
    planted = (
        'import { existsSync, readdirSync, readFileSync } from "fs";\n'
        "const raw = readFileSync(join(root, 'benchmarks/baseline/summary.json'), 'utf8');\n"
        "return readdirSync(dir).filter((f) => f.startsWith('ablation_'));\n"
    )
    assert fs_read_issues(planted), "the detector passes on the very code this change removed"
    for shape in ('from "node:fs"', "readFileSync(a, 'utf8')", "readdirSync(a)"):
        assert fs_read_issues(shape), f"the detector misses {shape}"
    assert fs_read_issues('const res = await fetch(apiUrl("/api/v1/benchmarks/baseline"));') == []
