"""What a model call costs, and what has been spent (audit §116, Phase 4 target 2 seam #8).

Split out of ``dsa_llm.providers``, which held the pricing estimate, the spend ceiling and the call
log beside two HTTP client classes. The ceiling is a control -- §96 turned an unparseable
``DSA_MAX_COST_USD`` from a silent "no limit" into a refusal -- and a control a reviewer has to hunt
for through transport code is a control nobody audits.

``dsa_llm.providers`` re-exports :func:`get_call_log` and :func:`reset_call_log`, because that is the
path its consumers already use; the binding is the same object, not a copy (pinned by
``tests/llm/test_cost_seam.py``).
"""

from __future__ import annotations

import os
from typing import Any

_CALL_LOG: list[dict[str, Any]] = []


def reset_call_log() -> None:
    _CALL_LOG.clear()


def get_call_log() -> list[dict[str, Any]]:
    return [dict(item) for item in _CALL_LOG]


def _usd_for_usage(usage: dict[str, Any]) -> float | None:
    """Estimated USD for one Responses API usage dict using env pricing.

    Returns None when rates are not configured (then no cap can apply).
    """
    try:
        in_rate = float(os.environ["DSA_INPUT_COST_PER_MILLION"])
        out_rate = float(os.environ["DSA_OUTPUT_COST_PER_MILLION"])
    except (KeyError, ValueError):
        return None

    def _n(*keys: str) -> int:
        for k in keys:
            v = usage.get(k)
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                return int(v)
        return 0

    total_in = _n("input_tokens") + _n("input_tokens_details")
    total_out = _n("output_tokens") + _n("output_tokens_details")
    return total_in / 1_000_000 * in_rate + total_out / 1_000_000 * out_rate


_SPEND_CAP_ENV = "DSA_MAX_COST_USD"


def _spend_cap_usd() -> float | None:
    """The configured spend ceiling, or None only when no ceiling was asked for.

    D-L3-07: this used to end in `except ValueError: return None`, and both cap guards test
    `if cap is not None`, so `DSA_MAX_COST_USD="5 USD"` or a negative value was indistinguishable
    from leaving it unset -- a configured money limit silently removed itself, and the run kept
    making paid calls. An unparseable or negative ceiling is now a refusal, not an absence.
    """
    raw = os.environ.get("DSA_MAX_COST_USD", "")
    if not raw.strip():
        return None
    try:
        cap = float(raw)
    except ValueError:
        raise ValueError(
            f"{_SPEND_CAP_ENV}={raw!r} is not a number; refusing to run uncapped. "
            "Set it to a USD amount like 4.50 or unset it to have no ceiling."
        ) from None
    if cap < 0:
        raise ValueError(f"{_SPEND_CAP_ENV}={raw!r} is negative; a spend ceiling must be >= 0.")
    return cap
