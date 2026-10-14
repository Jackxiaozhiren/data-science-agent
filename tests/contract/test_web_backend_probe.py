"""R-11: the wait and the failure have to be distinguishable, from one owner.

Measured while writing this (2026-10-13, the hosted demo, same machine): the first request to a sleeping
free instance took **44.5 s** to answer ``/health`` (``output/lane-c`` capture log, "health warmup: HTTP 200
in 44.507560s"). During that window the app had two states -- ``checking`` and ``down`` -- and the visible
text was the literal word "API" plus a coloured dot, so a first-time visitor could not tell a waking demo
from a broken one. That is B3, and it is the exact moment a trial is lost.

The requirement also names a second ambiguity: an empty list can mean "you are new" or "the backend is
down". The first half of that was closed by §167 (``datasets/page.tsx`` renders the empty state only when
there is no fetch failure); what remained is that a page cannot *know* the backend answered unless something
probed it. So the probe is the owner, and the pages read its phase instead of guessing from their own
request.

Structural checks here, behaviour in ``apps/web/scripts/regression.mjs`` (which is the only browser tooling
CI runs, and where a hanging ``/health`` can be simulated with route interception). Each absence-assertion is
run against a planted mutation so the check is shown capable of failing.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "apps/web/app/lib/backendProbe.ts"
DOT = ROOT / "apps/web/app/components/layout/ApiStatusDot.tsx"
DATASETS = ROOT / "apps/web/app/datasets/page.tsx"

PHASES = ("probing", "warming", "ready", "unreachable")


def _planted(source: str, old: str, new: str, label: str) -> str:
    assert source.count(old) >= 1, (
        f"{label}: the plant's anchor is not in the file -- the check is vacuous"
    )
    changed = source.replace(old, new, 1)
    assert changed != source, f"{label}: the plant did not change anything"
    return changed


def test_the_probe_is_one_owner_with_a_named_phase_for_the_wait() -> None:
    """Four phases, and the waking one is not folded into either neighbour."""
    assert PROBE.is_file(), (
        "apps/web/app/lib/backendProbe.ts does not exist -- nothing owns the wait"
    )
    source = PROBE.read_text(encoding="utf-8")

    declared = re.search(r"export type BackendPhase = ([^;]+);", source)
    assert declared, "no exported BackendPhase union"
    named = set(re.findall(r'"(\w+)"', declared.group(1)))
    assert named == set(PHASES), (
        f"the phase vocabulary is {sorted(named)}, expected {sorted(PHASES)}"
    )

    assert re.search(r"export function nextPhase\(", source), (
        "the phase transition is not a pure function"
    )
    assert re.search(r"export function probeCopy\(", source), "the wording has no owner"
    assert re.search(r"export function useBackendProbe\(", source), (
        "no hook, so every consumer fetches alone"
    )
    assert "useSyncExternalStore" in source, (
        "the hook is not a subscription, so a phase change after mount never repaints the page"
    )


def test_the_retry_is_bounded_and_says_so() -> None:
    """Spec: a bounded retry with a visible attempt count. Unbounded retries look like a hang too."""
    source = PROBE.read_text(encoding="utf-8")
    bound = re.search(r"export const PROBE_ATTEMPTS\s*=\s*(\d+)", source)
    assert bound, "no PROBE_ATTEMPTS bound"
    attempts = int(bound.group(1))
    assert 1 < attempts <= 6, (
        f"attempt bound {attempts} is either a single shot or an infinite wait"
    )

    assert re.search(r"export const PROBE_TIMEOUT_MS\s*=\s*(\d+)", source), "no per-attempt timeout"
    assert "Attempt ${attempt}" in source, (
        "the sentence does not carry the attempt count -- a bounded retry that hides its bound is still a hang"
    )
    # The published attempt is already 1-based; adding to it makes the paragraph disagree with the short
    # label in the same frame (measured: header "1/4" against "Attempt 2 of 4").
    assert not re.search(r"attempt\s*\+\s*1", source), (
        "the copy counts from a different base than the dot"
    )

    unbounded = _planted(
        source,
        f"export const PROBE_ATTEMPTS = {attempts}",
        "export const PROBE_ATTEMPTS = 1",
        "bound",
    )
    retry = re.search(r"export const PROBE_ATTEMPTS\s*=\s*(\d+)", unbounded)
    assert retry and int(retry.group(1)) == 1, (
        "the bound is not read from this line -- the check cannot fail"
    )


def test_a_warming_backend_is_never_described_as_ready_or_as_gone() -> None:
    """The copy is the product decision here, so it is pinned rather than paraphrased.

    Two wrongs this rules out: calling a sleeping instance "unreachable" (the visitor gives up), and calling
    a dead one "waking up" (the visitor waits for nothing). An answer that is not 2xx means something
    replied, so it is not warming -- that distinction is asserted, not assumed.
    """
    source = PROBE.read_text(encoding="utf-8")
    warming = re.search(r'if \(phase === "warming"\) return \(`([^`]+)`', source)
    assert warming, "no warming copy"
    text = warming.group(1).lower()
    assert "free" in text and ("sleep" in text or "idle" in text), (
        f"warming copy does not name the cause: {warming.group(1)!r}"
    )
    assert "error" not in text and "fail" not in text, (
        f"warming copy blames the reader: {warming.group(1)!r}"
    )

    body = source[source.index("export function nextPhase(") :]
    answered = re.search(r'outcome === "answered"[^\n]*return "unreachable"', body)
    assert answered, "a non-2xx answer must not be reported as warming -- something replied"

    swapped = _planted(body, 'return "unreachable";', 'return "warming";', "answered outcome")
    assert not re.search(r'outcome === "answered"[^\n]*return "unreachable"', swapped), (
        "the answered branch is not the one being asserted"
    )


def test_the_status_control_exposes_its_phase_to_a_reader_not_only_to_a_color() -> None:
    """R-13's rule applies here too: status must be conveyed by text, since the dot is the primary signal."""
    source = DOT.read_text(encoding="utf-8")
    assert "useBackendProbe" in source, "the dot still runs its own one-shot fetch"
    assert re.search(r"data-api-state=\{", source), (
        "the phase is not exposed as text/attribute -- a browser test cannot assert it"
    )
    blind = _planted(source, "data-api-state={", "data-blind={", "phase attribute")
    assert not re.search(r"data-api-state=\{", blind), "the attribute is not the one being matched"


