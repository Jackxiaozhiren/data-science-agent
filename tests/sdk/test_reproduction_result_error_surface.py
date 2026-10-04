"""§101: ``Reproduction.run()`` published numbers the artifact never held.

Two defects, one root -- the facade read keys it assumed rather than keys the harness writes:

1. every field defaults to ``0.0`` and every failure path returned the defaults, so a caller could
   not tell "the reproduction scored zero" from "there was no ``comparison.json`` to read" -- the one
   confusion the reproducibility facade must not ship. The class documents that it never raises, so
   the fix is not to raise: ``error`` names the reason, the Stable constructor keeps working.
2. the harness writes the trajectory rate under ``semantic`` (``dsa_evaluation/cli.py``
   ``reproduction_score``), and no producer anywhere writes a ``trajectory`` key, so
   ``ReproductionResult.trajectory`` was ``0.0`` for every real run. The committed
   ``reproduction/v2/comparison.json`` reports ``semantic: 1.0`` while the facade published
   ``trajectory=0.0``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from data_science_agent.sdk import (
    REPRODUCTION_DIMENSION_KEYS,
    Reproduction,
    ReproductionResult,
)

#: The key set ``dsa_evaluation.cli`` actually writes, transcribed from the producer.
PRODUCER_KEYS = ("execution", "numerical", "statistical", "evidence", "semantic", "overall")


@pytest.fixture
def silent_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise the harness itself; this test is about what `run` reports, not about scoring."""
    from dsa_evaluation import cli

    def no_op(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(cli, "_reproduce_benchmark", no_op)


def _write(out: Path, payload: object) -> Path:
    out.mkdir()
    (out / "comparison.json").write_text(json.dumps(payload), encoding="utf-8")
    return out


def test_a_real_zero_is_still_a_zero_and_not_an_error(tmp_path: Path, silent_harness: None) -> None:
    """Green-on-arrival guard against over-correcting in the other direction."""
    out = _write(
        tmp_path / "repro",
        {"reproduction_score": dict.fromkeys(PRODUCER_KEYS, 0.0)},
    )

    res = Reproduction().run(out=out)

    assert res.overall == 0.0
    assert res.error is None


def test_a_real_score_clears_the_error(tmp_path: Path, silent_harness: None) -> None:
    out = _write(
        tmp_path / "repro",
        {
            "reproduction_score": {
                "overall": 0.75,
                "execution": 0.7,
                "semantic": 0.8,
                "by_level": {"L0": 1.0},
            }
        },
    )

    res = Reproduction().run(out=out)

    assert res.overall == pytest.approx(0.75)
    assert res.by_level == {"L0": 1.0}
    assert res.error is None


def test_a_partial_artifact_names_the_dimension_it_lacks(
    tmp_path: Path, silent_harness: None
) -> None:
    """A dim the artifact never held must not publish as a measured ``0.0`` either."""
    out = _write(tmp_path / "repro", {"reproduction_score": {"overall": 0.5}})

    res = Reproduction().run(out=out)

    assert res.error is not None
    assert "execution" in res.error and "semantic" in res.error


def test_the_dimension_map_covers_every_published_score_field() -> None:
    """Drift guard: adding a score field to the Stable dataclass requires mapping its source key."""
    published = {
        f.name for f in dataclasses.fields(ReproductionResult) if f.type in (float, "float")
    }

    assert published == set(REPRODUCTION_DIMENSION_KEYS)


def test_the_trajectory_rate_is_read_from_the_key_the_harness_writes(
    tmp_path: Path, silent_harness: None
) -> None:
    """``semantic`` is where the producer puts the trajectory rate; ``trajectory`` is not written."""
    out = _write(
        tmp_path / "repro",
        {"reproduction_score": {"overall": 0.5, "execution": 0.6, "semantic": 0.8}},
    )

    res = Reproduction().run(out=out)

    assert res.trajectory == pytest.approx(0.8), (
        "the facade published 0.0 while the artifact held a measured trajectory"
    )


def test_the_committed_artifact_and_the_facade_agree(silent_harness: None) -> None:
    """End-to-end drift pin: the shipped ``reproduction/v2`` artifact, read through the facade."""
    artifact = Path("reproduction/v2/comparison.json")
    rs = json.loads(artifact.read_text(encoding="utf-8"))["reproduction_score"]

    res = Reproduction().run(out=artifact.parent)

    assert res.overall == pytest.approx(rs["overall"])
    assert res.execution == pytest.approx(rs["execution"])
    assert res.trajectory == pytest.approx(rs["semantic"])
    assert res.by_level == rs["by_level"]
    assert res.error is None


def test_a_missing_comparison_is_reported_as_missing_not_as_zero(
    tmp_path: Path, silent_harness: None
) -> None:
    out = tmp_path / "repro"
    out.mkdir()

    res = Reproduction().run(out=out)

    assert res.overall == 0.0, "the Stable default stays, so no existing caller breaks"
    assert res.error is not None, "no data was indistinguishable from a measured zero"
    assert "comparison.json" in res.error


def test_a_comparison_without_a_reproduction_score_says_so(
    tmp_path: Path, silent_harness: None
) -> None:
    out = _write(tmp_path / "repro", {"something_else": 1})

    res = Reproduction().run(out=out)

    assert res.error is not None
    assert "reproduction_score" in res.error


def test_unparseable_scores_are_reported_not_zeroed(tmp_path: Path, silent_harness: None) -> None:
    out = _write(
        tmp_path / "repro",
        {"reproduction_score": {"overall": "not-a-number", "execution": 1.0, "semantic": 1.0}},
    )

    res = Reproduction().run(out=out)

    assert res.error is not None
    assert "ValueError" in res.error or "not-a-number" in res.error


def test_the_new_field_is_additive_to_the_stable_constructor() -> None:
    """Existing call sites must keep working, positionally included."""
    legacy = ReproductionResult(0.9, 1.0, 0.5, {"L0": 1.0}, "/tmp/x")
    assert legacy.overall == 0.9
    assert legacy.error is None
    assert ReproductionResult(overall=0.9).error is None
