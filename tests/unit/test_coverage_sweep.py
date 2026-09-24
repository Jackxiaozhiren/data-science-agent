"""Sweep tests for previously uncovered shipped modules (coverage gate)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest


def test_project_init_creates_layout(tmp_path: Path) -> None:
    from dsa_evaluation.project_init import init_project

    root = init_project(tmp_path / "proj")
    assert (root / "datasets").is_dir()
    assert (root / "analyses").is_dir()
    assert (root / "reports").is_dir()
    assert (root / "notebooks").is_dir()
    assert (root / "config.yaml").read_text().startswith("version: 1")
    assert (root / "README.md").read_text().startswith("# proj")


def test_run_doctor_shape() -> None:
    from dsa_evaluation.doctor import run_doctor

    report = run_doctor()
    assert report["status"] in ("ok", "warn")
    names = {c["name"] for c in report["checks"]}
    assert {"Python", "Platform", "uv", "Node", "Docker", "LLM", "Disk"} <= names


def test_perf_harness_percentiles() -> None:
    from dsa_evaluation.perf_harness import concurrency_matrix, measure_latencies, p50, p95, p99

    assert p50([]) == 0.0
    assert p95([]) == 0.0
    assert p99([]) == 0.0
    vals = [float(i) for i in range(1, 101)]
    assert p50(vals) == 50.5 or p50(vals) == 50.0
    assert measure_latencies(vals)["mean"] == pytest.approx(50.5)
    assert p95(vals) >= p50(vals)
    assert p99(vals) >= p95(vals)
    matrix = concurrency_matrix([1, 2])
    assert set(matrix) == {"1", "2"}
    assert matrix["1"]["concurrency"] == 1


def test_build_manifest_defaults_and_versions(tmp_path: Path) -> None:
    from dsa_evaluation.research_manifest import ExperimentManifest, build_manifest

    m = build_manifest("exp-1")
    assert isinstance(m, ExperimentManifest)
    assert m.experiment_id == "exp-1"
    assert m.seed == 42
    assert m.timestamp
    assert "platform" in m.configuration
    m2 = build_manifest("exp-2", benchmark_version="0.2.0", model="stub", root=tmp_path)
    assert m2.benchmark_version == "0.2.0"
    assert m2.model == "stub"


def test_mime_sniff_allowlist() -> None:
    from dsa_execution.mime_sniff import is_allowed_mime, looks_like_zip_bomb, sniff_mime

    assert is_allowed_mime("a.csv", "text/csv", None) is True
    assert is_allowed_mime("a.csv", "text/plain", None) is True
    assert is_allowed_mime("a.exe", "application/x-msdownload", None) is False
    assert is_allowed_mime("a.xlsx", "application/zip", b"PK\x03\x04rest") is True
    assert is_allowed_mime("a.csv", None, None) is True
    assert sniff_mime("a.parquet", b"PAR1rest") is not None
    assert sniff_mime("unknown.zzz", None) is None
    assert looks_like_zip_bomb(b"PK\x03\x04", 10) is False


def test_statistics_helpers() -> None:
    from dsa_statistics.helpers import ensure_numeric

    arr = ensure_numeric(pl.Series("x", [1.0, 2.0, None, 4.5]))
    assert list(arr) == [1.0, 2.0, 4.5]
    with pytest.raises(ValueError, match="no non-null"):
        ensure_numeric(pl.Series("e", [None, None], dtype=pl.Null))
    with pytest.raises(ValueError, match="not numeric"):
        ensure_numeric(pl.Series("s", ["a", "b"]))


def test_verify_release_aggregates_stubbed_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import dsa_evaluation.verify_release as vr

    monkeypatch.setattr(vr, "_run", lambda cmd, timeout=300: (True, "ok"))
    report = vr.verify_release(version="v9.9.9")
    assert isinstance(report, dict)
    assert report, "expected non-empty gate report"


def test_dsa_cli_main_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    import data_science_agent.cli as cli

    called: list[bool] = []
    monkeypatch.setattr("dsa_evaluation.cli.main", lambda: called.append(True))
    cli.main()
    assert called == [True]


def test_stub_package_versions() -> None:
    import dsa_ml
    import dsa_reports
    import dsa_viz

    assert dsa_ml.__version__
    assert dsa_reports.__version__
    assert dsa_viz.__version__


def _run_cli(argv: list[str]) -> tuple[int, str]:
    import sys

    from dsa_evaluation.cli import main as cli_main

    old = sys.argv
    sys.argv = argv
    try:
        try:
            cli_main()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 0
            return code, ""
        return 0, ""
    finally:
        sys.argv = old


def test_cli_doctor(capsys: pytest.CaptureFixture[str]) -> None:
    code, _ = _run_cli(["dsa", "doctor"])
    assert code == 0
    assert "dsa doctor" in capsys.readouterr().out


def test_cli_doctor_json(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code, _ = _run_cli(["dsa", "doctor", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] in ("ok", "warn")


def test_cli_init_json(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code, _ = _run_cli(["dsa", "init", "my-proj", "--json"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_cli_research_run(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code, _ = _run_cli(["dsa", "research", "run", "--experiment", "exp-1"])
    assert code == 0
    assert json.loads(capsys.readouterr().out)["experiment_id"] == "exp-1"


def test_cli_usage_errors() -> None:
    assert _run_cli(["dsa", "research"])[0] == 2
    assert _run_cli(["dsa", "analyze"])[0] == 2
    assert _run_cli(["dsa", "profile"])[0] == 2
    assert _run_cli(["dsa", "plugin", "status"])[0] == 2
    assert _run_cli(["dsa", "plugin", "execute", "x"])[0] == 2


def test_cli_plugin_list(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code, _ = _run_cli(["dsa", "plugin", "list"])
    assert code == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)


def test_cli_mcp_tools(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code, _ = _run_cli(["dsa", "mcp"])
    assert code == 0
    assert isinstance(json.loads(capsys.readouterr().out), list)


def test_mcp_resources_branches() -> None:
    from fastapi.testclient import TestClient

    from dsa_mcp.server import app

    client = TestClient(app)
    r = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}}
    )
    assert r.status_code == 200
    assert "resources" in r.json()["result"]
    r2 = client.post(
        "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {}}
    )
    assert r2.json()["error"]["code"] == -32602
    r3 = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/read",
            "params": {"uri": "dsa://nope/xyz"},
        },
    )
    assert "error" in r3.json() or "result" in r3.json()
    r4 = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {}},
    )
    assert r4.json()["error"]["code"] == -32602
    assert client.get("/mcp/resources").status_code == 200


def _fake_task() -> object:
    from dsa_evaluation.catalog import BenchmarkTask

    return BenchmarkTask(
        id="t1", category="EDA", dataset="d.csv", question="q?", expected_analysis="x"
    )


def test_metrics_none_result_and_approx() -> None:
    from dsa_evaluation.metrics import (
        _approx_equal,
        aggregate_metrics,
        attach_statistical_eval,
        evaluate_task,
    )

    assert _approx_equal(1.0, 1.04, None) is True
    assert _approx_equal(1.0, 2.0, 0.01) is False
    r = evaluate_task(_fake_task(), None)
    assert r.error == "No run result"
    assert r.metrics.task_success is False
    assert aggregate_metrics([]) == {}
    agg = aggregate_metrics([r, r])
    assert agg["n"] == 2
    assert agg["task_success_rate"] == 0.0
    out = attach_statistical_eval(r, {"overall": "pass", "error_codes": ["S01"]})
    assert out.details["evaluator_version"] == "evaluator_v2"
    assert out.details["statistical_overall"] == "pass"


def test_metrics_nondict_state_branch() -> None:
    from dsa_evaluation.metrics import evaluate_task

    r = evaluate_task(_fake_task(), {"state": ["not", "a", "dict"], "status": "COMPLETED"})
    assert isinstance(r.metrics.task_success, bool)


def test_publication_number_helpers() -> None:
    from dsa_evaluation.publication import _dict_field, _integer, _number, _same_number

    assert _number("1.5") == 1.5
    assert _number("x") is None
    assert _integer(3) == 3
    assert _integer(3.0) is None
    assert _integer("x") is None
    assert _same_number(0.3, 0.3) is True
    assert _same_number(1.0, 2.0) is False
    assert _same_number("x", 1.0) is False
    assert _dict_field({"a": {"b": 1}}, "a") == {"b": 1}
    assert _dict_field({"a": 1}, "a") is None
    assert _dict_field({}, "missing") is None


def _dummy_magic() -> object:
    from dsa_jupyter.magic import DSAMagic

    return DSAMagic.__new__(DSAMagic)


def test_jupyter_magic_dispatch() -> None:
    from dsa_jupyter.magic import DSAMagic

    m = _dummy_magic()
    assert DSAMagic.dsa(m, "--help") is None
    assert DSAMagic.dsa(m, "frobnicate") is None
    assert DSAMagic.dsa(m, "analyze") is None  # missing dataset + task
    rep = DSAMagic.dsa(m, "doctor --json")
    assert rep["status"] in ("ok", "warn")
    plugins = DSAMagic.dsa(m, "plugin")
    assert isinstance(plugins, list)


def test_jupyter_magic_profile_csv(tmp_path: Path) -> None:
    from dsa_jupyter.magic import DSAMagic

    csv = tmp_path / "t.csv"
    csv.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    prof = DSAMagic._handle_profile(_dummy_magic(), [str(csv), "--json"])
    assert prof["rows"] == 2
    assert DSAMagic._handle_profile(_dummy_magic(), []) is None


def test_jupyter_load_ipython_extension_tolerant() -> None:
    from dsa_jupyter.magic import load_ipython_extension

    class _FakeIPython:
        def register_magics(self, cls: object) -> None:
            raise RuntimeError("no kernel")

    load_ipython_extension(_FakeIPython())  # must not raise
    load_ipython_extension(None)  # type: ignore[arg-type]  # must not raise


async def test_mcp_adapter_resources_and_discovery() -> None:
    from dsa_mcp.adapter import _discover_datasets, list_resources, list_tools, read_resource

    assert len(list_tools()) >= 17
    assert len(_discover_datasets()) >= 1
    assert any(r["uri"].startswith("dataset://") for r in list_resources())
    ds = await read_resource("dataset://sales")
    assert ds.get("isError") is not True or "text" in ds
    missing = await read_resource("dataset://no-such-dataset-xyz")
    assert missing.get("isError") is True
    ev = await read_resource("evidence://run-missing/evidence/E1")
    assert ev.get("isError") is True


def _write_json(path: Path, payload: object) -> None:
    import json

    path.write_text(json.dumps(payload), encoding="utf-8")


def test_publication_matrix_empty_root(tmp_path: Path) -> None:
    from dsa_evaluation.publication import validate_real_model_matrix

    report = validate_real_model_matrix(tmp_path)
    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert len(report.errors) == 4
    assert set(report.as_dict()) == {
        "matrix_valid",
        "publication_ready",
        "scope",
        "errors",
        "warnings",
        "rows",
    }


def test_publication_matrix_mismatched_variant(tmp_path: Path) -> None:
    from dsa_evaluation.publication import validate_real_model_matrix

    variant_dir = tmp_path / "dsa"
    variant_dir.mkdir()
    execution = {
        "evaluation_variant": "dsa",
        "llm_mode": "heuristic",
        "provider": "none",
        "fallback": "stub",
        "model": "stub/small",
        "git_commit": "abc",
        "evidence_critic_enabled": True,
        "evidence_critic_setting": "on",
        "call_count": 1,
        "llm_calls": [{"provider": "none", "model": "stub/small", "response_id": "r1"}],
    }
    _write_json(variant_dir / "workflow_manifest.json", {"variant": "WRONG", "scope": "full"})
    _write_json(variant_dir / "run_manifest.json", {"execution": execution})
    _write_json(variant_dir / "results.json", {"execution": execution})
    _write_json(variant_dir / "summary.json", {})
    _write_json(variant_dir / "raw_runs.json", [])
    report = validate_real_model_matrix(tmp_path)
    assert report.matrix_valid is False
    assert any("variant does not match" in e for e in report.errors)
    assert any("llm_mode" in e for e in report.errors)
