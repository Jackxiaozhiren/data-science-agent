from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator

import polars as pl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session
from dsa_api.main import app


@pytest.fixture
async def client_with_tmp_db() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_csv_and_get(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    csv_bytes = b"a,b,c\n1,hello,2024-01-01\n2,world,2024-01-02\n3,foo,2024-01-03\n"
    files: Any = {"file": ("sales.csv", csv_bytes, "text/csv")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code == 200, r.text
    data: Any = r.json()
    assert data["filename"] == "sales.csv"
    assert data["format"] == "csv"
    assert data["rows"] == 3
    assert "sha256" in data
    assert data["profile"] is not None
    assert data["profile"]["rows"] == 3
    ds_id: str = data["id"]

    r2 = await ac.get(f"/api/v1/datasets/{ds_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == ds_id

    r3 = await ac.get("/api/v1/datasets/")
    assert r3.status_code == 200
    assert len(r3.json()["datasets"]) == 1


@pytest.mark.asyncio
async def test_upload_parquet(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    df = pl.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.parquet"
        df.write_parquet(p)
        parquet_bytes = p.read_bytes()
    files2: Any = {"file": ("t.parquet", parquet_bytes, "application/octet-stream")}
    r = await ac.post("/api/v1/datasets/", files=files2)
    assert r.status_code == 200, r.text
    data: Any = r.json()
    assert data["format"] == "parquet"
    assert data["rows"] == 3


@pytest.mark.asyncio
async def test_large_file_csv(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    n = 20000
    buf = io.StringIO()
    buf.write("id,value,cat\n")
    for i in range(n):
        buf.write(f"{i},{i*0.5},{'a' if i % 2 == 0 else 'b'}\n")
    csv_bytes = buf.getvalue().encode()
    files: Any = {"file": ("large.csv", csv_bytes, "text/csv")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code == 200, r.text
    assert r.json()["rows"] == n


@pytest.mark.asyncio
async def test_malformed_csv_handled(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    files: Any = {"file": ("bad.csv", b"", "text/csv")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert r.json()["rows"] == 0


@pytest.mark.asyncio
async def test_reject_unsupported_format(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    files: Any = {"file": ("evil.exe", b"hello", "application/octet-stream")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reject_path_traversal(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    files: Any = {"file": ("../secret.csv", b"a,b\n1,2\n", "text/csv")}
    r = await ac.post("/api/v1/datasets/", files=files)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_not_found(client_with_tmp_db: AsyncClient) -> None:
    ac = client_with_tmp_db
    r = await ac.get("/api/v1/datasets/not-exist-id")
    assert r.status_code == 404
