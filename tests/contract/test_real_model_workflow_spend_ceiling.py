"""The pinned smoke must run under the spend ceiling its own page prescribes.

`docs/real-model-evaluation.md` tells the operator that a credentialed run always sets
`DSA_MAX_COST_USD`, and its cost table names `DSA_MAX_COST_USD=2` for the four-variant smoke;
`docs/audit/authorization-coverage.json` cites that paragraph as an existing control. Measured on
`main` before this file existed, the workflow set the variable nowhere and forwarded it into no
container, so the first run with a key in place would have been uncapped while three records said
otherwise. A cap that exists only in prose is the same defect as a gate whose exit code nobody
reads, so the reading below is derived from both files and a mutation of either side has to fail.

The workflow sets the variable for the job; `docker run` starts each variant in a fresh container
with only the variables it is told to forward, so the `-e` list is the part that actually bounds
spend. That distinction is why a job-level assignment alone does not satisfy this test.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/real-model-evaluation.yml"
PAGE = ROOT / "docs/real-model-evaluation.md"

CAP = "DSA_MAX_COST_USD"
DSA_ENTRYPOINT = ".venv/bin/dsa"
SMOKE_ROW = "| 4-variant smoke (CI pinned) |"
SPEND_HEADING = "## Spend cap (in-code guard)"
SCOPE_WORD = "per-process"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _env_block(workflow: str) -> str:
    """The job-level `env:` mapping, stopping at the first key back at column zero."""
    lines = workflow.splitlines()
    start = lines.index("env:")
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        block.append(line)
    return "\n".join(block)


def _configured_cap(workflow: str) -> str | None:
    match = re.search(rf"^  {CAP}:\s*\"?([^\"\n]+?)\"?\s*$", _env_block(workflow), re.MULTILINE)
    return match.group(1).strip() if match else None


def _docker_run_blocks(workflow: str) -> list[str]:
    """Every `docker run ...` invocation, joined until the line that drops the continuation."""
    lines = workflow.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip().startswith("docker run"):
            block = [lines[index]]
            while block[-1].rstrip().endswith("\\") and index + 1 < len(lines):
                index += 1
                block.append(lines[index])
            blocks.append("\n".join(block))
        index += 1
    return blocks


def _variant_blocks(workflow: str) -> list[str]:
    return [block for block in _docker_run_blocks(workflow) if DSA_ENTRYPOINT in block]


def _declared_variants(workflow: str) -> int:
    return len(re.findall(r"^\s+DSA_EVALUATION_VARIANT:\s*\S+$", workflow, re.MULTILINE))


def _documented_cap(page: str) -> str | None:
    for line in page.splitlines():
        if line.startswith(SMOKE_ROW):
            match = re.search(rf"{CAP}=([0-9.]+)", line)
            return match.group(1) if match else None
    return None


def _spend_section(page: str) -> str:
    section = page[page.index(SPEND_HEADING) :]
    following = section.find("\n## ", len(SPEND_HEADING))
    return section if following == -1 else section[:following]


def _cap_problems(configured: str | None, documented: str | None) -> list[str]:
    if configured is None:
        return [f"the workflow sets no {CAP}"]
    try:
        value = float(configured)
    except ValueError:
        return [f"{CAP}={configured!r} is not a number"]
    if value <= 0:
        return [f"{CAP}={configured!r} refuses the first paid call instead of bounding spend"]
    if documented is None:
        return ["the page states no cap for the pinned smoke"]
    if float(documented) != value:
        return [f"the workflow says {value} and the page says {documented}"]
    return []


def _problems(workflow: str, page: str) -> list[str]:
    problems = _cap_problems(_configured_cap(workflow), _documented_cap(page))
    variants = _variant_blocks(workflow)
    if len(variants) != _declared_variants(workflow):
        problems.append("a declared variant runs no entrypoint, or the two counts moved apart")
    problems.extend(
        f"variant {number} does not forward {CAP}"
        for number, block in enumerate(variants, 1)
        if f"-e {CAP}" not in block
    )
    if SCOPE_WORD not in _spend_section(page):
        problems.append(f"the page stopped calling the ceiling {SCOPE_WORD}")
    return problems


def test_the_pinned_smoke_forwards_the_cap_its_page_prescribes() -> None:
    assert _problems(_text(WORKFLOW), _text(PAGE)) == []


def test_a_dropped_forward_is_reported() -> None:
    workflow = _text(WORKFLOW)
    mutated = workflow.replace(f"            -e {CAP} \\\n", "", 1)
    assert mutated != workflow, "the forward this test removes no longer exists verbatim"
    assert any("does not forward" in problem for problem in _problems(mutated, _text(PAGE)))


def test_the_control_a_zero_cap_is_reported() -> None:
    workflow = _text(WORKFLOW)
    mutated = re.sub(rf"^  {CAP}:.*$", f'  {CAP}: "0"', workflow, count=1, flags=re.MULTILINE)
    reported = _problems(mutated, _text(PAGE))
    assert any("refuses the first paid call" in problem for problem in reported), reported


def test_a_page_that_moves_the_number_is_reported() -> None:
    page = _text(PAGE)
    mutated = page.replace(f"| `{CAP}=2` |", f"| `{CAP}=5` |", 1)
    assert mutated != page, "the row this test rewrites no longer states the cap verbatim"
    assert any("the page says" in problem for problem in _problems(_text(WORKFLOW), mutated))


def test_a_page_that_drops_the_per_process_scope_is_reported() -> None:
    page = _text(PAGE)
    mutated = page.replace(SCOPE_WORD, "run-wide")
    assert SCOPE_WORD not in mutated, "the scope word survives somewhere the reading still sees"
    reported = _problems(_text(WORKFLOW), mutated)
    assert any(SCOPE_WORD in problem for problem in reported), reported
