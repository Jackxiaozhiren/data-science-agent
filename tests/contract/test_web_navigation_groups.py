"""R-10: navigation is ordered by the analyst's loop, and every entry lands on a route that exists.

Measured before this file existed (2026-10-15): the top bar listed ``Analysis | Evaluation | Research`` at one
weight, the sidebar appeared only on three route prefixes, and ``/evaluations``, ``/failures`` and ``/mcp`` were
linked from nowhere at all. The requirement is that the loop comes first and the author surfaces are grouped and
labelled -- explicitly *not* removed, because they back published case studies, the leaderboard and the audit
trail. So the guard checks three things that can each silently regress: the declared order, that every entry
resolves to a real route directory, and that the diagnostic group says in its own label that it is about the
system rather than the visitor's data.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_APP = ROOT / "apps/web/app"
SIDEBAR = WEB_APP / "components/layout/Sidebar.tsx"
HEADER = WEB_APP / "components/layout/SiteHeader.tsx"
TOUR = ROOT / "apps/web/scripts/regression.mjs"

ANALYST_ORDER = ["/analysis", "/runs", "/reports", "/datasets"]


def _source() -> str:
    return SIDEBAR.read_text(encoding="utf-8")


def _group_items(source: str, key: str) -> list[str]:
    """The hrefs of one NAV_GROUPS entry, in the order they are written."""
    start = source.index(f'key: "{key}"')
    items_at = source.index("items: [", start)
    end = source.index("],", items_at)
    return re.findall(r'href: "([^"]+)"', source[items_at:end])


def _all_group_items(source: str) -> list[str]:
    """Every href in every declared group.

    The orphan check used to enumerate the two groups that existed when it was written, which made it correct
    only while the sidebar stayed at two. A third group -- R-05's local settings -- was then an orphan it
    reported even though the route was linked, so the check reads the declaration instead of a transcription.
    """
    keys = re.findall(r'key: "([^"]+)"', source)
    assert keys, "NAV_GROUPS no longer declares keyed groups, so this guard is blind"
    return [href for key in keys for href in _group_items(source, key)]


def _route_dirs() -> set[str]:
    """Routes that exist as page files, in URL form: ``app/benchmarks/page.tsx`` -> ``/benchmarks``."""
    routes: set[str] = set()
    for page in WEB_APP.rglob("page.tsx"):
        relative = page.parent.relative_to(WEB_APP).as_posix()
        if relative == ".":
            routes.add("/")
            continue
        # Detail and nested pages (`/runs/[id]`, `/runs/[id]/replay`) are entered from a list, not from the
        # navigation, so they are not orphans: only static route prefixes are comparable to nav hrefs.
        if "[" in relative:
            continue
        routes.add("/" + relative)
    return routes


def test_the_analyst_group_is_ordered_ask_runs_reports_datasets() -> None:
    assert _group_items(_source(), "analyst") == ANALYST_ORDER, (
        "the workspace navigation must lead with the loop the product teaches; §15 R-10 names the order"
    )


def test_every_nav_entry_resolves_to_a_route_that_exists() -> None:
    routes = _route_dirs()
    assert len(routes) > 10, (
        f"the route walk found only {sorted(routes)} -- the check is reading the wrong tree"
    )
    dangling = []
    for key in ("analyst", "system"):
        for href in _group_items(_source(), key):
            if href not in routes:
                dangling.append(f"{key}: {href}")
    assert not dangling, f"nav entries with no page behind them: {dangling}"


def _dictionary_value(locale: str, key: str) -> str:
    """One sentence out of the locale owner. R-13 moved the nav labels there: a declaration that names a key
    is only honest if the guard follows the key, and both languages have to carry the disclosure -- an English
    hint with a Chinese blank behind it is the half-translation this whole layer refuses."""
    folded = re.sub(r":\s+", ": ", (ROOT / "apps/web/lib/locale.ts").read_text(encoding="utf-8"))
    parts = folded.split(f"{locale}: {{", 1)
    assert len(parts) == 2, (
        f"the dictionary has no {locale} block written the way this guard parses it"
    )
    body = parts[1].split("\n  },", 1)[0]
    found = re.search(rf'"{re.escape(key)}": "((?:[^"\\]|\\.)*)"', body)
    assert found, f"{locale} defines no {key!r} -- the sidebar would render ⟨{key}⟩"
    return found.group(1)


def test_the_diagnostic_group_is_labelled_as_being_about_the_system() -> None:
    """De-emphasis that reads as hiding would be worse than the flat row this replaced."""
    source = _source()
    # The group's own label is the key written immediately before its `key`, not the last item label above it.
    label = re.search(r'labelKey: "([^"]+)",\s*key: "system"', source)
    assert label, "the diagnostic group has no label of its own"
    assert re.search(r"about|system|agent", _dictionary_value("en", label.group(1)), re.I), (
        f"the group is labelled {_dictionary_value('en', label.group(1))!r}, which does not tell a reader it is "
        "not their data"
    )
    assert re.search(r"系统|智能体|本身", _dictionary_value("zh", label.group(1))), (
        "the 中文 label for the diagnostic group does not say it is about the system"
    )
    system_start = source.index('key: "system"')
    hint = re.search(r'hintKey: "([^"]+)"', source[system_start:])
    assert hint, "the group has no sentence telling a reader what these surfaces measure"
    assert "not" in _dictionary_value("en", hint.group(1)).lower(), (
        "the group needs a sentence saying these measure the agent, not the visitor's work"
    )
    assert "而不是" in _dictionary_value("zh", hint.group(1)), (
        "the 中文 hint drops the disclaimer that these are not the visitor's data"
    )


def test_no_route_is_left_unlinked() -> None:
    """Item 2 forbids hiding a surface; an unlinked one is hidden in practice.

    The five routes that had no nav entry at all before this change are named here rather than counted, so a
    route added later has to be placed in a group instead of quietly joining the orphan list.
    """
    linked = set(_all_group_items(_source()))
    for href in (
        "/benchmarks",
        "/evaluations",
        "/failures",
        "/research",
        "/mcp",
        "/runs/compare",
        "/datasets/compare",
    ):
        assert href in linked, (
            f"{href} is reachable only by typing the URL -- the requirement says regroup, not hide"
        )
    compare_free = {path for path in _route_dirs() if path != "/"}
    orphans = sorted(compare_free - linked)
    assert not orphans, f"routes with no navigation entry: {orphans}"


def test_the_header_no_longer_flattens_author_and_analyst_entries() -> None:
    """The top bar reads its labels from the navigation owner now, so the two cannot disagree."""
    source = HEADER.read_text(encoding="utf-8")
    assert "NAV_GROUPS" in source, (
        "the header keeps its own link list and will drift from the sidebar"
    )
    for href in ('"/benchmarks"', '"/research"'):
        assert href not in source, (
            f"the header still links {href} directly: that is the flat row R-10 removes"
        )
    assert 'href="/analysis"' not in source or "analystGroup" in source


def test_a_planted_dangling_entry_is_caught() -> None:
    """Negative control: the resolve check has to fire on the mistake it exists for."""
    planted = _source().replace('href: "/mcp"', 'href: "/mcp-does-not-exist"', 1)
    assert planted != _source(), "the plant changed nothing, so this control proves nothing"
    routes = _route_dirs()
    linked = set(_group_items(planted, "analyst")) | set(_group_items(planted, "system"))
    assert "/mcp-does-not-exist" in linked and "/mcp-does-not-exist" not in routes, (
        "the planted href did not land in the nav list -- the check is not reading the list it claims"
    )
    assert (linked - routes) == {"/mcp-does-not-exist"}


def test_the_tour_visits_every_linked_route() -> None:
    """A nav entry the browser tour never loads is a 500 waiting to ship unobserved."""
    tour = TOUR.read_text(encoding="utf-8")
    listed = set(re.findall(r'^\s{2}"(/[a-z/-]*)",?$', tour, re.M))
    linked = (
        set(_group_items(_source(), "analyst")) | set(_group_items(_source(), "system")) | {"/"}
    )
    unvisited = sorted(linked - listed)
    assert not unvisited, f"nav entries the regression tour never opens: {unvisited}"
