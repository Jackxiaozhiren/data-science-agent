from __future__ import annotations

from pathlib import Path

from dsa_plugins.registry import (
    execute_plugin_tool,
    get_plugin_status,
    install_plugin,
    list_plugins,
    remove_plugin,
    validate_plugin,
)


def test_hello_metrics_plugin_round_trip(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = repo_root / "examples" / "plugins" / "hello-metrics"

    assert validate_plugin(source / "manifest.yaml") == []

    monkeypatch.chdir(tmp_path)
    manifest = install_plugin(source)
    assert manifest.name == "hello-metrics"
    assert get_plugin_status("hello-metrics") == "enabled"
    assert any(plugin.name == "hello-metrics" for plugin in list_plugins())

    execution = execute_plugin_tool(manifest, "metrics", values=[1.0, 2.0, 3.0, 4.0])
    assert execution["ok"] is True
    result = execution["result"]
    assert isinstance(result, dict)
    assert result["count"] == 4
    assert result["mean"] == 2.5

    evidence = result["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["source_type"] == "arguments"
    assert str(evidence["source_id"]).startswith("sha256:")
    assert evidence["validation_status"] == "validated"

    remove_plugin("hello-metrics")
    assert get_plugin_status("hello-metrics") == "not_found"
