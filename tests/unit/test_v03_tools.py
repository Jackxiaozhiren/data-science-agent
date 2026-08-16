from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest

from dsa_tools import bootstrap, clear, get


@pytest.fixture(autouse=True)
def _bootstrap():
    clear()
    bootstrap()
    yield
    clear()


def _csv_with_two_groups(path: Path) -> None:
    pl.DataFrame(
        {
            "treatment": ["A"] * 20 + ["B"] * 20,
            "outcome": [10] * 20 + [12] * 20,
            "conf": list(range(40)),
        }
    ).write_csv(path)


@pytest.mark.asyncio
async def test_causal_check_stub_never_passes_bar() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        _csv_with_two_groups(p)
        tool = get("causal_check")
        r = await tool.run({"dataset_path": str(p), "treatment": "treatment", "outcome": "outcome"})
        assert r.status == "ok", r.error
        assert r.output is not None
        assert r.output.passes_causal_bar is False
        assert (
            "not causation" in r.output.confidence_note or "Association" in r.output.confidence_note
        )


@pytest.mark.asyncio
async def test_causal_check_adjusted() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        pl.DataFrame(
            {"treatment": [0, 1] * 15, "outcome": [5, 6] * 15, "c1": list(range(30))}
        ).write_csv(p)
        tool = get("causal_check")
        r = await tool.run(
            {
                "dataset_path": str(p),
                "treatment": "treatment",
                "outcome": "outcome",
                "confounders": ["c1"],
                "method": "adjusted_regression",
            }
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        assert r.output.adjusted is True
        assert r.output.passes_causal_bar is False


@pytest.mark.asyncio
async def test_planner_adds_causal_on_keyword() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        pl.DataFrame(
            {"treatment": ["A", "B"] * 10, "outcome": [1, 2] * 10, "x": list(range(20))}
        ).write_csv(p)
        from dsa_agent.planner import heuristics_plan

        plan = heuristics_plan(
            "What is the causal effect of treatment on outcome?",
            str(p),
            ["treatment", "outcome", "x"],
        )
        tools = [s.tool for s in plan.steps]
        assert "causal_check" in tools


@pytest.mark.asyncio
async def test_experiments_crud_and_compare() -> None:
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from dsa_api.core.database import Base, get_session
    from dsa_api.main import app

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with SessionLocal() as s:
            yield s

    app.dependency_overrides[get_session] = _get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/experiments/",
            json={
                "run_id": "run-1",
                "dataset_id": "ds1",
                "name": "exp1",
                "params": {"lr": 0.1},
                "metrics": {"accuracy": 0.8},
            },
        )
        assert r.status_code == 200
        id1 = r.json()["id"]
        r2 = await ac.post(
            "/api/v1/experiments/",
            json={
                "run_id": "run-1",
                "dataset_id": "ds1",
                "name": "exp2",
                "metrics": {"accuracy": 0.9},
            },
        )
        assert r2.status_code == 200
        id2 = r2.json()["id"]
        r3 = await ac.get("/api/v1/experiments/", params={"run_id": "run-1"})
        assert r3.status_code == 200
        assert len(r3.json()["experiments"]) == 2
        r4 = await ac.post("/api/v1/experiments/compare", json={"ids": [id1, id2]})
        assert r4.status_code == 200
        assert r4.json()["ranking"][0] == id2  # higher accuracy first
    app.dependency_overrides.clear()
    await engine.dispose()
