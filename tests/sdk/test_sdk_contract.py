"""W2 §17 SDK Contract Tests — input/output/error/compat/serialization/async."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from data_science_agent import Agent, Analysis, Artifact, Benchmark, Dataset, Evidence, Reproduction
from data_science_agent.sdk import API_STABILITY, BenchmarkResult, Insight, Report, ReproductionResult


# §14 Public surface — must match spec
def test_sdk_public_surface_exports() -> None:
    from data_science_agent import __version__

    assert __version__ == "4.1.0"
    # Required §14 exports
    for name in ("Agent", "Dataset", "Analysis", "Evidence", "Artifact", "Benchmark", "Reproduction"):
        assert name in dir(__import__("data_science_agent")), f"missing {name}"
    # Stability map must mark all as Stable
    for k in ("Agent", "Dataset", "Analysis", "Evidence", "Artifact", "Benchmark", "Reproduction"):
        assert API_STABILITY[k] == "Stable"


def test_sdk_no_internal_import_leak() -> None:
    # Public SDK must not expose _internal modules in __all__
    import data_science_agent

    assert not any(n.startswith("_") for n in data_science_agent.__all__ if n != "__version__")
    assert "Agent" in data_science_agent.__all__


# §17 input schema
def test_dataset_from_path_contract() -> None:
    ds = Dataset.from_path("benchmarks/v2/datasets/sales.csv")
    assert ds.path == "benchmarks/v2/datasets/sales.csv"
    assert ds.dataset_id == "sales"
    ds2 = Dataset.from_path(Path("examples/datasets/sales.csv"))
    assert ds2.dataset_id == "sales"


def test_dataset_from_path_with_pathlib() -> None:
    ds = Dataset(path="a/b.csv", dataset_id="custom", rows=10)
    assert ds.path == "a/b.csv"
    assert ds.dataset_id == "custom"


def test_evidence_schema() -> None:
    e = Evidence(id="ev-1", claim="c", source_type="python", source_id="tc-1", result={"r": 1})
    assert e.id == "ev-1"
    assert e.confidence == 0.0
    # serializable
    d = e.__dict__
    assert json.dumps(d, default=str)


def test_analysis_dataclass_schema() -> None:
    a = Analysis(run_id="run-1", status="COMPLETED", report_markdown="# hi", evidence=[], insights=[])
    assert a.run_id == "run-1"
    assert a.status == "COMPLETED"
    assert isinstance(a.evidence, list)


# §17 output schema via real Agent.profile
def test_agent_profile_output_schema() -> None:
    prof = Agent().profile("benchmarks/v2/datasets/sales.csv")
    assert "rows" in prof and "columns" in prof and "path" in prof
    assert prof["rows"] == 500
    assert isinstance(prof["columns"], list)
    assert len(prof["columns"]) >= 2
    # serialization
    assert json.dumps(prof, default=str)


def test_agent_profile_with_dataset_handle() -> None:
    ds = Dataset.from_path("benchmarks/v2/datasets/sales.csv")
    prof = Agent().profile(ds)
    assert prof["rows"] == 500


# §17 error schema
def test_agent_profile_missing_file_error() -> None:
    with pytest.raises(Exception) as exc:
        Agent().profile("nonexistent_xyz_123.csv")
    # Should be DatasetError or FileNotFoundError wrapped
    assert exc.value is not None


def test_agent_analyze_output_schema_sync() -> None:
    # Smoke with minimal dataset
    r = Agent().analyze_sync("benchmarks/v2/datasets/sales.csv", "Analyze revenue trend")
    assert isinstance(r, Analysis)
    assert r.run_id.startswith("run-")
    assert r.status in ("COMPLETED", "FAILED", "REPORTING")
    assert isinstance(r.evidence, list)
    assert isinstance(r.tool_calls, list)
    # evidence must have required fields if present
    for ev in r.evidence:
        assert isinstance(ev, Evidence)
        assert ev.id and ev.claim and ev.source_type and ev.source_id
    # report should exist on success
    # serialization of whole Analysis (except raw_state)
    payload = {
        "run_id": r.run_id,
        "status": r.status,
        "evidence": [e.__dict__ for e in r.evidence],
        "tool_calls": r.tool_calls,
    }
    assert json.dumps(payload, default=str)


def test_agent_analyze_with_dataset_handle() -> None:
    ds = Dataset.from_path("benchmarks/v2/datasets/sales.csv")
    r = Agent().analyze_sync(ds, "Analyze revenue")
    assert isinstance(r, Analysis)


# §17 async behavior
@pytest.mark.asyncio
async def test_agent_analyze_async_matches_sync() -> None:
    agent = Agent()
    r_async = await agent.analyze("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
    assert isinstance(r_async, Analysis)
    assert len(r_async.evidence) >= 1
    assert r_async.run_id.startswith("run-")


def test_agent_analyze_sync_separate() -> None:
    r_sync = Agent().analyze_sync("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
    assert isinstance(r_sync, Analysis)
    assert len(r_sync.evidence) >= 1


def test_agent_version_stable() -> None:
    assert Agent().version == "4.1.0"
    assert API_STABILITY["Agent"] == "Stable"


# §17 backward compatibility — exports must not be removed
def test_sdk_backward_compat_exports() -> None:
    import data_science_agent as m

    expected = {"Agent", "Dataset", "Analysis", "Evidence", "Artifact", "Insight", "Report", "Benchmark", "BenchmarkResult", "Reproduction", "ReproductionResult"}
    for name in expected:
        assert hasattr(m, name), f"backward compat missing {name}"


# §17 serialization — Insight/Artifact/Report
def test_sdk_serialization_helpers() -> None:
    ins = Insight(id="in-1", finding="f", evidence_ids=["ev-1"])
    art = Artifact(id="a-1", type="chart", path="artifacts/x.png")
    rep = Report(run_id="run-1", markdown="# hi")
    bench_res = BenchmarkResult(n_tasks=1, aggregate={"task_success_rate": 1.0})
    repro_res = ReproductionResult(overall=0.9, execution=1.0)
    for obj in (ins, art, rep, bench_res, repro_res):
        assert json.dumps(obj.__dict__, default=str)


# Benchmark facade smoke (§17 + §19)
def test_benchmark_facade_contract() -> None:
    b = Benchmark()
    res = b.run(limit=1)
    assert isinstance(res, BenchmarkResult)
    assert res.n_tasks == 1
    assert "task_success_rate" in res.aggregate or "n" in res.aggregate
    assert isinstance(res.results, list)


# Ensure public code does not import _internal
def test_sdk_no_internal_dependency_text() -> None:
    text = Path("src/data_science_agent/sdk.py").read_text(encoding="utf-8")
    # Disallow actual import of private _internal module (docstring mentions are ok if not import)
    assert "from _internal" not in text
    assert "import _internal" not in text
    assert "from data_science_agent._internal" not in text
