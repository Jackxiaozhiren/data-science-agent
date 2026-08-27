"""Data Science Agent — Public SDK (W2 Distribution Hardening).

Public surface (§14): ``Agent, Dataset, Analysis, Evidence, Artifact, Benchmark, Reproduction``
plus stable companions ``Insight, Report, BenchmarkResult, ReproductionResult``.

Stability (§15 / §18): see :data:`API_STABILITY`. Only ``data_science_agent.*`` is public;
``dsa_agent``, ``dsa_tools`` etc. are ``Internal`` — public code must not import ``_internal``.

Each Stable API below documents: Description / Parameters / Return Value / Errors / Example / Version (§16).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Dataset:
    """A dataset handle for SDK calls.

    Description:
        Lightweight handle pointing to a local dataset file. Stable since 4.0.0.

    Parameters:
        path: Filesystem path to CSV/Parquet dataset.
        dataset_id: Optional logical id (defaults to file stem).
        rows: Populated after profiling if available.
        cols: Populated after profiling if available.

    Return Value:
        ``Dataset`` instance.

    Errors:
        No I/O on construction; ``Agent.profile`` / ``Agent.analyze`` may raise
        ``FileNotFoundError`` or ``ValueError`` for unsupported format.

    Example:
        >>> from data_science_agent import Dataset
        >>> ds = Dataset.from_path("benchmarks/v2/datasets/sales.csv")
        >>> ds.dataset_id
        'sales'

    Version:
        4.0.0 Stable
    """

    path: str
    dataset_id: str | None = None
    rows: int | None = None
    cols: int | None = None

    @classmethod
    def from_path(cls, path: str | Path) -> Dataset:
        """Create a Dataset from a filesystem path.

        Parameters:
            path: Path to dataset file.

        Return Value:
            ``Dataset`` with ``path`` and ``dataset_id`` set to stem.

        Errors:
            Never raises for missing file (deferred to ``Agent``).

        Example:
            >>> Dataset.from_path("sales.csv").path
            'sales.csv'

        Version:
            4.0.0 Stable
        """
        p = Path(path)
        return cls(path=str(p), dataset_id=p.stem)


@dataclass
class Evidence:
    """Evidence grounding an insight (Insight → Evidence → ToolCall → Dataset).

    Description:
        Evidence record produced by a tool call. Stable since 4.0.0.

    Parameters:
        id: Evidence id (e.g. ``ev-...``).
        claim: Natural-language claim backed by this evidence.
        source_type: One of ``sql|python|statistical_test|model|visualization``.
        source_id: ToolCall id or artifact id backing the claim.
        result: Tool output dict (JSON-serializable).
        confidence: 0.0–1.0.
        validation_status: ``pending|validated|rejected``.

    Return Value:
        ``Evidence`` dataclass.

    Errors:
        Construction never raises; validation happens in ``Analysis.validation``.

    Example:
        >>> from data_science_agent import Evidence
        >>> e = Evidence(id="ev-1", claim="price~revenue r=0.9", source_type="python", source_id="tc-1")
        >>> e.confidence
        0.0

    Version:
        4.0.0 Stable
    """

    id: str
    claim: str
    source_type: str
    source_id: str
    result: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    validation_status: str = "pending"


@dataclass
class Artifact:
    """Artifact produced during analysis (chart, table, report, etc.).

    Description:
        Pointer to a file artifact under ``artifacts/reports/<run_id>/``. Stable.

    Parameters:
        id: Artifact id.
        type: ``dataset|code|sql|table|chart|model|notebook|report|evidence``.
        path: Relative or absolute path.
        metadata: Free-form metadata (e.g. ``{rows: 500}``).
        created_by: Creator (default ``agent``).
        created_at: ISO-8601 timestamp or None.

    Return Value:
        ``Artifact`` instance.

    Errors:
        None on construction.

    Example:
        >>> Artifact(id="a-1", type="chart", path="artifacts/reports/run-1/chart.png")
        Artifact(...)

    Version:
        4.0.0 Stable
    """

    id: str
    type: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_by: str = "agent"
    created_at: str | None = None


@dataclass
class Insight:
    """Insight derived from evidence.

    Description:
        High-level finding linked to one or more ``Evidence`` ids. Stable.

    Parameters:
        id: Insight id.
        finding: Natural-language finding.
        evidence_ids: List of backing evidence ids.
        limitation: Optional limitation note.
        magnitude: Optional magnitude (e.g. ``large``).
        significance: Optional significance (e.g. ``p<0.01``).

    Return Value:
        ``Insight`` instance.

    Errors:
        None.

    Example:
        >>> Insight(id="in-1", finding="Revenue correlates with price", evidence_ids=["ev-1"])

    Version:
        4.0.0 Stable
    """

    id: str
    finding: str
    evidence_ids: list[str] = field(default_factory=list)
    limitation: str | None = None
    magnitude: str | None = None
    significance: str | None = None


@dataclass
class Analysis:
    """Result of ``Agent.analyze``.

    Description:
        Complete analysis result: status, report, evidence, insights, artifacts,
        tool_calls, validation, error, and raw_state. Stable.

    Parameters:
        run_id: Unique run id (``run-...``).
        status: ``COMPLETED|FAILED|...`` (mirrors ``AnalysisState.status``).
        report_markdown: Report markdown if generated.
        evidence: List of ``Evidence``.
        insights: List of ``Insight``.
        artifacts: List of ``Artifact``.
        tool_calls: Raw tool call dicts (JSON-serializable).
        validation: Validation result dicts.
        error: Error message if failed else None.
        raw_state: Original ``AnalysisState`` (Internal, may be None).

    Return Value:
        ``Analysis`` aggregate.

    Errors:
        ``Agent.analyze`` raises ``FileNotFoundError`` for missing dataset,
        ``ValueError`` for empty task.

    Example:
        >>> from data_science_agent import Agent
        >>> r = Agent().analyze_sync("benchmarks/v2/datasets/sales.csv", "Analyze revenue")
        >>> r.status
        'COMPLETED'

    Version:
        4.0.0 Stable
    """

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


API_STABILITY: dict[str, str] = {
    "Agent": "Stable",
    "Dataset": "Stable",
    "Analysis": "Stable",
    "Evidence": "Stable",
    "Artifact": "Stable",
    "Insight": "Stable",
    "Report": "Stable",
    "Benchmark": "Stable",
    "Reproduction": "Stable",
    "BenchmarkResult": "Stable",
    "ReproductionResult": "Stable",
}


class Agent:
    """Stable SDK facade (W2) over Core Engine (graph + evidence). [Stable]

    Description:
        Primary entrypoint for analyses. Wraps ``dsa_agent.graph.run_analysis``
        (LangGraph Planner→Scientist→Critic→Report) and exposes async and sync
        variants. Stable since 4.0.0; async behavior is cancellation-friendly.

    Parameters:
        None on construction; methods take dataset + task.

    Return Value:
        Constructed ``Agent`` with ``version == "4.2.6"``.

    Errors:
        Methods may raise ``FileNotFoundError`` (missing dataset),
        ``ValueError`` (empty task / unsupported format).

    Example:
        >>> from data_science_agent import Agent, Dataset
        >>> agent = Agent()
        >>> result = agent.analyze_sync(Dataset.from_path("sales.csv"), "Analyze revenue")
        >>> result.evidence[0].claim  # doctest: +SKIP

    Version:
        4.0.0 Stable
    """

    def __init__(self) -> None:
        self._version = "4.2.6"

    async def analyze(
        self,
        dataset: str | Path | Dataset,
        task: str,
        *,
        run_id: str | None = None,
    ) -> Analysis:
        """Run an analysis (async).

        Description:
            Execute the agent graph for a dataset + natural-language task.
            Returns evidence-grounded ``Analysis`` (report + evidence + artifacts).

        Parameters:
            dataset: Path string / ``Path`` / ``Dataset`` handle.
            task: Natural-language question (non-empty).
            run_id: Optional explicit run id for reproducibility.

        Return Value:
            ``Analysis`` with ``status`` (COMPLETED), ``report_markdown``,
            ``evidence``, ``insights``, ``artifacts``, ``tool_calls``.

        Errors:
            ``FileNotFoundError`` if dataset missing; ``ValueError`` if task empty.

        Example:
            >>> import asyncio
            >>> from data_science_agent import Agent
            >>> asyncio.run(Agent().analyze("sales.csv", "Analyze revenue"))  # doctest: +SKIP

        Version:
            4.0.0 Stable
        """
        from dsa_agent.graph import run_analysis

        if isinstance(dataset, Dataset):
            ds_path = dataset.path
            ds_id = (
                dataset.dataset_id or Path(ds_path).stem
                if ds_path
                else dataset.dataset_id or "dataset"
            )
        else:
            ds_path = str(dataset)
            ds_id = Path(ds_path).stem if ds_path else "dataset"

        state = await run_analysis(
            dataset_path=ds_path, dataset_id=ds_id, user_query=task, run_id=run_id
        )
        return Analysis(
            run_id=state.run_id,
            status=state.status.value if hasattr(state.status, "value") else str(state.status),
            report_markdown=state.report_markdown,
            evidence=[Evidence(**e.model_dump()) for e in state.evidence]
            if state.evidence and hasattr(state.evidence[0], "model_dump")
            else [Evidence(**dict(e)) for e in state.evidence],
            insights=[Insight(**i.model_dump()) for i in state.insights]
            if state.insights and hasattr(state.insights[0], "model_dump")
            else [Insight(**dict(i)) for i in state.insights],
            artifacts=[Artifact(**a.model_dump()) for a in state.artifacts]
            if state.artifacts and hasattr(state.artifacts[0], "model_dump")
            else [Artifact(**dict(a)) for a in state.artifacts],
            tool_calls=[
                c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c)
                for c in state.tool_calls
            ],
            validation=[
                v.model_dump(mode="json") if hasattr(v, "model_dump") else dict(v)
                for v in state.validation_results
            ],
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
        """Run an analysis (sync wrapper).

        Description:
            Sync wrapper around :meth:`analyze` via ``asyncio.run``.
            Suitable for scripts/CLI; in Jupyter with a running loop, use ``await analyze``.

        Parameters:
            Same as :meth:`analyze`.

        Return Value:
            ``Analysis``.

        Errors:
            Same as :meth:`analyze`; may raise ``RuntimeError`` if called inside
            a running event loop (use ``await analyze`` instead).

        Example:
            >>> from data_science_agent import Agent
            >>> Agent().analyze_sync("sales.csv", "Analyze revenue")  # doctest: +SKIP

        Version:
            4.0.0 Stable
        """
        return asyncio.run(self.analyze(dataset, task, run_id=run_id))

    def profile(self, dataset: str | Path | Dataset) -> dict[str, Any]:
        """Profile a dataset.

        Description:
            Load a dataset via ``dsa_datasets.loader`` and return row count
            and columns (Polars-aware). Stable.

        Parameters:
            dataset: Path or ``Dataset`` handle.

        Return Value:
            ``{"rows": int, "columns": list[str], "path": str}``.

        Errors:
            ``FileNotFoundError`` if missing; ``ValueError`` for unsupported format.

        Example:
            >>> Agent().profile("benchmarks/v2/datasets/sales.csv")  # doctest: +SKIP
            {'rows': 500, ...}

        Version:
            4.0.0 Stable
        """
        from dsa_datasets.loader import load_dataframe
        from dsa_datasets.validate import detect_format

        p = Path(dataset.path) if isinstance(dataset, Dataset) else Path(str(dataset))
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        return {
            "rows": df.height if hasattr(df, "height") else len(df),
            "columns": list(df.columns),
            "path": str(p),
        }

    @property
    def version(self) -> str:
        """SDK version (mirrors ``pyproject.toml``).

        Return Value:
            ``"4.2.6"`` string.

        Version:
            4.0.0 Stable
        """
        return self._version


@dataclass
class BenchmarkResult:
    """Result of ``Benchmark.run``.

    Description:
        Aggregate benchmark outcome over catalog tasks. Stable.

    Parameters:
        n_tasks: Number of tasks executed.
        aggregate: Aggregate metrics (task_success_rate etc.).
        results: Per-task result dicts.

    Return Value:
        ``BenchmarkResult``.

    Errors:
        ``Benchmark.run`` may raise ``FileNotFoundError`` for missing catalog.

    Example:
        >>> from data_science_agent import Benchmark
        >>> r = Benchmark().run(limit=1)  # doctest: +SKIP
        >>> r.n_tasks
        1

    Version:
        4.0.0 Stable
    """

    n_tasks: int
    aggregate: dict[str, Any] = field(default_factory=dict)
    results: list[dict[str, Any]] = field(default_factory=list)


class Benchmark:
    """Benchmark facade (V4 §16) over evaluation framework.

    Description:
        Runs ``dsa_evaluation.runner.run_benchmark`` and returns typed result.
        Stable since 4.0.0; catalog default is ``benchmarks/ds-agent-benchmark``.

    Parameters:
        None on construction.

    Return Value:
        Constructed ``Benchmark``.

    Errors:
        ``run`` may raise ``FileNotFoundError`` if catalog/datasets missing.

    Example:
        >>> from data_science_agent import Benchmark
        >>> Benchmark().run(limit=1)  # doctest: +SKIP

    Version:
        4.0.0 Stable
    """

    def run(
        self,
        catalog: str | Path = "benchmarks/ds-agent-benchmark/catalog.json",
        datasets: str | Path = "benchmarks/ds-agent-benchmark/datasets",
        out: str | Path = "benchmarks/ds-agent-benchmark/results",
        limit: int | None = None,
    ) -> BenchmarkResult:
        """Run benchmark.

        Description:
            Execute benchmark catalog over dataset dir.

        Parameters:
            catalog: Path to ``catalog.json``.
            datasets: Directory of datasets.
            out: Output dir for ``results.json`` etc.
            limit: Optional limit for smoke runs.

        Return Value:
            ``BenchmarkResult`` with ``n_tasks`` and ``aggregate``.

        Errors:
            ``FileNotFoundError`` for missing paths.

        Example:
            >>> Benchmark().run(limit=1)  # doctest: +SKIP

        Version:
            4.0.0 Stable
        """
        from dsa_evaluation.runner import run_benchmark

        payload = run_benchmark(Path(catalog), Path(datasets), Path(out), limit=limit)
        return BenchmarkResult(
            n_tasks=payload.get("n_tasks", 0),
            aggregate=payload.get("aggregate", {}),
            results=payload.get("results", []),
        )


@dataclass
class ReproductionResult:
    """Result of ``Reproduction.run``.

    Description:
        6-dim reproducibility score (overall/execution/trajectory/by_level). Stable.

    Parameters:
        overall: Overall score 0–1.
        execution: Execution match rate.
        trajectory: Trajectory match rate.
        by_level: Scores by level L0–L5.
        out_dir: Output directory.

    Return Value:
        ``ReproductionResult``.

    Errors:
        ``run`` may raise on missing catalog; fallback writes ``out_dir`` alone.

    Example:
        >>> ReproductionResult(overall=0.9)
        ReproductionResult(overall=0.9, ...)

    Version:
        4.0.0 Stable
    """

    overall: float = 0.0
    execution: float = 0.0
    trajectory: float = 0.0
    by_level: dict[str, float] = field(default_factory=dict)
    out_dir: str = ""


class Reproduction:
    """Reproduction facade (V4 §16) over reproducibility harness.

    Description:
        Runs fresh-twice reproduction harness and reads ``comparison.json``.
        Stable since 4.0.0.

    Parameters:
        None on construction.

    Return Value:
        ``Reproduction``.

    Errors:
        ``run`` may raise ``FileNotFoundError``; returns partial ``ReproductionResult`` on failure.

    Example:
        >>> from data_science_agent import Reproduction
        >>> Reproduction().run()  # doctest: +SKIP

    Version:
        4.0.0 Stable
    """

    def run(
        self,
        catalog: str | Path = "benchmarks/v2/catalog.json",
        datasets: str | Path = "benchmarks/v2/datasets",
        out: str | Path = "reproduction/v2",
    ) -> ReproductionResult:
        """Run reproduction harness.

        Description:
            Execute ``_reproduce_benchmark`` (or fallback ``run_benchmark``) and parse
            ``comparison.json`` for 6-dim scores.

        Parameters:
            catalog: Catalog json.
            datasets: Datasets dir.
            out: Output dir for ``manifest.json/comparison.json``.

        Return Value:
            ``ReproductionResult``.

        Errors:
            Never raises for missing ``comparison.json`` (returns empty scores).

        Example:
            >>> Reproduction().run()  # doctest: +SKIP

        Version:
            4.0.0 Stable
        """
        from dsa_evaluation.cli import _reproduce_benchmark

        # _reproduce_benchmark is internal; fallback to runner if missing
        try:
            _reproduce_benchmark(Path(catalog), Path(datasets), Path(out))
        except Exception:
            from dsa_evaluation.runner import run_benchmark as _rb

            _rb(Path(catalog), Path(datasets), Path(out))
        # Try to read comparison
        try:
            import json

            comp = json.loads((Path(out) / "comparison.json").read_text(encoding="utf-8"))
            rs = comp.get("reproduction_score", {})
            return ReproductionResult(
                overall=float(rs.get("overall", 0)),
                execution=float(rs.get("execution", 0)),
                trajectory=float(rs.get("trajectory", 0)),
                by_level=rs.get("by_level", {}),
                out_dir=str(out),
            )
        except Exception:
            return ReproductionResult(out_dir=str(out))


@dataclass
class Report:
    """Report handle.

    Description:
        Pointer to a generated report (markdown + optional path). Stable.

    Parameters:
        run_id: Associated run id.
        markdown: Markdown content if in-memory.
        path: Filesystem path if persisted.

    Return Value:
        ``Report``.

    Errors:
        None.

    Example:
        >>> Report(run_id="run-1", markdown="# Report")

    Version:
        4.0.0 Stable
    """

    run_id: str
    markdown: str | None = None
    path: str | None = None
