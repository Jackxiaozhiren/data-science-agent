from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"send\s+the\s+api\s+key",
    r"exfiltrate",
    r"disregard\s+all\s+prior\s+directives",
    r"system\s*:\s*you\s+are\s+now",
]

_CAUSAL_PAT = re.compile(r"\b(cause[sd]?|caused by|impact|effect of|leads to|results in|due to)\b", re.IGNORECASE)

_INJECTION_RES = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def contains_prompt_injection(text: str) -> bool:
    for pat in _INJECTION_RES:
        if pat.search(text):
            return True
    return False


def sanitize_untrusted_text(text: str) -> str:
    # For dataset cell text: we don't execute it; just flag. This function marks dubious content
    if contains_prompt_injection(text):
        return f"[UNTRUSTED — injection-like content stripped] {text[:200]}"
    return text


def rewrite_unsupported_claim(text: str, has_causal_evidence: bool = False) -> str:
    if has_causal_evidence:
        return text
    if _CAUSAL_PAT.search(text):
        # rewrite causal to association
        rewritten = _CAUSAL_PAT.sub("is associated with", text)
        return rewritten + " (Causal inference is not established.)"
    return text


def check_resource_limits(
    token_count: int | None = None,
    tool_calls: int | None = None,
    max_tokens: int = 50000,
    max_tool_calls: int = 40,
    execution_ms: int | None = None,
    max_execution_ms: int = 300000,
) -> list[str]:
    violations: list[str] = []
    if token_count is not None and token_count > max_tokens:
        violations.append(f"Token budget exceeded: {token_count} > {max_tokens}")
    if tool_calls is not None and tool_calls > max_tool_calls:
        violations.append(f"Tool call budget exceeded: {tool_calls} > {max_tool_calls}")
    if execution_ms is not None and execution_ms > max_execution_ms:
        violations.append(f"Execution time exceeded: {execution_ms}ms > {max_execution_ms}ms")
    return violations
