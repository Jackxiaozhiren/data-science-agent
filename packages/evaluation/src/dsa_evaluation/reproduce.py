"""The fresh-twice reproduction harness (audit §109, Phase 4 target 2, seam #3).

Split out of ``dsa_evaluation.cli``, which was both the ``dsa`` command surface and the thing the
command runs. Two names the harness reads are not CLI concerns at all: the dataset hash that goes into
``manifest.json`` (§90's provenance field) and the per-run record handed to
``dsa_evidence.reproducibility.compare_runs`` (§104's contract fix).

``reproduce_benchmark`` is the public entry. It was ``_reproduce_benchmark`` inside the CLI module,
which ``data_science_agent.sdk`` imported anyway and documented as "internal" -- a private name
crossing a package boundary is a seam asking to be named, and the SDK's runner fallback existed only
because of that ambiguity.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

from dsa_evaluation.runner import run_benchmark


def _datasets_sha256(datasets: Path) -> tuple[str | None, str]:
    """Hash the dataset set for a provenance manifest, or name why there is no hash.

    The first version of this returned a bare `None` from `except Exception: pass`, so a
    released manifest could not be told apart whether the datasets were unreadable, the
    directory was absent, or it was a file. `datasets_sha256: null` with no reason is the
    same class of hole as an unrecorded failed check.
    """
    if not datasets.exists():
        return None, "datasets dir absent"
    if not datasets.is_dir():
        return None, "datasets path is not a directory"
    try:
        h = hashlib.sha256()
        for p in sorted(datasets.glob("*.csv")):
            h.update(p.name.encode())
            h.update(str(p.stat().st_size).encode())
        return h.hexdigest()[:12], "ok"
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _comparison_record(
    state: dict[str, Any], dataset_sha256: str | None, environment: dict[str, str] | None
) -> dict[str, Any]:
    """The record `compare_runs` was written for: the analysis state plus that run's own provenance.

    §104. `build_experiment_json` writes `dataset_sha256` and `environment`, and `compare_runs` decides
    L2 and L3 from them, but the harness used to pass bare `AnalysisState` dumps -- so L2 fell back to
    `dataset_id` equality and L3 to a lenient pass, and a dataset edited between the two runs still
    reported same-data. Absent provenance stays absent: the comparator then says which weaker basis it
    used instead of implying a comparison that did not happen.
    """
    return dict(state, dataset_sha256=dataset_sha256, environment=environment)


def reproduce_benchmark(catalog: Path, datasets: Path, out: Path) -> None:
    from dsa_evidence.reproducibility import compare_runs

    src_catalog = Path(catalog)
    src_datasets = Path(datasets)
    first = Path(out) / "first"
    second = Path(out) / "second"
    first.mkdir(parents=True, exist_ok=True)
    second.mkdir(parents=True, exist_ok=True)

    print("=== Reproduction: first run ===", flush=True)
    run_benchmark(src_catalog, src_datasets, first)
    print("=== Reproduction: second run ===", flush=True)
    run_benchmark(src_catalog, src_datasets, second)

    raw1 = json.loads((first / "raw_runs.json").read_text(encoding="utf-8"))
    raw2 = json.loads((second / "raw_runs.json").read_text(encoding="utf-8"))
    summ1 = json.loads((first / "summary.json").read_text(encoding="utf-8"))
    summ2 = json.loads((second / "summary.json").read_text(encoding="utf-8"))

    # Build a unified comparison for reviewer (§19–21)
    N = len(raw1)
    per_task: list[dict[str, Any]] = []
    exec_match = 0
    traj_match = 0
    for a, b in zip(raw1, raw2):
        rr1 = a.get("run_result") or {}
        rr2 = b.get("run_result") or {}
        ok1 = bool(
            any(
                (c.get("status") == "ok")
                for c in (rr1.get("tool_calls") or [])
                if isinstance(c, dict)
            )
        )
        ok2 = bool(
            any(
                (c.get("status") == "ok")
                for c in (rr2.get("tool_calls") or [])
                if isinstance(c, dict)
            )
        )
        score = compare_runs(
            _comparison_record(
                rr1 if isinstance(rr1, dict) else {}, a.get("dataset_sha256"), a.get("environment")
            ),
            _comparison_record(
                rr2 if isinstance(rr2, dict) else {}, b.get("dataset_sha256"), b.get("environment")
            ),
        )
        # Derive 6-dim gate values for this task
        same_exec = ok1 == ok2
        same_traj = bool(score.tool_trajectory_match)
        exec_match += 1 if same_exec else 0
        traj_match += 1 if same_traj else 0
        per_task.append(
            {
                "task_id": a.get("task_id"),
                "L_level": score.level,
                "score": score.score,
                "execution_match": same_exec,
                "trajectory_match": same_traj,
                "conclusion_match": bool(score.conclusion_match),
                "details": score.details,
            }
        )

    overall = round(sum(float(t["score"]) for t in per_task) / N, 4) if N else 0.0
    execution_rate = round(exec_match / N, 4) if N else 0.0
    trajectory_rate = round(traj_match / N, 4) if N else 0.0
    numerical_rate = (
        round(
            sum(1 for t in per_task if float(t.get("score", 0)) >= 0.5) / N,
            4,
        )
        if N
        else 0.0
    )

    # ReproductionScore (6-dim) per §21 — mapped onto DSR reproducibility L0..L5
    reproduction_score = {
        "execution": execution_rate,
        "numerical": numerical_rate,
        "statistical": summ1.get("statistical_accuracy"),
        "evidence": summ1.get("evidence_coverage"),
        "semantic": trajectory_rate,
        "overall": overall,
        "method": (
            "compare_runs L0=L1 (code lenient), L2 decided by details.L2_basis (a sha is compared "
            "only when both runs carry one, else dataset_id equality), L3 by details.L3_basis, "
            "L4 trajectory, L5 conclusion (insights/evidence ±20%)"
        ),
        "by_level": {
            lvl: round(sum(1 for t in per_task if t["L_level"] == lvl) / N, 4)
            for lvl in ("L0", "L1", "L2", "L3", "L4", "L5")
        },
    }

    ds_sha256, ds_note = _datasets_sha256(src_datasets)
    manifest = {
        "catalog": str(src_catalog),
        "datasets_dir": str(src_datasets),
        "catalog_sha256": hashlib.sha256(src_catalog.read_bytes()).hexdigest()[:12]
        if src_catalog.exists()
        else None,
        "datasets_sha256": ds_sha256,
        "datasets_sha256_note": ds_note,
        "n_tasks": N,
        "seed": 42,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }

    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "environment.json").write_text(
        json.dumps(
            {"python_version": sys.version, "platform": platform.platform(), "manifest": manifest},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "results.json").write_text(
        json.dumps(
            {"first": summ1, "second": summ2, "reproduction_score": reproduction_score},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "comparison.json").write_text(
        json.dumps(
            {
                "per_task": per_task,
                "reproduction_score": reproduction_score,
                "first_summary": summ1,
                "second_summary": summ2,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "logs").mkdir(parents=True, exist_ok=True)
    (out / "logs" / "first_summary.json").write_text(
        json.dumps(summ1, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "logs" / "second_summary.json").write_text(
        json.dumps(summ2, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("=== Reproduction complete ===")
    print(f"Overall: {overall}  execution:{execution_rate}  trajectory:{trajectory_rate}")
    print(f"Results: {out}")
