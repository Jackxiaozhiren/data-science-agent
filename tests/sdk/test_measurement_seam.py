"""§112 (Phase 4 target 2, seam #4): the measurement facades are not the agent surface.

``data_science_agent.sdk`` was 716 lines holding two things: the analysis SDK (``Agent`` plus the six
value dataclasses the run produces) and the two *measurement* facades that shell into the evaluation
framework (``Benchmark`` and ``Reproduction``, each with its result dataclass). Only the second group
imports ``dsa_evaluation``, and only the first group is what a notebook or API caller means by "the SDK".

They now live in ``data_science_agent.measurement``. The published import path does not move: ``sdk``
re-exports the four names, so ``from data_science_agent.sdk import Benchmark`` and
``from data_science_agent import Benchmark`` keep resolving to the same objects -- which is what the
``API_STABILITY`` registry and ``docs/v4_3/V4_2_FINAL_TRUTH.md`` both promise.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import data_science_agent
from data_science_agent import measurement
from data_science_agent.sdk import (
    API_STABILITY,
    Benchmark,
    BenchmarkResult,
    Reproduction,
    ReproductionResult,
)

SDK_DIR = Path(__file__).resolve().parents[2] / "src/data_science_agent"

MOVED = ("Benchmark", "BenchmarkResult", "Reproduction", "ReproductionResult")


def _classes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.ClassDef)}


def test_the_measurement_facades_live_in_their_own_module() -> None:
    defined = _classes(SDK_DIR / "measurement.py")

    assert set(MOVED) <= defined, defined
    for name in MOVED:
        assert getattr(measurement, name) is not None


def test_the_sdk_module_no_longer_defines_them() -> None:
    """Re-exporting is the point; defining twice is the drift this prevents."""
    defined = _classes(SDK_DIR / "sdk.py")

    assert not set(MOVED) & defined, sorted(set(MOVED) & defined)


def test_the_documented_import_path_still_resolves_to_the_same_objects() -> None:
    assert Benchmark is measurement.Benchmark
    assert BenchmarkResult is measurement.BenchmarkResult
    assert Reproduction is measurement.Reproduction
    assert ReproductionResult is measurement.ReproductionResult
    assert data_science_agent.Benchmark is measurement.Benchmark
    assert data_science_agent.Reproduction is measurement.Reproduction


def test_every_declared_stability_name_is_importable_from_the_sdk() -> None:
    """The stability registry is a public claim about names; a move must not orphan one."""
    sdk = importlib.import_module("data_science_agent.sdk")
    missing = [name for name in API_STABILITY if not hasattr(sdk, name)]

    assert not missing, f"API_STABILITY declares names that no longer exist: {missing}"


def test_measurement_only_depends_on_the_evaluation_framework() -> None:
    """The seam is real only if the split separates the dependencies too."""
    tree = ast.parse((SDK_DIR / "measurement.py").read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)

    assert any(m.startswith("dsa_evaluation") for m in modules), modules
    assert not any(m.startswith("dsa_agent") for m in modules), (
        f"the measurement facades must not pull in the agent: {sorted(modules)}"
    )
