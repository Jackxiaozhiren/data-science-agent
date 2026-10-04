"""§98 D-L3-10: "no numeric columns" and "could not read the file" were the same answer.

`_numeric_columns` returned `[]` for a missing path, a missing file, a loader that raised,
*and* a dataset that genuinely has no numeric columns. The planner then wrote

    numeric_cols = _numeric_columns(path) or [name-based guess] or cols

so an `[]` that was a fact got overwritten by a guess: a text-only dataset was handed its
own text columns as the numeric set, and the correlation step was emitted against columns
that can never correlate. The fix separates the two states and keeps the guess exactly where
the guess belongs -- when nothing is known.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dsa_agent.columns import _numeric_columns
from dsa_agent.planner import heuristics_plan

TEXT_ONLY = "label,group\nalpha,x\nbeta,y\ngamma,z\ndelta,w\n"
MIXED = "label,value,other\nalpha,1,2\nbeta,3,4\ngamma,5,6\n"


def _csv(tmp_path: Path, name: str, body: str) -> str:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_a_dataset_with_no_numeric_columns_says_so_rather_than_nothing(tmp_path: Path) -> None:
    """Green-on-arrival pin of the truth: the loader worked and found zero numeric columns."""
    path = _csv(tmp_path, "text_only.csv", TEXT_ONLY)
    assert _numeric_columns(path) == []


def test_a_dataset_with_numeric_columns_still_lists_them(tmp_path: Path) -> None:
    path = _csv(tmp_path, "mixed.csv", MIXED)
    assert _numeric_columns(path) == ["value", "other"]


def test_no_path_is_unknown_not_empty() -> None:
    assert _numeric_columns(None) is None


def test_a_missing_file_is_unknown_not_empty(tmp_path: Path) -> None:
    assert _numeric_columns(str(tmp_path / "never_written.csv")) is None


def test_a_loader_failure_is_unknown_not_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _csv(tmp_path, "mixed.csv", MIXED)
    import dsa_datasets.loader as loader

    def explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("disk gone")

    monkeypatch.setattr(loader, "load_dataframe", explode)
    assert _numeric_columns(path) is None


def test_the_planner_does_not_correlate_text_columns(tmp_path: Path) -> None:
    """The consequence, at plan level: a known text-only dataset gets no correlation step."""
    path = _csv(tmp_path, "text_only.csv", TEXT_ONLY)
    plan = heuristics_plan("correlate label with group", path, ["label", "group"])
    tools = [step.tool for step in plan.steps]
    assert "correlation_analysis" not in tools, (
        f"text columns were handed to the planner as numeric: {tools}"
    )


def test_an_unreadable_dataset_still_gets_the_name_based_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve today's behaviour exactly where guessing is the only option.

    The point of the tri-state is not to make the planner stricter overall -- it is to stop
    overwriting a fact with a guess. When nothing could be read, the old fallback must still
    run, or every profiling hiccup silently degrades plans that used to work.
    """
    path = _csv(tmp_path, "mixed.csv", MIXED)
    import dsa_datasets.loader as loader

    def explode(*args: object, **kwargs: object) -> object:
        raise RuntimeError("disk gone")

    monkeypatch.setattr(loader, "load_dataframe", explode)
    plan = heuristics_plan("correlate value with other", path, ["label", "value", "other"])
    tools = [step.tool for step in plan.steps]
    assert "correlation_analysis" in tools, tools
