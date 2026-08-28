"""Validate and render the public benchmark leaderboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "benchmarks" / "leaderboard" / "leaderboard.json"
README = ROOT / "benchmarks" / "leaderboard" / "README.md"
START = "<!-- leaderboard:start -->"
END = "<!-- leaderboard:end -->"

REQUIRED = (
    "system_name",
    "version",
    "commit",
    "benchmark_version",
    "model",
    "task_success_rate",
    "statistical_accuracy",
    "evidence_coverage",
    "reproducibility",
    "latency_ms",
    "cost_usd",
)
RATE_FIELDS = (
    "task_success_rate",
    "statistical_accuracy",
    "evidence_coverage",
    "reproducibility",
)


def load_entries() -> list[dict[str, Any]]:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("leaderboard.json must contain a JSON array")

    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"entry {index} must be an object")
        missing = [field for field in REQUIRED if field not in entry]
        if missing:
            raise ValueError(f"entry {index} missing required fields: {', '.join(missing)}")
        for field in RATE_FIELDS:
            value = float(entry[field])
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"entry {index} {field} must be between 0 and 1")
        if float(entry["latency_ms"]) < 0:
            raise ValueError(f"entry {index} latency_ms must be non-negative")
        if float(entry["cost_usd"]) < 0:
            raise ValueError(f"entry {index} cost_usd must be non-negative")
        entries.append(entry)

    return sorted(
        entries,
        key=lambda e: (
            -float(e["task_success_rate"]),
            -float(e["statistical_accuracy"]),
            -float(e["evidence_coverage"]),
            -float(e["reproducibility"]),
            float(e["latency_ms"]),
            float(e["cost_usd"]),
            str(e["system_name"]).lower(),
        ),
    )


def pct(value: Any) -> str:
    return f"{float(value) * 100:.1f}%"


def render(entries: list[dict[str, Any]]) -> str:
    lines = [
        START,
        "",
        "| Rank | System | Version | Benchmark | Model | Task success | Statistical | Evidence | Reproducibility | Latency | Cost |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, entry in enumerate(entries, start=1):
        commit = str(entry["commit"])
        lines.append(
            "| {rank} | {system} | `{version}` (`{commit}`) | `{benchmark}` | `{model}` | {task} | {stat} | {evidence} | {repro} | {latency:.0f} ms | ${cost:.4f} |".format(
                rank=rank,
                system=entry["system_name"],
                version=entry["version"],
                commit=commit[:7],
                benchmark=entry["benchmark_version"],
                model=entry["model"],
                task=pct(entry["task_success_rate"]),
                stat=pct(entry["statistical_accuracy"]),
                evidence=pct(entry["evidence_coverage"]),
                repro=pct(entry["reproducibility"]),
                latency=float(entry["latency_ms"]),
                cost=float(entry["cost_usd"]),
            )
        )
    lines.extend(["", END])
    return "\n".join(lines)


def replace_block(text: str, block: str) -> str:
    if START not in text or END not in text:
        raise ValueError("README leaderboard markers are missing")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return before.rstrip() + "\n\n" + block + "\n\n" + after.lstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail if README is not synchronized")
    mode.add_argument("--write", action="store_true", help="rewrite the generated leaderboard table")
    args = parser.parse_args()

    entries = load_entries()
    current = README.read_text(encoding="utf-8")
    expected = replace_block(current, render(entries))

    if args.write:
        README.write_text(expected, encoding="utf-8")
        print(f"Rendered {len(entries)} leaderboard entr{'y' if len(entries) == 1 else 'ies'}.")
        return 0

    if current != expected:
        print("Leaderboard README is out of sync. Run: python scripts/render_leaderboard.py --write")
        return 1
    print(f"Leaderboard is valid and synchronized ({len(entries)} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
