from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, Field

ModelClass = Literal["local_small", "local_medium", "open_api", "frontier"]


class ModelRecord(BaseModel):
    model_class: ModelClass
    model_id: str
    provider: str
    available: bool = True
    reason: str = ""
    task_success: float | None = None
    statistical_accuracy: float | None = None
    evidence_coverage: float | None = None
    unsupported_claim_rate: float | None = None
    tool_selection_accuracy: float | None = None
    latency_ms: float | None = None
    token_input: int | None = None
    token_output: int | None = None
    token_total: int | None = None
    cost_usd: float | None = None
    failure_rate: float | None = None
    n: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class CrossModelMatrix(BaseModel):
    records: list[ModelRecord] = Field(default_factory=list)
    frontier_quality_cost: list[dict[str, Any]] = Field(default_factory=list)
    frontier_quality_latency: list[dict[str, Any]] = Field(default_factory=list)
    frontier_quality_tokens: list[dict[str, Any]] = Field(default_factory=list)
    cost_model: str = "heuristic stub: cost not fabricated; see cost_usd_method"
    details: dict[str, Any] = Field(default_factory=dict)


def _pricing_stub(model_class: ModelClass, tokens_total: int | None) -> float | None:
    # Do not fabricate real vendor pricing; return None and note method.
    # If tokens_total known we return a tiny placeholder only to rank costs.
    if tokens_total is None:
        return None
    # heuristic ordering: local free, open small cost, frontier higher — placeholder only
    scale = {"local_small": 0.0, "local_medium": 0.0, "open_api": 0.002, "frontier": 0.01}.get(
        model_class, 0.0
    )
    return round(scale * (tokens_total / 1000), 6)


def _probe_provider(model_class: ModelClass) -> tuple[str, bool, str]:
    # §31 categories mapped to actual env
    if model_class == "local_small":
        provider = (
            "ollama/small"
            if os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_MODEL")
            else "stub/small"
        )
        # stub is always available (§34 local-first)
        return provider, True, "stub/local small — deterministic heuristics (no LLM)"
    if model_class == "local_medium":
        # Would be Ollama medium; fallback to stub for now
        provider = "ollama/medium" if os.getenv("OLLAMA_HOST") else "stub/medium"
        return provider, True, "stub/local medium — deterministic heuristics"
    if model_class == "open_api":
        has_key = bool(
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        provider = (
            "openai"
            if os.getenv("OPENAI_API_KEY")
            else ("anthropic" if os.getenv("ANTHROPIC_API_KEY") else "not_configured")
        )
        return (
            provider,
            has_key,
            "open_api — requires env key (not fabricated)"
            if has_key
            else "NOT RUN — no API key configured",
        )
    if model_class == "frontier":
        has_key = bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        provider = "frontier/" + (
            "openai"
            if os.getenv("OPENAI_API_KEY")
            else "anthropic"
            if os.getenv("ANTHROPIC_API_KEY")
            else "not_configured"
        )
        return (
            provider,
            has_key,
            "frontier — requires env key" if has_key else "NOT RUN — no frontier key",
        )
    return "unknown", False, "unknown class"


def build_cross_model_matrix(
    results_by_class: dict[str, dict[str, Any]] | None = None,
    token_estimates: dict[str, tuple[int, int]] | None = None,
) -> CrossModelMatrix:
    """Build §32 matrix + §33 frontier without fabricating model runs.

    - For classes without credentials, marks NOT RUN with reason; does not fabricate scores.
    - For available classes (local stub + any env-probed open/frontier with key), uses
      provided results_by_class or defaults to local stub measurements when run.
    - Token/cost are heuristic placeholders unless caller supplies real counts.
    """
    records: list[ModelRecord] = []
    for mc in ("local_small", "local_medium", "open_api", "frontier"):
        provider, available, reason = _probe_provider(mc)
        agg: dict[str, Any] | None = (results_by_class or {}).get(mc)
        # Derive metrics from agg if supplied else mark NOT RUN for non-local
        if agg is None:
            if mc in ("local_small", "local_medium"):
                # Local-first §34: stub is runnable — mark as NOT YET MEASURED if caller didn't supply
                records.append(
                    ModelRecord(
                        model_class=mc,
                        model_id=f"{mc}:stub",
                        provider=provider,
                        available=True,
                        reason="NOT RUN — run with local stub to populate (see §34)",
                        n=0,
                    )
                )
            else:
                records.append(
                    ModelRecord(
                        model_class=mc,
                        model_id=f"{mc}:not_run",
                        provider=provider,
                        available=False,
                        reason=reason,
                        n=0,
                        details={"policy": "§31: do not fabricate — requires env"},
                    )
                )
            continue

        token_in, token_out = (token_estimates or {}).get(mc, (None, None))
        total = (
            (token_in or 0) + (token_out or 0)
            if token_in is not None or token_out is not None
            else None
        )
        records.append(
            ModelRecord(
                model_class=mc,
                model_id=agg.get("model_id", f"{mc}:stub") or f"{mc}:stub",
                provider=provider,
                available=available,
                reason=reason if not available else (agg.get("reason") or reason),
                task_success=agg.get("task_success_rate"),
                statistical_accuracy=agg.get("statistical_accuracy"),
                evidence_coverage=agg.get("evidence_coverage"),
                unsupported_claim_rate=agg.get("unsupported_claim_rate"),
                tool_selection_accuracy=agg.get("tool_selection_accuracy"),
                latency_ms=agg.get("mean_latency_ms"),
                token_input=token_in,
                token_output=token_out,
                token_total=total,
                cost_usd=_pricing_stub(mc, total),
                failure_rate=(1 - float(agg.get("task_success_rate") or 0))
                if agg.get("task_success_rate") is not None
                else None,
                n=int(agg.get("n") or 0),
                details={
                    k: v
                    for k, v in agg.items()
                    if k
                    not in (
                        "task_success_rate",
                        "statistical_accuracy",
                        "evidence_coverage",
                        "unsupported_claim_rate",
                    )
                },
            )
        )

    # §33 frontier — rank by quality vs cost/latency/tokens (only for available records with numeric fields)
    def _frontier(key: str, label: str) -> list[dict[str, Any]]:
        pts = [
            r
            for r in records
            if r.task_success is not None and getattr(r, key) is not None and r.available
        ]
        if not pts:
            return []
        # Sort by key ascending, keep Pareto frontier (max quality for increasing cost)
        pts_sorted = sorted(pts, key=lambda r: getattr(r, key) or 0)
        frontier: list[dict[str, Any]] = []
        best = -1.0
        for r in pts_sorted:
            q = r.task_success or 0
            if q > best:
                best = q
                frontier.append(
                    {
                        label: getattr(r, key),
                        "quality": q,
                        "model": r.model_id,
                        "class": r.model_class,
                    }
                )
        return frontier

    return CrossModelMatrix(
        records=records,
        frontier_quality_cost=_frontier("cost_usd", "cost_usd"),
        frontier_quality_latency=_frontier("latency_ms", "latency_ms"),
        frontier_quality_tokens=_frontier("token_total", "token_total"),
        cost_model="stub heuristic: local 0, open_api 0.002/1k, frontier 0.01/1k — placeholder to demonstrate trade-off (§33); real costs require provider billing",
        details={
            "policy": "§31–34: provider-agnostic, no fabricated scores; local-first stub is runnable; open/frontier require env keys"
        },
    )
