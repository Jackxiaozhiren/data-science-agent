"""Frozen benchmark and research artifacts, served read-only.

Audit §160 item 5 priced this option, §164 records the maintainer's pick (serve both pages through the API
instead of `COPY`ing the artifacts into the web image), and §167 landed the prerequisite that makes a
served artifact honest: the web layer can now tell a failed request apart from an empty payload.

The defect was never the files, it was who read them. `apps/web/app/benchmarks/page.tsx` opened
`benchmarks/baseline/summary.json` and `benchmarks/v2/catalog.json` with `readFileSync` and
`apps/web/app/research/page.tsx` listed `research/results/ablation_*` with `readdirSync`, while
`docker/Dockerfile.web` copies only `apps/web`. In a container those reads miss and the pages render their
empty state; in a platform build the same files freeze at build time and then read as current. Either way
the deployment shows a number it cannot substantiate.

Serving them here moves each read into an image that can carry it -- `docker/Dockerfile.api` copies the two
JSON artifacts and the results directory, ~153 KB against the 2.8 GB `benchmarks/` tree on disk -- and the
repository-relative layout is identical in the image (`WORKDIR /app`, workspace members installed editable)
and in a checkout, so one path expression covers both. Where the artifacts are genuinely absent -- an
installed wheel, a slim image built without them -- the answer is a 404 naming the artifact, so the page
says "the API answered 404" rather than "there are no results".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["artifacts"])

# .../dsa_api/routers/artifacts.py -> routers -> dsa_api -> src -> apps -> repository root.
REPO_ROOT = Path(__file__).resolve().parents[5]

BASELINE = "benchmarks/baseline/summary.json"
CATALOG = "benchmarks/v2/catalog.json"
RESULTS_DIR = "research/results"
RESULTS_PREFIX = "ablation_"
RESULTS_LIMIT = 10


def _artifact(relative: str) -> dict[str, Any]:
    path = REPO_ROOT / relative
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"{relative} is not present in this deployment")
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


@router.get("/api/v1/benchmarks/baseline")
def read_baseline() -> dict[str, Any]:
    """The frozen aggregate the benchmark headline sits on."""
    return _artifact(BASELINE)


@router.get("/api/v1/benchmarks/catalog")
def read_catalog() -> dict[str, Any]:
    """Task count and category spread, computed where the catalog lives rather than in the browser."""
    catalog = _artifact(CATALOG)
    tasks = catalog.get("tasks") or []
    by_category: dict[str, int] = {}
    for task in tasks:
        name = str(task.get("category"))
        by_category[name] = by_category.get(name, 0) + 1
    return {
        "tasks": len(tasks),
        "by_category": by_category,
        "datasets": catalog.get("datasets"),
        "source": CATALOG,
    }


@router.get("/api/v1/research/experiments")
def read_experiments() -> dict[str, Any]:
    """Ablation result files, capped the way the page always capped them."""
    directory = REPO_ROOT / RESULTS_DIR
    if not directory.is_dir():
        raise HTTPException(
            status_code=404, detail=f"{RESULTS_DIR} is not present in this deployment"
        )
    names = sorted(
        entry.name for entry in directory.iterdir() if entry.name.startswith(RESULTS_PREFIX)
    )
    return {"experiments": names[:RESULTS_LIMIT], "total": len(names)}
