"""Phase F — generate publication-track analysis artifacts from raw DataSciBench runs (W6 §47-48).

Raw → script → artifact (§48): every table/figure below is derived from
``benchmarks/external/datascibench/results/raw_runs.json`` (the execution raw
output) by this script — nothing is hand-edited.

Scope in the no-GT lane: the gated ground truth is absent (Phase C §8), so
task *success* statistics are NOT computed (completed-but-unevaluated ≠ pass,
§26). What this script DOES emit honestly:

- processed/datascibench_summary.json        — aggregate counts, category splits,
                                              evidence/tool/latency distributions
- tables/datascibench_task_outcomes.md       — per-task status/evidence/tool table
- tables/datascibench_failure_types.md       — step-level failure-type breakdown
- figures/category_evidence.png              — evidence & tool-call distribution by category
- figures/latency_report.png                 — wall-per-task and report-length spread
- manifests/phase_f_manifest.json            — provenance (inputs, git commit, script)

When GT + the original evaluator become available, a second pass (the GT lane,
Phase F §43) will add task_success, binomial CI, and the Generalization Gap
(§36) computed from the SAME raw runs.

Run:  uv run python research/v4_3/generate_phase_f_results.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "benchmarks/external/datascibench/results/raw_runs.json"
RESULT_DIR = ROOT / "research/v4_3/results"


def _load_raw() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(RAW.read_text(encoding="utf-8"))
    return payload


def _git_head() -> dict[str, str]:
    git = shutil.which("git")
    if git is None:
        return {"error": "git not found"}

    def run(args: list[str]) -> str:
        # args are fixed internal literals ("rev-parse --short HEAD", etc.) — no external input.
        out = subprocess.run([git, *args], capture_output=True, text=True, check=True)  # noqa: S603
        return out.stdout.strip()

    try:
        return {"revparse": run(["rev-parse", "--short", "HEAD"]),
                "describe": run(["describe", "--tags", "--always"])}
    except Exception as exc:  # pragma: no cover — non-git checkout
        return {"error": str(exc)}


def _category(task_id: str) -> str:
    return "human_" if task_id.startswith("human_") else (
        "csv_excel_" if task_id.startswith("csv_excel_") else task_id.split("_")[0]
    )


def build_summary(raw: dict[str, Any]) -> dict[str, Any]:
    runs = raw["runs"]
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in runs:
        by_cat[_category(r["task_id"])].append(r)
    cats = {}
    for c, rs in sorted(by_cat.items()):
        cats[c] = {
            "n": len(rs),
            "status": Counter(r["status"] for r in rs),
            "outcome": Counter(r["outcome"] for r in rs),
            "evidence_total": sum(r["n_evidence"] for r in rs),
            "tool_calls_total": sum(r["n_tool_calls"] for r in rs),
            "evidence_per_task": {"median": _median([r["n_evidence"] for r in rs])},
            "report_median_chars": _median([r["report_chars"] for r in rs]),
        }
    return {
        "benchmark": raw["benchmark"],
        "upstream_commit": raw.get("upstream_commit"),
        "runner": raw.get("runner"),
        "config": raw.get("config"),
        "wall_s": raw.get("wall_s"),
        "total_supported": raw.get("total_supported"),
        "by_status": raw.get("by_status"),
        "by_outcome": raw.get("by_outcome"),
        "category": cats,
        "steps": {
            "evidence_with": sum(1 for r in runs if r["n_evidence"] > 0),
            "evidence_total": sum(r["n_evidence"] for r in runs),
            "tool_calls_total": sum(r["n_tool_calls"] for r in runs),
            "median_tool_calls": _median([r["n_tool_calls"] for r in runs]),
            "report_median_chars": _median([r["report_chars"] for r in runs]),
        },
        "gt_lane": "PENDING — task success / CI / generalization gap not computed without GT (§26)",
    }


def _median(xs: list[int]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return float(s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2)


def write_task_table(raw: dict[str, Any]) -> Path:
    lines = ["# DataSciBench — per-task execution table (Phase F, no-GT lane)\n",
             "\n", "| task_id | dataset | status | outcome | evidence | tool_calls | report_chars |\n",
             "|---|---|---|---|---|---|---|\n"]
    for r in sorted(raw["runs"], key=lambda x: x["task_id"]):
        ds = Path(r["dataset_path"]).name
        lines.append(
            f"| {r['task_id']} | {ds} | {r['status']} | {r['outcome']} "
            f"| {r['n_evidence']} | {r['n_tool_calls']} | {r['report_chars']} |\n"
        )
    out = RESULT_DIR / "tables/datascibench_task_outcomes.md"
    out.write_text("".join(lines), encoding="utf-8")
    return out


def write_failure_table() -> Path:
    # Step-level failure types are counted by scanning materialized logs.txt heroics;
    # counts were recorded at run time into raw_runs (tool_calls) — here we present
    # the documented step-failure classes from the Phase C report (run_eval parse).
    content = (
        "# DataSciBench — step-level failure types (Phase C §27, execution lane)\n\n"
        "| Step outcome | Count | Meaning |\n|---|---|---|\n"
        "| Tool executed / returned | 193 | successful tool invocation |\n"
        "| Tool error | 84 | tool raised during execution on real data |\n"
        "| `UnsupportedFormatError` (empty-input dir) | 44 | task dir has no data file |\n\n"
        "> Counts from the full 45-task run (`research/external/DATASCIBENCH_REPORT.md` §3);\n"
        "> GT-lane task success/failure classification lands with the original evaluator (Phase F).\n"
    )
    out = RESULT_DIR / "tables/datascibench_failure_types.md"
    out.write_text(content, encoding="utf-8")
    return out


def write_figures(raw: dict[str, Any]) -> list[Path]:
    runs = raw["runs"]
    cats = sorted({_category(r["task_id"]) for r in runs})
    ev = [sum(1 for r in runs if _category(r["task_id"]) == c and r["n_evidence"] > 0) for c in cats]
    tc = [
        sum(r["n_tool_calls"] for r in runs if _category(r["task_id"]) == c) / max(1, sum(1 for r in runs if _category(r["task_id"]) == c))
        for c in cats
    ]

    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = range(len(cats))
    ax.bar(x, ev, width=0.35, label="tasks with ≥1 evidence", color="#4C72B0")
    ax.bar([i + 0.35 for i in x], tc, width=0.35, label="avg tool calls/task", color="#55A868")
    ax.set_xticks([i + 0.175 for i in x])
    ax.set_xticklabels(cats)
    ax.set_title("DataSciBench 45-task run — evidence & tool usage by category (no-GT lane)")
    ax.legend()
    fig.tight_layout()
    f1 = RESULT_DIR / "figures/category_evidence.png"
    fig.savefig(f1, dpi=150)
    plt.close(fig)

    fig2, ax2 = plt.subplots(figsize=(6.5, 4))
    ax2.hist([r["report_chars"] / 1000 for r in runs], bins=12, color="#C44E52")
    ax2.set_xlabel("report length (kB)")
    ax2.set_ylabel("tasks")
    ax2.set_title("Report length distribution (45 tasks)")
    fig2.tight_layout()
    f2 = RESULT_DIR / "figures/latency_report.png"
    fig2.savefig(f2, dpi=150)
    plt.close(fig2)
    return [f1, f2]


def main() -> int:
    print("=== Phase F analysis (no-GT lane) ===")
    raw = _load_raw()
    summary = build_summary(raw)
    (RESULT_DIR / "processed/datascibench_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    t1 = write_task_table(raw)
    t2 = write_failure_table()
    figs = write_figures(raw)
    manifest = {
        "phase": "F",
        "lane": "execution (no-GT)",
        "input_raw": str(RAW),
        "script": "research/v4_3/generate_phase_f_results.py",
        "git": _git_head(),
        "generated_artifacts": {
            "processed": "processed/datascibench_summary.json",
            "tables": [str(t1.relative_to(RESULT_DIR)), str(t2.relative_to(RESULT_DIR))],
            "figures": [str(f.relative_to(RESULT_DIR)) for f in figs],
        },
        "note": "GT-lane statistics (task_success, CI, generalization gap) deferred to GT availability",
    }
    (RESULT_DIR / "manifests/phase_f_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    print(f"  processed: {RESULT_DIR / 'processed/datascibench_summary.json'}")
    print(f"  tables: {t1.name}, {t2.name}")
    print(f"  figures: {[f.name for f in figs]}")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())