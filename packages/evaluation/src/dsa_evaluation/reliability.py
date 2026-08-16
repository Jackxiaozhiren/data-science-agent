from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

Config = Literal["single", "planner", "planner_critic", "full"]


class ReliabilityReport(BaseModel):
    """W5 Agent Reliability (§26–30).

    Metrics: Task Success / Statistical Correctness / Unsupported Claim / Evidence Coverage
             / Tool Efficiency / Recovery Success / Reproducibility (via L5)
             + §28 Critic Effectiveness + §29 Tool Selection Quality + §30 Loop Quality.
    """

    config: Config
    label: str
    n: int = 0
    task_success: float | None = None
    statistical_correctness: float | None = None
    unsupported_claim_rate: float | None = None
    evidence_coverage: float | None = None
    tool_correctness: float | None = None
    tool_selection_accuracy: float | None = None
    tool_efficiency: float | None = None  # 1 - duplicate rate
    recovery_success: float | None = None
    reproducibility: float | None = None
    latency_ms: float | None = None

    # §28
    critic_errors_detected: int = 0
    critic_corrections: int = 0
    critic_false_positives: int = 0
    critic_false_negatives: int = 0
    critic_correction_success: float | None = None
    critic_latency_ms: float | None = None
    critic_benefit: float | None = None  # quality_gain / additional_cost

    # §29
    tool_correct: int = 0
    tool_unnecessary: int = 0
    tool_wrong: int = 0
    tool_missing: int = 0

    # §30
    duplicate_calls: int = 0
    oscillation: int = 0
    repeated_failures: int = 0
    unnecessary_retries: int = 0
    premature_termination: int = 0
    over_analysis: int = 0
    agent_efficiency: float | None = None

    details: dict[str, Any] = Field(default_factory=dict)


_TOOL_ALIAS = {
    "run_sql": "run_sql",
    "run_python": "run_python",
    "correlation_analysis": "correlation",
    "correlation": "correlation",
    "hypothesis_test": "hypothesis",
    "regression_analysis": "regression",
    "train_model": "ml",
    "forecast": "forecast",
    "create_chart": "visualization",
    "profile_dataset": "profile",
}

_REQUIRED_BY_CATEGORY: dict[str, set[str]] = {
    "SQL": {"run_sql"},
    "Statistics": {"correlation", "hypothesis"},
    "Regression": {"regression"},
    "Classification": {"ml"},
    "Time Series": {"forecast"},
    "Visualization": {"visualization"},
    "Evidence Validation": set(),
}


def _tool_selection_quality(
    tool_names: list[str], category: str
) -> tuple[float | None, dict[str, int]]:
    if not tool_names:
        return None, {"correct": 0, "unnecessary": 0, "wrong": 0, "missing": 0}
    normalized = [_TOOL_ALIAS.get(t, t) for t in tool_names]
    required = _REQUIRED_BY_CATEGORY.get(category, set())
    # Heuristic: correct = required tool present; wrong = stats tool on non-stats without need
    has_required = bool(required & set(normalized)) if required else any("profile" in n or "run_sql" in n for n in tool_names)
    correct = 1 if has_required else 0
    unnecessary = max(0, len(tool_names) - (3 if category in ("Evidence Validation", "EDA") else 2))
    wrong = 0
    if category == "SQL" and not any("run_sql" in t for t in tool_names):
        wrong = 1
    missing = 0 if has_required else 1
    acc = 1.0 if has_required and wrong == 0 else 0.0
    return acc, {"correct": correct, "unnecessary": unnecessary, "wrong": wrong, "missing": missing}


def _loop_quality(tool_calls: list[dict[str, Any]]) -> dict[str, Any]:
    names = [c.get("tool", "") for c in tool_calls if isinstance(c, dict)]
    # duplicate consecutive
    dups = sum(1 for i in range(1, len(names)) if names[i] == names[i - 1])
    # oscillation: A-B-A pattern
    osc = sum(1 for i in range(2, len(names)) if names[i] == names[i - 2] and names[i] != names[i - 1])
    # repeated failures: same tool failed twice
    failed = [c.get("tool") for c in tool_calls if c.get("status") == "error"]
    rep_fail = len(failed) - len(set(failed)) if failed else 0
    # over-analysis: >6 tool calls when category is EDA/Data Quality
    over = 1 if len(names) > 6 else 0
    # unnecessary retries heuristic: retries when no error
    has_error = any(c.get("status") == "error" for c in tool_calls)
    unnecessary_retries = 0 if has_error else (1 if len(names) > 4 else 0)
    # efficiency: 1 - dups/len
    eff = round(1 - dups / max(1, len(names)), 3) if names else None
    return {
        "duplicate_calls": dups,
        "oscillation": osc,
        "repeated_failures": rep_fail,
        "unnecessary_retries": unnecessary_retries,
        "premature_termination": 0,
        "over_analysis": over,
        "agent_efficiency": eff,
    }


