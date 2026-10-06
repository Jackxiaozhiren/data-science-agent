"""Every pipe table in shipped markdown must render as a table (audit §118).

A contiguous ``|`` block renders only when its first line is the header row and its second is the
delimiter row. A blank line inside a long table starts a *new* block, and if that continuation has no
header it renders as a paragraph -- the rows are still there, still readable in a raw file, and simply
not a table. That is a silent failure: the record looks complete.

Measured before this file existed, with the parser this repository builds with
(``markdown.markdown(block, extensions=["tables"])`` over 249 table blocks in 136 tracked ``*.md``
files): exactly one block of 249 failed to render, in ``AUDIT_LEDGER.md``. The rule below is that
parser's requirement expressed structurally, so the guard needs no transitive dependency; the parser
cross-check is what justifies trusting the structural form.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DELIMITER = re.compile(r"^\|(\s*:?-{3,}:?\s*\|)+\s*$")
SKIP_SEGMENTS = frozenset(
    {"node_modules", ".venv", "site", "_vendor", "dist", "build", ".workspace"}
)


def _tracked_markdown() -> list[Path]:
    listing = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    paths = []
    for rel in listing.stdout.split():
        if any(seg in SKIP_SEGMENTS for seg in Path(rel).parts):
            continue
        if rel.startswith("data-science-agent/"):
            continue
        candidate = ROOT / rel
        if candidate.is_file():
            paths.append(candidate)
    assert len(paths) >= 100, (
        f"only {len(paths)} markdown files found -- the glob or checkout broke"
    )
    return paths


def _blocks(text: str) -> list[tuple[int, list[str]]]:
    out: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    for i, line in enumerate(text.splitlines()):
        if line.startswith("|"):
            if not cur:
                start = i + 1
            cur.append(line)
        elif cur:
            out.append((start, cur))
            cur = []
    if cur:
        out.append((start, cur))
    return out


def _offenders(paths: list[Path]) -> list[str]:
    found = []
    for path in paths:
        for start, block in _blocks(path.read_text(encoding="utf-8", errors="replace")):
            if len(block) < 2:
                continue
            if not DELIMITER.match(block[1]):
                shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                found.append(f"{shown}:{start} (header row {block[0][:48]!r})")
    return found


def test_markdown_tables_have_a_header_row() -> None:
    offenders = _offenders(_tracked_markdown())
    assert not offenders, f"{len(offenders)} table block(s) cannot render as tables:\n" + "\n".join(
        offenders
    )


def test_the_control_a_headerless_continuation_is_caught(tmp_path: Path) -> None:
    """The guard must be able to fail, and must not fire on a well-formed table."""
    good = tmp_path / "good.md"
    good.write_text(
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n| c | d |\n| --- | --- |\n| 3 | 4 |\n",
        encoding="utf-8",
    )
    assert _offenders([good]) == [], "a well-formed two-table file was reported"

    split = tmp_path / "split.md"
    split.write_text(
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n\n| 3 | 4 |\n| 5 | 6 |\n",
        encoding="utf-8",
    )
    caught = _offenders([split])
    assert len(caught) == 1 and "split.md:5" in caught[0], caught
