from __future__ import annotations

import re
from collections.abc import Sequence

from dsa_agent.state import AnalysisState, ValidationResult

_CAUSAL_WORDS = re.compile(
    r"\b(cause[sd]?|caused by|impact(?:s|ed)?|effect(?: of)?|leads to|results in|due to|drives|driven by)\b",
    re.IGNORECASE,
)


def rewrite_unsupported_claim(text: str, has_causal_evidence: bool = False) -> str:
    if has_causal_evidence:
        return text
    if _CAUSAL_WORDS.search(text):
        rewritten = _CAUSAL_WORDS.sub("is associated with", text)
        return rewritten + " (Causal inference is not established.)"
    return text


def check_unsupported_claims(
    insights: Sequence[object], has_causal_evidence: bool = False
) -> ValidationResult:
    for ins in insights:
        text = getattr(ins, "finding", "") or str(ins)
        if _CAUSAL_WORDS.search(text) and not has_causal_evidence:
            return ValidationResult(
                check="unsupported_claim",
                passed=False,
                message="Causal language detected without causal evidence; rewrite as association.",
                details={"finding": text},
            )
    return ValidationResult(
        check="unsupported_claim", passed=True, message="No unsupported causal claims detected"
    )


def check_evidence_coverage(state: AnalysisState) -> ValidationResult:
    if not state.evidence:
        # allow if only profiling steps so far
        if state.status.value in ("UNDERSTANDING", "PLANNING", "DATA_PROFILING"):
            return ValidationResult(
                check="evidence_coverage", passed=True, message="Early stage, no evidence yet"
            )
        return ValidationResult(
            check="evidence_coverage", passed=False, message="No evidence collected", details={}
        )
    # every insight should have at least one evidence
    for ins in state.insights:
        if not ins.evidence_ids:
            return ValidationResult(
                check="evidence_coverage",
                passed=False,
                message=f"Insight {ins.id} has no evidence",
                details={"insight_id": ins.id},
            )
    return ValidationResult(check="evidence_coverage", passed=True, message="Evidence coverage ok")


def critic_validate(state: AnalysisState) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    results.append(check_evidence_coverage(state))
    results.append(check_unsupported_claims(state.insights, has_causal_evidence=False))

    # statistical sanity: if any tool call errored, flag
    errors = [tc for tc in state.tool_calls if tc.status == "error"]
    if errors and state.status.value not in ("FAILED", "HUMAN_REVIEW"):
        results.append(
            ValidationResult(
                check="tool_errors",
                passed=False,
                message=f"{len(errors)} tool error(s)",
                details={"errors": [e.error for e in errors[:3]]},
            )
        )
    else:
        results.append(ValidationResult(check="tool_errors", passed=True, message="No tool errors"))

    # budget guard
    if state.tool_call_count > state.budget.max_tool_calls:
        results.append(
            ValidationResult(check="budget", passed=False, message="Tool call budget exceeded")
        )
    else:
        results.append(ValidationResult(check="budget", passed=True, message="Budget ok"))

    return results


def should_retry(
    validation_results: list[ValidationResult], retry_count: int, max_retries: int = 3
) -> bool:
    failed = [
        r
        for r in validation_results
        if not r.passed and r.check in ("evidence_coverage", "tool_errors")
    ]
    return bool(failed) and retry_count < max_retries


def detect_prompt_injection(dataset_text: str) -> ValidationResult:
    # Dataset cells are UNTRUSTED DATA — flag injection-like payloads without blocking the run
    import dsa_execution.guardrails as _g

    if _g.contains_prompt_injection(dataset_text):
        return ValidationResult(
            check="prompt_injection",
            passed=False,
            message="Injection-like content detected in dataset; treated as untrusted data (not executed).",
            details={"snippet": dataset_text[:300]},
        )
    return ValidationResult(check="prompt_injection", passed=True, message="No injection detected")


def check_resource_limits(state: AnalysisState) -> ValidationResult:
    import dsa_execution.guardrails as _g

    violations = _g.check_resource_limits(
        tool_calls=state.tool_call_count,
        max_tool_calls=state.budget.max_tool_calls,
        max_tokens=state.budget.max_tokens,
    )
    if violations:
        return ValidationResult(
            check="resource_limits", passed=False, message="; ".join(violations)
        )
    return ValidationResult(check="resource_limits", passed=True, message="Within limits")


def correction_message(results: list[ValidationResult]) -> str:
    failed = [r for r in results if not r.passed]
    if not failed:
        return ""
    return "; ".join(f"{r.check}: {r.message}" for r in failed)
