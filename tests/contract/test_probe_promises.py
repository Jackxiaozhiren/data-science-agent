"""The two probe promises on the free tier, pinned to the behaviour they describe.

`docs/api.md` says `/health` is "liveness only: no database I/O and no optional scientific/LLM imports, so a
small instance can answer probes immediately", and `/ready` "degrades to `degraded` when the DB check fails".
Both are true when measured (2026-10-22) and neither was checked by anything: the demo runs on Render's free
instance, where the whole reason those two routes exist is that a probe must not fail because a cold database or
a heavy import says so first. A prose claim with no witness is how the last three rounds went wrong, so this one
starts the same way -- measure, then pin.

Three shapes of proof, because the claim has three parts: behaviour under a deliberately broken engine, the
import closure of the route module measured in a clean interpreter, and the handler's own syntax (a future
`Depends(get_session)` on the liveness route would be invisible to the first two if the database happened to be
reachable during the test run).
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from dsa_api.routers import health as health_module
from dsa_api.routers.health import dependency_health, health, ready

REPO = Path(__file__).resolve().parents[2]
DOC = (REPO / "docs/api.md").read_text(encoding="utf-8")

#: What the liveness route is promised not to pull in. `numpy` is on the list because it is the bulk of the
#: import cost the sentence is really about, not because it is optional in the packaging sense.
HEAVY_TOP_LEVEL = ("polars", "duckdb", "numpy", "pandas", "openai", "langchain")

BROKEN = "sqlite+aiosqlite:////definitely/not/a/path/probe-cannot-open.db"


def _row(path: str) -> str:
    rows = [line for line in DOC.splitlines() if line.startswith(f"| GET | `{path}`")]
    assert len(rows) == 1, f"{path} must have exactly one route row in the docs: {rows}"
    return rows[0]


@pytest.mark.asyncio
async def test_liveness_answers_ok_when_the_database_is_unopenable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_module, "engine", create_async_engine(BROKEN))
    body = await health()
    assert body["status"] == "ok", body
    assert body["details"] == {"process": {"status": "ok"}}, body


@pytest.mark.asyncio
async def test_readiness_degrades_instead_of_lying_or_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The word the docs use has to be the word the code returns, and the cause has to travel with it."""
    monkeypatch.setattr(health_module, "engine", create_async_engine(BROKEN))
    body = await ready()
    assert body["status"] == "degraded", body
    db = body["details"]["db"]
    assert db["status"] == "error", db
    assert "unable to open database file" in db["error"], db
    assert "degraded" in _row("/ready"), _row("/ready")


@pytest.mark.asyncio
async def test_readiness_reports_ok_against_a_working_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without this, the previous test would also pass on a route that always says `degraded`."""
    monkeypatch.setattr(
        health_module, "engine", create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'ok.db'}")
    )
    body = await ready()
    assert body["status"] == "ok", body
    assert body["details"]["db"] == {"status": "ok"}, body


def test_the_liveness_handler_reaches_for_no_database() -> None:
    """Structural, because a reachable database would hide a session dependency from the behavioural test."""
    tree = ast.parse(inspect.getsource(health))
    named = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    forbidden = {"engine", "session", "Depends", "_database_status", "AsyncSession"}
    assert not (named | attrs) & forbidden, (
        f"liveness now touches the database: {sorted(named | attrs)}"
    )
    assert inspect.signature(health).parameters == {}, "liveness gained a dependency"


def test_importing_the_liveness_route_does_not_load_the_scientific_stack() -> None:
    """In a clean interpreter: the module's closure decides cold-start cost more than the handler body does.

    Run out of process on purpose -- the test session has already imported polars and duckdb, so a
    `sys.modules` census here would prove nothing.
    """
    probe = (
        "import sys, json;"
        "before = set(sys.modules);"
        "import dsa_api.routers.health;"
        f"heavy = [m for m in set(sys.modules) - before if m.split('.')[0] in {list(HEAVY_TOP_LEVEL)}];"
        "print(json.dumps(heavy))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr[-400:]
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert loaded == [], f"the liveness module pulls in the optional stack: {loaded}"


def test_the_dependency_route_is_the_one_that_probes_the_optional_stack() -> None:
    """The separation only means something if the deep check exists somewhere; assert where it lives."""
    body = inspect.getsource(dependency_health)
    assert "_probe_import" in body, body
    assert "duckdb" in body and "polars" in body, body
    assert "no optional-dependency" not in _row("/health"), _row("/health")
    assert "optional-dependency diagnostic" in _row("/health/dependencies"), _row(
        "/health/dependencies"
    )


def _heavy_loaded_by(import_statement: str) -> list[str]:
    """Which of the heavy top-levels a single import brings into a clean interpreter."""
    probe = (
        "import sys, json;"
        "before = set(sys.modules);"
        f"{import_statement};"
        f"heavy = [m for m in set(sys.modules) - before if m.split('.')[0] in {list(HEAVY_TOP_LEVEL)}];"
        "print(json.dumps(sorted(heavy)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=REPO,
    )
    assert result.returncode == 0, result.stderr[-400:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_the_upload_route_does_not_drag_the_dataframe_stack_in() -> None:
    """`dataset_service` defers its dataframe imports for exactly this; the package initialiser undid it.

    `dsa_datasets/__init__.py` re-exported `load_dataframe` eagerly, and importing a submodule runs the package
    initialiser first, so `from dsa_datasets.errors import ValidationError` in the upload route pulled polars
    into the process. Measured on 2026-10-22: 87.8 MiB and ~0.15 s for that route with the eager chain, 64.3 MiB
    without it.
    """
    assert _heavy_loaded_by("import dsa_api.routers.datasets") == []
    assert _heavy_loaded_by("import dsa_datasets.errors, dsa_datasets.validate") == []


def test_the_public_surface_of_the_package_still_resolves() -> None:
    """Lazy does not mean missing: the names the package advertises have to keep working."""
    probe = (
        "import dsa_datasets as d;"
        "missing = [n for n in d.__all__ if getattr(d, n, None) is None];"
        "from dsa_datasets import load_dataframe, validate_file, DatasetFormat;"
        "print(len(missing), load_dataframe is d.load_dataframe, DatasetFormat.csv.value)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, timeout=180, cwd=REPO
    )
    assert result.returncode == 0, result.stderr[-400:]
    assert result.stdout.strip() == "0 True csv", result.stdout
