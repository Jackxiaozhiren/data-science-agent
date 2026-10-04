"""§96 D-L3-07: a malformed `DSA_MAX_COST_USD` used to mean "no cap at all".

`_spend_cap_usd()` wrapped `float(...)` in `except ValueError: return None`, and both cap
guards read `if cap is not None and spent >= cap`. So an operator who set the limit to
`5 USD` or `-1` got the behaviour of not setting it, and the run proceeded to make paid
model calls with no ceiling -- the one direction a spend guard must never fail in.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from dsa_llm.providers import _spend_cap_usd

REPO = Path(__file__).resolve().parents[2]
PROVIDERS = REPO / "packages/llm/src/dsa_llm/providers.py"
ENV = "DSA_MAX_COST_USD"


def test_unset_means_no_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Green-on-arrival: an absent variable is genuinely no limit, and stays so."""
    monkeypatch.delenv(ENV, raising=False)
    assert _spend_cap_usd() is None


def test_blank_means_no_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Green-on-arrival: whitespace is what an empty entry in a .env file looks like."""
    monkeypatch.setenv(ENV, "   ")
    assert _spend_cap_usd() is None


def test_a_real_number_is_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Green-on-arrival: the working configuration must be untouched by this fix."""
    monkeypatch.setenv(ENV, "4.50")
    assert _spend_cap_usd() == pytest.approx(4.5)


def test_a_malformed_value_refuses_instead_of_uncapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV, "5 USD")
    with pytest.raises(ValueError, match=ENV):
        _spend_cap_usd()


def test_a_negative_value_refuses_instead_of_uncapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """`-1` parsed fine and then `cap if cap >= 0 else None` turned it into no limit."""
    monkeypatch.setenv(ENV, "-1")
    with pytest.raises(ValueError, match="negative"):
        _spend_cap_usd()


def test_the_cap_call_sites_are_not_inside_a_swallowing_try() -> None:
    """A raise is only a stop if nothing upstream absorbs it. Parsed, not assumed.

    The widened-catch lesson applies to this fix directly: `_request` would have been free
    to wrap its own body in `except Exception` and quietly resume spending.
    """
    tree = ast.parse(PROVIDERS.read_text(encoding="utf-8"))
    calls = 0
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for call in ast.walk(fn):
            if not (
                isinstance(call, ast.Call) and getattr(call.func, "id", "") == "_spend_cap_usd"
            ):
                continue
            calls += 1
            for node in ast.walk(fn):
                if not isinstance(node, ast.Try):
                    continue
                for handler in node.handlers:
                    if handler.lineno <= call.lineno <= (handler.end_lineno or handler.lineno):
                        raise AssertionError(
                            f"{fn.name}:{call.lineno} sits inside a handler "
                            f"({ast.unparse(handler.type) if handler.type else 'bare'})"
                        )
    assert calls == 2, f"expected the two cap guards, found {calls}"
