from __future__ import annotations

import hashlib
import json
from statistics import fmean
from typing import Literal

from dsa_plugins.plugin import BasePlugin
from pydantic import BaseModel, Field


class MetricsInput(BaseModel):
    """Typed input accepted by the hello-world metrics tool."""

    values: list[float] = Field(min_length=1)


class EvidenceRecord(BaseModel):
    """Small provenance record returned beside the derived metric."""

    id: str
    claim: str
    source_type: Literal["arguments"] = "arguments"
    source_id: str
    result: dict[str, float | int | str]
    confidence: float = 1.0
    validation_status: Literal["validated"] = "validated"


class MetricsOutput(BaseModel):
    """Typed deterministic output from the example tool."""

    count: int
    mean: float
    evidence: EvidenceRecord


class HelloMetricsPlugin(BasePlugin):
    """Minimal offline plugin used by the contributor walkthrough."""

    name = "hello-metrics"
    version = "0.1.0"
    permissions = ["dataset.read", "process"]
    dependencies: list[str] = []

    def register_tools(self) -> list[str]:
        return ["metrics"]

    def metrics(self, values: list[float]) -> dict[str, object]:
        payload = MetricsInput(values=values)
        normalized = payload.values
        mean = float(fmean(normalized))
        canonical = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        evidence = EvidenceRecord(
            id=f"ev-{digest[:12]}",
            claim=f"Arithmetic mean of {len(normalized)} supplied values is {mean}.",
            source_id=f"sha256:{digest}",
            result={
                "operation": "arithmetic_mean",
                "input_count": len(normalized),
                "input_sha256": digest,
                "mean": mean,
            },
        )
        return MetricsOutput(count=len(normalized), mean=mean, evidence=evidence).model_dump(
            mode="json"
        )


def register() -> HelloMetricsPlugin:
    """Manifest entrypoint: return the plugin instance discovered by DSA."""

    return HelloMetricsPlugin()
