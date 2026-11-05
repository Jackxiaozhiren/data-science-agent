"""The wake budget must stay above the slowest wake anyone has measured.

`apps/web/app/lib/backendProbe.ts` holds a visitor in a "waking" state for a bounded time and only then
declares the backend unreachable. That bound is `PROBE_BUDGET_MS`, computed from one per-attempt ceiling,
an attempt count and a backoff list. The module header records why it is computed rather than restated:
the first budget cleared the 44.5 s wake measured on 2026-10-13 and then gave up during the 92.8 s wake
measured on 2026-10-22, reporting a sleeping machine as a dead one -- the defect R-11 exists to remove.

Two wakes are on record, and a third was witnessed in a browser on 2026-11-05 (AUDIT_LEDGER §318):
81.5 s from the first `/health` request to the first 200, with three consecutive 18 s attempts timing
out before the fourth caught the answer. The slowest remains the 2026-10-22 curl measurement, so that
is the floor this guard defends.

What a green here means, and does not: the bound still exceeds every wake anyone wrote down. It does
not mean a wake was observed, and it does not test the phase machine -- the numbers are read from the
source, so the only thing proven is that the arithmetic still clears the recorded floor.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "apps" / "web" / "app" / "lib" / "backendProbe.ts"

#: Slowest wake on record: 2026-10-22, `curl -w` with the connection held open, cited in the module header.
SLOWEST_RECORDED_WAKE_MS = 92_800
#: Browser witness, 2026-11-05 (§318): first `/health` request to the first 200, three aborts in between.
BROWSER_WITNESS_WAKE_MS = 81_532


def _source() -> str:
    assert PROBE.is_file(), (
        f"{PROBE.relative_to(ROOT)} is gone; the probe's budget can no longer be checked against the "
        "measurements it exists to cover"
    )
    return PROBE.read_text(encoding="utf-8")


def _scalar(name: str) -> int:
    match = re.search(rf"(?m)^export const {name} = ([0-9][0-9_]*);", _source())
    assert match, (
        f"backendProbe.ts no longer declares a literal `{name}`, so the budget cannot be recomputed "
        "from its parts and this guard would silently stop checking anything"
    )
    return int(match.group(1).replace("_", ""))


def _backoff() -> list[int]:
    match = re.search(r"(?m)^export const PROBE_BACKOFF_MS = \[([^\]]*)\] as const;", _source())
    assert match, "backendProbe.ts no longer declares `PROBE_BACKOFF_MS` as a literal tuple"
    values = [int(v.strip().replace("_", "")) for v in match.group(1).split(",") if v.strip()]
    assert values, (
        "the backoff list is empty, so every attempt follows the previous one with no gap and the "
        "budget is no longer the quantity the module header describes"
    )
    return values


def _budget_ms() -> int:
    """The same arithmetic as `PROBE_BUDGET_MS`: one ceiling per attempt, plus one backoff per gap."""
    attempts = _scalar("PROBE_ATTEMPTS")
    timeout = _scalar("PROBE_TIMEOUT_MS")
    backoff = _backoff()
    gaps = [backoff[min(gap, len(backoff) - 1)] for gap in range(max(0, attempts - 1))]
    return attempts * timeout + sum(gaps)


def test_the_budget_is_computed_from_its_three_parts_not_restated() -> None:
    """A restated constant can drift from the three values it claims to be derived from."""
    derived = re.search(r"(?s)export const PROBE_BUDGET_MS =\s*(.*?);", _source())
    assert derived, "backendProbe.ts no longer declares `PROBE_BUDGET_MS`"
    body = derived.group(1)
    missing = [
        name
        for name in ("PROBE_ATTEMPTS", "PROBE_TIMEOUT_MS", "PROBE_BACKOFF_MS")
        if name not in body
    ]
    assert not missing, (
        "PROBE_BUDGET_MS no longer refers to "
        + ", ".join(missing)
        + ", so it is a restated number that can disagree with the constants it is supposed to follow"
    )


def test_the_budget_exceeds_the_slowest_recorded_wake() -> None:
    budget = _budget_ms()
    assert budget >= SLOWEST_RECORDED_WAKE_MS, (
        f"PROBE_BUDGET_MS computes to {budget} ms, below the {SLOWEST_RECORDED_WAKE_MS} ms wake measured "
        "on 2026-10-22. A sequence that gives up first reports a sleeping instance as a dead one, which "
        "is the regression the module header records from the 44.5 s era."
    )


def test_the_budget_also_covers_the_browser_witness() -> None:
    budget = _budget_ms()
    assert budget >= BROWSER_WITNESS_WAKE_MS, (
        f"PROBE_BUDGET_MS computes to {budget} ms, below the {BROWSER_WITNESS_WAKE_MS} ms wake observed "
        "in a browser on 2026-11-05 (AUDIT_LEDGER §318), where the fourth attempt was still in flight "
        "when the instance answered."
    )


def test_the_waiting_hint_stays_much_shorter_than_one_attempt() -> None:
    """The budget buys coverage; the hint is what makes the wait visible while it happens."""
    hint = _scalar("PROBE_SILENCE_HINT_MS")
    timeout = _scalar("PROBE_TIMEOUT_MS")
    assert hint * 4 <= timeout, (
        f"PROBE_SILENCE_HINT_MS is {hint} ms against a {timeout} ms attempt ceiling, so a waiting visitor "
        "is left on the probing copy for a quarter of the attempt or longer -- the 18 s silence the hint "
        "exists to break up"
    )


def test_the_sequence_is_bounded_but_not_degenerate() -> None:
    attempts = _scalar("PROBE_ATTEMPTS")
    assert attempts >= 2, (
        f"PROBE_ATTEMPTS is {attempts}: a single attempt cannot outlast a wake that takes several "
        "timeouts, because the whole sequence ends inside the first one"
    )
    assert _scalar("PROBE_TIMEOUT_MS") > 0
