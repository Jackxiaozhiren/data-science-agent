"""Measurement claims in docs must be compared against the repository, not against typed literals.

`stale_test_counts` / `stale_mypy` / `stale_coverage` / `stale_routes` were each a hand-typed list of
numbers someone had once seen -- `155 tests|86+ tests|86 tests`, `81 source files|92 source files`,
`7 routes`. Measured over the scanned surface today they produce **no live coverage at all**: the only
hits are inside `CHANGELOG.md`, where they are release records and therefore false positives. So the
detector could not see `apps/vscode/README.md:83`, which advertises

    uv run pytest tests/vscode -v  # 6 tests: ...

against seven `def test_` in that directory. The replacement is the §74 shape: a small table of
*declared* assertions, each compared with a value derived from the tree.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REAL = REPO / "scripts/check_public_claims.py"


def _load(root: Path):
    spec = importlib.util.spec_from_file_location(f"cpm_{abs(hash(str(root)))}", REAL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    return module


def _scratch(tmp_path: Path, *, files: dict[str, str], tests: dict[str, int]) -> Path:
    for rel, body in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    for rel, count in tests.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f"def test_{i}() -> None:\n    assert True\n" for i in range(count))
        target.write_text(body, encoding="utf-8")
    return tmp_path


def _issues(root: Path) -> list[str]:
    return _load(root).check_measurement_claims(root)


def test_a_stale_test_count_against_the_real_directory_is_flagged(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        files={
            "apps/vscode/README.md": "uv run pytest tests/vscode -v  # 6 tests: a, b, c\n",
        },
        tests={"tests/vscode/test_ext.py": 7},
    )
    found = _issues(root)
    assert any("6" in i and "7" in i for i in found), found
    assert any("apps/vscode/README.md" in i for i in found), found


def test_a_matching_count_is_not_flagged(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        files={"apps/vscode/README.md": "uv run pytest tests/vscode -v  # 7 tests: a, b, c\n"},
        tests={"tests/vscode/test_ext.py": 7},
    )
    assert _issues(root) == []


def test_a_claim_about_an_absent_target_is_reported_not_dropped(tmp_path: Path) -> None:
    """Silence here would read as 'checked and clean' while nothing was compared."""
    root = _scratch(
        tmp_path,
        files={"apps/vscode/README.md": "uv run pytest tests/vscode -v  # 7 tests\n"},
        tests={},
    )
    found = _issues(root)
    assert any("tests/vscode" in i and "absent" in i for i in found), found


def test_the_four_typed_number_patterns_are_gone() -> None:
    tree = ast.parse(REAL.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "PATTERNS" for t in node.targets
        ):
            keys = {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
            break
    else:
        pytest.fail("no PATTERNS dict to inspect")
    dead = {"stale_test_counts", "stale_mypy", "stale_coverage", "stale_routes"}
    assert not (dead & keys), f"typed literals are back in PATTERNS: {sorted(dead & keys)}"
    # naming guards stay: they are a different class and still earn their place
    assert {"old_package_pip", "old_repo"} <= keys, sorted(keys)


def test_the_real_repository_has_a_claim_to_check() -> None:
    """A denominator of zero would make every assertion above pass on nothing.

    The scanned surface must contain at least the vscode line, or the rule is untested here
    rather than working here.
    """
    module = _load(REPO)
    root = REPO
    assert module.measurement_claims_evaluated(root) >= 1, "no measurement claim found on disk"
