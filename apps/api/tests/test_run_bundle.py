"""The bundle route is the only thing a visitor can keep from a run, so it must carry what it claims.

Three properties, each with a case that would fail if the route were written the obvious way:

* it reads only inside the configured artifact root. The artifact list is stored state, and a route that
  trusts a path column is a file reader for whoever can write that column.
* an absent file is reported, not skipped in silence -- and a run with nothing left answers 404. An empty
  zip would look like success on exactly the deployment where the filesystem was cleared under the run.
* the disclosure `/version` makes about storage travels with the bundle, because the archive is what the
  visitor keeps after the instance is gone.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session
from dsa_api.main import app
from dsa_api.models.analysis import AnalysisRunORM

ROOT = Path(__file__).resolve().parents[3]
RUN_ID = "run-bundle01"
SENTINEL = b"do-not-exfiltrate-me"


async def _seed(factory: Any, artifacts: list[dict[str, Any]]) -> None:
    state = {"run_id": RUN_ID, "status": "COMPLETED", "artifacts": artifacts}
    async with factory() as session:
        session.add(
            AnalysisRunORM(
                id=RUN_ID,
                dataset_id="ds-1",
                user_query="bundle me",
                status="COMPLETED",
                state_json=json.dumps(state),
            )
        )
        await session.commit()


@pytest.fixture
async def bundle_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple, None]:
    root = tmp_path / "disk" / "artifacts"
    root.mkdir(parents=True)
    monkeypatch.setenv("DSA_ARTIFACT_ROOT", str(root))
    # Pinned because the accessor's fallback is derived from wherever the package is installed: a clone under
    # `/tmp` (a scratch tree, a CI cache dir) makes the datasets root match the ephemeral prefixes and this test
    # asserts a property of the checkout's location instead of the bundle. The Render image layout names this
    # path, so it is the durable case the assertion means to hold.
    monkeypatch.setenv("DSA_DATASET_DIR", "/app/data/datasets")

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _session() -> AsyncGenerator[Any, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, factory, root, tmp_path
    app.dependency_overrides.clear()
    await engine.dispose()


def _members(payload: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return {info.filename: archive.read(info.filename) for info in archive.infolist()}


def _manifest(payload: bytes) -> dict[str, Any]:
    return json.loads(_members(payload)[f"{RUN_ID}/manifest.json"])


async def test_bundle_carries_every_artifact_recorded_for_the_run(bundle_env: Any) -> None:
    client, factory, root, _ = bundle_env
    (root / "report.md").write_text("# report\n", encoding="utf-8")
    charts = root / "charts"
    charts.mkdir()
    (charts / "chart.png").write_bytes(b"\x89PNG fake")
    await _seed(
        factory,
        [
            {"id": "A1", "type": "report", "path": str(root / "report.md")},
            {"id": "A2", "type": "chart", "path": str(charts / "chart.png")},
        ],
    )

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 200, res.text
    assert res.headers["content-type"] == "application/zip"
    assert res.headers["content-disposition"] == f'attachment; filename="{RUN_ID}-bundle.zip"'
    assert res.headers["x-bundle-files"] == "2" and res.headers["x-bundle-excluded"] == "0"

    manifest = _manifest(res.content)
    assert manifest["included"] == ["chart.png", "report.md"]
    assert manifest["excluded"] == []
    assert manifest["run_id"] == RUN_ID
    assert manifest["artifact_root"] == str(root.resolve())
    assert manifest["storage"]["ephemeral_roots"] == ["artifacts"], (
        "the bundle the visitor keeps must say the storage it came from may be cleared"
    )
    assert set(_members(res.content)) == {
        f"{RUN_ID}/report.md",
        f"{RUN_ID}/chart.png",
        f"{RUN_ID}/manifest.json",
    }


async def test_relative_paths_resolve_against_the_configured_root(bundle_env: Any) -> None:
    client, factory, root, _ = bundle_env
    (root / "exports").mkdir()
    (root / "exports" / "result_table.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    await _seed(factory, [{"id": "A1", "type": "table", "path": "exports/result_table.csv"}])

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 200, res.text
    assert _manifest(res.content)["included"] == ["result_table.csv"]


async def test_a_recorded_path_outside_the_artifact_root_is_never_read(bundle_env: Any) -> None:
    client, factory, root, tmp_path = bundle_env
    (root / "report.md").write_text("# report\n", encoding="utf-8")
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_bytes(SENTINEL)
    await _seed(
        factory,
        [
            {"id": "A1", "type": "report", "path": str(root / "report.md")},
            {"id": "A2", "type": "file", "path": str(secret)},
        ],
    )

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 200, res.text
    manifest = _manifest(res.content)
    assert manifest["included"] == ["report.md"]
    assert manifest["excluded"] == [{"name": "secret.txt", "reason": "outside the artifact root"}]
    assert SENTINEL not in res.content, "the bundle carried bytes from outside the artifact root"


async def test_a_symlink_out_of_the_root_is_refused(bundle_env: Any) -> None:
    """Containment has to be checked after resolution, or a link inside the root walks straight out."""
    client, factory, root, tmp_path = bundle_env
    (root / "report.md").write_text("# report\n", encoding="utf-8")
    target = tmp_path / "outside-target.txt"
    target.write_bytes(SENTINEL)
    os.symlink(target, root / "evil.png")
    await _seed(
        factory,
        [
            {"id": "A1", "type": "report", "path": str(root / "report.md")},
            {"id": "A2", "type": "chart", "path": str(root / "evil.png")},
        ],
    )

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 200, res.text
    manifest = _manifest(res.content)
    assert manifest["included"] == ["report.md"]
    assert manifest["excluded"] == [{"name": "evil.png", "reason": "outside the artifact root"}]
    assert SENTINEL not in res.content


async def test_a_run_whose_files_are_gone_answers_404_not_with_an_empty_zip(
    bundle_env: Any,
) -> None:
    client, factory, root, _ = bundle_env
    await _seed(factory, [{"id": "A1", "type": "report", "path": str(root / "report.md")}])

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 404, res.text
    detail = res.json()["detail"]
    assert RUN_ID in detail, "the answer should name the run it looked for"
    assert "no artifact file" in detail, detail
    assert "/report" in detail, "the answer should point at the text that did survive"


async def test_missing_entries_are_listed_beside_the_ones_that_exist(bundle_env: Any) -> None:
    client, factory, root, _ = bundle_env
    (root / "report.md").write_text("# report\n", encoding="utf-8")
    await _seed(
        factory,
        [
            {"id": "A1", "type": "report", "path": str(root / "report.md")},
            {"id": "A2", "type": "bundle", "path": str(root / "experiment.json")},
            {"id": "A3", "type": "chart", "path": ""},
        ],
    )

    res = await client.get(f"/api/v1/analysis/{RUN_ID}/bundle")
    assert res.status_code == 200, res.text
    manifest = _manifest(res.content)
    assert manifest["excluded"] == [
        {"name": "chart", "reason": "no path recorded"},
        {"name": "experiment.json", "reason": "not present in this deployment"},
    ]


async def test_an_unknown_run_still_answers_404(bundle_env: Any) -> None:
    client, _, _, _ = bundle_env
    assert (await client.get("/api/v1/analysis/run-doesnotexist/bundle")).status_code == 404
    # A path-shaped run id must not be treated as one, nor reach the database with it.
    assert (await client.get("/api/v1/analysis/run-..%2F..%2Fetc/bundle")).status_code == 404


def test_the_bundle_route_sits_inside_the_authenticated_api_family() -> None:
    from dsa_api.core.security import _AUTH_PUBLIC_PATHS
    from dsa_api.routers.bundles import router

    paths = [route.path for route in router.routes]
    assert paths == ["/api/v1/analysis/{run_id}/bundle"]
    for path in paths:
        assert path.startswith("/api/") and path not in _AUTH_PUBLIC_PATHS


def test_the_bundle_route_is_documented() -> None:
    documented = (ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    # docs/api.md writes this family's parameter as `{id}` while the router declares `{run_id}`, so the
    # row is asserted in the table's own spelling and the served path is pinned separately above.
    assert "| GET | `/api/v1/analysis/{id}/bundle` |" in documented, (
        "the route is served but absent from docs/api.md"
    )
