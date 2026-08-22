"""W2 §20 CLI Contract — help / exit code / structured output / clear errors."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]


def run_dsa(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "dsa", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_cli_help_shows_all_subcommands() -> None:
    r = run_dsa("--help")
    assert r.returncode == 0
    for cmd in (
        "doctor",
        "init",
        "analyze",
        "profile",
        "benchmark",
        "demo",
        "verify-release",
        "plugin",
        "mcp",
    ):
        assert cmd in r.stdout, f"missing {cmd} in --help"


def test_cli_doctor_plain_and_json() -> None:
    r = run_dsa("doctor")
    assert r.returncode == 0
    assert "dsa doctor" in r.stdout
    assert "Status:" in r.stdout
    rj = run_dsa("doctor", "--json")
    assert rj.returncode == 0, rj.stderr
    payload = json.loads(rj.stdout)
    assert "status" in payload
    assert payload["status"] in ("ok", "warn", "error")
    assert "checks" in payload


def test_cli_doctor_help() -> None:
    r = run_dsa("doctor", "--help")
    assert r.returncode == 0
    assert "doctor" in r.stdout.lower()


def test_cli_init_json_creates_project() -> None:
    r = run_dsa("init", "tmp-cli-test-proj", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["status"] == "ok"
    assert "project" in payload


def test_cli_analyze_missing_args_error_schema() -> None:
    r = run_dsa("analyze")
    assert r.returncode == 2
    # Should be JSON error (structured)
    payload = json.loads(r.stdout)
    assert "error" in payload
    assert "Usage" in payload["error"]


def test_cli_profile_missing_args_error_schema() -> None:
    r = run_dsa("profile")
    assert r.returncode == 2
    payload = json.loads(r.stdout)
    assert "error" in payload


def test_cli_analyze_profile_help() -> None:
    for cmd in ("analyze", "profile", "benchmark", "plugin", "mcp", "reproduce", "verify-release"):
        r = run_dsa(cmd, "--help")
        assert r.returncode == 0, f"{cmd} --help failed: {r.stderr}"
        assert "--help" in r.stdout or cmd in r.stdout.lower()


def test_cli_benchmark_json() -> None:
    r = run_dsa("benchmark", "--limit", "1", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["n_tasks"] == 1
    assert "aggregate" in payload


def test_cli_plugin_json() -> None:
    r = run_dsa("plugin", "--json")
    # plugin historically ignored --json but now supports it (same JSON)
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert isinstance(payload, list)
    assert any(p["name"] == "dsa-time-series" for p in payload)


def test_cli_mcp_json() -> None:
    r = run_dsa("mcp", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert isinstance(payload, list)
    assert len(payload) >= 10
    assert any(t["name"] == "profile_dataset" for t in payload)


def test_cli_analyze_success_json() -> None:
    # Real analysis smoke (1-2s) — structured output
    r = run_dsa(
        "analyze", "benchmarks/v2/datasets/sales.csv", "--task", "Analyze revenue", "--json"
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["run_id"].startswith("run-")
    assert payload["status"] in ("COMPLETED", "REPORTING", "FAILED")
    assert "evidence" in payload


def test_cli_profile_success_json() -> None:
    r = run_dsa("profile", "benchmarks/v2/datasets/sales.csv", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    assert payload["rows"] == 500
    assert "columns" in payload


def test_cli_benchmark_help_and_json_consistency() -> None:
    r_help = run_dsa("benchmark", "--help")
    assert r_help.returncode == 0
    assert "--limit" in r_help.stdout
    assert "--json" in r_help.stdout
