"""§132 (D-L4-12): which flag actually decides the paths for `dsa --reproduce`.

The `--reproduce` flag form resolved its catalog and datasets with a pair of ternaries whose two
branches were the *same expression* (`cli.py:452-461` at the revision this section started from), so
they decided nothing. The work was done by the `if target in (...) / elif "v2" in target / elif
target == "benchmark"` chain underneath, which re-assigned `catalog` and `datasets`
**unconditionally** -- so `dsa --reproduce v2 --catalog mine.json` ran the bundled v2 catalog and
reported the user's file nowhere. The spelled subcommand form a few lines below already let an
explicit flag win (`args.repro_catalog or <base>`), which is what the dead ternary was reaching for.
`docs/reproducibility.md:20` tells readers `--catalog` and `--datasets` are taken; nothing in
`tests/` pinned either reading until this file.

Two kinds of assertion are here. The dispatch cases are the differential over the spellings, and the
structural cases are the falsification of the defect itself: an AST scan for a conditional expression
whose branches are the same tree, and a count of each default path literal. Both are proven to fire
against the shapes the defect actually takes -- a guard that cannot go red over this bug would
 certify nothing.

The in-process cases bind `dsa_evaluation.cli` through `import`, and the shipped `dsa` console script
binds the vendored copy of the same module (`src/data_science_agent/_vendor/`). Which copy a test
process gets is environment-dependent, so no case asserts a path for it; instead
`test_the_two_cli_copies_are_identical` pins the premise that makes a reading of one a reading of the
other, and `scripts/sync_vendor.py --check` polices it in CI.
"""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO / "packages/evaluation/src/dsa_evaluation"
VENDOR_CLI = REPO / "src/data_science_agent/_vendor/dsa_evaluation/cli.py"

V1_CATALOG = "benchmarks/ds-agent-benchmark/catalog.json"
V1_DATASETS = "benchmarks/ds-agent-benchmark/datasets"
V1_RESULTS = "benchmarks/ds-agent-benchmark/results"
V2_CATALOG = "benchmarks/v2/catalog.json"
V2_DATASETS = "benchmarks/v2/datasets"
OUT_V2 = "reproduction/v2"
OUT_BENCHMARK = "reproduction/benchmark"

#: Every default path the reproduce/resolution code can hand to the harness. One owner each means one
#: place to change when the benchmark layout moves.
OWNED_LITERALS = (
    V1_CATALOG,
    V1_DATASETS,
    V1_RESULTS,
    V2_CATALOG,
    V2_DATASETS,
    OUT_V2,
    OUT_BENCHMARK,
)


def _dispatch(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> tuple[str, str, str]:
    """Run the CLI's reproduce dispatch and return the paths it hands the harness, in order.

    `reproduce_benchmark` is captured rather than run: the harness shells out two full benchmark
    passes, and the question here is which arguments it would receive.
    """
    from dsa_evaluation import cli

    seen: list[tuple[Any, Any, Any]] = []

    def fake(catalog: Any, datasets: Any, out: Any, *rest: Any, **kw: Any) -> None:
        seen.append((catalog, datasets, out))

    monkeypatch.setattr(cli, "reproduce_benchmark", fake)
    monkeypatch.setattr(sys, "argv", ["dsa", *argv])
    cli.main()
    assert len(seen) == 1, f"expected one harness call, got {seen}"
    catalog, datasets, out = seen[0]
    return str(catalog), str(datasets), str(out)


def _noop_conditionals(source: str) -> list[int]:
    """Line numbers of `A if cond else A` -- a conditional expression that decides nothing.

    Compares the printed subtrees of the two branches, which ignores where they sit in the file, so a
    ternary that merely repeats itself is reported and one with different arms is not.
    """
    dead: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.IfExp) and ast.dump(node.body) == ast.dump(node.orelse):
            dead.append(node.lineno)
    return dead


# --- the differential over the spellings -------------------------------------------------------


def test_bare_reproduce_runs_the_benchmark_catalog_into_the_benchmark_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Green on arrival: `--reproduce` with no target means `benchmark`, and that is unchanged."""
    assert _dispatch(monkeypatch, ["--reproduce"]) == (V1_CATALOG, V1_DATASETS, OUT_BENCHMARK)


def test_reproduce_benchmark_target_is_the_same_spelling_written_out(monkeypatch) -> None:
    assert _dispatch(monkeypatch, ["--reproduce", "benchmark"]) == (
        V1_CATALOG,
        V1_DATASETS,
        OUT_BENCHMARK,
    )


@pytest.mark.parametrize("target", ["v2", "benchmark-v2", "v2.0", "V2"])
def test_every_v2_spelling_runs_the_v2_paths(monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    assert _dispatch(monkeypatch, ["--reproduce", target]) == (V2_CATALOG, V2_DATASETS, OUT_V2)


def test_reproduce_with_an_unknown_target_falls_back_to_the_benchmark_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unchanged: a target no branch claims keeps the v1 defaults, as `--reproduce` does."""
    assert _dispatch(monkeypatch, ["--reproduce", "v9"]) == (V1_CATALOG, V1_DATASETS, OUT_BENCHMARK)


