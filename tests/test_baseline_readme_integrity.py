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

CI_FILE = REPO / ".github/workflows/ci.yml"
CATALOG = REPO / "benchmarks/ds-agent-benchmark/catalog.json"
DATASETS = REPO / "benchmarks/ds-agent-benchmark/datasets"
GENERATOR = REPO / "scripts/generate_benchmark_datasets.py"
RUNNER = REPO / "packages/evaluation/src/dsa_evaluation/runner.py"

# The bullet that promises a CI consequence. `fails CI` is the only phrasing the file uses today;
# widening it to "blocks"/"required" was measured first and rejected, because the scope notes under
# the same heading use "required" about the release process rather than about a check.
CLAIMS_CI = re.compile(r"\bfails CI\b")
TOLERATION_OWNER = "tests/regression/test_regression_matrix.py::test_baseline_contract"
MODE_ENV = "DSA_LLM_MODE"

# A number glued to a whole-repository measurement noun. Catalog sizes and latencies are not in
# this class, which is why the alternation names neither: §76 measured that a wider net also caught
# McNemar 6:2 and a verified run's "6 evidence items".
UNOWNED_MEASURE = re.compile(
    r"\b\d[\d.]*\s*(?:%\s*(?:coverage|branch)?|tests?|files|routes?|pages)\b"
    r"|\b(?:mypy|ruff|next|compose)\s+\d[\d./]*",
    re.IGNORECASE,
)


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


# --- §113: the freeze's enforcement, gate-figure and mode claims -------------------------------
#
# Three more sentences in the same file are claims about the repository rather than about the
# benchmark, and all three were false while unchecked because this directory sits outside every
# prose guard: `.github/workflows/ci.yml` never reads it, `tests/test_doc_census_claims.py` scans
# only `README.md`, `docs/**` and `apps/**`, and `scripts/check_public_claims.py` names
# `benchmarks/` in its historical skip-list without any glob able to reach it. The most telling
# measurement is that §76 retired the literal `86 tests` pattern from that checker's rules -- and
# `86 tests pass` is still printed here.


def _section(text: str, heading: str) -> str:
    """The body of one `## ` heading, up to the next one."""
    parts = [p for p in text.split("\n## ") if p.startswith(heading)]
    assert parts, f"the README no longer has a `## {heading}` section"
    return parts[0]


def _ci_reads_baseline() -> int:
    """How many times the workflow mentions this directory -- measured, never assumed."""
    return CI_FILE.read_text(encoding="utf-8").count("benchmarks/baseline")


def _offending_ci_claims(text: str) -> list[str]:
    """Lines in this file that assert a CI consequence.

    Banned unconditionally rather than lifted if a workflow step ever appears: the freeze document
    states what the repository promises, and enforcement belongs to `ci.yml`, where a reader can
    actually see it. Conditional guards go quietly vacuous the day the thing they allow-list exists.
    """
    return [ln.strip() for ln in text.splitlines() if CLAIMS_CI.search(ln)]


def test_the_tolerance_rule_does_not_claim_ci_enforcement_the_workflow_does_not_provide() -> None:
    """RED before §113: the bullet promised "fails CI" while ci.yml has zero refs to this dir."""
    refs = _ci_reads_baseline()
    offenders = _offending_ci_claims(README.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{len(offenders)} line(s) assert a CI consequence; measured just now, "
        f"`benchmarks/baseline` appears {refs} time(s) in ci.yml: {offenders}"
    )


def test_the_tolerance_rule_names_the_check_that_actually_runs() -> None:
    """The real owner is `test_baseline_contract`, and the pointer must resolve.

    Unconditional, so the guard above's conditional lift cannot leave this section unswept: even
    if a CI step is added tomorrow, the bullet has to point at something that exists.
    """
    gates = _section(README.read_text(encoding="utf-8"), "Gates anchored here")
    bullets = [b for b in gates.split("\n- ") if b.startswith("Tolerance")]
    assert bullets, "the Gates section no longer carries the tolerance rule"
    tolerance = bullets[0]
    assert TOLERATION_OWNER in tolerance, tolerance
    owner = REPO / TOLERATION_OWNER.split("::")[0]
    assert owner.is_file(), f"{TOLERATION_OWNER} points at a file that is not there"
    name = TOLERATION_OWNER.split("::")[1]
    assert re.search(
        rf"^(?:async )?def {re.escape(name)}\(", owner.read_text(encoding="utf-8"), re.M
    ), f"{owner} no longer defines {name}"


def test_the_control_a_ci_claim_is_caught_and_an_honest_rewording_is_not() -> None:
    """Synthetic on purpose: a control that only fires while the defect stands becomes a lie once
    the prose is fixed, and a guard whose bite depends on the shipped file's wording rots with it."""
    planted = "- Tolerance: any PR that drops the metric fails CI\n"
    assert _offending_ci_claims(planted) == [planted.strip()], "a planted CI claim slipped through"
    honest = "- Tolerance: no automated check recomputes this; see test_baseline_contract\n"
    assert _offending_ci_claims(honest) == [], "an honest rewording was still reported"


