from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from dsa_tools.base import BaseTool


class ValidateResultInput(BaseModel):
    claim: str
    result: dict[str, Any] = Field(default_factory=dict)
    check_type: Literal["evidence_coverage", "unsupported_claim", "completeness"] = "completeness"


class ValidateResultOutput(BaseModel):
    check: str
    passed: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidateResultTool(BaseTool[ValidateResultInput, ValidateResultOutput]):
    name = "validate_result"
    description = "Validate a claim/result for evidence coverage and unsupported claim guard"
    input_model = ValidateResultInput
    output_model = ValidateResultOutput

    async def execute(self, inp: ValidateResultInput) -> ValidateResultOutput:
        import re

        causal_pat = re.compile(r"\b(cause[sd]?|caused by|impact|effect of|leads to|results in|due to)\b", re.IGNORECASE)

        if inp.check_type == "unsupported_claim":
            if causal_pat.search(inp.claim):
                return ValidateResultOutput(check="unsupported_claim", passed=False, message="Causal language requires causal evidence; use association.", details={"claim": inp.claim})
            return ValidateResultOutput(check="unsupported_claim", passed=True, message="No unsupported causal language")

        if inp.check_type == "evidence_coverage":
            if not inp.result:
                return ValidateResultOutput(check="evidence_coverage", passed=False, message="Result is empty; no evidence to trace")
            return ValidateResultOutput(check="evidence_coverage", passed=True, message="Evidence present")

        # completeness: require both
        if not inp.result:
            return ValidateResultOutput(check="completeness", passed=False, message="Missing result for claim")
        if causal_pat.search(inp.claim):
            return ValidateResultOutput(check="completeness", passed=False, message="Causal claim without causal evidence")
        return ValidateResultOutput(check="completeness", passed=True, message="Validation passed")
