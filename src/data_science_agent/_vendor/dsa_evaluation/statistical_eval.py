from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

Dimension = Literal[
    "method_selection",
    "assumption_validation",
    "test_execution",
    "parameter_estimation",
    "p_value_correctness",
    "ci_correctness",
    "effect_size",
    "interpretation",
    "uncertainty_communication",
    "causal_language",
]

ErrorCode = Literal["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"]

ERROR_LABELS: dict[ErrorCode, str] = {
    "S01": "Wrong Test",
    "S02": "Missing Assumption Check",
    "S03": "Incorrect Statistic",
    "S04": "Incorrect P-value",
    "S05": "Incorrect Confidence Interval",
    "S06": "Incorrect Effect Size",
    "S07": "Multiple Testing Error",
    "S08": "Misinterpretation",
    "S09": "Causal Overclaim",
    "S10": "Uncertainty Omission",
}

_CAUSAL_RE = re.compile(
    r"\b(causes?|caused by|leads to|impact(?:s|ed)?|effect(?:s)?|drives?|results in|due to)\b",
    re.IGNORECASE,
)
_UNCERTAINTY_RE = re.compile(
    r"\b(confidence interval|forecast interval|uncertainty|limitation|sampling (?:error|uncertainty)|model uncertainty)\b",
    re.IGNORECASE,
)


class DimensionScore(BaseModel):
    dimension: Dimension
    score: float | None = None  # 0..1, None = not applicable
    passed: bool | None = None
    reason: str = ""
    error_codes: list[ErrorCode] = Field(default_factory=list)


class StatisticalEvaluation(BaseModel):
    task_id: str
    dimensions: dict[Dimension, DimensionScore] = Field(default_factory=dict)
    error_codes: list[ErrorCode] = Field(default_factory=list)
    overall: float | None = None  # mean of applicable dimensions
    causal_flag: bool = False
    uncertainty_flag: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


