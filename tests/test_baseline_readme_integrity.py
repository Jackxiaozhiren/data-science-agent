"""§100: the baseline README describes repository facts, so the repository checks them.

`benchmarks/baseline/README.md` is the frozen regression contract, and two of its sentences are
claims about files and numbers rather than about history: the fenced tree block listing what is
in the directory, and the aggregate line quoting `summary.json`'s values. The tree block named
`raw_runs.json` -- a file a reproduce run writes into its own output directory and nobody ever
committed -- since the freeze, and nothing noticed, because no test read the prose against the
directory. These assertions are one-directional on purpose: each is paired with a control that
mutates the input, so a parser that quietly accepts anything cannot pass.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "benchmarks/baseline"
README = BASELINE / "README.md"

TREE_BLOCK = re.compile(r"```[^\n]*\n(benchmarks/baseline/\n(?:.*\n)*?)```")
ENTRY = re.compile(r"^[├└]── (\S+)")
ANNOTATION = re.compile(r"NOT committed", re.I)


def _tree_lines(text: str) -> list[str]:
    match = TREE_BLOCK.search(text)
    assert match, "the README no longer carries the fenced `benchmarks/baseline/` tree block"
    return match.group(1).splitlines()


def _named_files(lines: list[str]) -> list[str]:
    names = []
    for line in lines:
        found = ENTRY.search(line)
        if found:
            names.append(found.group(1))
    assert names, "the tree block lists no files -- the parser stopped matching anything"
    return names


def test_every_file_named_in_the_tree_block_is_present_or_annotated() -> None:
    """RED before §100: run against HEAD's README this reports `['raw_runs.json']`."""
    lines = _tree_lines(README.read_text(encoding="utf-8"))
    on_disk = {p.name for p in BASELINE.iterdir() if p.is_file()}
    offenders = []
    for line in lines:
        found = ENTRY.search(line)
        if not found:
            continue
        name = found.group(1)
        if name not in on_disk and not ANNOTATION.search(line):
            offenders.append(name)
    assert not offenders, f"the tree block names files that are not there: {offenders}"


def test_the_aggregate_line_quotes_summary_json_exactly(tmp_path: Path) -> None:
    """Every number in the `summary.json` comment must be the number in the file.

    GREEN ON ARRIVAL -- the quoted numbers were already correct; this exists so they cannot
    drift, not to report a fixed defect.

    Written as pairs read from the artifact rather than typed literals here, because the point
    is that the prose tracks the file -- if the file changes, this goes red and says so.
    """
    summary = json.loads((BASELINE / "summary.json").read_text(encoding="utf-8"))
    line = next(e for e in _tree_lines(README.read_text(encoding="utf-8")) if "summary.json" in e)

    assert f"{summary['n']}/{summary['n']} @ {summary['task_success_rate']}" in line, line
    quoted = {
        "task_success": summary["task_success_rate"],
        "sql": summary["sql_accuracy"],
        "statistical": summary["statistical_accuracy"],
        "code": summary["code_execution_success"],
        "evidence": summary["evidence_coverage"],
        "unsupported": summary["unsupported_claim_rate"],
        "mean_latency": summary["mean_latency_ms"],
    }
    missing = [f"{k}={v}" for k, v in quoted.items() if str(v) not in line]
    assert not missing, f"the README's aggregate line no longer quotes these: {missing}"


def test_the_control_a_missing_file_without_an_annotation_is_caught(tmp_path: Path) -> None:
    """The guard above must be able to fail: strip the annotation, keep the phantom name."""
    text = README.read_text(encoding="utf-8")
    mutated = text.replace(
        "└── raw_runs.json  # NOT committed.",
        "└── raw_runs.json  # full run_result dump.",
    )
    assert mutated != text, "the fixture edit did not land -- the control below proves nothing"
    lines = _tree_lines(mutated)
    on_disk = {p.name for p in BASELINE.iterdir() if p.is_file()}
    offenders = [
        m.group(1)
        for line in lines
        if (m := ENTRY.search(line)) and m.group(1) not in on_disk and not ANNOTATION.search(line)
    ]
    assert offenders == ["raw_runs.json"], offenders


def test_the_control_a_stale_number_in_the_prose_is_caught(tmp_path: Path) -> None:
    summary = json.loads((BASELINE / "summary.json").read_text(encoding="utf-8"))
    text = README.read_text(encoding="utf-8")
    wrong = text.replace(f"unsupported {summary['unsupported_claim_rate']}", "unsupported 0.99", 1)
    assert wrong != text, "the fixture edit did not land -- this control proves nothing"
    line = next(e for e in _tree_lines(wrong) if "summary.json" in e)
    assert str(summary["unsupported_claim_rate"]) not in line


def test_the_reproduce_command_names_the_artifacts_the_dir_actually_has() -> None:
    """`cat`/`diff` in the How-to-reproduce block must reference real summary files."""
    text = README.read_text(encoding="utf-8")
    block = re.search(r"## How to reproduce\n+```bash\n(.*?)```", text, re.S)
    assert block, "the reproduce block is gone; its commands are how a reader checks the freeze"
    cmds = block.group(1)
    for name in re.findall(r"benchmarks/baseline/([\w.-]+\.json)", cmds):
        assert (BASELINE / name).is_file(), f"the reproduce commands read {name}, which is absent"
