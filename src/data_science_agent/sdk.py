from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Dataset:
    path: str
    dataset_id: str | None = None
    rows: int | None = None
    cols: int | None = None

    @classmethod
    def from_path(cls, path: str | Path) -> Dataset:
        p = Path(path)
        return cls(path=str(p), dataset_id=p.stem)


@dataclass
class Evidence:
    id: str
    claim: str
    source_type: str
    source_id: str
    result: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    validation_status: str = "pending"


@dataclass
class Artifact:
    id: str
    type: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str = "agent"
    created_at: str | None = None


@dataclass
class Insight:
    id: str
    finding: str
    evidence_ids: list[str] = field(default_factory=list)
    limitation: str | None = None
    magnitude: str | None = None
    significance: str | None = None


@dataclass
class Analysis:
    run_id: str
    status: str
    report_markdown: str | None = None
    evidence: list[Evidence] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    validation: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    raw_state: Any = None


class Agent:
    """Stable SDK facade (W2) over Core Engine (graph + evidence)."""

    def __init__(self) -> None:
        self._version = "3.0.0"

    async def analyze(
        self,
        dataset: str | Path | Dataset,
        task: str,
        *,
        run_id: str | None = None,
    ) -> Analysis:
        from dsa_agent.graph import run_analysis

        if isinstance(dataset, Dataset):
            ds_path = dataset.path
            ds_id = dataset.dataset_id or Path(ds_path).stem if ds_path else dataset.dataset_id or "dataset"
        else:
            ds_path = str(dataset)
            ds_id = Path(ds_path).stem if ds_path else "dataset"

        state = await run_analysis(dataset_path=ds_path, dataset_id=ds_id, user_query=task, run_id=run_id)
        return Analysis(
            run_id=state.run_id,
            status=state.status.value if hasattr(state.status, "value") else str(state.status),
            report_markdown=state.report_markdown,
            evidence=[Evidence(**e.model_dump()) for e in state.evidence] if state.evidence and hasattr(state.evidence[0], "model_dump") else [Evidence(**dict(e)) for e in state.evidence],
            insights=[Insight(**i.model_dump()) for i in state.insights] if state.insights and hasattr(state.insights[0], "model_dump") else [Insight(**dict(i)) for i in state.insights],
            artifacts=[Artifact(**a.model_dump()) for a in state.artifacts] if state.artifacts and hasattr(state.artifacts[0], "model_dump") else [Artifact(**dict(a)) for a in state.artifacts],
            tool_calls=[c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c) for c in state.tool_calls],
            validation=[v.model_dump(mode="json") if hasattr(v, "model_dump") else dict(v) for v in state.validation_results],
            error=state.error,
            raw_state=state,
        )

    def analyze_sync(
        self,
        dataset: str | Path | Dataset,
        task: str,
        *,
        run_id: str | None = None,
    ) -> Analysis:
        return asyncio.run(self.analyze(dataset, task, run_id=run_id))

    def profile(self, dataset: str | Path | Dataset) -> dict[str, Any]:
        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format

        p = Path(dataset.path) if isinstance(dataset, Dataset) else Path(str(dataset))
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        return {"rows": df.height if hasattr(df, "height") else len(df), "columns": list(df.columns), "path": str(p)}

    @property
    def version(self) -> str:
        return self._version
