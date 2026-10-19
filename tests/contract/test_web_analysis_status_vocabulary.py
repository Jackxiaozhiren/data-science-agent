"""Contract: the web run-status vocabulary must be the backend's, and only its owner may list it.

Phase 4 target 4 / L2 half. Audit §67.1 established at T1 that `AnalysisStatus` has exactly eleven
members and that none of `RUNNING`, `PENDING`, `QUEUED`, `STARTED` exists -- verified again here by
importing the enum -- while the web layer branched on all four. The consequences were not cosmetic:
a genuinely in-flight run (`ANALYSIS`, `PLANNING`, ...) matched none of the badge's in-flight names and
fell through to a neutral grey badge, and `RunInspector`'s active-step branch keyed on `RUNNING`, so the
trace timeline could never mark a step active.

Why a cross-language test instead of a fixed list in TS: the enum is the fact, the TS module is a
rendering of it, and today nothing connects the two. Adding a twelfth status to `AnalysisStatus` would
otherwise keep rendering grey with no signal anywhere. So this file compares the two sets in both
directions, requires the presentation categories to cover the vocabulary completely, and checks the two
structural claims that keep the vocabulary single-owned -- a filter must offer a reachable value, and a
consumer must import the module rather than hand-copy names (§82: one number, one owner).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from dsa_agent.state import AnalysisStatus

ROOT = Path(__file__).resolve().parents[2]
STATUS_MODULE = ROOT / "apps/web/app/lib/analysisStatus.ts"
WEB_APP = ROOT / "apps/web/app"
LOCALE_TS = ROOT / "apps/web/lib/locale.ts"


def _ts_array(source: str, name: str) -> set[str] | None:
    """Extract `export const NAME = [ ... ] as const` as a set of string literals."""
    match = re.search(
        rf"export const {re.escape(name)}(?:[^=]*)=\s*\[(.*?)\]\s*as const",
        source,
        re.DOTALL,
    )
    if match is None:
        return None
    out: set[str] = set()
    for single, double in re.findall(r"'([^']*)'|\"([^\"]*)\"", match.group(1)):
        out.add(single or double)
    return out


def _module_source() -> str:
    assert STATUS_MODULE.is_file(), (
        f"{STATUS_MODULE.relative_to(ROOT)} is missing -- the run-status vocabulary has no owner"
    )
    return STATUS_MODULE.read_text(encoding="utf-8")


def _enum_values() -> set[str]:
    return {member.value for member in AnalysisStatus}


def _dictionary_keys(locale: str) -> set[str]:
    """The key names one locale block of the shared dictionary defines.

    Read here rather than imported from test_web_locale_parity.py so this file's claim -- the status
    vocabulary is sayable -- stands on its own when that file changes shape.
    """
    source = LOCALE_TS.read_text(encoding="utf-8")
    start = source.index(f"  {locale}: {{")
    body = source[start : source.index("\n  },", start)]
    keys = set(re.findall(r'"([^"]+)":', body))
    assert len(keys) > 100, f"the {locale} block parsed only {len(keys)} keys -- the slice broke"
    return keys


def test_enum_itself_is_the_measured_shape() -> None:
    """Guards the premise of the whole file: no RUNNING-classified name is added silently."""
    values = _enum_values()
    assert len(values) == 11, f"AnalysisStatus changed shape: {sorted(values)}"
    for invented in ("RUNNING", "PENDING", "QUEUED", "STARTED"):
        assert invented not in values, f"{invented} is now emitted by the backend; re-audit §67.1"


def test_ts_vocabulary_equals_the_python_enum_both_ways() -> None:
    ts = _ts_array(_module_source(), "ANALYSIS_STATUSES")
    assert ts is not None, "analysisStatus.ts exports no ANALYSIS_STATUSES array"
    assert ts == _enum_values(), (
        "the web vocabulary and AnalysisStatus disagree -- "
        f"web-only {sorted(ts - _enum_values())}, backend-only {sorted(_enum_values() - ts)}"
    )


def test_presentation_categories_cover_every_status() -> None:
    """A new enum member must be classified, not left to fall through to a neutral badge."""
    source = _module_source()
    vocab = _ts_array(source, "ANALYSIS_STATUSES")
    in_flight = _ts_array(source, "IN_FLIGHT_STATUSES")
    terminal = _ts_array(source, "TERMINAL_STATUSES")
    assert in_flight is not None and terminal is not None, (
        "missing IN_FLIGHT_STATUSES / TERMINAL_STATUSES"
    )
    review = _enum_values() - in_flight - terminal
    assert review == {"HUMAN_REVIEW"}, (
        f"statuses with no presentation category: {sorted(review - {'HUMAN_REVIEW'})} "
        f"(terminal={sorted(terminal)}, in-flight={sorted(in_flight)})"
    )
    assert in_flight and terminal, "a category may not be empty -- that would silence the badge"
    assert not (in_flight & terminal), (
        f"a status cannot be both in-flight and terminal: {in_flight & terminal}"
    )
    assert in_flight | terminal | review == vocab, "categories must partition the vocabulary"


def _status_select_options() -> list[tuple[Path, str]]:
    """`<option value="X">` inside the shadcn `<Select>` that offers COMPLETED/FAILED.

    The component is capital-S (`@/app/components/ui/select`), so a lowercase `<select>` scan finds
    nothing -- which reads as a pass. The `"all"` entry is the filter-off control, not a status.
    """
    hits: list[tuple[Path, str]] = []
    for path in sorted(WEB_APP.rglob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"<Select\b[^>]*>(.*?)</Select>", text, re.DOTALL):
            if 'value="COMPLETED"' not in block:
                continue  # not a run-status filter
            for value in re.findall(r'<option\s+value="([^"]+)"', block):
                hits.append((path, value))
    return hits


NON_STATUS_CONTROL_VALUES = {"all"}


def test_status_filters_offer_only_reachable_values() -> None:
    """§67.1: a filter on an unreachable status can only ever return an empty list."""
    options = _status_select_options()
    assert len(options) >= 4, (
        f"found {len(options)} status options -- the scan broke, not a clean pass"
    )
    reachable = _enum_values() | NON_STATUS_CONTROL_VALUES
    bad = sorted(
        {
            f"{p.relative_to(ROOT)}: {v}"
            for p, v in options
            if v not in reachable and v.lower() != "all statuses"
        }
    )
    assert not bad, "run-status filters offering values the backend cannot emit:\n  " + "\n  ".join(
        bad
    )


@pytest.mark.parametrize(
    "relative",
    ["components/data/StatusBadge.tsx", "analysis/[runId]/RunInspector.tsx"],
)
def test_status_consumers_import_the_vocabulary(relative: str) -> None:
    """Single ownership: a consumer that re-types status names is a second owner of the fact.

    Checked structurally (an import of the module) rather than by banning literals, because the same
    components legitimately compare non-status strings such as "ok" and "error".
    """
    path = WEB_APP / relative
    assert path.is_file(), f"{relative} moved -- this test would check nothing"
    text = path.read_text(encoding="utf-8")
    assert re.search(r'from "@/app/lib/analysisStatus"', text), (
        f"{relative} still hard-codes run-status names instead of importing the vocabulary"
    )


def test_module_is_valid_typescript_shape() -> None:
    """Cheap structural check so the regex parser cannot pass on garbage."""
    source = _module_source()
    for name in ("ANALYSIS_STATUSES", "IN_FLIGHT_STATUSES", "TERMINAL_STATUSES"):
        assert f"export const {name}" in source, f"no exported {name}"
    assert "as const" in source, "arrays must be `as const` so TS narrows the literal types"
    # every extracted element must be an UPPER_SNAKE status name, not a stray token
    vocab = _ts_array(source, "ANALYSIS_STATUSES") or set()
    assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*", v) for v in vocab), sorted(vocab)


# ---------------------------------------------------------------------------
# R-13: status is a word, not a colour.
#
# Status badges are the primary signal in this app, and the requirement is that they read for a reader who
# cannot distinguish amber from grey. `StatusBadge` is written that way today -- every branch renders the
# state text and the pulsing dot is `aria-hidden` -- and this is the guard that keeps a later edit from
# turning one branch into a colour swatch. A browser check could not cover it: the badges render only when
# a run exists, and the web tour is deliberately backend-independent. So the invariant is asserted where
# the choice is made, over every badge in the app, enumerated rather than named.
# ---------------------------------------------------------------------------

BADGE_OWNER = WEB_APP / "components/data/StatusBadge.tsx"

# A badge carries a word when, with every element stripped out, some word character is left: `{status}` and
# `A: {c.name}` do, `<Icon />` alone does not, and neither does `{" "}` -- which is why the test is a word
# search over the stripped children rather than "has a brace expression". Attributes holding a literal `>`
# would fool the tag stripper, so `_iter_badges` above is what keeps the element boundaries honest.
_WORD = re.compile(r"\w")
_TAG_ONLY = re.compile(r"<[^>]*>")


def _find_badge(text: str, i: int) -> int:
    """Index of the next real `<Badge` element, or -1 -- `<Badger` and `<StatusBadge` are not it."""
    while True:
        start = text.find("<Badge", i)
        if start == -1:
            return -1
        nxt = text[start + len("<Badge") :]
        if nxt[:1] in (" ", "\t", "\n", ">", "/", "{"):
            return start
        i = start + 1


def _iter_badges(text: str):
    """Yield `(opening_tag, children_or_None)` for every `<Badge ...>` JSX element.

    Hand-written rather than regex-paired because an attribute legitimately holds a `>` inside braces
    (`{"A > B"}`): a `.*?` match would end the opening tag early and mis-pair the children with some other
    element's `</Badge>`. `None` children means the element was self-closing -- and the slash that says so
    sits *before* the `>`, which the test below keeps asserted.
    """
    out = []
    i = 0
    while True:
        start = _find_badge(text, i)
        if start == -1:
            return out
        depth, j = 0, start + len("<Badge")
        while j < len(text):
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == ">" and depth == 0:
                break
            j += 1
        else:
            raise AssertionError(f"unterminated <Badge at offset {start}")
        opening = text[start : j + 1]
        if text[start:j].rstrip().endswith("/"):
            out.append((opening, None))
            i = j + 1
            continue
        # Walk the children, counting nested badges so a badge inside a badge closes at the right tag.
        k, nested = j + 1, 0
        while True:
            nxt_open = _find_badge(text, k)
            nxt_close = text.find("</Badge>", k)
            if nxt_close == -1:
                raise AssertionError(f"unclosed <Badge> opened at offset {start}")
            if nxt_open != -1 and nxt_open < nxt_close:
                nested += 1
                k = nxt_open + len("<Badge")
                continue
            if nested == 0:
                out.append((opening, text[j + 1 : nxt_close]))
                # Recurse so a badge nested inside a badge is censused on its own; the outer element's text
                # may be perfectly good while the inner one is a bare colour swatch.
                out.extend(_iter_badges(text[j + 1 : nxt_close]))
                i = nxt_close + len("</Badge>")
                break
            nested -= 1
            k = nxt_close + len("</Badge>")


def _badge_sites() -> list[tuple[Path, str, str | None]]:
    sites: list[tuple[Path, str, str | None]] = []
    for path in sorted(WEB_APP.rglob("*.tsx")):
        text = path.read_text(encoding="utf-8")
        for opening, children in _iter_badges(text):
            sites.append((path, opening, children))
    return sites


def test_badge_parser_reads_the_shapes_the_corpus_can_hold() -> None:
    """The parser is asserted against synthetic JSX, because a parser that silently mis-pairs makes the
    census above pass on an empty or wrong list.

    Each case is a shape the app can legitimately grow: a self-closing badge (the mutation the guard exists
    to catch), a `>` inside an attribute expression, and a badge nested in a badge. `<StatusBadge` is the
    negative control -- matching it would double-count the owner file's own consumers.
    """
    cases = [
        ('<Badge variant="secondary" />', [('<Badge variant="secondary" />', None)]),
        ("<Badge>{x}</Badge>", [("<Badge>", "{x}")]),
        ('<Badge label={"A > B"}>{s}</Badge>', [('<Badge label={"A > B"}>', "{s}")]),
        (
            "<Badge><Badge>{inner}</Badge>{outer}</Badge>",
            [
                ("<Badge>", "<Badge>{inner}</Badge>{outer}"),
                ("<Badge>", "{inner}"),
            ],
        ),
        ("<StatusBadge status={r} />", []),
    ]
    for source, wanted in cases:
        got = _iter_badges(source)
        assert got == wanted, f"parsed {got} from {source!r}, wanted {wanted}"


def test_badge_word_rule_rejects_a_brace_that_holds_nothing() -> None:
    """The census above asks for a word in the children with the elements stripped, and this is that rule
    pinned on its own -- `{" "}` is a badge that renders a space, and a mutation that turns a state badge
    into one must not be able to hide behind the brace expression.
    """
    for children, carries_word in [
        ("{status}", True),
        ("A: {c.name}", True),
        ('{t(locale, "home.title")}', True),
        ("{'completed'}", True),
        ('<Plug2 className="size-3" aria-hidden /> {t}', True),
        (" ", False),
        ('{" "}', False),
        ('<span className="size-1.5 bg-amber-500" aria-hidden />', False),
        ("{ }", False),
    ]:
        assert bool(_WORD.search(_TAG_ONLY.sub("", children))) is carries_word, children


def test_every_badge_renders_text_and_only_decorates_with_colour() -> None:
    sites = _badge_sites()
    # Two independently derived denominators: the parser's own count against a plain substring count over
    # the same corpus, and the four branches of the file that owns run-status presentation. Without these a
    # parser that silently matched nothing would report a clean sweep of an empty list.
    raw = sum(
        path.read_text(encoding="utf-8").count("<Badge") for path in sorted(WEB_APP.rglob("*.tsx"))
    )
    assert len(sites) == raw, (
        f"the badge parser accounted for {len(sites)} of {raw} `<Badge` occurrences"
    )
    owner_sites = [s for s in sites if s[0] == BADGE_OWNER]
    assert len(owner_sites) == 4, (
        f"StatusBadge.tsx contributed {len(owner_sites)} badges; the guard is written for its four branches "
        "and a fifth return path needs its text child checked by hand"
    )

    problems: list[str] = []
    for path, opening, children in sites:
        where = f"{path.relative_to(ROOT)}: {opening.splitlines()[0][:72]}"
        if children is None:
            problems.append(
                f"{where} -- a self-closing badge has no text child, so it speaks only in colour"
            )
            continue
        if not children.strip():
            problems.append(f"{where} -- empty badge, colour only")
            continue
        if not _WORD.search(_TAG_ONLY.sub("", children)):
            problems.append(f"{where} -- children carry no word: {children.strip()[:60]!r}")
        # A coloured element inside a badge is fine while it is hidden from the accessibility tree; a
        # second, *unhidden* colour swatch is where the state starts living only in hue.
        for tag in re.findall(r"<[a-zA-Z][^>]*>", children):
            if (
                re.search(r"\bbg-(?:red|amber|emerald|green|yellow|orange|rose|lime)-\d", tag)
                and "aria-hidden" not in tag
            ):
                problems.append(f"{where} -- coloured element without aria-hidden: {tag[:80]}")
    assert not problems, "badges that can convey state by colour alone:\n  " + "\n  ".join(problems)


def test_status_badge_branches_all_carry_the_state_word() -> None:
    """The narrower claim for the run-status owner: the text child is the status itself.

    R-13f moved that text behind `statusLabel(locale, status)`, so what the JSX renders is a local named
    `label`. The invariant was never the spelling of the identifier -- it is that the badge says the state in
    words and that those words come from the status through the locale owner, so both halves are pinned.
    """
    source = BADGE_OWNER.read_text(encoding="utf-8")
    assert "const label = statusLabel(locale, status);" in source, (
        "StatusBadge no longer derives its text from the status argument through the locale owner, so a "
        "declared state could be rendered in the wrong language or not at all"
    )
    branches = [(opening, children) for opening, children in _iter_badges(source)]
    assert len(branches) == 4, f"expected StatusBadge's four branches, parsed {len(branches)}"
    for opening, children in branches:
        assert children is not None and "{label}" in children, (
            f"a run-status badge branch no longer renders the state text: {opening[:60]} -> "
            f"{(children or '').strip()[:60]!r}"
        )


def test_every_declared_status_has_a_label_in_both_locales() -> None:
    """A status the interface knows about must be sayable in the language the visitor chose.

    `statusLabel` deliberately falls back to the raw token for a value outside the enum -- inventing a
    translation for an undeclared state is worse. That fallback is exactly why this needs a pin: without it,
    adding a state to `ANALYSIS_STATUSES` would ship an English chip on a 中文 page and nothing would notice.
    """
    statuses = _ts_array(_module_source(), "ANALYSIS_STATUSES")
    assert statuses is not None and len(statuses) >= 8, (
        f"the vocabulary parsed as {statuses} -- the extraction has gone blind, so this check proves nothing"
    )
    for locale in ("en", "zh"):
        keys = _dictionary_keys(locale)
        missing = sorted(f"status.{s}" for s in statuses if f"status.{s}" not in keys)
        assert not missing, (
            f"{locale} carries no label for {missing}; the badge would silently fall back to the raw token "
            "and a 中文 visitor would read an English status chip"
        )
