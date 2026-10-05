"""§110: a mistyped `%dsa` flag used to vanish without a trace.

§96 left the three `except SystemExit: return None` handlers in `apps/jupyter/magic.py` unread "to claim
either way". This measures them: they are benign -- argparse prints a usage block to stderr before it
raises, so `%dsa benchmark --limit` (missing value) reports 110-113 bytes of `usage: %dsa benchmark …`
and then returns ``None`` to keep a traceback out of the notebook.

The real defect is one line earlier. Each of the three handlers called
``ns, _ = parser.parse_known_args(args)`` and threw the leftover list away, so an argument the magic does
not know about is *silently ignored*: measured, `%dsa profile sales.csv --jsoon` (a typo of ``--json``)
prints nothing about ``--jsoon`` and profiles the dataset as if the flag had never been typed.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import io
from pathlib import Path

import pytest
from dsa_jupyter.magic import _known_args

MAGIC = Path(__file__).resolve().parents[2] / "apps/jupyter/src/dsa_jupyter/magic.py"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="%dsa profile", add_help=False)
    parser.add_argument("dataset", nargs="?", default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def test_an_unknown_flag_is_reported_instead_of_vanishing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    ns = _known_args(_parser(), ["sales.csv", "--jsoon"])

    assert ns.dataset == "sales.csv", "the recognized arguments still parse"
    err = capsys.readouterr().err
    assert "--jsoon" in err, "a typo must name itself, not be dropped on the floor"
    assert "%dsa profile" in err


def test_a_clean_invocation_says_nothing() -> None:
    """The other direction: valid input must not start producing noise."""
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        ns = _known_args(_parser(), ["sales.csv", "--json"])

    assert ns.json is True
    assert buffer.getvalue() == ""


def test_a_declared_flag_with_a_missing_value_still_raises_systemexit() -> None:
    """The behaviour the existing `except SystemExit` handlers were written around must survive.

    Measured while writing this: an *unknown* flag cannot raise -- `parse_known_args` hands it back as
    a leftover, which is precisely the hole §110 closes. Only a declared option with an absent value
    reaches argparse's error path.
    """
    parser = _parser()
    parser.add_argument("--limit", type=int)

    with pytest.raises(SystemExit):
        _known_args(parser, ["--limit"])


def test_no_handler_discards_the_leftovers_anymore() -> None:
    """Structural pin: `ns, _ = parse_known_args(...)` was the shape that hid the typo."""
    tree = ast.parse(MAGIC.read_text(encoding="utf-8"))
    discarded: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        if not (isinstance(func, ast.Attribute) and func.attr == "parse_known_args"):
            continue
        for target in node.targets:
            if isinstance(target, ast.Tuple) and any(
                isinstance(e, ast.Name) and e.id == "_" for e in target.elts
            ):
                discarded.append(node.lineno)

    assert not discarded, f"parse_known_args results discarded at lines {discarded}"
    assert "_known_args(" in MAGIC.read_text(encoding="utf-8")


def test_the_helper_is_used_by_every_handler_that_parses() -> None:
    """Three handlers parsed; all three must go through the reporting helper."""
    tree = ast.parse(MAGIC.read_text(encoding="utf-8"))
    using = 0
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_known_args"
        ):
            using += 1

    assert using == 3, (
        f"expected the three parsing handlers to route through the helper, saw {using}"
    )


def test_the_report_goes_to_stderr_and_not_stdout() -> None:
    """A notebook renders a magic's stdout as the cell result, so that is the wrong place for a warning."""
    err, out = io.StringIO(), io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        _known_args(_parser(), ["sales.csv", "--nope"])

    assert "--nope" in err.getvalue()
    assert out.getvalue() == "", (
        "the dataset listing is the cell's output; a warning must not join it"
    )
