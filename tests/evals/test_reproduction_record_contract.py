"""§104: give the reproducibility comparison the record it was written for.

§102 established the mismatch by measurement: `compare_runs` decides L2 from `dataset_sha256` and L3
from `environment`, `build_experiment_json` writes both, and the reproduction harness passes neither --
it compares `AnalysisState` dumps, so L2 fell back to `dataset_id` equality and L3 to a lenient pass,
meaning two runs over different bytes of the same dataset id reported `L2_same_data: True`. §102 made
that visible; this closes it, because the per-run dataset hash and environment exist at run time and
were simply never carried into the record.

The dataset hash is captured *during each run*, so a file edited between the two runs changes the
answer -- which is the whole point of an L2.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from dsa_datasets.hash_utils import sha256_file
from dsa_evaluation import reproduce as harness
from dsa_evaluation.runner import dataset_provenance

#: The keys §104 carries from the runner into the compared record.
PROVENANCE_KEYS = ("dataset_sha256", "environment")


def _state_dump(**overrides: Any) -> dict[str, Any]:
    """A record shaped like `AnalysisState.model_dump()` -- what the harness already passes."""
    base = {
        "run_id": "r1",
        "dataset_id": "sales",
        "dataset_path": "benchmarks/v2/datasets/sales.csv",
        "user_query": "what sold",
        "tool_calls": [{"tool": "profile_dataset", "status": "ok"}],
        "insights": [{"finding": "x"}],
        "evidence": [{"claim": "y"}],
    }
    base.update(overrides)
    return base


def _fake_run_benchmark(first_payload: list[dict[str, Any]], second_payload: list[dict[str, Any]]):
    """Stand in for `run_benchmark`, writing the artifacts `_reproduce_benchmark` reads.

    The payload lists are the `raw_runs.json` contents for run one and run two; the summary is the
    minimum the aggregation touches (`statistical_accuracy`, `evidence_coverage`).
    """
    payloads = (first_payload, second_payload)
    counter = {"i": 0}

    def fake(catalog: Path, datasets: Path, out: Path, *args: Any, **kwargs: Any) -> dict[str, Any]:
        index = counter["i"]
        counter["i"] += 1
        out.mkdir(parents=True, exist_ok=True)
        (out / "raw_runs.json").write_text(json.dumps(payloads[index]), encoding="utf-8")
        (out / "summary.json").write_text(
            json.dumps({"statistical_accuracy": 1.0, "evidence_coverage": 1.0}), encoding="utf-8"
        )
        return {}

    return fake


def _comparison(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, one: list, two: list) -> dict:
    monkeypatch.setattr(harness, "run_benchmark", _fake_run_benchmark(one, two))
    harness.reproduce_benchmark(tmp_path / "catalog.json", tmp_path / "datasets", tmp_path / "out")
    return json.loads((tmp_path / "out" / "comparison.json").read_text(encoding="utf-8"))


def test_the_runner_records_the_hash_of_the_bytes_it_actually_ran_against(tmp_path: Path) -> None:
    dataset = tmp_path / "sales.csv"
    dataset.write_text("a,b\n1,2\n", encoding="utf-8")

    sha, environment = dataset_provenance(dataset)

    assert sha == sha256_file(dataset)
    assert environment["python_version"]


def test_a_missing_dataset_yields_no_hash_rather_than_a_crash(tmp_path: Path) -> None:
    sha, environment = dataset_provenance(tmp_path / "gone.csv")

    assert sha is None, (
        "an absent dataset is a fact about the run, not an error in the harness; L2 says so itself"
    )
    assert environment["python_version"]


def test_the_compared_record_carries_both_provenance_keys() -> None:
    state = _state_dump()
    record = harness._comparison_record(state, "a" * 64, {"python_version": "3.12"})

    assert record["dataset_sha256"] == "a" * 64
    assert record["environment"] == {"python_version": "3.12"}
    assert record["user_query"] == state["user_query"], "the state fields must survive the merge"


def test_reproduction_now_decides_l2_from_a_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§102's basis field must read `dataset_sha256`, not `dataset_id`, on a normal run."""
    sha = "a" * 64
    one = [{"task_id": "t1", "run_result": _state_dump(), "dataset_sha256": sha, "environment": {}}]
    two = [{"task_id": "t1", "run_result": _state_dump(), "dataset_sha256": sha, "environment": {}}]

    comparison = _comparison(tmp_path, monkeypatch, one, two)

    details = comparison["per_task"][0]["details"]
    assert details["L2_basis"] == "dataset_sha256"
    assert details["L2_same_data"] is True


def test_a_dataset_edited_between_the_two_runs_now_fails_l2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The capability that did not exist: identical ids, different bytes, L2 says False."""
    one = [
        {
            "task_id": "t1",
            "run_result": _state_dump(),
            "dataset_sha256": "a" * 64,
            "environment": {},
        }
    ]
    two = [
        {
            "task_id": "t1",
            "run_result": _state_dump(),
            "dataset_sha256": "b" * 64,
            "environment": {},
        }
    ]

    comparison = _comparison(tmp_path, monkeypatch, one, two)

    details = comparison["per_task"][0]["details"]
    assert details["L2_same_data"] is False, (
        "before §104 this read True: id equality could not see the bytes change"
    )
    assert details["L2_basis"] == "dataset_sha256"


def test_a_run_without_a_hash_still_reports_the_weaker_basis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    one = [
        {"task_id": "t1", "run_result": _state_dump(), "dataset_sha256": None, "environment": {}}
    ]
    two = [
        {"task_id": "t1", "run_result": _state_dump(), "dataset_sha256": None, "environment": {}}
    ]

    comparison = _comparison(tmp_path, monkeypatch, one, two)

    assert comparison["per_task"][0]["details"]["L2_basis"] == "dataset_id"


def test_the_runner_appends_provenance_into_every_raw_run() -> None:
    """Producer pin: the record `run_benchmark` writes must carry what the comparison reads."""
    source = (
        Path(__file__).resolve().parents[2] / "packages/evaluation/src/dsa_evaluation/runner.py"
    )
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        func = getattr(node, "func", None)
        if not (isinstance(node, ast.Call) and isinstance(func, ast.Attribute)):
            continue
        if func.attr != "append" or getattr(func.value, "id", "") != "raw_runs":
            continue
        written = {
            key.value
            for key in node.args[0].keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        assert set(PROVENANCE_KEYS) <= written, written
        return
    raise AssertionError("no `raw_runs.append({...})` literal found in runner.py")
