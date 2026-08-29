from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

REQUIRED_VARIANTS = ("dsa", "dsa-no-critic", "llm-tools", "llm-only")
_REQUIRED_FILES = (
    "workflow_manifest.json",
    "run_manifest.json",
    "results.json",
    "summary.json",
    "raw_runs.json",
)
_SHARED_WORKFLOW_FIELDS = (
    "workflow",
    "github_run_id",
    "github_run_attempt",
    "git_commit",
    "model",
    "scope",
    "task_limit",
    "catalog_sha256",
    "datasets_sha256",
    "dataset_file_count",
    "input_cost_per_million",
    "output_cost_per_million",
    "pricing_reference_date",
)
_EXPECTED_CRITIC: dict[str, tuple[bool | None, str]] = {
    "dsa": (True, "on"),
    "dsa-no-critic": (False, "off"),
    "llm-tools": (None, "not-applicable"),
    "llm-only": (None, "not-applicable"),
}


@dataclass(frozen=True)
class MatrixValidationReport:
    matrix_valid: bool
    publication_ready: bool
    scope: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    rows: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "matrix_valid": self.matrix_valid,
            "publication_ready": self.publication_ready,
            "scope": self.scope,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "rows": self.rows,
        }


def _load_object(path: Path) -> dict[str, Any]:
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, Any], data)


def _load_list(path: Path) -> list[Any]:
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _same_number(left: Any, right: Any) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    return left_number is not None and right_number is not None and left_number == right_number


def _dict_field(container: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = container.get(key)
    if not isinstance(value, dict):
        return None
    return cast(dict[str, Any], value)


def _task_ids(
    variant: str, raw_runs: list[Any], errors: list[str]
) -> tuple[str, ...] | None:
    prefix = f"{variant}:"
    task_ids: list[str] = []
    seen: set[str] = set()
    valid = True
    for index, raw_run in enumerate(raw_runs):
        if not isinstance(raw_run, dict):
            errors.append(f"{prefix} raw_runs[{index}] is not an object")
            valid = False
            continue
        task_id = raw_run.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"{prefix} raw_runs[{index}] is missing a non-empty task_id")
            valid = False
            continue
        if task_id in seen:
            errors.append(f"{prefix} duplicate task_id {task_id!r} in raw_runs")
            valid = False
        seen.add(task_id)
        task_ids.append(task_id)
    return tuple(task_ids) if valid else None


