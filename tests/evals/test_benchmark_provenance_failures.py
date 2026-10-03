"""§90 L3 adjudication: a provenance field that is absent must carry its reason.

Two of the fourteen `except: pass` / `except: continue` sites in shipped code sat on
benchmark *provenance* artifacts. Both are fixed here by contract, not by message: the
computation still tolerates failure, but the artifact records which case happened.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from dsa_evaluation.cli import _datasets_sha256
from dsa_evaluation.metrics import EvaluationResult, TaskMetrics
from dsa_evaluation.runner import _attach_statistical


def _result() -> EvaluationResult:
    return EvaluationResult(
        task_id="t-1", category="eda", dataset="d.csv", question="q?", metrics=TaskMetrics()
    )


def test_datasets_sha_hashes_names_and_sizes_in_sorted_order(tmp_path: Path) -> None:
    (tmp_path / "b.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "a.csv").write_text("yy\n", encoding="utf-8")
    (tmp_path / "ignored.json").write_text("{}", encoding="utf-8")

    sha, note = _datasets_sha256(tmp_path)

    h = hashlib.sha256()
    for name, size in (("a.csv", 3), ("b.csv", 2)):
        h.update(name.encode())
        h.update(str(size).encode())
    assert sha == h.hexdigest()[:12]
    assert note == "ok"


def test_a_missing_datasets_dir_is_named_not_blanked(tmp_path: Path) -> None:
    sha, note = _datasets_sha256(tmp_path / "absent")

    assert sha is None
    assert note == "datasets dir absent"


def test_a_non_directory_datasets_path_is_named_not_blanked(tmp_path: Path) -> None:
    a_file = tmp_path / "plain.txt"
    a_file.write_text("x", encoding="utf-8")

    sha, note = _datasets_sha256(a_file)

    assert sha is None
    assert note == "datasets path is not a directory"


def test_an_io_failure_while_hashing_is_recorded(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.csv").write_text("x", encoding="utf-8")
    real_stat = Path.stat

    def exploding_stat(self: Path, **kwargs: object) -> object:
        if self.suffix == ".csv":
            raise OSError("disk gone")
        return real_stat(self, **kwargs)

    monkeypatch.setattr(Path, "stat", exploding_stat)

    sha, note = _datasets_sha256(tmp_path)

    assert sha is None
    assert "OSError" in note and "disk gone" in note


def test_statistical_dimensions_are_attached_on_success(monkeypatch) -> None:
    import dsa_evaluation.statistical_eval as statistical_eval

    ev = _result()
    monkeypatch.setattr(
        statistical_eval,
        "evaluate_statistical",
        lambda task, run_result, elapsed_ms: statistical_eval.StatisticalEvaluation(
            task_id="t-1", overall=1.0, error_codes=[]
        ),
    )

    out = _attach_statistical(ev, None, None, elapsed_ms=1)

    assert out.details["evaluator_version"] == "evaluator_v2"
    assert "statistical_eval_error" not in out.details


def test_a_failing_statistical_eval_leaves_no_doubt_about_why_it_is_absent(
    monkeypatch,
) -> None:
    import dsa_evaluation.statistical_eval as statistical_eval

    ev = _result()

    def boom(task: object, run_result: object, elapsed_ms: int) -> object:
        raise RuntimeError("statistical dimension unavailable")

    monkeypatch.setattr(statistical_eval, "evaluate_statistical", boom)

    out = _attach_statistical(ev, None, None, elapsed_ms=1)

    assert out is ev
    assert out.details["statistical_eval_error"] == (
        "RuntimeError: statistical dimension unavailable"
    )
    assert "statistical_eval" not in out.details
