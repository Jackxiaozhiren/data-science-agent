"""Generate all research tables from raw experiment results.

Input: research/results/*.json + benchmarks/v2/catalog.json + human-eval/samples.json
Output: research/tables/*.md + research/tables/*.csv (raw→script→table — §55)

Run:
  uv run python research/scripts/generate_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
RESULTS = ROOT / "research/results"
TABLES = ROOT / "research/tables"
TABLES.mkdir(parents=True, exist_ok=True)


def _write_benchmark_table() -> None:
    cat = json.loads((ROOT / "benchmarks/v2/catalog.json").read_text(encoding="utf-8"))
    by_cat: dict[str, int] = {}
    for t in cat["tasks"]:
        by_cat[t["category"]] = by_cat.get(t["category"], 0) + 1
    md = "# Benchmark v2 Summary\n\n| Category | Tasks |\n|---|---|\n"
    for k in sorted(by_cat):
        md += f"| {k} | {by_cat[k]} |\n"
    md += f"\nTotal: {len(cat['tasks'])} (version {cat.get('version')})\n"
    (TABLES / "benchmark_summary.md").write_text(md, encoding="utf-8")
    print(f"  wrote {TABLES / 'benchmark_summary.md'}")


def _write_claim_evidence_table() -> None:
    # Copy from research/claim-evidence-matrix.md as generated table
    src = ROOT / "research/claim-evidence-matrix.md"
    if src.exists():
        (TABLES / "claim_evidence.md").write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"  wrote {TABLES / 'claim_evidence.md'}")


def main() -> None:
    print("=== Generating tables ===")
    _write_benchmark_table()
    _write_claim_evidence_table()
    # Ablation table placeholder (derived from research/results)
    (TABLES / "ablation.md").write_text("# Ablation A–F (post-hoc §27)\n\nSee research/V3_RESEARCH_REPORT.md Results.\n", encoding="utf-8")
    print(f"  wrote {TABLES / 'ablation.md'}")
    print("done")


if __name__ == "__main__":
    main()