def _validate_execution(
    variant: str,
    workflow: dict[str, Any],
    run_manifest: dict[str, Any],
    results: dict[str, Any],
    raw_runs: list[Any],
    errors: list[str],
) -> dict[str, Any]:
    prefix = f"{variant}:"
    execution = _dict_field(run_manifest, "execution")
    results_execution = _dict_field(results, "execution")
    if execution is None:
        errors.append(f"{prefix} run_manifest.json is missing execution metadata")
        return {}
    if results_execution is None:
        errors.append(f"{prefix} results.json is missing execution metadata")
    elif execution != results_execution:
        errors.append(f"{prefix} run_manifest/results execution metadata differ")

    if execution.get("evaluation_variant") != variant:
        errors.append(f"{prefix} execution variant does not match directory")
    if execution.get("llm_mode") not in {"real", "openai"}:
        errors.append(f"{prefix} llm_mode is not a real-model mode")
    if execution.get("provider") != "openai":
        errors.append(f"{prefix} provider is not openai")
    if execution.get("fallback") != "error":
        errors.append(f"{prefix} fallback must be 'error' for publication review")
    if execution.get("model") != workflow.get("model"):
        errors.append(f"{prefix} execution model differs from workflow manifest")
    if execution.get("git_commit") != workflow.get("git_commit"):
        errors.append(f"{prefix} execution commit differs from workflow manifest")

    expected_critic, expected_setting = _EXPECTED_CRITIC[variant]
    if execution.get("evidence_critic_enabled") is not expected_critic:
        errors.append(f"{prefix} evidence critic enabled state is incorrect")
    if execution.get("evidence_critic_setting") != expected_setting:
        errors.append(f"{prefix} evidence critic setting is incorrect")

    call_count = _integer(execution.get("call_count"))
    calls = execution.get("llm_calls")
    call_input_tokens = 0
    call_output_tokens = 0
    call_total_tokens = 0
    call_latency_ms = 0
    call_rollup_complete = True
    if call_count is None or call_count <= 0:
        errors.append(f"{prefix} call_count must be greater than zero")
    if not isinstance(calls, list):
        errors.append(f"{prefix} llm_calls must be a list")
        call_rollup_complete = False
    else:
        if call_count is not None and len(calls) != call_count:
            errors.append(f"{prefix} llm_calls length differs from call_count")
        for index, call in enumerate(calls):
            if not isinstance(call, dict):
                errors.append(f"{prefix} llm_calls[{index}] is not an object")
                call_rollup_complete = False
                continue
            call_obj = cast(dict[str, Any], call)
            if call_obj.get("provider") != execution.get("provider"):
                errors.append(f"{prefix} llm_calls[{index}] provider mismatch")
            if call_obj.get("model") != execution.get("model"):
                errors.append(f"{prefix} llm_calls[{index}] model mismatch")
            response_id = call_obj.get("response_id")
            if not isinstance(response_id, str) or not response_id.strip():
                errors.append(f"{prefix} llm_calls[{index}] is missing response_id")

            per_call_latency = _integer(call_obj.get("latency_ms"))
            if per_call_latency is None or per_call_latency <= 0:
                errors.append(f"{prefix} llm_calls[{index}] latency_ms must be greater than zero")
                call_rollup_complete = False
            else:
                call_latency_ms += per_call_latency

            usage = _dict_field(call_obj, "usage")
            if usage is None:
                errors.append(f"{prefix} llm_calls[{index}] is missing usage metadata")
                call_rollup_complete = False
                continue
            input_tokens = _integer(usage.get("input_tokens"))
            output_tokens = _integer(usage.get("output_tokens"))
            total_tokens = _integer(usage.get("total_tokens"))
            if input_tokens is None or input_tokens < 0:
                errors.append(f"{prefix} llm_calls[{index}] input_tokens is invalid")
                call_rollup_complete = False
            else:
                call_input_tokens += input_tokens
            if output_tokens is None or output_tokens < 0:
                errors.append(f"{prefix} llm_calls[{index}] output_tokens is invalid")
                call_rollup_complete = False
            else:
                call_output_tokens += output_tokens
            if total_tokens is None or total_tokens <= 0:
                errors.append(f"{prefix} llm_calls[{index}] total_tokens must be greater than zero")
                call_rollup_complete = False
            else:
                call_total_tokens += total_tokens

    token_usage = _dict_field(execution, "token_usage")
    aggregate_input_tokens = (
        _integer(token_usage.get("input_tokens")) if token_usage is not None else None
    )
    aggregate_output_tokens = (
        _integer(token_usage.get("output_tokens")) if token_usage is not None else None
    )
    total_tokens = _integer(token_usage.get("total_tokens")) if token_usage is not None else None
    if aggregate_input_tokens is None or aggregate_input_tokens < 0:
        errors.append(f"{prefix} aggregate input token usage is invalid")
    if aggregate_output_tokens is None or aggregate_output_tokens < 0:
        errors.append(f"{prefix} aggregate output token usage is invalid")
    if total_tokens is None or total_tokens <= 0:
        errors.append(f"{prefix} total token usage must be greater than zero")

    latency_ms = _integer(execution.get("model_latency_ms"))
    if latency_ms is None or latency_ms <= 0:
        errors.append(f"{prefix} model latency must be greater than zero")

    if call_rollup_complete:
        if aggregate_input_tokens != call_input_tokens:
            errors.append(f"{prefix} aggregate input_tokens differs from llm_calls sum")
        if aggregate_output_tokens != call_output_tokens:
            errors.append(f"{prefix} aggregate output_tokens differs from llm_calls sum")
        if total_tokens != call_total_tokens:
            errors.append(f"{prefix} aggregate total_tokens differs from llm_calls sum")
        if latency_ms != call_latency_ms:
            errors.append(f"{prefix} model_latency_ms differs from llm_calls sum")

    workflow_input_rate = _number(workflow.get("input_cost_per_million"))
    workflow_output_rate = _number(workflow.get("output_cost_per_million"))
    if workflow_input_rate is None or workflow_input_rate <= 0:
        errors.append(f"{prefix} workflow input-token price must be greater than zero")
    if workflow_output_rate is None or workflow_output_rate <= 0:
        errors.append(f"{prefix} workflow output-token price must be greater than zero")

    pricing = _dict_field(execution, "pricing")
    if pricing is None:
        errors.append(f"{prefix} execution pricing metadata is missing")
    else:
        if not _same_number(
            pricing.get("input_cost_per_million"), workflow.get("input_cost_per_million")
        ):
            errors.append(f"{prefix} input-token price differs from workflow manifest")
        if not _same_number(
            pricing.get("output_cost_per_million"), workflow.get("output_cost_per_million")
        ):
            errors.append(f"{prefix} output-token price differs from workflow manifest")
        if pricing.get("source") != "explicit environment rates":
            errors.append(f"{prefix} pricing source is not explicit environment rates")
    cost_usd = _number(execution.get("cost_usd"))
    if cost_usd is None or cost_usd <= 0:
        errors.append(f"{prefix} cost_usd must be greater than zero with explicit pricing")

    n_tasks = _integer(run_manifest.get("n_tasks"))
    results_n_tasks = _integer(results.get("n_tasks"))
    task_limit = _integer(workflow.get("task_limit"))
    if n_tasks is None or n_tasks <= 0:
        errors.append(f"{prefix} n_tasks must be greater than zero")
    if n_tasks != results_n_tasks:
        errors.append(f"{prefix} run_manifest/results n_tasks differ")
    if task_limit is None or task_limit < 0:
        errors.append(f"{prefix} workflow task_limit is invalid")
    elif task_limit > 0 and n_tasks != task_limit:
        errors.append(f"{prefix} n_tasks does not match workflow task_limit")
    if n_tasks is not None and len(raw_runs) != n_tasks:
        errors.append(f"{prefix} raw_runs length differs from n_tasks")

    if variant in {"llm-only", "llm-tools"}:
        baseline_config = execution.get("baseline_config")
        if not isinstance(baseline_config, dict):
            errors.append(f"{prefix} baseline_config is missing")

    return {
        "call_count": call_count,
        "n_tasks": n_tasks,
        "total_tokens": total_tokens,
        "cost_usd": execution.get("cost_usd"),
        "model_latency_ms": latency_ms,
    }


