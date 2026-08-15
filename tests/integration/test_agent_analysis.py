from __future__ import annotations

import io
import tempfile
from pathlib import Path

import polars as pl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from dsa_agent.critic import check_unsupported_claims, critic_validate
from dsa_agent.graph import run_analysis
from dsa_agent.state import AnalysisState, AnalysisStatus, Insight
from dsa_api.core.database import Base, get_session
from dsa_api.main import app
from dsa_tools import bootstrap, clear
from dsa_tools.registry import clear as tools_clear

# Ensure tools bootstrapped for graph tests
try:
    from dsa_tools import list_tools

    if not list_tools():
        bootstrap()
except Exception:
    pass


def _make_csv(path: Path, rows: int = 80) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("a,b,group,target\n")
        for i in range(rows):
            f.write(f"{i},{i*1.5 + (i%4)},{'A' if i%2==0 else 'B'},{i%2}\n")


@pytest.mark.asyncio
async def test_run_analysis_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p)
        state = await run_analysis(dataset_path=str(p), dataset_id="ds1", user_query="Analyze correlation between a and b and build a predictive model")
        assert state.run_id.startswith("run-")
        assert state.status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED)
        # should have at least profile + correlation + chart
        tools = [tc.tool for tc in state.tool_calls]
        assert "profile_dataset" in tools
        assert len(state.tool_calls) >= 3
        assert len(state.evidence) >= 1
        assert state.report_markdown is not None
        assert "# Analysis Report" in state.report_markdown


@pytest.mark.asyncio
async def test_critic_blocks_causal_claim() -> None:
    from dsa_agent.state import Evidence

    ins = Insight(id="I-1", finding="X causes Y", evidence_ids=[])
    res = check_unsupported_claims([ins])
    assert not res.passed
    assert "Causal" in res.message or "causal" in res.message.lower()


@pytest.mark.asyncio
async def test_critic_evidence_coverage() -> None:
    state = AnalysisState(run_id="r1", dataset_id="d1", user_query="hello", status=AnalysisStatus.ANALYSIS)
    # no evidence yet at ANALYSIS stage -> should fail coverage
    results = critic_validate(state)
    checks = {r.check: r.passed for r in results}
    assert checks["evidence_coverage"] is False


@pytest.mark.asyncio
async def test_api_analysis_flow() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # upload dataset
        csv_bytes = b"a,b,group,target\n1,2.0,A,0\n2,3.5,B,1\n3,4.1,A,0\n4,6.0,B,1\n5,7.2,A,0\n6,8.1,B,1\n7,9.0,A,0\n8,10.2,B,1\n9,11.1,A,0\n10,12.3,B,1\n11,13.0,A,0\n12,14.5,B,1\n"
        files = {"file": ("t.csv", csv_bytes, "text/csv")}
        r = await ac.post("/api/v1/datasets/", files=files)
        assert r.status_code == 200, r.text
        ds_id = r.json()["id"]

        # create analysis
        r2 = await ac.post("/api/v1/analysis/", json={"dataset_id": ds_id, "user_query": "Analyze correlation between a and b and test group differences"})
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "id" in data
        assert data["status"] in ("COMPLETED", "FAILED")
        run_id = data["id"]

        # get analysis
        r3 = await ac.get(f"/api/v1/analysis/{run_id}")
        assert r3.status_code == 200
        assert r3.json()["id"] == run_id

        # report
        r4 = await ac.get(f"/api/v1/analysis/{run_id}/report")
        assert r4.status_code == 200
        assert "markdown" in r4.json()
        assert r4.json()["markdown"] is not None

        # artifacts
        r5 = await ac.get(f"/api/v1/analysis/{run_id}/artifacts")
        assert r5.status_code == 200
        assert "artifacts" in r5.json()

        # events (SSE JSON stream)
        r6 = await ac.get(f"/api/v1/analysis/{run_id}/events")
        assert r6.status_code == 200
        assert "text/event-stream" in r6.headers.get("content-type", "")

        # list
        r7 = await ac.get("/api/v1/analysis/")
        assert r7.status_code == 200
        assert len(r7.json()["analyses"]) >= 1

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_tool_budget_exceeded() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _make_csv(p, rows=20)
        # force budget to 1 to trigger budget guard — we do via state patch by calling graph with mocked plan
        # Instead, test via direct critic: exceed max_tool_calls
        state = AnalysisState(run_id="r1", dataset_id="d1", dataset_path=str(p), user_query="hello", status=AnalysisStatus.ANALYSIS)
        state.tool_call_count = 100
        state.budget.max_tool_calls = 5
        results = critic_validate(state)
        assert any(not r.passed and r.check == "budget" for r in results)
