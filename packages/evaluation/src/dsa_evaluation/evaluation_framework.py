from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from dsa_evaluation.metrics import EvaluationResult


class EvaluationResultV2(BaseModel):
    """V2 evaluation — 10-dim + latency/token split (V2 spec §9–13)."""

    task_id: str
    run_id: str = ""
    category: str = ""
    difficulty: Literal["easy", "medium", "hard", "expert"] = "medium"
    task_success: float = 0.0
    statistical_correctness: float | None = None
    tool_correctness: float | None = None
    evidence_coverage: float | None = None
    unsupported_claim_rate: float | None = None
    code_execution_rate: float | None = None
    sql_correctness: float | None = None
    reproducibility_score: float | None = None
    safety_score: float | None = None
    # V2 §34–38 telemetry
    latency_ms: int = 0
    planning_latency_ms: int | None = None
    tool_latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    # 6-level breakdown (§18)
    level_scores: dict[str, float | None] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    passed: bool = False


def from_metrics(
    m: EvaluationResult, run_id: str = "", difficulty: str = "medium"
) -> EvaluationResultV2:
    ev = m.metrics.evidence_coverage
    unsupported = m.metrics.unsupported_claim
    return EvaluationResultV2(
        task_id=m.task_id,
        run_id=run_id,
        category=m.category,
        difficulty=difficulty,  # type: ignore[arg-type]
        task_success=float(m.metrics.task_success),
        statistical_correctness=float(m.metrics.statistical_accuracy)
        if m.metrics.statistical_accuracy is not None
        else None,
        tool_correctness=float(m.metrics.code_execution_success)
        if m.metrics.code_execution_success is not None
        else None,
        evidence_coverage=float(ev) if ev is not None else None,
        unsupported_claim_rate=(1.0 - float(unsupported))
        if unsupported is not None
        else None,  # inverted to rate
        code_execution_rate=float(m.metrics.code_execution_success)
        if m.metrics.code_execution_success is not None
        else None,
        sql_correctness=float(m.metrics.sql_accuracy)
        if m.metrics.sql_accuracy is not None
        else None,
        latency_ms=m.metrics.latency_ms,
        details=dict(m.details),
        passed=bool(m.metrics.task_success),
        level_scores={
            "tool_execution": float(m.metrics.code_execution_success)
            if m.metrics.code_execution_success is not None
            else None,
            "numerical": float(m.metrics.statistical_accuracy)
            if m.metrics.statistical_accuracy is not None
            else None,
            "sql": float(m.metrics.sql_accuracy) if m.metrics.sql_accuracy is not None else None,
            "evidence": float(ev) if ev is not None else None,
        },
    )


def aggregate_v2(results: list[EvaluationResultV2]) -> dict[str, Any]:
    if not results:
        return {}
    n = len(results)

    def _mean(key: str) -> float | None:
        vals = [getattr(r, key) for r in results if getattr(r, key) is not None]
        return (sum(vals) / len(vals)) if vals else None

    by_cat: dict[str, list[EvaluationResultV2]] = {}
    for r in results:
        by_cat.setdefault(r.category or "unknown", []).append(r)
    by_diff: dict[str, list[EvaluationResultV2]] = {}
    for r in results:
        by_diff.setdefault(r.difficulty, []).append(r)
    return {
        "n": n,
        "task_success_rate": _mean("task_success"),
        "statistical_correctness": _mean("statistical_correctness"),
        "tool_correctness": _mean("tool_correctness"),
        "evidence_coverage": _mean("evidence_coverage"),
        "unsupported_claim_rate": _mean("unsupported_claim_rate"),
        "code_execution_rate": _mean("code_execution_rate"),
        "sql_correctness": _mean("sql_correctness"),
        "mean_latency_ms": sum(r.latency_ms for r in results) / n,
        "by_category": {
            k: {"n": len(v), "task_success": sum(x.task_success for x in v) / len(v)}
            for k, v in by_cat.items()
        },
        "by_difficulty": {
            k: {"n": len(v), "task_success": sum(x.task_success for x in v) / len(v)}
            for k, v in by_diff.items()
        },
    }
