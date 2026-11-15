"""ADR-003's S3 entry condition, derived from the migration row and Appendix C as they stand.

The appendix's closing paragraph was written during the 2026-11-13 sweep, when three producer gaps
still kept S2 un-exited. S2 exited on 2026-11-14, so the reason in that sentence no longer holds.
This file does not rewrite a dated sentence: it derives the entry condition from the migration row,
reads the three answers appended to Appendix C on 2026-11-15, and holds the status line, the
measurement page and the ledger to the same verdict. The stale reason is checked as history rather
than deleted from the record, which is what lets the two statements coexist without contradicting a
reader who reaches the appendix first.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/ADR/ADR-003-zero-cost-self-hosted-baseline-2026-11-09.md"
PAGE = ROOT / "docs/measurement-basis.md"
LEDGER = ROOT / "AUDIT_LEDGER.md"
BASELINE_README = ROOT / "benchmarks/baseline/README.md"
REAL_MODEL_DOC = ROOT / "docs/real-model-evaluation.md"

APPENDIX_HEADING = "## Appendix C — Open items"
REVIEW_HEADING = "### Entry review — 2026-11-15"
STATUS_PREFIX = "- Status: Accepted"
MIGRATION_PREFIX = "| S3 controlled expansion |"
HISTORIC_REASON = "three gaps still name a producer change"
LEDGER_HEADING = "## §333 — "
OPEN_MARK = "**not provided**"
ROW_LABELS = (
    "Cloud reporting from the `langsmith` SDK",
    "Model credentials and spend ceiling",
    "Whether the free lane produces a stable enough comparison",
)
EVIDENCE = (
    ROOT / "docs/measurement-basis.md",
    REAL_MODEL_DOC,
    BASELINE_README,
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _appendix(adr: str) -> str:
    return adr[adr.index(APPENDIX_HEADING) :]


def _review(adr: str) -> str:
    appendix = _appendix(adr)
    return appendix[appendix.index(REVIEW_HEADING) :]


def _answer_rows(adr: str) -> list[str]:
    """The three data rows of the appended review, without its header or separator."""
    table = [line for line in _review(adr).splitlines() if line.startswith("| ")]
    assert len(table) == 4, table
    return table[1:]


def _s3_cells(adr: str) -> list[str]:
    rows = [line for line in adr.splitlines() if line.startswith(MIGRATION_PREFIX)]
    assert len(rows) == 1, rows
    return [cell.strip() for cell in rows[0].split("|")]


def _replace_line(adr: str, prefix: str, old: str, new: str) -> str:
    lines = adr.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    assert len(matches) == 1, (prefix, matches)
    index = matches[0]
    assert old in lines[index], (old, lines[index])
    lines[index] = lines[index].replace(old, new, 1)
    return "".join(lines)


def _entry_state(adr: str) -> dict[str, bool]:
    """Four clauses of one judgement, each read out of the ADR rather than typed as a verdict."""
    status = adr.splitlines()[2]
    rows = _answer_rows(adr)
    entry = _s3_cells(adr)[2]
    return {
        "s2 exited": "S2 complete" in status and "S2 in progress" not in status,
        "entry names both halves": "S2 exit" in entry and "Appendix C" in entry,
        "one open row, the credential one": len(rows) == 3
        and sum(OPEN_MARK in row for row in rows) == 1
        and any(OPEN_MARK in row and ROW_LABELS[1] in row for row in rows),
        "s3 unstarted": "S3 not started" in status,
    }


def test_the_entry_condition_names_both_halves() -> None:
    entry = _s3_cells(_text(ADR))[2]
    assert "S2 exit" in entry
    assert "Appendix C" in entry
    assert "answered" in entry


def test_each_appendix_row_is_answered_once() -> None:
    rows = _answer_rows(_text(ADR))
    assert len(rows) == 3, rows
    for label in ROW_LABELS:
        assert sum(label in row for row in rows) == 1, label


def test_every_path_the_review_cites_exists() -> None:
    review = _review(_text(ADR))
    for path in EVIDENCE:
        rel = path.relative_to(ROOT).as_posix()
        assert rel in review, rel
        assert path.is_file(), rel


def test_the_free_lane_readings_are_quoted_from_the_baseline_page() -> None:
    """The review's latency numbers must be readings the baseline README actually holds."""
    rows = _answer_rows(_text(ADR))
    free_lane = [row for row in rows if ROW_LABELS[2] in row]
    assert len(free_lane) == 1, free_lane
    readings = re.findall(r"\b\d+\.\d{2}\b", free_lane[0])
    assert len(readings) == 3, readings
    baseline = _text(BASELINE_README)
    assert all(reading in baseline for reading in readings), readings


def test_the_historic_reason_is_kept_and_labelled() -> None:
    appendix = _appendix(_text(ADR))
    assert HISTORIC_REASON in appendix
    assert appendix.index(HISTORIC_REASON) < appendix.index(REVIEW_HEADING)
    review = _review(_text(ADR))
    assert "2026-11-13" in review
    assert "stays as written" in review


def test_the_review_does_not_open_the_stage_or_move_the_gate() -> None:
    review = _review(_text(ADR))
    assert "S3 stays `not started`" in review
    assert "publication_ready" in review
    assert "INV4" in review
    assert "S3 in progress" not in review
    assert "S3 started" not in review


def test_the_page_and_the_ledger_carry_the_same_verdict() -> None:
    adr = _text(ADR)
    status = adr.splitlines()[2]
    assert "S2 complete" in status and "S3 not started" in status
    page = _text(PAGE)
    not_s3 = page[page.index("- **Not S3.**") : page.index("## What this page is not")]
    assert "entry review" in not_s3
    assert "`not provided`" in not_s3
    ledger = _text(LEDGER)
    assert ledger.count(LEDGER_HEADING) == 1
    section = ledger[ledger.index(LEDGER_HEADING) :]
    assert "not provided" in section
    assert "S3 not started" in section
    assert "test_s3_entry_review.py" in section


def test_every_clause_holds_and_a_single_edit_flips_exactly_one() -> None:
    """Negative controls: the verdict is a conjunction, not one sentence agreeing with itself."""
    adr = _text(ADR)
    assert all(_entry_state(adr).values()), _entry_state(adr)

    reverted = _replace_line(adr, STATUS_PREFIX, "S2 complete", "S2 in progress")
    assert _entry_state(reverted)["s2 exited"] is False
    assert sum(_entry_state(reverted).values()) == 3

    halved = _replace_line(adr, MIGRATION_PREFIX, "S2 exit", "S1 exit")
    assert _entry_state(halved)["entry names both halves"] is False
    assert sum(_entry_state(halved).values()) == 3

    provided = adr.replace(OPEN_MARK, "**provided with a ceiling**", 1)
    assert _entry_state(provided)["one open row, the credential one"] is False
    assert sum(_entry_state(provided).values()) == 3

    started = _replace_line(adr, STATUS_PREFIX, "S3 not started", "S3 in progress")
    assert _entry_state(started)["s3 unstarted"] is False
    assert sum(_entry_state(started).values()) == 3
