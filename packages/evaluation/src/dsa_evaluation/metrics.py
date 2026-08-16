from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskMetrics(BaseModel):
    task_success: bool = False
    statistical_accuracy: bool | None = None
    sql_accuracy: bool | None = None
    code_execution_success: bool | None = None
    evidence_coverage: bool | None = None
    unsupported_claim: bool | None = None  # False = good (no unsupported claim)
    latency_ms: int = 0


class EvaluationResult(BaseModel):
    task_id: str
    category: str
    dataset: str
    question: str
    metrics: TaskMetrics
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


def _approx_equal(a: float, b: float, tol: float | None) -> bool:
    if tol is None:
        tol = 0.05
    return abs(a - b) <= abs(tol * max(1, abs(b))) + 1e-9


def evaluate_task(
    task: Any,  # BenchmarkTask
    run_result: dict[str, Any] | None,
    elapsed_ms: int = 0,
) -> EvaluationResult:
    """Pure evaluation given a task and the agent's run_result (state dict or summary)."""
    gt = task.ground_truth
    criteria = task.criteria
    metrics = TaskMetrics(latency_ms=elapsed_ms)
    details: dict[str, Any] = {}
    error: str | None = None

    if run_result is None:
        metrics.task_success = False
        error = "No run result"
        return EvaluationResult(
            task_id=task.id,
            category=task.category,
            dataset=task.dataset,
            question=task.question,
            metrics=metrics,
            details=details,
            error=error,
        )

    # Task success: at least one tool succeeded and report exists
    tcalls = run_result.get("tool_calls") or run_result.get("toolCalls") or []
    # run_result may be state dict or orm-to_dict wrapper
    state = run_result.get("state") or run_result
    if isinstance(state, dict):
        tcalls = state.get("tool_calls", tcalls)
        evidence = state.get("evidence", [])
        insights = state.get("insights", [])
        validation = state.get("validation_results", [])
        status = state.get("status") or run_result.get("status")
    else:
        evidence, insights, validation, status = [], [], [], None

    has_ok = any((c.get("status") == "ok") for c in tcalls) if isinstance(tcalls, list) else False
    has_report = bool(
        (state.get("report_markdown") if isinstance(state, dict) else None)
        or run_result.get("report_markdown")
    )
    metrics.task_success = bool(has_ok and (has_report or tcalls))
    metrics.code_execution_success = has_ok

    # Evidence coverage
    if criteria.evidence_coverage:
        # every insight should have evidence
        if isinstance(insights, list) and insights:
            metrics.evidence_coverage = all(bool(i.get("evidence_ids")) for i in insights)
        else:
            # fallback: at least one evidence if insights expected
            metrics.evidence_coverage = bool(evidence)
        details["evidence_count"] = len(evidence) if isinstance(evidence, list) else 0
    else:
        metrics.evidence_coverage = None

    # Unsupported claim: check insights for causal words without evidence
    try:
        from dsa_agent.critic import check_unsupported_claims

        # adapt insights to sequence
        seq = []
        for ins in insights or []:
            if isinstance(ins, dict):
                seq.append(type("O", (), {"finding": ins.get("finding", "")})())
            else:
                seq.append(ins)
        cres = check_unsupported_claims(seq)
        metrics.unsupported_claim = not cres.passed
        details["unsupported_claim_check"] = cres.message
    except Exception:
        metrics.unsupported_claim = None

    if criteria.statistical_accuracy:
        if gt.expected_value is None:
            # No ground truth value — treat execution as success, don't penalize accuracy
            metrics.statistical_accuracy = None
        else:
            found: float | None = None
            for c in tcalls if isinstance(tcalls, list) else []:
                out = c.get("output") or {}
                if isinstance(out, dict):
                    for key in ("r", "p_value", "statistic", "accuracy", "r2", "mae"):
                        if key in out and isinstance(out[key], (int, float)):
                            found = float(out[key])
                            break
                    if found is not None:
                        break
            if found is None:
                for ev in evidence if isinstance(evidence, list) else []:
                    res = ev.get("result") or {}
                    for key in ("r", "p_value", "metric"):
                        if key in res and isinstance(res[key], (int, float)):
                            found = float(res[key])
                            break
            if found is not None:
                try:
                    ev2 = float(gt.expected_value)
                    metrics.statistical_accuracy = _approx_equal(found, ev2, gt.tolerance)
                    details["found_value"] = found
                    details["expected_value"] = ev2
                except Exception:
                    metrics.statistical_accuracy = None
            else:
                metrics.statistical_accuracy = None
                details["expected_value"] = gt.expected_value
    else:
        metrics.statistical_accuracy = None

    # SQL accuracy: check sql_contains (empty sql_contains means any successful run_sql suffices when sql_accuracy required)
    if criteria.sql_accuracy:
        if gt.sql_contains:
            sql_texts = []
            for c in tcalls if isinstance(tcalls, list) else []:
                if c.get("tool") == "run_sql":
                    inp = c.get("input") or {}
                    sql_texts.append((inp.get("sql") or "").upper())
            need = [s.upper() for s in gt.sql_contains]
            metrics.sql_accuracy = (
                all(any(n in t for t in sql_texts) for n in need) if sql_texts else False
            )
            details["sql_contains"] = gt.sql_contains
        else:
            # sql_accuracy requested but no explicit fragments: pass if any run_sql succeeded
            has_sql_ok = any(
                c.get("tool") == "run_sql" and c.get("status") == "ok"
                for c in (tcalls if isinstance(tcalls, list) else [])
            )
            metrics.sql_accuracy = bool(has_sql_ok)
            details["sql_contains"] = []
    else:
        metrics.sql_accuracy = None

    # Visualization check
    if criteria.visualization:
        has_chart = any(
            c.get("tool") == "create_chart" and c.get("status") == "ok"
            for c in (tcalls if isinstance(tcalls, list) else [])
        )
        metrics.task_success = (
            metrics.task_success and has_chart if gt.chart_type else metrics.task_success
        )
        details["has_chart"] = has_chart

    return EvaluationResult(
        task_id=task.id,
        category=task.category,
        dataset=task.dataset,
        question=task.question,
        metrics=metrics,
        details=details,
        error=error,
    )


def aggregate_metrics(results: list[EvaluationResult]) -> dict[str, Any]:
    n = len(results)
    if n == 0:
        return {}

    def _avg(key: str) -> float | None:
        vals = [getattr(r.metrics, key) for r in results if getattr(r.metrics, key) is not None]
        if not vals:
            return None
        return sum(1 for v in vals if v) / len(vals)

    def _mean_latency() -> float:
        return sum(r.metrics.latency_ms for r in results) / n

    by_cat: dict[str, list[EvaluationResult]] = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    return {
        "n": n,
        "task_success_rate": _avg("task_success"),
        "statistical_accuracy": _avg("statistical_accuracy"),
        "sql_accuracy": _avg("sql_accuracy"),
        "code_execution_success": _avg("code_execution_success"),
        "evidence_coverage": _avg("evidence_coverage"),
        "unsupported_claim_rate": _avg("unsupported_claim"),
        "mean_latency_ms": _mean_latency(),
        "by_category": {
            k: {"n": len(v), "task_success": sum(1 for x in v if x.metrics.task_success) / len(v)}
            for k, v in by_cat.items()
        },
    }