def evaluate_reliability(
    config: Config,
    results: list[Any],
    raw_runs: list[dict[str, Any]] | None = None,
    supports_repro: bool = True,
) -> ReliabilityReport:
    """Build W5 reliability from evaluator results + raw runs.

    - results: list[EvaluationResult] (with details.statistical_eval if available)
    - raw_runs: raw benchmark raw_runs entries (for loop/critic/tool signals)
    """
    n = len(results)
    if n == 0:
        return ReliabilityReport(config=config, label=config, n=0)

    def _avg(key: str) -> float | None:
        vals = [getattr(r.metrics, key, None) for r in results if getattr(r.metrics, key, None) is not None]
        return round(sum(1 for v in vals if v) / len(vals), 4) if vals else None

    # From evaluator metrics
    task_success = _avg("task_success")
    code_ok = _avg("code_execution_success")
    evidence_cov = _avg("evidence_coverage")
    unsupported = _avg("unsupported_claim")
    # statistical from evaluator_v2 overall if present
    stat_vals: list[float] = []
    for r in results:
        det = getattr(r, "details", {}) or {}
        se = det.get("statistical_eval") or {}
        ov = se.get("overall")
        if isinstance(ov, (int, float)):
            stat_vals.append(float(ov))
    statistical_correctness = round(sum(stat_vals) / len(stat_vals), 4) if stat_vals else None

    # Tool selection & loop from raw_runs
    loop_acc: list[dict[str, Any]] = []
    sel_acc_vals: list[float] = []
    dup_total = 0
    osc_total = 0
    rep_fail_total = 0
    over_total = 0
    tool_eff_vals: list[float] = []
    correct_t = unnecessary_t = wrong_t = missing_t = 0

    if raw_runs:
        for rr, r in zip(raw_runs, results):
            tcalls = (rr.get("run_result") or {}).get("tool_calls") or []
            if not isinstance(tcalls, list):
                tcalls = []
            tool_names = [c.get("tool", "") for c in tcalls if isinstance(c, dict)]
            cat = getattr(r, "category", "EDA")
            acc, counts = _tool_selection_quality(tool_names, cat)
            if acc is not None:
                sel_acc_vals.append(acc)
            correct_t += counts["correct"]
            unnecessary_t += counts["unnecessary"]
            wrong_t += counts["wrong"]
            missing_t += counts["missing"]
            lq = _loop_quality(tcalls)
            loop_acc.append(lq)
            dup_total += lq["duplicate_calls"]
            osc_total += lq["oscillation"]
            rep_fail_total += lq["repeated_failures"]
            over_total += lq["over_analysis"]
            if lq["agent_efficiency"] is not None:
                tool_eff_vals.append(float(lq["agent_efficiency"]))

    tool_selection_accuracy = round(sum(sel_acc_vals) / len(sel_acc_vals), 4) if sel_acc_vals else None
    tool_efficiency = round(sum(tool_eff_vals) / len(tool_eff_vals), 4) if tool_eff_vals else None
    agent_efficiency = tool_efficiency

    # §28 Critic: count validation_results failures vs corrections
    critic_detected = 0
    critic_corrections = 0
    if raw_runs:
        for rr in raw_runs:
            rr_state = (rr.get("run_result") or {})
            vres = rr_state.get("validation_results") or []
            for v in vres if isinstance(vres, list) else []:
                if isinstance(v, dict) and v.get("passed") is False:
                    critic_detected += 1
                    if v.get("check") in ("unsupported_claim", "evidence_coverage"):
                        critic_corrections += 1

    critic_correction_success = None
    if critic_detected:
        critic_correction_success = round(critic_corrections / max(1, critic_detected), 4)
    critic_benefit = None
    # quality improvement proxy: evidence_coverage gain if critic present
    if config in ("planner_critic", "full") and evidence_cov is not None:
        quality_gain = evidence_cov
        additional_cost = 0.15  # heuristic: critic adds ~15% latency/cost
        critic_benefit = round(quality_gain / additional_cost, 3) if additional_cost else None

    # Recovery: successful after retry (retry_count >0 and final ok)
    recovery_vals: list[bool] = []
    if raw_runs:
        for rr in raw_runs:
            rr_state = rr.get("run_result") or {}
            rc = rr_state.get("retry_count") or 0
            tcalls = rr_state.get("tool_calls") or []
            has_ok = any(c.get("status") == "ok" for c in tcalls if isinstance(c, dict))
            if rc and rc > 0:
                recovery_vals.append(bool(has_ok))
    recovery_success = round(sum(1 for v in recovery_vals if v) / len(recovery_vals), 4) if recovery_vals else None

    latency_vals = [getattr(r.metrics, "latency_ms", 0) for r in results if hasattr(r.metrics, "latency_ms")]
    latency_ms = round(sum(latency_vals) / len(latency_vals), 2) if latency_vals else None

    # Reproducibility proxy: tool_efficiency as stability signal
    reproducibility = tool_efficiency

    label_map = {"single": "Single Agent", "planner": "Planner + Agent", "planner_critic": "Planner + Agent + Critic", "full": "Full Evidence-Grounded Agent"}

    return ReliabilityReport(
        config=config,
        label=label_map.get(config, config),
        n=n,
        task_success=task_success,
        statistical_correctness=statistical_correctness,
        unsupported_claim_rate=unsupported,
        evidence_coverage=evidence_cov,
        tool_correctness=code_ok,
        tool_selection_accuracy=tool_selection_accuracy,
        tool_efficiency=tool_efficiency,
        recovery_success=recovery_success,
        reproducibility=reproducibility,
        latency_ms=latency_ms,
        critic_errors_detected=critic_detected,
        critic_corrections=critic_corrections,
        critic_false_positives=0,
        critic_false_negatives=0,
        critic_correction_success=critic_correction_success,
        critic_benefit=critic_benefit,
        tool_correct=correct_t,
        tool_unnecessary=unnecessary_t,
        tool_wrong=wrong_t,
        tool_missing=missing_t,
        duplicate_calls=dup_total,
        oscillation=osc_total,
        repeated_failures=rep_fail_total,
        unnecessary_retries=0,
        premature_termination=0,
        over_analysis=over_total,
        agent_efficiency=agent_efficiency,
        details={"by_config": config},
    )


_RE_LABEL = re.compile(r"(cause|association|evidence|covariance)", re.IGNORECASE)
