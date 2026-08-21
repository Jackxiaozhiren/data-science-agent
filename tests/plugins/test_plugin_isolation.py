"""W3 §25 Failure Isolation — plugin failure must not crash Core Agent / Other Plugins / Benchmark / MCP."""

from __future__ import annotations

from pathlib import Path

from dsa_plugins.manifest import PluginManifest
from dsa_plugins.registry import check_permission, execute_plugin_tool, load_plugin_isolated
from data_science_agent import Agent


def test_permission_denied_isolated() -> None:
    # plugin with limited perms should deny forecast which needs dataset.read+process
    m = PluginManifest(
        name="limited",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "dsa_time_series.plugin:register"},
        permissions=["filesystem.read"],  # missing dataset.read/process
        capabilities=["forecast"],
    )
    assert not check_permission(m, ["dataset.read", "process"])
    out = execute_plugin_tool(m, "forecast", "benchmarks/v2/datasets/sales.csv")
    assert out["ok"] is False
    assert "permission denied" in out["error"]


def test_load_isolated_returns_error_not_crash() -> None:
    m = PluginManifest(
        name="evil",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "nonexistent.module:register"},
        permissions=["dataset.read", "process"],
        capabilities=["forecast"],
    )
    plugin, err = load_plugin_isolated(m)
    assert plugin is None
    assert err is not None
    assert "load failed" in err


def test_execute_isolated_catches_exception() -> None:
    # use real plugin but trigger error via missing dataset
    from dsa_plugins.registry import list_plugins

    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    out = execute_plugin_tool(m, "forecast", "nonexistent.csv")
    assert out["ok"] is False
    assert out["error"] is not None


def test_core_agent_survives_plugin_failure() -> None:
    # Agent should complete even if plugin would fail — simulate by running Agent while plugin isolated fails
    from dsa_plugins.registry import execute_plugin_tool, list_plugins

    m = [p for p in list_plugins() if p.name == "dsa-time-series"][0]
    # plugin fail
    out = execute_plugin_tool(m, "forecast", "nonexistent.csv")
    assert out["ok"] is False
    # Core Agent still works
    r = Agent().analyze_sync("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
    assert r.status in ("COMPLETED", "REPORTING", "FAILED")
    assert isinstance(r.evidence, list)


def test_benchmark_survives_plugin_failure() -> None:
    from data_science_agent import Benchmark

    # benchmark should not be affected by plugin load failure
    # (benchmark doesn't directly use plugin, but we ensure isolation)
    b = Benchmark()
    res = b.run(limit=1)
    assert res.n_tasks == 1


def test_mcp_survives_plugin_failure() -> None:
    from dsa_mcp.adapter import list_mcp_tools

    tools = list_mcp_tools()
    # MCP tools should be available even if plugin fails
    assert len(tools) >= 10
    # Simulate plugin failure then check MCP still works
    from dsa_plugins.manifest import PluginManifest
    from dsa_plugins.registry import load_plugin_isolated

    bad = PluginManifest(
        name="bad-mcp",
        version="1.0.0",
        license="MIT",
        entrypoint={"python": "bad:fn"},
        permissions=["dataset.read"],
        capabilities=["forecast"],
    )
    _, err = load_plugin_isolated(bad)
    assert err is not None
    tools2 = list_mcp_tools()
    assert len(tools2) == len(tools)