def validate_real_model_matrix(root: Path) -> MatrixValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    rows: dict[str, dict[str, Any]] = {}
    workflow_manifests: dict[str, dict[str, Any]] = {}
    baseline_configs: dict[str, dict[str, Any]] = {}
    task_ids_by_variant: dict[str, tuple[str, ...]] = {}

    for variant in REQUIRED_VARIANTS:
        row_dir = root / variant
        missing = [name for name in _REQUIRED_FILES if not (row_dir / name).is_file()]
        if missing:
            errors.append(f"{variant}: missing required files: {', '.join(missing)}")
            continue
        try:
            workflow = _load_object(row_dir / "workflow_manifest.json")
            run_manifest = _load_object(row_dir / "run_manifest.json")
            results = _load_object(row_dir / "results.json")
            _load_object(row_dir / "summary.json")
            raw_runs = _load_list(row_dir / "raw_runs.json")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{variant}: cannot read artifacts: {exc}")
            continue

        if workflow.get("variant") != variant:
            errors.append(f"{variant}: workflow manifest variant does not match directory")
        workflow_manifests[variant] = workflow
        rows[variant] = _validate_execution(
            variant, workflow, run_manifest, results, raw_runs, errors
        )
        validated_task_ids = _task_ids(variant, raw_runs, errors)
        if validated_task_ids is not None:
            task_ids_by_variant[variant] = validated_task_ids

        execution = _dict_field(run_manifest, "execution")
        if execution is not None and variant in {"llm-only", "llm-tools"}:
            config = execution.get("baseline_config")
            if isinstance(config, dict):
                baseline_configs[variant] = cast(dict[str, Any], config)

    if len(workflow_manifests) == len(REQUIRED_VARIANTS):
        reference_variant = REQUIRED_VARIANTS[0]
        reference = workflow_manifests[reference_variant]
        for variant in REQUIRED_VARIANTS[1:]:
            candidate = workflow_manifests[variant]
            for field in _SHARED_WORKFLOW_FIELDS:
                if candidate.get(field) != reference.get(field):
                    errors.append(f"{variant}: workflow {field} differs from {reference_variant}")

        task_limit = _integer(reference.get("task_limit"))
        raw_scope = reference.get("scope")
        if raw_scope == "full":
            if task_limit != 0:
                errors.append("scope=full requires task_limit=0")
        elif raw_scope == "smoke-5":
            if task_limit != 5:
                errors.append("scope=smoke-5 requires task_limit=5")
        else:
            errors.append(f"unsupported workflow scope {raw_scope!r}")

    if set(rows) == set(REQUIRED_VARIANTS):
        reference_n_tasks = rows["dsa"].get("n_tasks")
        for variant in REQUIRED_VARIANTS[1:]:
            if rows[variant].get("n_tasks") != reference_n_tasks:
                errors.append(f"{variant}: n_tasks differs from dsa")

    if set(task_ids_by_variant) == set(REQUIRED_VARIANTS):
        reference_task_ids = task_ids_by_variant["dsa"]
        for variant in REQUIRED_VARIANTS[1:]:
            if task_ids_by_variant[variant] != reference_task_ids:
                errors.append(f"{variant}: task_id sequence differs from dsa")

    if (
        set(baseline_configs) == {"llm-only", "llm-tools"}
        and baseline_configs["llm-only"] != baseline_configs["llm-tools"]
    ):
        errors.append("baseline controls differ between llm-only and llm-tools")

    scope: str | None = None
    if workflow_manifests:
        raw_scope = next(iter(workflow_manifests.values())).get("scope")
        if isinstance(raw_scope, str):
            scope = raw_scope

    matrix_valid = not errors
    publication_ready = matrix_valid and scope == "full"
    if matrix_valid and not publication_ready:
        warnings.append(
            "Matrix integrity is valid, but this is not a full-catalog run; "
            "do not promote it to the public leaderboard."
        )

    return MatrixValidationReport(
        matrix_valid=matrix_valid,
        publication_ready=publication_ready,
        scope=scope,
        errors=tuple(errors),
        warnings=tuple(warnings),
        rows=rows,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate four-way real-model benchmark artifacts before publication."
    )
    parser.add_argument("root", type=Path, help="Directory containing the four variant folders")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    parser.add_argument("--output", type=Path, default=None, help="Write the JSON report to a file")
    parser.add_argument(
        "--require-publication-ready",
        action="store_true",
        help="Fail unless the matrix is valid and uses the full catalog",
    )
    args = parser.parse_args()

    report = validate_real_model_matrix(args.root)
    payload = json.dumps(report.as_dict(), indent=2, ensure_ascii=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.json or args.output is None:
        print(payload)

    if not report.matrix_valid:
        raise SystemExit(1)
    if args.require_publication_ready and not report.publication_ready:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
