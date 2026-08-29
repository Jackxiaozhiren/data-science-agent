from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from dsa_evaluation.baselines import run_llm_only_baseline, run_llm_tools_baseline
from dsa_evaluation.catalog import BenchmarkTask


class _FakeProvider:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        self.prompts.append(prompt)
        return "Grounded baseline answer"

    async def structured_output(self, prompt: str, schema: type, **kwargs: Any) -> Any:
        self.prompts.append(prompt)
        return schema.model_validate(
            {
                "rationale": "Count rows with one direct query.",
                "calls": [
                    {
                        "tool": "run_sql",
                        "input": {"sql": "SELECT COUNT(*) AS n FROM dataset"},
                    }
                ],
            }
        )


def _task(dataset_name: str) -> BenchmarkTask:
    return BenchmarkTask(
        id="baseline-01",
        category="SQL",
        dataset=dataset_name,
        question="How many rows are in the dataset?",
        expected_analysis="Count rows",
    )


def test_llm_only_baseline_has_no_tool_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "sample.csv"
    dataset.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    provider = _FakeProvider()
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: provider)
    monkeypatch.setenv("DSA_BASELINE_PREVIEW_ROWS", "1")

    result = asyncio.run(run_llm_only_baseline(_task(dataset.name), dataset))

    assert result["state"]["tool_calls"] == []
    assert result["baseline"]["tool_access"] is False
    assert result["baseline"]["dataset_context"]["preview_row_count"] == 1
    assert result["baseline"]["dataset_context"]["preview_truncated"] is True
    assert result["report_markdown"] == "Grounded baseline answer"


def test_llm_tools_baseline_executes_selected_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = tmp_path / "sample.csv"
    dataset.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    provider = _FakeProvider()
    monkeypatch.setattr("dsa_llm.providers.auto_provider", lambda: provider)

    result = asyncio.run(run_llm_tools_baseline(_task(dataset.name), dataset))

    calls = result["state"]["tool_calls"]
    assert len(calls) == 1
    assert calls[0]["tool"] == "run_sql"
    assert calls[0]["status"] == "ok"
    assert calls[0]["input"]["dataset_path"] == str(dataset)
    assert calls[0]["output"]["row_count"] == 1
    assert result["baseline"]["tool_access"] is True
    assert result["baseline"]["plan"]["calls"][0]["tool"] == "run_sql"
