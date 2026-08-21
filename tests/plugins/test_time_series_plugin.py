"""W3 §27 dsa-time-series flagship — forecast/backtest/metrics/viz/evidence + §26 evaluation."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from dsa_plugins.registry import list_plugins


@pytest.fixture
def plugin():
    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    from dsa_plugins.registry import load_plugin

    return load_plugin(m)


DATASET = "benchmarks/v2/datasets/sales.csv"


def test_plugin_registers_expected_capabilities(plugin) -> None:
    assert "forecast" in plugin.register_tools()
    assert "backtest" in plugin.register_tools()
    assert "forecast_viz" in plugin.register_tools()
    assert "metrics" in plugin.register_tools()
    assert "evidence" in plugin.register_tools()
    assert "forecast_mae" in plugin.register_evaluators()


def test_forecast_returns_metrics_and_forecast(plugin) -> None:
    out = plugin.forecast(DATASET, periods=5, method="linear_trend")
    assert out["method"] == "linear_trend"
    assert out["periods"] == 5
    assert len(out["forecast"]) == 5
    assert "mae" in out["metrics"]
    assert out["value_col"] in ("revenue", "price", "value", "sales", "demand")
    assert out["n_train"] >= 10


def test_backtest_aggregate(plugin) -> None:
    bt = plugin.backtest(DATASET, folds=2, method="linear_trend")
    assert "folds" in bt
    assert len(bt["folds"]) == 2
    for f in bt["folds"]:
        assert "mae" in f and "rmse" in f
    assert "mae_mean" in bt["aggregate"]


def test_metrics_from_forecast(plugin) -> None:
    fr = plugin.forecast(DATASET, periods=5)
    m = plugin.metrics(fr)
    assert "mae" in m
    # explicit arrays
    m2 = plugin.metrics(y_true=[1, 2, 3], y_pred=[1.1, 1.9, 3.2])
    assert "mae" in m2 and "rmse" in m2 and "mape" in m2


def test_visualization_creates_artifact(plugin) -> None:
    fr = plugin.forecast(DATASET, periods=5)
    viz = plugin.forecast_viz(DATASET, fr)
    assert "artifact_path" in viz
    assert Path(viz["artifact_path"]).exists()
    assert viz["base64_png"]
    # valid base64
    assert base64.b64decode(viz["base64_png"][:20] + "==")


def test_evidence_structure(plugin) -> None:
    fr = plugin.forecast(DATASET, periods=5)
    ev = plugin.evidence(DATASET, fr)
    assert ev["id"].startswith("ev-")
    assert "claim" in ev and ev["claim"]
    assert ev["source_type"] == "model"
    assert "forecast" in ev["result"]
    assert 0 <= ev["confidence"] <= 1


def test_full_pipeline_sdk_cli_benchmark_report_integration(plugin) -> None:
    """§27 must接入 Agent/SDK/CLI/Benchmark/Report."""
    # SDK: plugin via registry
    from dsa_plugins.registry import execute_plugin_tool, list_plugins

    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    out = execute_plugin_tool(m, "forecast", DATASET, periods=3)
    assert out["ok"] is True
    # Agent: independent but evidence structure compatible
    from data_science_agent import Agent

    r = Agent().analyze_sync(DATASET, "Analyze revenue and forecast trend")
    assert r.status in ("COMPLETED", "REPORTING")
    # CLI: via dsa plugin list (already tested)
    import subprocess

    cp = subprocess.run(["uv", "run", "dsa", "plugin", "--json"], capture_output=True, text=True, cwd=Path.cwd())
    assert cp.returncode == 0
    assert "dsa-time-series" in cp.stdout
    # Benchmark: plugin evaluator not crashing benchmark
    from data_science_agent import Benchmark

    br = Benchmark().run(limit=1)
    assert br.n_tasks == 1
    # Report: viz artifact exists for embedding
    fr = plugin.forecast(DATASET, periods=3)
    viz = plugin.forecast_viz(DATASET, fr)
    assert Path(viz["artifact_path"]).exists()


def test_plugin_has_documentation_and_example() -> None:
    """§26 documentation + example (§27)."""
    readme = Path("plugins/dsa-time-series/README.md")
    assert readme.exists()
    txt = readme.read_text()
    assert "forecast" in txt.lower()
    manifest = Path("plugins/dsa-time-series/manifest.yaml")
    assert manifest.exists()


def test_plugin_security_permissions_default_deny() -> None:
    """§23 DENY default — plugin must explicitly request needed perms."""
    from dsa_plugins.registry import check_permission, list_plugins

    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    assert check_permission(m, "dataset.read")
    assert check_permission(m, "process")
    assert check_permission(m, "artifact.write")
    # not granted
    assert not check_permission(m, "network")