def evaluate_statistical(
    task: Any,
    run_result: dict[str, Any] | None,
    elapsed_ms: int = 0,
) -> StatisticalEvaluation:
    task_id = getattr(task, "id", "unknown")
    criteria = getattr(task, "criteria", None)
    statistical_required = (
        bool(getattr(criteria, "statistical_accuracy", False)) if criteria else False
    )

    tcalls: list[dict[str, Any]] = []
    insights: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    report_md: str = ""
    if isinstance(run_result, dict):
        state = run_result.get("state") or run_result
        if isinstance(state, dict):
            tcalls = state.get("tool_calls") or run_result.get("tool_calls") or []
            if not isinstance(tcalls, list):
                tcalls = []
            evidence = state.get("evidence") or []
            insights = state.get("insights") or []
            report_md = state.get("report_markdown") or run_result.get("report_markdown") or ""
            if not isinstance(report_md, str):
                report_md = str(report_md)
        tcalls = [c for c in tcalls if isinstance(c, dict)]

    # Collect tool outputs for inspection
    tool_names = [c.get("tool", "") for c in tcalls]
    statuses = [c.get("status", "") for c in tcalls]
    has_ok = any(s == "ok" for s in statuses)

    def _score(
        d: Dimension, passed: bool | None, reason: str, codes: list[ErrorCode] | None = None
    ) -> DimensionScore:
        sc = 1.0 if passed is True else (0.0 if passed is False else None)
        return DimensionScore(
            dimension=d, score=sc, passed=passed, reason=reason, error_codes=codes or []
        )

    dims: dict[Dimension, DimensionScore] = {}

    # 1. Method selection: if statistical_accuracy required, tool should be correlation/hypothesis/regression/causal
    if statistical_required:
        stats_tools = {
            "correlation_analysis",
            "hypothesis_test",
            "regression_analysis",
            "causal_check",
            "assumption_check",
        }
        used_stats = any(t in stats_tools for t in tool_names)
        dims["method_selection"] = _score(
            "method_selection",
            used_stats and has_ok,
            "used stats tool" if used_stats else "no statistical tool",
            [] if used_stats else ["S01"],
        )
    else:
        dims["method_selection"] = _score("method_selection", None, "not applicable for this task")

    # 2. Assumption validation: did an assumption_check or validator run, or are limitations noted?
    assump_tool = "assumption_check" in tool_names
    has_assumptions = any(
        (c.get("output") or {}).get("assumptions")
        for c in tcalls
        if isinstance(c.get("output"), dict)
    )
    dims["assumption_validation"] = _score(
        "assumption_validation",
        True if (assump_tool or has_assumptions or not statistical_required) else False,
        "assumption evidence present"
        if (assump_tool or has_assumptions)
        else "missing assumption check",
        [] if (assump_tool or has_assumptions or not statistical_required) else ["S02"],
    )

    # 3. Test execution: at least one ok tool
    dims["test_execution"] = _score(
        "test_execution",
        has_ok if statistical_required else (has_ok if tcalls else None),
        "ok" if has_ok else "no ok tool call",
        [] if has_ok else (["S03"] if statistical_required else []),
    )

    # 4. Parameter estimation: tool output has numeric params (r/statistic/coef etc.)
    has_params = any(
        isinstance(c.get("output"), dict)
        and any(
            k in c["output"]
            for k in ("r", "statistic", "coef", "coefficients", "accuracy", "r2", "mae")
        )
        for c in tcalls
    )
    dims["parameter_estimation"] = _score(
        "parameter_estimation",
        True if (has_params or not statistical_required) else False,
        "params present" if has_params else "no parameter estimate",
        [] if (has_params or not statistical_required) else ["S03"],
    )

    # 5. P-value correctness: p_value in [0,1] if present
    pvals: list[float] = []
    for c in tcalls:
        out = c.get("output") or {}
        if isinstance(out, dict) and isinstance(out.get("p_value"), (int, float)):
            pvals.append(float(out["p_value"]))
    p_ok: bool | None = None
    if pvals:
        p_ok = all(0 <= v <= 1 for v in pvals)
    else:
        p_ok = None if not statistical_required else None
    dims["p_value_correctness"] = _score(
        "p_value_correctness",
        p_ok,
        "p in [0,1]" if p_ok is True else ("p out of range" if p_ok is False else "no p_value"),
        [] if p_ok is not False else ["S04"],
    )

    # 6. CI correctness: ci_low <= ci_high and finite if present
    ci_ok: bool | None = None
    ci_pairs: list[tuple[float, float]] = []
    for c in tcalls:
        out = c.get("output") or {}
        if (
            isinstance(out, dict)
            and out.get("ci_low") is not None
            and out.get("ci_high") is not None
        ):
            try:
                ci_pairs.append((float(out["ci_low"]), float(out["ci_high"])))
            except Exception:
                pass
    if ci_pairs:
        ci_ok = all(lo <= hi and abs(lo) < 1e12 and abs(hi) < 1e12 for lo, hi in ci_pairs)
    else:
        ci_ok = None
    dims["ci_correctness"] = _score(
        "ci_correctness",
        ci_ok,
        "ci valid" if ci_ok is True else ("ci invalid" if ci_ok is False else "no CI emitted"),
        [] if ci_ok is not False else ["S05"],
    )

    # 7. Effect size: at least one tool reports effect_size / r2 / cohen_d etc.
    has_effect = any(
        isinstance(c.get("output"), dict)
        and any(k in c["output"] for k in ("effect_size", "r", "r2", "cohen_d", "cramers_v"))
        for c in tcalls
    )
    dims["effect_size"] = _score(
        "effect_size",
        True if (has_effect or not statistical_required) else False,
        "effect present" if has_effect else "no effect size",
        [] if (has_effect or not statistical_required) else ["S06"],
    )

    # 8. Interpretation: unsupported_claim check (reuses critic)
    try:
        from dsa_agent.critic import check_unsupported_claims

        seq: list[object] = []
        for ins in insights or []:
            if isinstance(ins, dict):
                seq.append(type("O", (), {"finding": ins.get("finding", "")})())
            else:
                seq.append(ins)
        cres = check_unsupported_claims(seq)
        interp_pass = bool(cres.passed)
        dims["interpretation"] = _score(
            "interpretation", interp_pass, cres.message, [] if interp_pass else ["S08"]
        )
    except Exception:
        dims["interpretation"] = _score("interpretation", None, "critic unavailable")

    # 9. Causal language audit §24
    texts: list[str] = []
    for ins in insights:
        if isinstance(ins, dict):
            texts.append(str(ins.get("finding", "")))
        else:
            texts.append(str(getattr(ins, "finding", "")))
    if report_md:
        texts.append(report_md)
    joined = "\n".join(texts)
    causal_flag = bool(_CAUSAL_RE.search(joined))
    # If causal language present without causal tool, flag S09
    has_causal_tool = "causal_check" in tool_names
    causal_pass: bool | None = None
    if causal_flag:
        causal_pass = bool(has_causal_tool)
    else:
        causal_pass = True
    dims["causal_language"] = _score(
        "causal_language",
        causal_pass,
        "causal without evidence" if causal_flag and not has_causal_tool else "no overclaim",
        ["S09"] if causal_flag and not has_causal_tool else [],
    )

    # 10. Uncertainty communication §25
    uncertainty_flag = bool(_UNCERTAINTY_RE.search(joined))
    # Also evidence: tool emitted ci_low/ci_high or limitations
    has_uncertainty_evidence = bool(ci_pairs) or any(
        isinstance(c.get("output"), dict) and c["output"].get("limitations") for c in tcalls
    )
    unc_pass: bool | None = (
        True
        if (uncertainty_flag or has_uncertainty_evidence or not statistical_required)
        else False
    )
    dims["uncertainty_communication"] = _score(
        "uncertainty_communication",
        unc_pass,
        "uncertainty present"
        if (uncertainty_flag or has_uncertainty_evidence)
        else "uncertainty omitted",
        []
        if (uncertainty_flag or has_uncertainty_evidence or not statistical_required)
        else ["S10"],
    )

    # Aggregate: collect error codes
    all_codes: list[ErrorCode] = []
    for d in dims.values():
        all_codes.extend(d.error_codes)
    # S07 multiple testing heuristic: if task mentions Bonferroni / FDR without tool handling, not checked deeply — only flag if question says "multiple testing" and no correction emitted
    q = str(getattr(task, "question", "") or "")
    if re.search(r"multiple testing|bonferroni|FDR|false discovery", q, re.IGNORECASE):
        has_correction = any("bonferroni" in str(c.get("output") or "").lower() for c in tcalls)
        if not has_correction:
            all_codes.append("S07")
            prev = dims.get("interpretation")
            if prev and "S07" not in prev.error_codes:
                prev.error_codes.append("S07")

    applicable = [d.score for d in dims.values() if d.score is not None]
    overall = round(sum(applicable) / len(applicable), 4) if applicable else None

    return StatisticalEvaluation(
        task_id=str(task_id),
        dimensions=dims,
        error_codes=sorted(set(all_codes)),
        overall=overall,
        causal_flag=causal_flag,
        uncertainty_flag=uncertainty_flag,
        details={"elapsed_ms": elapsed_ms, "tool_names": tool_names},
    )