def _unowned_gate_figures(text: str) -> list[str]:
    """Measurement counts in the Gates section -- the class §63 settled as 'removed, not corrected'.

    Shape-based on purpose. Catalog facts (task and dataset counts) and a latency figure are not
    matched here: they have owners elsewhere, and §76 showed that a blanket ban on numbers also
    bans McNemar 6:2.
    """
    gates = _section(text, "Gates anchored here")
    return [m.group(0) for m in UNOWNED_MEASURE.finditer(gates)]


def test_the_gates_section_carries_no_measurement_count_without_an_owner() -> None:
    """RED before §113: 86 tests / 74% coverage / mypy 81 files / ruff 184 / next 7/7 are dated."""
    found = _unowned_gate_figures(README.read_text(encoding="utf-8"))
    assert not found, f"the Gates section quotes measurements nothing recomputes: {found}"


def test_the_control_a_planted_gate_figure_is_caught() -> None:
    """The rule must bite on a measurement count and stay silent on the catalog facts beside it.

    Written against synthetic fixtures rather than the shipped file so it keeps proving both
    halves after the fix lands: a guard that could only fail while the defect stood would itself
    be a dated record.
    """
    clean = (
        "\n## Gates anchored here\n"
        "- Budget: 50 tasks / 20 datasets (seed 42) — mean_latency 47.92ms baseline\n"
    )
    assert _unowned_gate_figures(clean) == [], "catalog sizes were flagged as unowned measurements"
    planted = clean + "- Functional: 999 tests pass · 74% coverage\n"
    assert _unowned_gate_figures(planted) == ["999 tests", "74% coverage"], _unowned_gate_figures(
        planted
    )


def test_the_budget_bullet_quotes_sizes_the_catalog_actually_has() -> None:
    """GREEN ON ARRIVAL -- 50 tasks / 20 datasets / seed 42 all match their owners today.

    This exists so the one place the freeze is allowed to keep numbers stays derived from the
    catalog rather than from memory.
    """
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    n_tasks = len(catalog["tasks"])
    n_datasets = sum(1 for p in DATASETS.iterdir() if p.is_file())
    seed = re.search(r"random\.Random\((\d+)\)", GENERATOR.read_text(encoding="utf-8")).group(1)
    gates = _section(README.read_text(encoding="utf-8"), "Gates anchored here")
    budget = next(ln for ln in gates.splitlines() if ln.strip().startswith("- Budget"))
    for expected in (f"{n_tasks} tasks", f"{n_datasets} datasets", f"seed {seed}"):
        assert expected in budget, f"{expected!r} (measured) is not quoted in: {budget}"


def _runner_mode_default(source: Path = RUNNER) -> str:
    """The default the runner resolves `DSA_LLM_MODE` to, read out of its own source."""
    found = re.search(
        r'os\.getenv\("DSA_LLM_MODE",\s*"([^"]+)"\)', source.read_text(encoding="utf-8")
    )
    assert found, "the runner no longer resolves DSA_LLM_MODE with a literal default to read"
    return found.group(1)


def _undeclared_mode(text: str, source: Path = RUNNER) -> str | None:
    """Why the reproduce section misleads, or None if a reader can tell what will run.

    Two things have to be true: the section names the switch, and it names the value the switch
    resolves to when unset -- read from the runner's own source, not typed here. Naming the
    variable alone would leave a reader unable to predict what the documented command does.
    """
    default = _runner_mode_default(source)
    section = _section(text, "How to reproduce")
    if MODE_ENV not in section:
        return f"the switch is not named at all (the harness will run {MODE_ENV}={default})"
    if not re.search(rf"\b{re.escape(default)}\b", section):
        return f"the switch is named but its default ({default!r}) is not"
    return None


def test_the_reproduce_block_declares_the_mode_the_runner_defaults_to() -> None:
    """RED before §113: `dsa --limit 50` silently runs the heuristic stub; the block never says so.

    The frozen `results.json` carries no `execution` block (see §113's measurement), so the mode of
    the run these numbers came from is not recorded anywhere in the artifact either. A reader
    following this section therefore compares a stub run against a snapshot of unknown mode and
    reads a non-empty `diff` as a regression report.
    """
    reason = _undeclared_mode(README.read_text(encoding="utf-8"))
    assert reason is None, f"the reproduce section does not tell a reader what will run: {reason}"


def test_the_control_a_declared_mode_passes_and_a_moved_default_does_not(tmp_path: Path) -> None:
    """Both directions: the guard is not a ban on the word, and it tracks the code's default."""
    text = README.read_text(encoding="utf-8")
    honest = text.replace(
        "uv run dsa --limit 50",
        f"`DSA_LLM_MODE` defaults to `{_runner_mode_default()}`; uv run dsa --limit 50",
        1,
    )
    assert honest != text, "the fixture edit did not land -- this control proves nothing"
    assert _undeclared_mode(honest) is None, "an honest disclosure was still reported"

    source = RUNNER.read_text(encoding="utf-8").replace(
        'os.getenv("DSA_LLM_MODE", "stub")', 'os.getenv("DSA_LLM_MODE", "real")', 1
    )
    assert source != RUNNER.read_text(encoding="utf-8"), "the source edit did not land"
    moved = tmp_path / "runner.py"
    moved.write_text(source, encoding="utf-8")
    assert _runner_mode_default(moved) == "real", (
        "the default is not being read from the source given"
    )
    reason = _undeclared_mode(honest, source=moved)
    assert reason is not None, "prose declaring the old default still passes after it moved"
