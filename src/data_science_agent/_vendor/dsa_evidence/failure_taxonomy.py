from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FailureCode = Literal[
    "F01",
    "F02",
    "F03",
    "F04",
    "F05",
    "F06",
    "F07",
    "F08",
    "F09",
    "F10",
    "F11",
    "F12",
    "F13",
    "F14",
    "F15",
]

FAILURE_LABELS: dict[str, str] = {
    "F01": "Data Understanding Error",
    "F02": "Tool Selection Error",
    "F03": "SQL Error",
    "F04": "Python Error",
    "F05": "Statistical Method Error",
    "F06": "Numerical Error",
    "F07": "Model Error",
    "F08": "Interpretation Error",
    "F09": "Unsupported Claim",
    "F10": "Evidence Missing",
    "F11": "Security Error",
    "F12": "Reproducibility Error",
    "F13": "Agent Loop Error",
    "F14": "Prompt Injection",
    "F15": "Resource Budget Error",
}


class FailureLog(BaseModel):
    run_id: str
    failure_code: FailureCode
    agent: str = "data_scientist"
    node: str = "analysis"
    tool: str | None = None
    severity: Literal["low", "medium", "high"] = "medium"
    recoverable: bool = True
    recovery_attempts: int = 0
    resolved: bool = False
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


def classify_tool_error(tool: str, error: str) -> FailureCode:
    e = (error or "").lower()
    if "sql" in e or "duckdb" in e or "disallowed sql" in e:
        return "F03"
    if "import denied" in e or "sandbox" in e or "attribute denied" in e:
        return "F04"
    if "traversal" in e or "injection" in e or "untrusted" in e:
        return "F14"
    if "budget" in e or "too large" in e:
        return "F15"
    if "evidence" in e:
        return "F10"
    return "F04" if tool == "run_python" else ("F03" if tool == "run_sql" else "F02")


def from_validation_results(
    run_id: str, validation_results: list[dict[str, Any]]
) -> list[FailureLog]:
    out: list[FailureLog] = []
    for v in validation_results:
        if v.get("passed") is False:
            check = str(v.get("check", ""))
            code: FailureCode = (
                "F09"
                if "unsupported" in check
                else (
                    "F10"
                    if "evidence" in check or "insight_evidence" in check
                    else ("F03" if "sql" in check else "F08")
                )
            )
            out.append(
                FailureLog(
                    run_id=run_id,
                    failure_code=code,
                    message=str(v.get("message", "")),
                    severity="medium",
                )
            )
    return out
