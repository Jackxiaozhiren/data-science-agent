"""R-13b: a control may not claim a delivery the browser has refused.

Found by reading the run report in a live browser rather than by a source sweep: `toggleNotify` asked for
permission and then threw the answer away, flipping its own state on whatever the prompt returned. The send at
the other end requires `Notification.permission === "granted"`, so a visitor who had already clicked "Block"
got `aria-pressed="true"` and the words "Notifying" (通知已开启) on a bell that could never ring -- and on a
browser whose permission was already ``denied`` the old code did not even show a prompt, because it only
requested when the state was ``default``. Measured directly: with the pre-fix bundle the control reported
``pressed=true, text=Notifying`` while the page's own ``Notification.permission`` read ``denied``.

This file is the CI half. The browser probe that produced the measurement is not wired into the tour (the tour
runs static routes with no notification decision), so without a static guard the same regression -- any handler
that sets a capability state from a click instead of from the result -- would go back in silently.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSPECTOR = ROOT / "apps/web/app/analysis/[runId]/RunInspector.tsx"
LOCALE_TS = ROOT / "apps/web/lib/locale.ts"


def _inspector() -> str:
    assert INSPECTOR.is_file(), (
        f"{INSPECTOR.relative_to(ROOT)} is missing -- the run report has no owner"
    )
    text = INSPECTOR.read_text(encoding="utf-8")
    start = text.index("const toggleNotify")
    end = text.index("return { prog,", start)
    body = text[start:end]
    assert len(body) > 100, (
        f"the toggle handler parsed as {len(body)} characters -- the slice is wrong"
    )
    return body


def _locale_block() -> str:
    return LOCALE_TS.read_text(encoding="utf-8")


def test_the_permission_result_decides_whether_the_control_is_on() -> None:
    """The handler must branch on what the prompt returned, and never on the click alone."""
    body = _inspector()
    assert re.search(r"permission\s*!==\s*[\"']granted[\"']", body), (
        "toggleNotify no longer inspects the permission result; the control can read as enabled while the "
        "browser will never deliver, which is the defect this file exists to keep out"
    )
    assert "setNotify(true)" in body and "setNotifyBlocked(true)" in body, (
        f"the handler must both enable on a grant and report a refusal; body was:\n{body}"
    )
    # The lying pattern itself: an unconditional toggle. `setNotify((v) => !v)` ignored whatever came back.
    assert "setNotify((v) => !v)" not in body, (
        "the unconditional flip is back -- it turns the bell on for a denied visitor"
    )


def test_a_refusal_is_explained_in_both_languages() -> None:
    """Silence is the failure mode: the visitor has to be told why the control stayed off."""
    src = INSPECTOR.read_text(encoding="utf-8")
    assert 't(locale, "insp.notifyBlocked")' in src, "the refusal is never rendered, only swallowed"
    assert 't(locale, "insp.notifyBlockedWhy")' in src, (
        "the reason is not reachable from the control"
    )

    # Two occurrences means the key is written twice in the dictionary, which together with the parity guard
    # (`test_web_locale_parity`, which holds the two locale blocks key-identical) puts it in both languages.
    # Counting alone would not, so this asserts the rendering above and leaves the both-locales half to the
    # guard that actually proves it.
    loc = _locale_block()
    for key in ("insp.notifyBlocked", "insp.notifyBlockedWhy"):
        occurrences = loc.count(f'"{key}"')
        assert occurrences >= 2, (
            f"{key} appears {occurrences} time(s); a refusal message that exists in one language only is the "
            "same defect wearing a translated label"
        )


def test_the_pressed_state_follows_the_state_not_the_click() -> None:
    """`aria-pressed` is the accessible claim; it must be bound to the verified state."""
    src = INSPECTOR.read_text(encoding="utf-8")
    assert "aria-pressed={notify}" in src, (
        "the button's pressed state is no longer the gated flag, so a screen reader is told something the "
        "browser will not do"
    )
    assert "notifyBlocked" in src.split("aria-pressed={notify}")[0], (
        "the blocked flag is never consulted before the pressed attribute"
    )
