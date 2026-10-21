"""R-12 (found while re-verifying it): a backend identifier is displayed exactly as the backend made it.

The prompt's Lane B obligation was to re-check the follow-up button after R-03 changed run creation. Driving
it in a real browser surfaced a defect in the lineage line itself: ``analysis_service.py`` mints ids that
already carry their prefix (``run_id = f"run-{uuid.uuid4().hex[:10]}"`` -- a stored id reads
``run-2a4d6eeeb2``), and the inspector rendered the parent as ``run-{fromRunId.slice(0, 12)}``. A reader was
therefore shown ``run-run-2a4d6eee``: a string that matches no id the API ever produced, truncated so it
cannot even be searched for. It looks like an identifier and is not one, which is the failure mode §7.5 of
the plan exists to prevent.

Behaviour is proven in ``output/lane-b/capture-r12.sh``; this is the static gate that keeps the class from
coming back, and it is corpus-wide rather than one-line so the next component cannot reintroduce it.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_APP = ROOT / "apps/web/app"
INSPECTOR = WEB_APP / "analysis/[runId]/RunInspector.tsx"

# Every id this product mints by prefixing a uuid/hex fragment. The list is deliberately derived from the
# server, not from what the web happens to render today -- a new prefix has to be added here when the
# backend starts using it, which is the moment the display could go wrong.
ID_PREFIXES = ("run", "dataset", "evidence", "artifact", "insight", "tool-call")

PREFIX_GLUE = re.compile(rf"(?<![\w-])({'|'.join(ID_PREFIXES)})-\{{")


def _sources() -> list[Path]:
    files = sorted(p for p in WEB_APP.rglob("*.tsx") if "node_modules" not in p.parts)
    assert len(files) > 10, (
        f"the corpus walk found only {len(files)} .tsx files -- the gate is scanning nothing"
    )
    return files


def test_no_component_glues_an_id_prefix_onto_a_backend_id() -> None:
    """`run-${id}` where the id is already `run-…` invents an identifier; the display must be the value."""
    offenders = []
    for path in _sources():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if PREFIX_GLUE.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:120]}")
    assert not offenders, (
        "these lines prepend a prefix to a value that already carries one, producing an id the API never "
        "made:\n" + "\n".join(offenders)
    )


def test_a_planted_prefix_is_caught_and_the_rule_is_not_the_only_thing_matching() -> None:
    """Negative control: the pattern has to fire on the mutation it describes, not just pass on the fix."""
    planted = "Follow-up of <Link href={`/analysis/${fromRunId}`}>run-{fromRunId}</Link>"
    assert PREFIX_GLUE.search(planted), (
        "the pattern no longer matches the defect it was written for"
    )

    # And it must not fire on the legitimate shapes that live nearby: template literals building *routes*
    # and *URLs*, where the prefix is part of the path, not a second copy of an id.
    for ok in (
        "`/analysis/${fromRunId}`",
        "`/api/v1/analysis/${runId}/report`",
        "href={`/datasets/${row.id}`}",
    ):
        assert not PREFIX_GLUE.search(ok), f"the pattern-indictment is too broad, it matches {ok!r}"


def test_the_lineage_line_shows_the_parent_id_verbatim() -> None:
    """The one line a user copies to ask about a follow-up's parent has to be the parent's real id."""
    assert INSPECTOR.is_file(), "apps/web/app/analysis/[runId]/RunInspector.tsx is gone"
    source = INSPECTOR.read_text(encoding="utf-8")

    # R-13c moved the label into the locale owner, so the anchor is the key call and the thing under test stays
    # what it always was: the interpolated value inside the link, not the English words in front of it.
    anchor = '{t(locale, "insp.followupOf")} <Link'
    lineage = re.search(rf"{re.escape(anchor)}[^>]*>\{{([^}}]+)\}}</Link>", source)
    assert lineage, (
        "the lineage line no longer renders an interpolated value -- check what it shows instead"
    )
    assert lineage.group(1) == "fromRunId", (
        f"the parent is displayed as {{{lineage.group(1)}}}, which is not the stored id rendered verbatim"
    )

    # Gluing the label to the link is the shape this refuses: a reader who copies it gets `Follow-up ofrun-…`,
    # an identifier the API never issued.
    glued = _planted(source, anchor, '{t(locale, "insp.followupOf")}<Link')
    assert not re.search(rf"{re.escape(anchor)}[^>]*>\{{([^}}]+)\}}</Link>", glued), (
        "the assertion is not anchored to the lineage line"
    )
    assert re.search(r"insp\.followupOf", glued), (
        "the plant removed the lineage line entirely, so it proves nothing about spacing"
    )


def _planted(source: str, old: str, new: str) -> str:
    assert source.count(old) >= 1, (
        f"the plant's anchor {old!r} is not in the file -- the check is vacuous"
    )
    changed = source.replace(old, new, 1)
    assert changed != source, "the plant did not change anything"
    return changed
