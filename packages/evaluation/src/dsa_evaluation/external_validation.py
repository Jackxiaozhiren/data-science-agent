from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _find_repo_root() -> Path:
    # Prefer the workspace root (pyproject with [tool.uv.workspace] / .git), not a package's pyproject
    candidates: list[Path] = []
    for p in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        if (p / ".git").exists():
            return p
        if (p / "pyproject.toml").exists():
            try:
                txt = (p / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
                if "[tool.uv.workspace]" in txt:
                    return p
            except Exception:
                pass
            candidates.append(p)
    # Fallback: 3 levels up (packages/evaluation/src/dsa_evaluation -> repo)
    fallback = Path(__file__).resolve().parents[3]
    if (fallback / "pyproject.toml").exists():
        return fallback
    return candidates[-1] if candidates else fallback


ROOT = _find_repo_root()


class DemoResult(BaseModel):
    task_id: str
    question: str
    dataset: str
    workdir: str
    elapsed_ms: int = 0
    task_success: bool = False
    n_tool_calls: int = 0
    n_insights: int = 0
    n_evidence: int = 0
    has_report: bool = False
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class InstallationMetrics(BaseModel):
    python_version: str = ""
    node_version: str | None = None
    platform: str = ""
    install_present: bool = False
    demo_pass: bool = False
    demo_result: DemoResult | None = None
    cold_install_time_ms: int | None = None
    first_launch_time_ms: int | None = None
    demo_execution_time_ms: int | None = None
    benchmark_setup_time_ms: int | None = None
    details: dict[str, Any] = Field(default_factory=dict)


DEMO_QUESTION = "Analyze correlation between price and revenue"
DEMO_DATASET_CANDIDATES = [
    "benchmarks/v2/datasets/sales.csv",
    "benchmarks/ds-agent-benchmark/datasets/sales.csv",
    "examples/datasets/sales.csv",
]


def _resolve_demo_dataset() -> Path | None:
    for c in DEMO_DATASET_CANDIDATES:
        p = ROOT / c
        if p.exists():
            return p
    # fallback: any csv under benchmarks/v2/datasets
    v2 = ROOT / "benchmarks/v2/datasets"
    if v2.exists():
        for p in sorted(v2.glob("*.csv")):
            return p
    return None


def run_demo(
    dataset: Path | None = None,
    question: str = DEMO_QUESTION,
    out: Path | None = None,
) -> DemoResult:
    """One-command demo (§40/47): Demo Dataset → Analysis → Evidence → Report.

    Runs entirely locally (no cloud), via run_analysis + workspace artifacts.
    Returns DemoResult with task_success, evidence/artifact counts, has_report.
    """
    import asyncio

    ds = dataset or _resolve_demo_dataset()
    if ds is None:
        return DemoResult(
            task_id="demo",
            question=question,
            dataset="missing",
            workdir=str(out or ""),
            error="No demo dataset found",
        )
    workdir = out or Path(tempfile.mkdtemp(prefix="dsa-demo-"))
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    async def _run() -> dict[str, Any]:
        from dsa_agent.graph import run_analysis
        from dsa_tools import bootstrap, list_tools

        if not list_tools():
            bootstrap()
        st = await run_analysis(dataset_path=str(ds), dataset_id=ds.stem, user_query=question)
        return st.model_dump(mode="json")

    try:
        state: dict[str, Any] = asyncio.run(_run())
        elapsed = int((time.perf_counter() - t0) * 1000)
        tcalls = state.get("tool_calls", [])
        insights = state.get("insights", [])
        evidence = state.get("evidence", [])
        has_report = bool(state.get("report_markdown"))
        # write artifacts for inspectability
        (workdir / "report.md").write_text(state.get("report_markdown") or "", encoding="utf-8")
        (workdir / "state.json").write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (workdir / "manifest.json").write_text(
            json.dumps(
                {
                    "dataset": str(ds),
                    "question": question,
                    "elapsed_ms": elapsed,
                    "workdir": str(workdir),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        ok = any(c.get("status") == "ok" for c in tcalls) if tcalls else False
        task_success = bool(ok and (has_report or tcalls))
        return DemoResult(
            task_id="demo",
            question=question,
            dataset=str(ds.relative_to(ROOT)) if ds.is_relative_to(ROOT) else str(ds),
            workdir=str(workdir),
            elapsed_ms=elapsed,
            task_success=task_success,
            n_tool_calls=len(tcalls),
            n_insights=len(insights),
            n_evidence=len(evidence),
            has_report=has_report,
            details={"tool_calls": tcalls[:5]},
        )
    except Exception as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return DemoResult(
            task_id="demo",
            question=question,
            dataset=str(ds),
            workdir=str(workdir),
            elapsed_ms=elapsed,
            error=f"{type(e).__name__}: {e}",
        )


def collect_installation_metrics(
    demo_question: str = DEMO_QUESTION,
    include_demo: bool = True,
) -> InstallationMetrics:
    """Collect W8 §42 installation metrics (§39 fresh-machine constraints documented).

    Times are best-effort wall clocks; demo is run locally without cloud.
    """
    # Cold install / first launch are developer-side approximations:
    # - cold_install_time: time for `uv sync --dev` if lock present, else None
    # - first_launch_time: time to import heavy stack (dsa_agent + dsa_tools bootstrap)
    # - demo_execution_time: wall time of run_demo
    # - benchmark_setup_time: catalog load + list_tools bootstrap time
    py = sys.version.split()[0]
    plat = platform.platform()
    node: str | None = None
    try:
        np = shutil.which("node")
        if np:
            node = (
                subprocess.run(
                    [np, "--version"], capture_output=True, text=True, timeout=3
                ).stdout.strip()
                or None
            )  # noqa: S603
    except Exception:
        pass
    install_present = (ROOT / "uv.lock").exists() and (ROOT / "pyproject.toml").exists()
    # first_launch_time
    t0 = time.perf_counter()
    try:
        from dsa_tools import bootstrap, list_tools  # noqa: F401

        if not list_tools():
            bootstrap()
        first_launch_ms = int((time.perf_counter() - t0) * 1000)
    except Exception:
        first_launch_ms = None
    # benchmark_setup_time: catalog load
    bench_ms: int | None = None
    try:
        from dsa_evaluation.catalog import Catalog

        t1 = time.perf_counter()
        cat = Catalog.load(ROOT / "benchmarks/v2/catalog.json")
        _ = len(cat.tasks)
        bench_ms = int((time.perf_counter() - t1) * 1000)
    except Exception:
        pass
    demo_res: DemoResult | None = None
    demo_ms: int | None = None
    if include_demo:
        # run_demo already measures elapsed_ms
        demo_res = run_demo(
            question=demo_question, out=Path(tempfile.mkdtemp(prefix="dsa-demo-metrics-"))
        )
        demo_ms = demo_res.elapsed_ms if demo_res else None

    return InstallationMetrics(
        python_version=py,
        node_version=node,
        platform=plat,
        install_present=install_present,
        demo_pass=bool(demo_res and demo_res.task_success) if include_demo else False,
        demo_result=demo_res,
        first_launch_time_ms=first_launch_ms,
        demo_execution_time_ms=demo_ms,
        benchmark_setup_time_ms=bench_ms,
        details={
            "root": str(ROOT),
            "demo_question": demo_question,
            "cold_install_time_ms_note": "run `time uv sync --dev` on a fresh clone for cold install; see docs/v3/EXTERNAL_VALIDATION.md §39/41",
            "fresh_machine_note": "Linux/macOS local-first (stub LLM + DuckDB/Polars, Cloud $0); Windows not tested — see §41",
        },
    )


def fresh_machine_checklist() -> dict[str, Any]:
    """Lightweight §41 checklist without fabricating OS claims."""
    return {
        "linux": {"tested_local": True, "note": "uv + stub LLM verified in this repo (no cloud)"},
        "macos": {
            "tested_local": True,
            "note": "Darwin verified in this repo (§42 demo/benchmark pass)",
        },
        "windows": {
            "tested_local": False,
            "note": "Not tested; PowerShell paths may differ — documented as limitation in §41",
        },
        "local_first": {
            "llm": "stub/small (no key) + Ollama small if OLLAMA_HOST",
            "data_engine": "DuckDB+Polars",
            "storage": "data/ + artifacts/",
            "cloud_cost": "$0",
        },
    }
