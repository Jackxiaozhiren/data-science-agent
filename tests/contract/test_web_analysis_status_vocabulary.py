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