def test_the_datasets_entrance_states_the_wait_before_it_happens() -> None:
    """Spec: put the expectation in copy once at the trial's entrance, not in a toast after failure.

    And the empty list must be an assertion about data, not a side effect of a request that never answered:
    "No datasets yet" is only allowed once the probe says the backend is ready.
    """
    source = DATASETS.read_text(encoding="utf-8")
    assert re.search(r"sleeps|idle|wake", source, re.I), (
        "the entrance says nothing about the cold start, so the first 45 seconds are unexplained"
    )
    assert re.search(r"phase === \"ready\"|isReady", source), (
        "the empty state does not depend on the probe answering -- an unreachable API still reads as 'empty'"
    )

    # The file legitimately mentions the ready phase twice (the entrance line and the empty-state gate), so
    # the plant is checked against the gate's own pattern -- a broader regex would survive it and prove
    # nothing.
    gate = r'items\.length === 0 && !err && phase === "ready"'
    assert re.search(gate, source), (
        "the empty state is not gated on readiness by the list-length condition"
    )
    blind = _planted(
        source,
        'items.length === 0 && !err && phase === "ready"',
        'items.length === 0 && !err && phase === "never"',
        "ready gate",
    )
    assert not re.search(gate, blind), "the readiness gate is not the one matched"


ASK_PAGE = ROOT / "apps/web/app/analysis/page.tsx"


def test_the_ask_page_does_not_claim_an_empty_account_while_the_api_is_only_slow() -> None:
    """B4's ambiguity, second entrance: `/analysis` lists datasets in a select.

    With nothing listening the page's own fetch rejects and §167's failure path fires, which is already
    correct. The case that is not handled is a waking instance: the request neither resolves nor rejects, so
    the list is empty and no failure is set, and the page tells a first-time visitor "No datasets loaded --
    upload one" when the truth is that nothing has answered yet. That sentence is a claim about the user's
    account, and it is only safe once the probe says the backend is ready.
    """
    source = ASK_PAGE.read_text(encoding="utf-8")
    assert "useBackendProbe" in source, (
        "the ask page still guesses the backend's state from its own fetch"
    )
    assert re.search(r'phase === "ready"', source), (
        "the empty-list notice is not gated on a ready probe -- a cold start reads as an empty account"
    )
    blind = _planted(source, 'phase === "ready"', 'phase === "never"', "ask-page ready gate")
    assert not re.search(r'phase === "ready"', blind), "the gate matched something else"
