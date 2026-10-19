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


def _dictionary_value(locale: str, key: str) -> str:
    """One key's value out of `lib/locale.ts`, folded so a wrapped line still parses."""
    folded = re.sub(r":\s+", ": ", (ROOT / "apps/web/lib/locale.ts").read_text(encoding="utf-8"))
    parts = folded.split(f"{locale}: {{", 1)
    assert len(parts) == 2, f"UI_STRINGS has no {locale} block written the way this guard parses it"
    # Cut at the block's own closing brace: searching the remainder of the file would let a key defined only
    # in the *other* locale satisfy this one.
    body = parts[1].split("\n  },", 1)[0]
    found = re.search(rf'"{re.escape(key)}": "((?:[^"\\]|\\.)*)"', body)
    assert found, f"{locale} defines no {key!r} -- the probe would render ⟨{key}⟩"
    return found.group(1)


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
    # The waking sentence must carry the attempt count and its bound -- a bounded retry that hides its bound
    # is still a hang. R-13c moved the wording to the locale owner, so what this checks is the placeholder
    # pair in both languages: a zh value that dropped `{total}` would read "第 2 次尝试，共 次".
    for locale in ("en", "zh"):
        warming = _dictionary_value(locale, "probe.warming")
        assert "{attempt}" in warming and "{total}" in warming, (
            f"the {locale} waking sentence names no bound: {warming!r}"
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


COLD_START_MS_MEASURED = 44_500  # hosted demo, 2026-10-13: /health answered 200 after 44.5 s


def test_the_probe_waits_longer_than_the_cold_start_it_is_meant_to_cover() -> None:
    """The budget has to outrun the measurement, and the copy has to promise only what the budget does.

    The first version of this module advertised "can take about a minute" while its own constants added up to
    37 s (4 attempts x 4 s + 21 s of backoff), so on a 44.5 s wake the page told the visitor to keep waiting
    and the code had already published `unreachable`. That is requirement R-11's central claim stated in the
    wrong direction, and no text-matching assertion could see it because every piece of it was individually
    plausible -- so the coverage is computed from the constants here, the same way the runtime computes it.
    """
    source = PROBE.read_text(encoding="utf-8")
    timeout = re.search(r"export const PROBE_TIMEOUT_MS\s*=\s*(\d+)", source)
    attempts = re.search(r"export const PROBE_ATTEMPTS\s*=\s*(\d+)", source)
    backoff = re.search(r"export const PROBE_BACKOFF_MS\s*=\s*\[([\d,\s]+)\]", source)
    assert timeout and attempts and backoff, (
        "one of the three budget constants is missing or renamed"
    )

    timeouts_ms = int(timeout.group(1))
    count = int(attempts.group(1))
    waits = [int(part) for part in backoff.group(1).replace(" ", "").split(",") if part]
    assert waits, "PROBE_BACKOFF_MS is empty"

    # Mirror `probeSequence`: one timeout per attempt, one backoff per gap, clamped to the last entry.
    coverage = count * timeouts_ms + sum(
        waits[min(gap, len(waits) - 1)] for gap in range(count - 1)
    )
    assert coverage >= COLD_START_MS_MEASURED, (
        f"the probe gives up after {coverage / 1000:.1f}s but the measured cold start is "
        f"{COLD_START_MS_MEASURED / 1000}s -- a waking instance would be reported as unreachable"
    )

    # The budget is derived in one place rather than restated, so the UI and this guard cannot drift apart.
    assert re.search(r"export const PROBE_BUDGET_MS\s*=", source), (
        "no derived PROBE_BUDGET_MS -- coverage would then live only in prose"
    )

    # The promise inside the waking sentence is what the budget has to keep. R-13c moved the words to the
    # locale owner, so the promise is read from there -- in both languages, because a reader of either is owed
    # the same coverage, and a zh sentence that quietly dropped the wait would otherwise be invisible here.
    for locale in ("en", "zh"):
        warming = _dictionary_value(locale, "probe.warming")
        assert re.search(r"minute|分钟|second|秒", warming, re.I), (
            f"the {locale} waking sentence names no wait, so the reader cannot tell how long to stay"
        )
        if re.search(r"minute|分钟", warming, re.I):
            assert coverage >= 45_000, (
                f"the {locale} warming copy promises about a minute but the probe stops at "
                f"{coverage / 1000:.1f}s"
            )

    thin = _planted(
        source,
        f"export const PROBE_TIMEOUT_MS = {timeouts_ms}",
        "export const PROBE_TIMEOUT_MS = 1000",
        "per-attempt timeout",
    )
    re_timeouts = re.search(r"export const PROBE_TIMEOUT_MS\s*=\s*(\d+)", thin)
    assert re_timeouts and int(re_timeouts.group(1)) == 1000, (
        "the plant did not reach the line the coverage reads"
    )
    planted_coverage = count * int(re_timeouts.group(1)) + sum(
        waits[min(gap, len(waits) - 1)] for gap in range(count - 1)
    )
    assert planted_coverage < COLD_START_MS_MEASURED, (
        "a 1 s attempt still clears the bound, so this guard could not fail on a shrinking budget"
    )


def test_the_wait_is_named_while_it_is_happening() -> None:
    """Coverage and legibility are two different clocks, and the shorter one has to win the first paint.

    Fixing the budget to clear 44.5 s pushed `warming` out to 12.4 s -- the tour measured it -- because the
    phase used to be published only when an attempt *ended*. A visitor then stared at "Checking API…" for the
    whole first attempt, which is the same silence R-11 was raised about. So a request that has not answered
    within the hint window repaints as `warming` while still in flight, and the browser scenario asserts the
    number.
    """
    source = PROBE.read_text(encoding="utf-8")
    hint = re.search(r"export const PROBE_SILENCE_HINT_MS\s*=\s*(\d+)", source)
    timeout = re.search(r"export const PROBE_TIMEOUT_MS\s*=\s*(\d+)", source)
    assert hint and timeout, "the silence hint or the attempt timeout is missing"
    hint_ms, timeout_ms = int(hint.group(1)), int(timeout.group(1))
    assert hint_ms < timeout_ms, (
        f"the hint fires at {hint_ms}ms but an attempt lasts {timeout_ms}ms -- nothing would repaint until the attempt ends"
    )

    assert re.search(r"setTimeout\(onSilent, PROBE_SILENCE_HINT_MS\)", source), (
        "the hint timer is not what drives the silence callback"
    )
    assert re.search(r"clearTimeout\(hint\)", source), (
        "the hint timer is never cancelled, so it fires after the answer"
    )
    assert re.search(
        r'if \(snapshot\.phase === "probing"\) publish\(\{ phase: "warming"', source
    ), (
        "warming is published without checking that the request is still outstanding -- an answered failure "
        "could be repainted as a wake-up"
    )

    long_hint = _planted(
        source,
        f"export const PROBE_SILENCE_HINT_MS = {hint_ms}",
        f"export const PROBE_SILENCE_HINT_MS = {timeout_ms + 1}",
        "hint window",
    )
    re_hint = re.search(r"export const PROBE_SILENCE_HINT_MS\s*=\s*(\d+)", long_hint)
    assert re_hint and int(re_hint.group(1)) > timeout_ms, (
        "the plant did not reach the line the comparison reads"
    )


def test_a_warming_backend_is_never_described_as_ready_or_as_gone() -> None:
    """The copy is the product decision here, so it is pinned rather than paraphrased.

    Two wrongs this rules out: calling a sleeping instance "unreachable" (the visitor gives up), and calling
    a dead one "waking up" (the visitor waits for nothing). An answer that is not 2xx means something
    replied, so it is not warming -- that distinction is asserted, not assumed.
    """
    source = PROBE.read_text(encoding="utf-8")
    # The sentence names the cause, in whichever language it is read, and does not blame the reader for a
    # sleeping machine. Wording moved to the locale owner in R-13c, so the keywords are checked per locale --
    # an English-only assertion here would pass while the zh reader was told nothing about why they are waiting.
    for locale, cause, sleep in (
        ("en", "free", ("sleep", "idle")),
        ("zh", "免费", ("休眠", "空闲")),
    ):
        warming = _dictionary_value(locale, "probe.warming")
        text = warming.lower()
        assert cause in text and any(word in text for word in sleep), (
            f"the {locale} warming copy does not name the cause: {warming!r}"
        )
        assert not any(word in text for word in ("error", "fail", "错误", "失败")), (
            f"the {locale} warming copy blames the reader: {warming!r}"
        )
    assert 't(locale, "probe.warming")' in source, (
        "the probe no longer renders the waking sentence through its owner"
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
    # R-13 moved the sentence into the string owner so it can be said in Chinese as well; the entrance is still
    # asserted to render it, and the wording is asserted where it now lives.
    assert 't(locale, "ds.coldStart")' in " ".join(source.split()), (
        "the entrance no longer renders the cold-start expectation through its owner"
    )
    for locale in ("en", "zh"):
        # Read the value out of *that* locale's block. Splitting on `en: {` and searching the remainder used to
        # walk into the zh block, so an en sentence deleted in English only still passed the en arm.
        sentence = _dictionary_value(locale, "ds.coldStart")
        assert re.search(r"sleeps|idle|wake|休眠|空闲", sentence, re.I), (
            f"the {locale} entrance says nothing about the cold start, so the first 45 seconds are unexplained"
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
