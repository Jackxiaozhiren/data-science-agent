"""Benchmark and reproduction facades (audit §112, Phase 4 target 2, seam #4).

Split out of ``data_science_agent.sdk``, which held the analysis surface (``Agent`` and the value
dataclasses a run produces) and the measurement surface (these two facades, which shell into
``dsa_evaluation``) in one 716-line module. Only this file needs the evaluation framework, and only
that framework's output shapes leak into here -- so the dependency direction became honest as well as
the size.

The published import path is unchanged: ``data_science_agent.sdk`` re-exports these names, and
``API_STABILITY`` still lists them, because the docs table and every existing caller import them there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
        trajectory: Trajectory match rate (the harness writes it as ``semantic``).
        by_level: Scores by level L0–L5.
        out_dir: Output directory.
        error: Why the scores are not backed by a comparison artifact, or ``None`` when they are.
            A measured ``0.0`` keeps ``error`` as ``None``; a score that was defaulted because the
            artifact was missing, unreadable, or short a dimension reports the reason here.

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
    error: str | None = None


#: ``ReproductionResult`` field -> key ``dsa_evaluation.cli`` writes in ``reproduction_score``.
#: The trajectory rate is published as ``semantic``; no producer writes a ``trajectory`` key, so
#: reading for one reported ``0.0`` through this facade for every real run, including the committed
#: ``reproduction/v2/comparison.json`` whose ``semantic`` is ``1.0``.
REPRODUCTION_DIMENSION_KEYS: dict[str, str] = {
    "overall": "overall",
    "execution": "execution",
    "trajectory": "semantic",
}


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
            Execute ``dsa_evaluation.reproduce.reproduce_benchmark`` (or fallback
            ``run_benchmark``) and parse
            ``comparison.json`` for 6-dim scores.

        Parameters:
            catalog: Catalog json.
            datasets: Datasets dir.
            out: Output dir for ``manifest.json/comparison.json``.

        Return Value:
            ``ReproductionResult``.

        Errors:
            Never raises for missing ``comparison.json``: ``error`` says which scores were not read,
            so a defaulted ``0.0`` is never mistaken for a measured one.

        Example:
            >>> Reproduction().run()  # doctest: +SKIP

        Version:
            4.0.0 Stable
        """
        from dsa_evaluation.reproduce import reproduce_benchmark

        # fallback to the runner if the harness itself fails
        harness_error: str | None = None
        try:
            reproduce_benchmark(Path(catalog), Path(datasets), Path(out))
        except Exception as exc:
            harness_error = f"{type(exc).__name__}: {exc}"
            from dsa_evaluation.runner import run_benchmark as _rb

            _rb(Path(catalog), Path(datasets), Path(out))
        import json

        comparison_path = Path(out) / "comparison.json"
        why_harness = f"; harness also failed: {harness_error}" if harness_error else ""
        # Try to read comparison
        try:
            comp = json.loads(comparison_path.read_text(encoding="utf-8"))
            rs = comp.get("reproduction_score")
            if not isinstance(rs, dict):
                return ReproductionResult(
                    out_dir=str(out),
                    error=f"{comparison_path} holds no 'reproduction_score' object{why_harness}",
                )
            absent = sorted(set(REPRODUCTION_DIMENSION_KEYS.values()) - rs.keys())
            if absent:
                return ReproductionResult(
                    out_dir=str(out),
                    error=(
                        f"{comparison_path} 'reproduction_score' holds no {', '.join(absent)}"
                        f"{why_harness}"
                    ),
                )
            return ReproductionResult(
                overall=float(rs["overall"]),
                execution=float(rs["execution"]),
                trajectory=float(rs["semantic"]),
                by_level=rs.get("by_level", {}),
                out_dir=str(out),
            )
        except Exception as exc:
            detail = f"could not read {comparison_path}: {type(exc).__name__}: {exc}"
            return ReproductionResult(out_dir=str(out), error=f"{detail}{why_harness}")
