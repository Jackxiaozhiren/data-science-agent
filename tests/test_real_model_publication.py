from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dsa_evaluation.publication import REQUIRED_VARIANTS, validate_real_model_matrix


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_row(
    root: Path,
    variant: str,
    *,
    scope: str = "smoke-5",
    task_limit: int = 5,
    git_commit: str = "abc123",
    datasets_sha256: str = "dataset-sha",
    call_count: int = 1,
    task_ids: list[str] | None = None,
    aggregate_total_tokens: int | None = None,
) -> None:
    row = root / variant
    selected_task_ids = task_ids or [
        f"task-{index}" for index in range(5 if task_limit == 0 else task_limit)
    ]
    n_tasks = len(selected_task_ids)
    critic_enabled: bool | None
    critic_setting: str
    if variant == "dsa":
        critic_enabled, critic_setting = True, "on"
    elif variant == "dsa-no-critic":
        critic_enabled, critic_setting = False, "off"
    else:
        critic_enabled, critic_setting = None, "not-applicable"

    calls = [
        {
            "provider": "openai",
            "model": "gpt-5.6-luna",
            "response_id": f"resp-{variant}-{index}",
            "latency_ms": 25,
            "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        }
        for index in range(call_count)
    ]
    expected_total_tokens = 120 * call_count
    execution: dict[str, Any] = {
        "llm_mode": "real",
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "fallback": "error",
        "git_commit": git_commit,
        "evaluation_variant": variant,
        "evidence_critic_enabled": critic_enabled,
        "evidence_critic_setting": critic_setting,
        "call_count": call_count,
        "model_latency_ms": 25 * call_count,
        "token_usage": {
            "input_tokens": 100 * call_count,
            "output_tokens": 20 * call_count,
            "total_tokens": (
                expected_total_tokens
                if aggregate_total_tokens is None
                else aggregate_total_tokens
            ),
        },
        "pricing": {
            "input_cost_per_million": 0.2,
            "output_cost_per_million": 1.2,
            "source": "explicit environment rates",
        },
        "cost_usd": 0.000044 * call_count,
        "llm_calls": calls,
    }
    if variant in {"llm-only", "llm-tools"}:
        execution["baseline_config"] = {
            "prompt_version": "baseline-v1",
            "preview_rows": 20,
            "max_tool_calls": 3,
            "max_tool_output_chars": 12000,
        }

    workflow = {
        "workflow": "Real Model Evaluation Smoke",
        "github_run_id": "12345",
        "github_run_attempt": "1",
        "git_commit": git_commit,
        "variant": variant,
        "model": "gpt-5.6-luna",
        "scope": scope,
        "task_limit": task_limit,
        "catalog": "benchmarks/ds-agent-benchmark/catalog.json",
        "catalog_sha256": "catalog-sha",
        "datasets_dir": "benchmarks/ds-agent-benchmark/datasets",
        "datasets_sha256": datasets_sha256,
        "dataset_file_count": 4,
        "input_cost_per_million": "0.20",
        "output_cost_per_million": "1.20",
        "pricing_reference_date": "2026-08-29",
    }
    run_manifest = {
        "catalog": "/benchmarks/ds-agent-benchmark/catalog.json",
        "datasets_dir": "/benchmarks/ds-agent-benchmark/datasets",
        "n_tasks": n_tasks,
        "execution": execution,
    }
    results = {
        "catalog": run_manifest["catalog"],
        "datasets_dir": run_manifest["datasets_dir"],
        "n_tasks": n_tasks,
        "execution": execution,
        "aggregate": {},
        "results": [],
    }
    raw_runs = [
        {"task_id": task_id, "elapsed_ms": 10, "run_result": {}, "error": None}
        for task_id in selected_task_ids
    ]

    _write_json(row / "workflow_manifest.json", workflow)
    _write_json(row / "run_manifest.json", run_manifest)
    _write_json(row / "results.json", results)
    _write_json(row / "summary.json", {})
    _write_json(row / "raw_runs.json", raw_runs)


def _write_matrix(root: Path, *, scope: str = "smoke-5", task_limit: int = 5) -> None:
    for variant in REQUIRED_VARIANTS:
        _write_row(root, variant, scope=scope, task_limit=task_limit)


def test_valid_smoke_matrix_is_not_publication_ready(tmp_path: Path) -> None:
    _write_matrix(tmp_path)

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is True
    assert report.publication_ready is False
    assert report.scope == "smoke-5"
    assert report.errors == ()
    assert report.warnings


def test_full_matrix_can_be_publication_ready(tmp_path: Path) -> None:
    _write_matrix(tmp_path, scope="full", task_limit=0)

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is True
    assert report.publication_ready is True
    assert report.errors == ()
    assert report.warnings == ()


def test_full_scope_requires_unlimited_task_limit(tmp_path: Path) -> None:
    _write_matrix(tmp_path, scope="full", task_limit=5)

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert "scope=full requires task_limit=0" in report.errors


def test_snapshot_drift_invalidates_matrix(tmp_path: Path) -> None:
    _write_matrix(tmp_path)
    _write_row(tmp_path, "llm-only", datasets_sha256="different-dataset-sha")

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert any("datasets_sha256 differs" in error for error in report.errors)


def test_task_id_drift_invalidates_matrix(tmp_path: Path) -> None:
    _write_matrix(tmp_path)
    _write_row(
        tmp_path,
        "llm-only",
        task_ids=["task-0", "task-1", "task-2", "task-3", "different-task"],
    )

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert any("task_id sequence differs from dsa" in error for error in report.errors)


def test_duplicate_task_ids_invalidate_row(tmp_path: Path) -> None:
    _write_matrix(tmp_path)
    _write_row(
        tmp_path,
        "dsa",
        task_ids=["task-0", "task-1", "task-1", "task-3", "task-4"],
    )

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert any("duplicate task_id" in error for error in report.errors)


def test_zero_real_model_calls_invalidates_row(tmp_path: Path) -> None:
    _write_matrix(tmp_path)
    _write_row(tmp_path, "dsa", call_count=0)

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert any("call_count must be greater than zero" in error for error in report.errors)
    assert any("total token usage must be greater than zero" in error for error in report.errors)


def test_call_rollup_must_match_execution_totals(tmp_path: Path) -> None:
    _write_matrix(tmp_path)
    _write_row(tmp_path, "dsa", aggregate_total_tokens=999)

    report = validate_real_model_matrix(tmp_path)

    assert report.matrix_valid is False
    assert report.publication_ready is False
    assert any("aggregate total_tokens differs from llm_calls sum" in error for error in report.errors)
