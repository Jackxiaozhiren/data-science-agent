"""R-03's web half: a run that fails must look failed, including when it fails before writing anything.

The component already polls (``useLiveProgress`` in ``RunInspector.tsx``) and already null-guards every
``state`` read, so an in-flight row renders as zeros rather than crashing -- that part needed no change and
this file does not pretend to have made it.

What it does need is the row's own ``error``. A crash before the first stage write leaves ``state_json``
null, and the existing "This run failed" card is derived from ``state.tool_calls`` with a non-ok status:
with no state there are no tool calls, so the page would show a FAILED badge over an empty report and never
say why. The row carries the sentence; nothing displayed it.

These checks read the shipped TypeScript rather than a browser, and the browser journey is the acceptance
step (``output/lane-b/``); a text assertion here that cannot go red is decorative, so each one is run
against a planted mutation.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = ROOT / "apps/web/app/analysis/[runId]/RunInspector.tsx"
ASK_PAGE = ROOT / "apps/web/app/analysis/page.tsx"


def _read(path: Path) -> str:
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    return path.read_text(encoding="utf-8")


def _planted(source: str, old: str, new: str, label: str) -> str:
    """Apply a mutation the check must notice, and prove the mutation actually changed the text."""
    assert source.count(old) >= 1, (
        f"{label}: the plant's anchor is not in the file -- the check is vacuous"
    )
    changed = source.replace(old, new, 1)
    assert changed != source, f"{label}: the plant did not change anything"
    return changed


def test_the_row_error_field_reaches_the_component_that_has_to_speak_for_it() -> None:
    """``RunDetail`` must carry ``error``, or the failure sentence never arrives in the browser."""
    source = _read(INSPECTOR)
    block = re.search(r"export type RunDetail = \{(.*?)\n\};", source, re.DOTALL)
    assert block, "RunInspector no longer declares RunDetail as a top-level type"
    fields = set(re.findall(r"^\s{2}(\w+)(?:\?)?:", block.group(1), re.MULTILINE))
    assert "error" in fields, f"RunDetail fields: {sorted(fields)}"

    removed = _planted(
        source, "  error?: string | null;", "  // error removed\n", "RunDetail.error"
    )
    retry = re.search(r"export type RunDetail = \{(.*?)\n\};", removed, re.DOTALL)
    assert retry is not None
    assert "error" not in set(re.findall(r"^\s{2}(\w+)(?:\?)?:", retry.group(1), re.MULTILINE)), (
        "the field census matched something that is not a declared member -- it cannot fail"
    )


def test_a_failed_run_is_reported_from_the_row_and_not_only_from_its_tool_trace() -> None:
    """The failure card has to speak with the row's own voice when there is no tool trace to quote.

    ``FailureCard`` already appears for ``status === "FAILED"`` with no failed calls, so the badge was never
    the gap: what was missing is the sentence. A crash before the first stage write leaves ``state`` null,
    and the card's body is a map over ``state.tool_calls`` -- the page would read "This run failed" with
    nothing underneath it, which is the frozen-looking-failed case the requirement names.
    """
    source = _read(INSPECTOR)
    assert re.search(r"\{run\.error &&", source), (
        "the failure card never renders run.error -- a stateless failure has no stated reason"
    )
    assert re.search(r"error: run\.error", source), (
        "copyDiagnostics omits the row error, so the text a supporter pastes into an issue lacks the reason"
    )

    renamed = _planted(source, "{run.error && (", "{run.dataset_id && (", "run.error render")
    assert not re.search(r"\{run\.error &&", renamed), (
        "the gate still matches after the mutation -- the assertion above proves nothing"
    )


def test_the_ask_form_treats_any_2xx_as_a_started_run() -> None:
    """The create call answers 202 now, and 200 when it reuses a run already in flight.

    A handler that pinned ``status === 201`` would show an error for every successful submit, which is the
    kind of break that a status-code change quietly causes on the client side.
    """
    source = _read(ASK_PAGE)
    assert re.search(r"res\.ok", source), (
        "the ask page no longer decides success from the response class, so a 202 may read as a failure"
    )
    assert "=== 201" not in source and "!== 201" not in source, (
        "the ask page hard-codes 201; R-03 makes 202 (and 200 for a reused run) the normal answer"
    )

    pinned = _planted(source, "if (!res.ok) {", "if (res.status !== 201) {", "201 pin")
    assert "!== 201" in pinned and re.search(r"res\.ok", source), (
        "the plant did not create a pin, or the file already had one"
    )
