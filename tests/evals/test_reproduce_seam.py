"""§109 (Phase 4 target 2, seam #3): the reproduction harness moves out of the CLI parser.

`dsa_evaluation/cli.py` was 702 lines holding two things: the `dsa` command surface (argparse, ~470
lines in `main`) and the fresh-twice reproduction harness (dataset hashing, the per-task comparison
record, and the whole `_reproduce_benchmark` run). The harness had one external consumer besides the CLI
-- `data_science_agent.sdk.Reproduction` -- and it reached it by importing a name documented as
internal, which is why the SDK needed a fallback at all.

The boundary: `dsa_evaluation.reproduce.reproduce_benchmark` is the harness; `cli.py` is the command
that invokes it. Behaviour-preserving, and pinned by a differential below rather than by assertion.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

EVAL_DIR = Path(__file__).resolve().parents[2] / "packages/evaluation/src/dsa_evaluation"
SDK = Path(__file__).resolve().parents[2] / "src/data_science_agent/sdk.py"


def _top_level_defs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)}


def test_the_harness_lives_in_its_own_module() -> None:
    from dsa_evaluation import reproduce

    assert hasattr(reproduce, "reproduce_benchmark")
    assert {"_datasets_sha256", "_comparison_record"} <= _top_level_defs(EVAL_DIR / "reproduce.py")


def test_the_cli_no_longer_defines_the_harness() -> None:
    defined = _top_level_defs(EVAL_DIR / "cli.py")

    assert "_reproduce_benchmark" not in defined, "the CLI must invoke the harness, not own it"
    assert "_datasets_sha256" not in defined
    assert "_comparison_record" not in defined


def test_the_sdk_reaches_the_harness_through_its_public_name() -> None:
    """The SDK used to import a name documented as internal and paper over it with a fallback.

    Scanned across both files rather than one path, because §112 moved `Reproduction` out of `sdk.py`
    into `measurement.py` -- pinning a filename here would only restate where the code happened to sit.
    """
    sdk_dir = SDK.parent
    imported: list[tuple[str, str]] = []
    for name in ("sdk.py", "measurement.py"):
        tree = ast.parse((sdk_dir / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.append((node.module, ",".join(a.name for a in node.names)))

    assert ("dsa_evaluation.reproduce", "reproduce_benchmark") in imported, imported
    assert not any(
        module == "dsa_evaluation.cli" and "reproduce" in names for module, names in imported
    ), "the SDK must not reach the harness through the CLI module"


def test_the_cli_still_dispatches_to_the_harness() -> None:
    source = (EVAL_DIR / "cli.py").read_text(encoding="utf-8")

    assert "reproduce_benchmark(" in source, "the `dsa reproduce` path must still be wired"
    assert "from dsa_evaluation.reproduce import reproduce_benchmark" in source


def _fake_runs(payload: list[dict[str, Any]]) -> Any:
    def fake(catalog: Path, datasets: Path, out: Path, *args: Any, **kwargs: Any) -> dict[str, Any]:
        out.mkdir(parents=True, exist_ok=True)
        (out / "raw_runs.json").write_text(json.dumps(payload), encoding="utf-8")
        (out / "summary.json").write_text(
            json.dumps({"statistical_accuracy": 1.0, "evidence_coverage": 1.0}), encoding="utf-8"
        )
        return {}

    return fake


def _state(**overrides: Any) -> dict[str, Any]:
    base = {
        "run_id": "r1",
        "dataset_id": "sales",
        "dataset_path": "sales.csv",
        "user_query": "what sold",
        "tool_calls": [{"tool": "run_sql", "status": "ok", "call_id": "c1"}],
        "insights": [{"finding": "x"}],
        "evidence": [{"claim": "y"}],
    }
    base.update(overrides)
    return base


@pytest.fixture
def harness_inputs(tmp_path: Path) -> Path:
    datasets = tmp_path / "datasets"
    datasets.mkdir()
    (datasets / "sales.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "catalog.json").write_text(json.dumps({"tasks": []}), encoding="utf-8")
    return tmp_path


def test_the_harness_end_to_end_still_scores_a_reproduction(
    harness_inputs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the moved module must still do, independent of where the code lives."""
    from dsa_evaluation import reproduce

    rows = [
        {
            "task_id": "t1",
            "run_result": _state(),
            "dataset_sha256": "a" * 64,
            "environment": {"python_version": "3.12"},
        }
    ]
    monkeypatch.setattr(reproduce, "run_benchmark", _fake_runs(rows))

    out = harness_inputs / "repro"
    reproduce.reproduce_benchmark(harness_inputs / "catalog.json", harness_inputs / "datasets", out)

    comparison = json.loads((out / "comparison.json").read_text(encoding="utf-8"))
    score = comparison["reproduction_score"]
    assert set(score) == {
        "execution",
        "numerical",
        "statistical",
        "evidence",
        "semantic",
        "overall",
        "method",
        "by_level",
    }
    assert comparison["per_task"][0]["details"]["L2_basis"] == "dataset_sha256"
    assert (out / "manifest.json").exists()
    assert (out / "environment.json").exists()


def test_the_manifest_records_the_dataset_hash_it_hashed(harness_inputs: Path, monkeypatch) -> None:
    """§90's provenance field survives the move: a real datasets dir yields a real hash."""
    from dsa_evaluation import reproduce

    rows = [{"task_id": "t1", "run_result": _state(), "dataset_sha256": None, "environment": {}}]
    monkeypatch.setattr(reproduce, "run_benchmark", _fake_runs(rows))

    out = harness_inputs / "repro2"
    reproduce.reproduce_benchmark(harness_inputs / "catalog.json", harness_inputs / "datasets", out)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["datasets_sha256"], manifest
    assert manifest["datasets_sha256_note"] == "ok", (
        "§90's convention names the state that produced the value, and a present dir is 'ok'"
    )
