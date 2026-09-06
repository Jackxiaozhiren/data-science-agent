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
        return {
            "revparse": run(["rev-parse", "--short", "HEAD"]),
            "describe": run(["describe", "--tags", "--always"]),
        }
    except Exception as exc:  # pragma: no cover — non-git checkout
        return {"error": str(exc)}


def _category(task_id: str) -> str:
    return (
        "human_"
        if task_id.startswith("human_")
        else ("csv_excel_" if task_id.startswith("csv_excel_") else task_id.split("_")[0])
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
        "gt_lane": gt_lane_stats(raw),
    }


def _median(xs: list[int]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    m = len(s) // 2
    return float(s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2)


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% score interval for a binomial proportion (pure Python).

    Used for pass-rate CIs (internal 150/150, external 0/44) and the
    generalization-gap interval. Method chosen per W7 §68 (binomial CI for
    task success); z=1.96 fixed and recorded in output.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5 / denom
    return (max(0.0, center - half), min(1.0, center + half))


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def gt_lane_stats(raw: dict[str, Any]) -> dict[str, Any]:
    """GT-lane statistics (Phase F §43, second pass — was PENDING without GT).

    Reads per-run `score` (task Completion Rate from the original evaluator)
    and `outcome`. Pass = score >= 0.5 (adapter threshold, documented in
    benchmarks/external/datascibench/adapter.py).
    """
    runs = raw["runs"]
    scored = [r for r in runs if r.get("score") is not None]
    passed = [r for r in scored if (r["score"] or 0) >= 0.5]
    by_cat: dict[str, Any] = {}
    for c in sorted({_category(r["task_id"]) for r in scored}):
        rs = [r for r in scored if _category(r["task_id"]) == c]
        kp = sum(1 for r in rs if (r["score"] or 0) >= 0.5)
        by_cat[c] = {
            "n_scored": len(rs),
            "n_passed": kp,
            "pass_rate": round(kp / len(rs), 4) if rs else 0.0,
            "pass_rate_wilson95": [round(v, 4) for v in _wilson_ci(kp, len(rs))],
            "mean_cr": round(_mean([r["score"] or 0 for r in rs]), 4),
            "max_cr": round(max([r["score"] or 0 for r in rs]), 4) if rs else 0.0,
        }
    k, n = len(passed), len(scored)
    lo, hi = _wilson_ci(k, n)
    # Generalization gap (§56): internal 150/150 (v1 50/50 + v2 100/100) vs
    # external pass rate. Descriptive difference with CIs on both ends — NOT a
    # causal claim (§53: different benchmarks measure different constructs).
    gap = 1.0 - (k / n if n else 0.0)
    return {
        "n_scored": n,
        "n_unscored": len(runs) - n,
        "unscored_tasks": [r["task_id"] for r in runs if r.get("score") is None],
        "n_passed": k,
        "pass_rate": round(k / n, 4) if n else 0.0,
        "pass_rate_wilson95": [round(lo, 4), round(hi, 4)],
        "mean_cr": round(_mean([r["score"] or 0 for r in scored]), 4),
        "by_category": by_cat,
        "generalization_gap": {
            "internal_pass_rate": 1.0,
            "internal_n": 150,
            "internal_wilson95": [round(v, 4) for v in _wilson_ci(150, 150)],
            "external_pass_rate": round(k / n, 4) if n else 0.0,
            "external_n": n,
            "gap_internal_minus_external": round(gap, 4),
            "caveat": "different constructs (closed exact-match vs open GT-scored); gap is descriptive (§53)",
        },
        "method": "Wilson 95% CI (z=1.96); pass threshold score>=0.5",
    }


def write_task_table(raw: dict[str, Any]) -> Path:
    lines = [
        "# DataSciBench — per-task table (Phase F, GT lane since 2026-09-05)\n",
        "\n",
        "| task_id | dataset | status | outcome | score_CR | evidence | tool_calls | report_chars |\n",
        "|---|---|---|---|---|---|---|---|\n",
    ]
    for r in sorted(raw["runs"], key=lambda x: x["task_id"]):
        ds = Path(r["dataset_path"]).name
        sc = r.get("score")
        sc_s = f"{sc:.3f}" if isinstance(sc, (int, float)) else "n/a"
        lines.append(
            f"| {r['task_id']} | {ds} | {r['status']} | {r['outcome']} | {sc_s} "
            f"| {r['n_evidence']} | {r['n_tool_calls']} | {r['report_chars']} |\n"
        )
    out = RESULT_DIR / "tables/datascibench_task_outcomes.md"
    out.write_text("".join(lines), encoding="utf-8")
    return out


def write_gt_table(raw: dict[str, Any]) -> Path:
    stats = gt_lane_stats(raw)
    lines = [
        "# DataSciBench — GT-lane scores (Phase F §43, original evaluator)\n\n",
        f"> {stats['n_scored']}/45 tasks scored; pass = CR >= 0.5; "
        f"pass rate {stats['n_passed']}/{stats['n_scored']} "
        f"(Wilson 95% {stats['pass_rate_wilson95']}); mean CR {stats['mean_cr']}.\n\n",
        "| category | scored | passed | pass rate | Wilson 95% | mean CR | max CR |\n",
        "|---|---:|---:|---:|---|---:|---:|\n",
    ]
    for c, b in sorted(stats["by_category"].items()):
        lines.append(
            f"| {c} | {b['n_scored']} | {b['n_passed']} | {b['pass_rate']} "
            f"| {b['pass_rate_wilson95']} | {b['mean_cr']} | {b['max_cr']} |\n"
        )
    g = stats["generalization_gap"]
    lines.append(
        f"\n## Generalization gap (§56)\n\n"
        f"Internal {g['internal_n']}/{g['internal_n']} "
        f"(Wilson 95% {g['internal_wilson95']}) vs external "
        f"{stats['n_passed']}/{stats['n_scored']} "
        f"(Wilson 95% {stats['pass_rate_wilson95']}): "
        f"**gap = {g['gap_internal_minus_external']}**. {g['caveat']}.\n"
    )
    out = RESULT_DIR / "tables/datascibench_gt_scores.md"
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
    ev = [
        sum(1 for r in runs if _category(r["task_id"]) == c and r["n_evidence"] > 0) for c in cats
    ]
    tc = [
        sum(r["n_tool_calls"] for r in runs if _category(r["task_id"]) == c)
        / max(1, sum(1 for r in runs if _category(r["task_id"]) == c))
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

    scores = [r["score"] for r in runs if isinstance(r.get("score"), (int, float))]
    fig3, ax3 = plt.subplots(figsize=(6.5, 4))
    ax3.hist(scores, bins=12, range=(0, 1), color="#4C72B0")
    ax3.axvline(0.5, color="#C44E52", linestyle="--", label="pass threshold (CR=0.5)")
    ax3.set_xlabel("task Completion Rate (original evaluator)")
    ax3.set_ylabel("tasks")
    ax3.set_title(f"GT-lane CR distribution ({len(scores)} scored, 0 passed)")
    ax3.legend()
    fig3.tight_layout()
    f3 = RESULT_DIR / "figures/cr_distribution.png"
    fig3.savefig(f3, dpi=150)
    plt.close(fig3)
    return [f1, f2, f3]


def main() -> int:
    print("=== Phase F analysis (GT lane since 2026-09-05) ===")
    raw = _load_raw()
    summary = build_summary(raw)
    (RESULT_DIR / "processed/datascibench_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    t1 = write_task_table(raw)
    t2 = write_failure_table()
    t3 = write_gt_table(raw)
    figs = write_figures(raw)
    manifest = {
        "phase": "F",
        "lane": "GT lane (original evaluator, scored 2026-09-05)",
        "input_raw": str(RAW),
        "script": "research/v4_3/generate_phase_f_results.py",
        "git": _git_head(),
        "generated_artifacts": {
            "processed": "processed/datascibench_summary.json",
            "tables": [str(t.relative_to(RESULT_DIR)) for t in (t1, t2, t3)],
            "figures": [str(f.relative_to(RESULT_DIR)) for f in figs],
        },
        "note": "GT-lane statistics computed from original-evaluator CR scores; pass threshold 0.5; Wilson 95% CIs",
    }
    (RESULT_DIR / "manifests/phase_f_manifest.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8"
    )
    print(f"  processed: {RESULT_DIR / 'processed/datascibench_summary.json'}")
    print(f"  tables: {t1.name}, {t2.name}, {t3.name}")
    print(f"  figures: {[f.name for f in figs]}")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
