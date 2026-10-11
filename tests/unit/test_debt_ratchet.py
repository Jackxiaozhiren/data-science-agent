"""The ratchet's second consumer: a red gate must survive without anyone running a CLI.

A check that only exists as a command line is a check that gets skipped. These
tests import the collector directly, so CI's ``pytest`` step fails on debt regrowth
even if the dedicated ratchet step is dropped from a workflow.

The last three tests are the point of the file: a guard nobody has watched fail is
a guard that may be vacuous. Each fires a deliberate violation and asserts the
ratchet names it.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
LIMITS = ROOT / "docs" / "audit" / "facts.limits.json"


def _collector() -> Any:
    spec = importlib.util.spec_from_file_location(
        "audit_facts", ROOT / "scripts" / "audit_facts.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def facts() -> dict[str, Any]:
    return _collector().collect_facts()


def test_limits_file_is_committed_policy() -> None:
    assert LIMITS.is_file(), "docs/audit/facts.limits.json is the reviewable ceiling ledger"
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    assert limits.get("_seededAtHead"), "the ledger must record the ref it was seeded at"
    assert limits.get("_keys") or limits.get("_floorKeys"), "an empty ledger guards nothing"


def test_every_guarded_key_is_actually_measured(facts: dict[str, Any]) -> None:
    """A key the ledger names that nothing measures is a silent no-op."""
    collector = _collector()
    leaves = collector.numeric_leaves(facts)
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    declared = set(limits.get("ceiling", {})) | set(limits.get("floor", {}))
    unmeasured = sorted(key for key in declared if key not in leaves)
    assert not unmeasured, f"ledger guards keys nothing measures: {unmeasured}"


def test_every_ceiling_key_states_the_debt_it_guards() -> None:
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    reasons = limits.get("_keys", {})
    for key in limits.get("ceiling", {}):
        assert reasons.get(key), f"{key} has no reason string: a reviewer cannot vote on it"
    assert limits.get("_excluded"), "the excluded-key register must travel with its reasons"


def test_the_ratchet_is_currently_satisfied(facts: dict[str, Any]) -> None:
    collector = _collector()
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    report = collector.evaluate_ratchet(facts, limits)
    assert not report["violations"], f"debt grew past its ceiling: {report['violations']}"


def test_ratchet_fails_when_debt_grows(facts: dict[str, Any]) -> None:
    collector = _collector()
    leaves = collector.numeric_leaves(facts)
    key = "debt.suppressionDirectives"
    tampered = {"ceiling": {key: max(leaves[key] - 1, -1)}, "floor": {}}
    report = collector.evaluate_ratchet(facts, tampered)
    problems = {v["problem"] for v in report["violations"]}
    assert "debt_grew" in problems, "the ratchet did not notice a ceiling being crossed"


def test_ratchet_fails_when_a_floor_guard_shrinks(facts: dict[str, Any]) -> None:
    collector = _collector()
    leaves = collector.numeric_leaves(facts)
    tampered = {"ceiling": {}, "floor": {"debt.testFunctions": leaves["debt.testFunctions"] + 1}}
    report = collector.evaluate_ratchet(facts, tampered)
    assert any(v["problem"] == "guard_shrank" for v in report["violations"])


def test_ratchet_fails_when_a_key_stops_being_measured(facts: dict[str, Any]) -> None:
    collector = _collector()
    tampered = {"ceiling": {"debt.nothing_ever_measures_this": 1}, "floor": {}}
    report = collector.evaluate_ratchet(facts, tampered)
    assert any(v["problem"] == "key_no_longer_measured" for v in report["violations"])


def test_capability_probes_report_contradictions_not_opinions(facts: dict[str, Any]) -> None:
    """Each warning id must be a measured pair the reader can re-derive, never a verdict."""
    for entry in facts["warnings"]["contradictions"]:
        assert isinstance(entry, str) and entry, f"malformed warning id: {entry!r}"
        assert not any(word in entry.lower() for word in ("bad", "should", "must", "broken")), (
            f"probe emitted a judgement instead of a contradiction: {entry}"
        )


def test_excluded_keys_are_not_secretly_ceilings(facts: dict[str, Any]) -> None:
    collector = _collector()
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    leaked = sorted(set(limits.get("ceiling", {})) & set(collector.EXCLUDED_KEYS))
    assert not leaked, f"these keys were documented as ungateable yet carry a ceiling: {leaked}"


def test_seed_preserves_human_authored_notes(tmp_path: Path, facts: dict[str, Any]) -> None:
    """The limits ledger is a reviewable policy asset, so a re-seed must not eat prose.

    A generator silently overwriting a human's provenance note is the same failure
    class as hand-editing a generated mirror: the edit looks shipped and is gone at
    the next run. Isolated in tmp_path so the committed ledger is never touched.
    """
    collector = _collector()
    limits = tmp_path / "facts.limits.json"
    monkeypatch_module_paths(collector, limits, tmp_path / "facts.snapshot.json")
    assert collector._seed(facts) == 0
    written = json.loads(limits.read_text(encoding="utf-8"))
    written["_reviewNote"] = "a human's reasoning, not a measurement"
    limits.write_text(json.dumps(written), encoding="utf-8")
    assert collector._seed(facts) == 0
    assert json.loads(limits.read_text(encoding="utf-8"))["_reviewNote"], (
        "re-seed clobbered policy prose"
    )


def monkeypatch_module_paths(collector: Any, limits: Path, snapshot: Path) -> None:
    collector.LIMITS = limits
    collector.SNAPSHOT = snapshot


def test_committed_registers_match_the_collector_that_wrote_them(facts: dict[str, Any]) -> None:
    """The ledger's reason registers are written by the collector, so they must agree.

    A key can be redefined in code and left stale in the committed policy; the gate
    then enforces one thing while the reviewable contract describes another. This
    test is what makes a partial re-seed or a hand edit visible instead of silent.
    """
    collector = _collector()
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    assert limits["_keys"] == collector.CEILING_KEYS, "ceiling reasons drifted from the code"
    assert limits["_floorKeys"] == collector.FLOOR_KEYS, "floor reasons drifted from the code"
    assert limits["_excluded"] == collector.EXCLUDED_KEYS, "the exclusion register drifted"
    assert not (set(limits["ceiling"]) & set(collector.EXCLUDED_KEYS)), "an excluded key is gated"
    assert set(limits["ceiling"]) == set(collector.CEILING_KEYS), "a keyed ceiling is missing"


def test_the_redefined_swallow_key_is_a_live_ceiling_not_a_printout(facts: dict[str, Any]) -> None:
    """One unit of headroom is the proof the key measures something.

    `debt.swallowedExceptionSites` was redefined to an AST count on 2026-10-03 and its
    ceiling moved with it. A redefined key is exactly the kind of gate that can quietly
    stop firing -- so the ceiling is set at the measured value, and this fires the
    violation the next swallow would produce, without touching the committed ledger.
    """
    collector = _collector()
    leaves = collector.numeric_leaves(facts)
    measured = leaves["debt.swallowedExceptionSites"]
    tampered = {"ceiling": {"debt.swallowedExceptionSites": measured - 1}, "floor": {}}
    report = collector.evaluate_ratchet(facts, tampered)
    problems = {(v["key"], v["problem"]) for v in report["violations"]}
    assert ("debt.swallowedExceptionSites", "debt_grew") in problems, (
        "a handler whose body is only `pass` would not be noticed by the redefined key"
    )
    committed = json.loads(LIMITS.read_text(encoding="utf-8"))["ceiling"][
        "debt.swallowedExceptionSites"
    ]
    assert committed == measured, (
        f"the ledger ceilings this at {committed} while the tree reads {measured}; "
        "slack here is unvoted headroom, and a number lower than the reading means the "
        "fix was never recorded"
    )


def test_the_swallow_key_counts_swallowing_and_not_the_shape_of_except(
    tmp_path: Path,
) -> None:
    """§90's redefinition, pinned: a re-raising handler must cost nothing.

    The key was written as ``SWALLOW_RE`` over source lines, which matched any line shaped
    like an ``except`` header. This tree has three handlers and two of them can only hide a
    failure; the retired line-shaped instrument scored **five** for it, and three of those
    five are not swallows at all -- a comment reading "The exception is deliberately
    narrow:", a membership test on a variable named ``exceptions``, and a handler that
    re-raises. Kept as a standing demonstration, because "180 sites" is quoted in five
    places and none of them measured a site.
    """
    collector = _collector()
    (tmp_path / "real_swallow.py").write_text(
        "def f(d):\n"
        "    try:\n"
        '        return d["k"]\n'
        "    except Exception:\n"
        "        pass\n"
        "    return None\n"
        "\n"
        "\n"
        "def g(items):\n"
        "    for i in items:\n"
        "        try:\n"
        "            int(i)\n"
        "        except ValueError:\n"
        "            continue\n"
        "    return len(items)\n",
        encoding="utf-8",
    )
    (tmp_path / "loud_handlers.py").write_text(
        "class Broken(Exception):\n"
        "    pass\n"
        "\n"
        "\n"
        "def f(path):\n"
        "    try:\n"
        "        return path.read_text()\n"
        "    except OSError as exc:\n"
        "        raise Broken(str(exc)) from exc\n"
        "\n"
        "\n"
        "def narrow(text):\n"
        "    # The exception is deliberately narrow:\n"
        '    return "except" in text\n'
        "\n"
        "\n"
        "def registry():\n"
        "    exceptions = {}\n"
        '    if "k" not in exceptions:\n'
        '        exceptions["k"] = 1\n'
        "    return exceptions\n",
        encoding="utf-8",
    )
    paths = sorted(tmp_path.glob("*.py"))
    handlers, swallows = collector._handler_shapes(paths)
    assert (handlers, swallows) == (3, 2), (
        f"expected 3 handlers with 2 that can only hide a failure, got {(handlers, swallows)}"
    )

    # The retired instrument, re-derived here so the disagreement stays checkable.
    import re

    line_shaped = re.compile(r"except[^\n:]*:\s*(?:#.*)?$|except.*:\s*pass$")
    scored = sum(
        1
        for p in paths
        for line in p.read_text(encoding="utf-8").splitlines()
        if line_shaped.search(line)
    )
    assert scored == 5, scored
    assert scored != swallows, "if these ever agree the demonstration has stopped meaning anything"


def test_an_unparseable_shipped_file_is_counted_not_skipped_silently(tmp_path: Path) -> None:
    """A counter that quietly drops a file it cannot parse reports less debt, not fewer files.

    The boundary is part of the contract: this pass parses only files whose text contains
    `except`, because a conservative prefilter cost +0.195s of the collector's sub-second
    promise. So the visible skip covers exactly the files that could have held a handler,
    and a file with no `except` in it is never listed here -- which is provably harmless,
    since no handler can exist in it.
    """
    collector = _collector()
    (tmp_path / "broken.py").write_text(
        "def f():\n"
        "    try:\n"
        "        return 1\n"
        "    except ValueError\n"  # missing colon: a handler-shaped file that cannot parse
        "        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "good.py").write_text(
        "def g():\n    try:\n        return 1\n    except ValueError:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "quiet.py").write_text("def h():\n    return 1\n", encoding="utf-8")

    paths = sorted(tmp_path.glob("*.py"))
    handlers, swallows = collector._handler_shapes(paths)
    assert (handlers, swallows) == (1, 1), "a file that fails to parse must not zero out the rest"
    unparseable = [p.name for p in collector._unparseable_shipped_files(paths)]
    assert unparseable == ["broken.py"], unparseable


AUDIT_DOC = "REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md"


def test_the_apparatus_ceiling_counts_the_audit_document_and_nothing_else(tmp_path: Path) -> None:
    """§150: a prompt-shaped *name* is not the debt the key describes.

    `debt.auditApparatusLines` was collected as the line count of every root markdown whose
    name matches `^[A-Z][A-Z_]*_(PROMPT|SPEC)\\.md$`. §149 measured what that costs: an
    unrelated product PRD dropped at root pushed the reading to 1659 against a ceiling of
    1128, and 1128 is the audit document alone -- so the gate was about to red main over
    somebody else's writing, and the only ways to silence it were raising a ceiling or
    deleting a document. Here the subject is the audit series' own prose budget, so the
    count is by declared document, and a foreign file in the same shape costs nothing.
    """
    collector = _collector()
    (tmp_path / AUDIT_DOC).write_text("a\nb\nc\nd\ne\n", encoding="utf-8")
    (tmp_path / "SOME_OTHER_MASTER_PROMPT.md").write_text("x\n" * 100, encoding="utf-8")
    assert collector._apparatus_lines(tmp_path) == 5, (
        "the apparatus count must be the audit document's own volume, not every prompt-shaped name"
    )


def test_an_undeclared_prompt_document_is_named_rather_than_silently_uncounted(
    tmp_path: Path,
) -> None:
    """Scoping the key down must not open a hole the same size.

    Counting by declared name means a second audit-series document added without being
    declared would escape the ceiling with no signal at all -- the blind spot an ignore
    list always grows. So anything at root that matches the old pattern and is in neither
    register is reported, and `debt.unclassifiedApparatusDocs` keeps that report at zero.
    A declared name that is absent is not an error: the register outlives the file.
    """
    collector = _collector()
    (tmp_path / AUDIT_DOC).write_text("a\n", encoding="utf-8")
    (tmp_path / "NEW_AUDIT_PROMPT.md").write_text("b\n", encoding="utf-8")
    (tmp_path / "WEB_PRODUCT_MASTER_PROMPT.md").write_text("c\n", encoding="utf-8")
    assert collector._unclassified_apparatus(tmp_path) == ["NEW_AUDIT_PROMPT.md"]
    assert AUDIT_DOC in collector.AUDIT_APPARATUS_DOCS
    assert "WEB_PRODUCT_MASTER_PROMPT.md" in collector.NON_APPARATUS_DOCS


def test_growing_the_audit_document_still_moves_the_ceiling(tmp_path: Path) -> None:
    """The scoped key must still be able to fire, or §150 traded a false red for no guard.

    One added line above the committed ceiling is the whole contract of this key: the
    audit document may only grow by cutting a line elsewhere.
    """
    collector = _collector()
    real = len((ROOT / AUDIT_DOC).read_text(encoding="utf-8").splitlines())
    committed = json.loads(LIMITS.read_text(encoding="utf-8"))["ceiling"][
        "debt.auditApparatusLines"
    ]
    assert committed == real, f"ceiling {committed} while the document reads {real}"
    (tmp_path / AUDIT_DOC).write_text("line\n" * (real + 1), encoding="utf-8")
    grown = collector._apparatus_lines(tmp_path)
    assert grown == committed + 1, grown
    report = collector.evaluate_ratchet(
        {"debt": {"auditApparatusLines": grown}},
        {"ceiling": {"debt.auditApparatusLines": committed}, "floor": {}},
    )
    assert ("debt.auditApparatusLines", "debt_grew") in {
        (v["key"], v["problem"]) for v in report["violations"]
    }, "one line over the cap went unnoticed"


def test_the_live_tree_reads_the_apparatus_ceiling_exactly(facts: dict[str, Any]) -> None:
    """No headroom, and no foreign file inside the number -- measured on this tree.

    The working tree may hold another session's untracked `*_PROMPT.md` (it did on
    2026-10-11); that must not be visible in this key, and nothing the audit series owns
    may be hidden in it either.
    """
    collector = _collector()
    leaves = collector.numeric_leaves(facts)
    real = len((ROOT / AUDIT_DOC).read_text(encoding="utf-8").splitlines())
    assert leaves["debt.auditApparatusLines"] == real
    assert leaves["debt.unclassifiedApparatusDocs"] == 0, (
        "a root prompt-shaped document exists that neither register claims"
    )
