from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field

from dsa_evaluation.catalog import BenchmarkTask

_BASELINE_VARIANTS = {"llm-only", "llm-tools"}
_INTERNAL_TOOLS = {"create_evidence", "validate_result", "generate_report", "save_artifact"}
_PROMPT_VERSION = "baseline-v1"


class BaselineToolCall(BaseModel):
    tool: str
    input: dict[str, Any] = Field(default_factory=dict)


class BaselineToolPlan(BaseModel):
    rationale: str = ""
    calls: list[BaselineToolCall] = Field(default_factory=list)


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def baseline_config() -> dict[str, Any]:
    return {
        "prompt_version": _PROMPT_VERSION,
        "preview_rows": _int_env("DSA_BASELINE_PREVIEW_ROWS", 20, 1, 100),
        "max_tool_calls": _int_env("DSA_BASELINE_MAX_TOOL_CALLS", 3, 1, 8),
        "max_tool_output_chars": _int_env(
            "DSA_BASELINE_MAX_TOOL_OUTPUT_CHARS", 12_000, 1_000, 100_000
        ),
    }


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _dataset_context(dataset_path: Path) -> dict[str, Any]:
    from dsa_datasets.loader import load_dataframe
    from dsa_datasets.validate import detect_format

    config = baseline_config()
    fmt = detect_format(dataset_path.name)
    df = load_dataframe(dataset_path, fmt)
    preview_rows = int(config["preview_rows"])
    preview = df.head(preview_rows).to_dicts()
    return cast(
        dict[str, Any],
        _json_safe(
            {
                "row_count": df.height,
                "column_count": df.width,
                "columns": [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns],
                "preview_rows": preview,
                "preview_row_count": len(preview),
                "preview_truncated": df.height > preview_rows,
            }
        ),
    )


def _tool_catalog() -> dict[str, dict[str, Any]]:
    from dsa_tools import bootstrap, get, list_tools

    if not list_tools():
        bootstrap()
    catalog: dict[str, dict[str, Any]] = {}
    for name in list_tools():
        if name in _INTERNAL_TOOLS:
            continue
        tool = get(name)
        catalog[name] = {
            "description": tool.description,
            "input_schema": tool.input_model.model_json_schema(),
        }
    return catalog


def _tool_input(tool: Any, requested: dict[str, Any], dataset_path: Path) -> dict[str, Any]:
    payload = dict(requested)
    fields = getattr(tool.input_model, "model_fields", {})
    if "dataset_path" in fields:
        payload["dataset_path"] = str(dataset_path)
    if tool.name == "profile_dataset" and "path" in fields:
        payload["path"] = str(dataset_path)
    return payload


def _tool_record(result: Any, payload: dict[str, Any]) -> dict[str, Any]:
    output = result.output
    if hasattr(output, "model_dump"):
        output_payload = output.model_dump(mode="json")
    elif isinstance(output, dict):
        output_payload = output
    else:
        output_payload = None
    return {
        "call_id": result.call_id,
        "tool": result.tool,
        "input": _json_safe(payload),
        "output": _json_safe(output_payload),
        "status": result.status,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }


def _context_for_prompt(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))


async def run_llm_only_baseline(task: BenchmarkTask, dataset_path: Path) -> dict[str, Any]:
    from dsa_llm.providers import auto_provider

    context = _dataset_context(dataset_path)
    provider = auto_provider()
    prompt = (
        "You are an LLM-only data-analysis baseline. You have no Python, SQL, tools, retrieval, "
        "or hidden access to the dataset beyond the context below. Answer the user's question using "
        "only that context. Do not invent values that are not visible. If the preview is insufficient, "
        "say so explicitly.\n\n"
        f"Question: {task.question}\n"
        f"Dataset context: {_context_for_prompt(context)}\n"
    )
    answer = await provider.generate(prompt, max_output_tokens=2000)
    return {
        "state": {
            "tool_calls": [],
            "evidence": [],
            "insights": [],
            "validation_results": [],
            "report_markdown": answer,
            "status": "completed",
        },
        "report_markdown": answer,
        "baseline": {
            "variant": "llm-only",
            "prompt_version": _PROMPT_VERSION,
            "dataset_context": context,
            "final_answer": answer,
            "tool_access": False,
        },
    }


