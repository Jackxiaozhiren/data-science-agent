from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal[
    "EDA",
    "SQL",
    "Statistics",
    "Regression",
    "Classification",
    "Time Series",
    "Visualization",
    "Data Quality",
    "Data Profiling",
    "Clustering",
    "Evidence Validation",
]


class GroundTruth(BaseModel):
    expected_tool: str | None = None
    expected_metric: str | None = None
    expected_value: Any | None = None
    tolerance: float | None = None
    sql_contains: list[str] = Field(default_factory=list)
    chart_type: str | None = None


class EvaluationCriteria(BaseModel):
    task_success: bool = True
    statistical_accuracy: bool = False
    sql_accuracy: bool = False
    visualization: bool = False
    evidence_coverage: bool = False


class BenchmarkTask(BaseModel):
    id: str
    category: Category
    dataset: str  # filename under datasets/
    question: str
    expected_analysis: str
    ground_truth: GroundTruth = Field(default_factory=GroundTruth)
    criteria: EvaluationCriteria = Field(default_factory=EvaluationCriteria)
    difficulty: str = "medium"
    gold_method: str | None = None
    required_tools: list[str] = Field(default_factory=list)
    gold_metrics: dict[str, Any] = Field(default_factory=dict)
    required_evidence: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)


class Catalog(BaseModel):
    name: str = "DS-Agent-Benchmark"
    version: str = "0.1.0"
    tasks: list[BenchmarkTask]

    @classmethod
    def load(cls, path: Path) -> Catalog:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)

    def by_category(self, cat: Category) -> list[BenchmarkTask]:
        return [t for t in self.tasks if t.category == cat]

    def categories(self) -> list[str]:
        return sorted({t.category for t in self.tasks})