def test_an_explicit_catalog_beats_the_target_derived_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED before §132: the target chain re-assigned `catalog`, so this ran the bundled v2 catalog."""
    mine = "some/where/my_catalog.json"
    assert _dispatch(monkeypatch, ["--reproduce", "v2", "--catalog", mine]) == (
        mine,
        V2_DATASETS,
        OUT_V2,
    )


def test_explicit_datasets_beats_the_target_derived_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """RED before §132: same re-assignment, this time for the datasets directory."""
    mine = "some/where/my_datasets"
    assert _dispatch(monkeypatch, ["--reproduce", "v2", "--datasets", mine]) == (
        V2_CATALOG,
        mine,
        OUT_V2,
    )


def test_an_explicit_catalog_with_a_benchmark_target_is_not_discarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RED before §132 on the catalog slot; the out slot keeps the reading it had.

    Measured at the revision this section started from, `--reproduce --catalog
    benchmarks/v2/catalog.json` handed the harness the *v1* catalog with `reproduction/benchmark` --
    the explicit catalog was discarded, and the `default_out` expression that keyed the out dir on the
    catalog's path string was immediately cancelled by the `benchmark` branch rewriting
    `out == default_out`. So the out dir followed the target after all, by accident. §132 keeps that
    reading and makes it the rule: the target selects the family, a flag overrides its own slot.
    """
    assert _dispatch(monkeypatch, ["--reproduce", "--catalog", V2_CATALOG]) == (
        V2_CATALOG,
        V1_DATASETS,
        OUT_BENCHMARK,
    )


def test_a_v2_substring_somewhere_in_the_catalog_path_no_longer_moves_the_out_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The heuristic the section removes, pinned by the case it used to get wrong.

    `--reproduce v9 --catalog benchmarks/v2x/catalog.json` reached no branch of the old chain, so the
    cancelled-out path stayed open and the bundle landed in `reproduction/v2` for a run that used the
    catalog the reader named but the v1 datasets dir. Both spellings now agree that only a v2-ish
    target selects the v2 family.
    """
    assert _dispatch(
        monkeypatch, ["--reproduce", "v9", "--catalog", "benchmarks/v2x/cat.json"]
    ) == (
        "benchmarks/v2x/cat.json",
        V1_DATASETS,
        OUT_BENCHMARK,
    )


def test_an_explicit_out_beats_the_target_derived_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Green on arrival: `--out` already won, which is what `docs/evaluation.md:57` advertises."""
    assert _dispatch(monkeypatch, ["--reproduce", "v2", "--out", "my/runs"]) == (
        V2_CATALOG,
        V2_DATASETS,
        "my/runs",
    )


def test_naming_the_benchmark_results_dir_as_out_counts_as_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The documented convention: argparse pre-fills the defaults, so a default value is not an intent.

    `--out benchmarks/ds-agent-benchmark/results` is what `dsa --reproduce` would have carried anyway,
    and reproduce must not write a reproduction bundle over the benchmark results dir.
    """
    assert _dispatch(monkeypatch, ["--reproduce", "--out", V1_RESULTS]) == (
        V1_CATALOG,
        V1_DATASETS,
        OUT_BENCHMARK,
    )


def test_the_subcommand_spelling_honours_the_same_explicit_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Green on arrival: the subcommand form already let `--catalog` win, and it still does.

    Pinning both spellings in one file is the point -- before §132 they disagreed on whether an
    explicit flag means anything, which is how a dead ternary survives a test suite.
    """
    mine = "some/where/my_catalog.json"
    assert _dispatch(monkeypatch, ["reproduce", "--benchmark", "v2", "--catalog", mine]) == (
        mine,
        V2_DATASETS,
        OUT_V2,
    )


def test_bare_subcommand_reproduce_still_defaults_to_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unchanged, and deliberately not unified with `--reproduce`'s bare default (see §132)."""
    assert _dispatch(monkeypatch, ["reproduce"]) == (V2_CATALOG, V2_DATASETS, OUT_V2)


# --- structural guards: the defect itself, not only its symptoms --------------------------------


def test_the_reproduce_dispatch_has_no_conditional_that_decides_nothing() -> None:
    source = (EVAL_DIR / "cli.py").read_text(encoding="utf-8")

    assert _noop_conditionals(source) == [], (
        "`A if cond else A` is a no-op; either the arms differ or the expression goes"
    )


def _string_constants(source: str) -> list[str]:
    """Every `str` literal the module carries, as the parser sees it.

    Counted through the AST rather than as a substring of the file, because prose about a path is not
    a second owner of it -- and a guard that counted comments would fail on this section's own
    comments, which is the kind of gate that gets widened instead of read.
    """
    return [
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


@pytest.mark.parametrize("literal", OWNED_LITERALS)
def test_each_default_path_literal_has_one_owner(literal: str) -> None:
    source = (EVAL_DIR / "cli.py").read_text(encoding="utf-8")

    found = [value for value in _string_constants(source) if value == literal]
    assert len(found) == 1, f"{literal!r} is written out {len(found)} times; it needs one constant"


def test_the_two_cli_copies_are_identical() -> None:
    """The premise behind every case above: whichever copy this process bound, the other is the same.

    RED between the source edit and `sync_vendor --file`, which is the ordering this section follows;
    `scripts/sync_vendor.py --check` is the CI gate that keeps it true afterwards.
    """
    from dsa_evaluation import cli

    bound = Path(inspect.getsourcefile(cli) or "").resolve()
    assert bound.name == "cli.py", bound
    assert VENDOR_CLI.read_bytes() == (EVAL_DIR / "cli.py").read_bytes(), (
        "the shipped console script and the workspace source disagree; run "
        "`uv run --frozen python scripts/sync_vendor.py --file packages/evaluation/src/dsa_evaluation/cli.py`"
    )


def test_the_no_op_detector_fires_on_the_shape_of_the_bug_and_not_on_a_real_ternary() -> None:
    """Negative control for the guard above: it must be able to see the defect and spare the valid."""
    assert _noop_conditionals('x = a.foo if a.bar != "z" or q else a.foo') == [1]
    assert _noop_conditionals('x = Path("reproduction/v2") if "v2" in target else x') == []
    assert _noop_conditionals("x = 1 if c else 1") == [1]