async def run_llm_tools_baseline(task: BenchmarkTask, dataset_path: Path) -> dict[str, Any]:
    from dsa_llm.providers import auto_provider
    from dsa_tools import get

    context = _dataset_context(dataset_path)
    catalog = _tool_catalog()
    config = baseline_config()
    provider = auto_provider()
    planning_prompt = (
        "You are a vanilla LLM + data-analysis-tools baseline. Select the minimum useful tool calls "
        "needed to answer the user's question. You do not have DSA's evidence critic, retry policy, "
        "evidence bundle, multi-agent orchestration, or hidden ground truth. Use only the supplied tool "
        "names and input schemas. Never invent tool outputs. Dataset path fields are injected by the "
        "runner and should be omitted.\n\n"
        f"Question: {task.question}\n"
        f"Dataset context: {_context_for_prompt(context)}\n"
        f"Available tools: {json.dumps(catalog, ensure_ascii=False, default=str)}\n"
        f"Maximum tool calls: {config['max_tool_calls']}\n"
    )
    raw_plan = await provider.structured_output(
        planning_prompt, BaselineToolPlan, max_output_tokens=2500
    )
    plan = (
        raw_plan
        if isinstance(raw_plan, BaselineToolPlan)
        else BaselineToolPlan.model_validate(raw_plan)
    )

    tool_calls: list[dict[str, Any]] = []
    max_tool_calls = int(config["max_tool_calls"])
    for requested in plan.calls[:max_tool_calls]:
        if requested.tool not in catalog:
            tool_calls.append(
                {
                    "call_id": "baseline-invalid-tool",
                    "tool": requested.tool,
                    "input": _json_safe(requested.input),
                    "output": None,
                    "status": "error",
                    "error": f"Tool not allowed in baseline: {requested.tool}",
                    "duration_ms": 0,
                }
            )
            continue
        tool = get(requested.tool)
        payload = _tool_input(tool, requested.input, dataset_path)
        result = await tool.run(payload)
        tool_calls.append(_tool_record(result, payload))

    max_chars = int(config["max_tool_output_chars"])
    serialized_calls = json.dumps(tool_calls, ensure_ascii=False, default=str)
    if len(serialized_calls) > max_chars:
        serialized_calls = serialized_calls[:max_chars] + "...[truncated]"
    answer_prompt = (
        "You are the answer-writing stage of a vanilla LLM + tools baseline. Answer the user's question "
        "using only the executed tool results below. Do not claim evidence that was not produced, and "
        "state limitations when calls failed or the results are insufficient.\n\n"
        f"Question: {task.question}\n"
        f"Tool results: {serialized_calls}\n"
    )
    answer = await provider.generate(answer_prompt, max_output_tokens=2000)
    return {
        "state": {
            "tool_calls": tool_calls,
            "evidence": [],
            "insights": [],
            "validation_results": [],
            "report_markdown": answer,
            "status": "completed",
        },
        "report_markdown": answer,
        "baseline": {
            "variant": "llm-tools",
            "prompt_version": _PROMPT_VERSION,
            "dataset_context": context,
            "plan": plan.model_dump(mode="json"),
            "final_answer": answer,
            "tool_access": True,
            "max_tool_calls": max_tool_calls,
        },
    }


async def run_baseline(variant: str, task: BenchmarkTask, dataset_path: Path) -> dict[str, Any]:
    normalized = variant.strip().lower()
    if normalized == "llm-only":
        return await run_llm_only_baseline(task, dataset_path)
    if normalized == "llm-tools":
        return await run_llm_tools_baseline(task, dataset_path)
    raise ValueError(
        f"Unsupported baseline variant: {variant!r}; expected {sorted(_BASELINE_VARIANTS)}"
    )
