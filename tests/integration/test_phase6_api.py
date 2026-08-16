from __future__ import annotations

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_api.core.database import Base, get_session
from dsa_api.main import app


@pytest.fixture
async def ac():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


async def _upload_and_run(ac: AsyncClient) -> tuple[str, str]:
    csv = b"a,b,group\n1,2.0,A\n2,3.5,B\n3,4.1,A\n4,6.0,B\n5,7.2,A\n6,8.1,B\n7,9.0,A\n8,10.2,B\n9,11.1,A\n10,12.3,B\n11,13.0,A\n12,14.5,B\n"
    r = await ac.post("/api/v1/datasets/", files={"file": ("t.csv", csv, "text/csv")})
    assert r.status_code == 200, r.text
    ds_id = r.json()["id"]
    r2 = await ac.post("/api/v1/analysis/", json={"dataset_id": ds_id, "user_query": "Analyze correlation between a and b"})
    assert r2.status_code == 200, r2.text
    return ds_id, r2.json()["id"]


@pytest.mark.asyncio
async def test_sse_events_and_json_fallback(ac: AsyncClient) -> None:
    _, run_id = await _upload_and_run(ac)
    # SSE
    r = await ac.get(f"/api/v1/analysis/{run_id}/events", headers={"Accept": "text/event-stream"})
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    body = r.text
    assert "event:" in body or "data:" in body
    # JSON fallback when client prefers JSON
    r2 = await ac.get(f"/api/v1/analysis/{run_id}/events", headers={"Accept": "application/json"})
    assert r2.status_code == 200
    assert r2.headers.get("content-type", "").startswith("application/json")
    assert "events" in r2.json()


@pytest.mark.asyncio
async def test_progress_and_evidence_trace(ac: AsyncClient) -> None:
    _, run_id = await _upload_and_run(ac)
    r = await ac.get(f"/api/v1/analysis/{run_id}/progress")
    assert r.status_code == 200
    data = r.json()
    assert "progress_pct" in data
    assert 0 <= data["progress_pct"] <= 100
    # artifacts includes progress
    r2 = await ac.get(f"/api/v1/analysis/{run_id}/artifacts")
    assert r2.status_code == 200
    assert "progress" in r2.json()
    # report json + markdown negotiation
    r3 = await ac.get(f"/api/v1/analysis/{run_id}/report")
    assert r3.status_code == 200
    assert "markdown" in r3.json()
    r4 = await ac.get(f"/api/v1/analysis/{run_id}/report?format=markdown")
    assert r4.status_code == 200
    assert r4.headers.get("content-type", "").startswith("text/markdown")
    assert "# Analysis Report" in r4.text
    # evidence trace
    # pick first evidence id from report
    state_ev = r3.json().get("evidence", [])
    if state_ev:
        eid = state_ev[0]["id"]
        r5 = await ac.get(f"/api/v1/analysis/{run_id}/evidence/{eid}")
        assert r5.status_code == 200
        assert "evidence" in r5.json()
        assert "tool_call" in r5.json()
        # 404 for unknown evidence
        r6 = await ac.get(f"/api/v1/analysis/{run_id}/evidence/E-notexist")
        assert r6.status_code == 404
    # 404 for unknown run
    r7 = await ac.get("/api/v1/analysis/not-exist/progress")
    assert r7.status_code == 404
    r8 = await ac.get("/api/v1/analysis/not-exist/events")
    assert r8.status_code == 404
