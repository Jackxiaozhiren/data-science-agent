"""Run-checkpointing must not be described as a capability the shipped engine has.

Measured, not assumed: the only `MemorySaver()` in the repository is constructed inside
`packages/agent/src/dsa_agent/langgraph_graph.py` (`build_graph`), `build_graph` and
`run_analysis_langgraph` have no caller outside `tests/`, and every shipped entry point --
API `analysis_service.py`, `sdk.py`, the evaluation runner and `external_validation.py` -- calls
the sequential engine in `dsa_agent/graph.py` instead. There is no resume endpoint, no CLI resume
subcommand, and `thread_id` is generated and discarded inside a single `ainvoke`. So a document
that pairs checkpoints with "pause / resume / replay / fork" promises a feature no shipped path
implements.

Scope of this guard: the over-claim *shape* (a checkpoint mention and one of those verbs in the
same sentence). Two things it deliberately does not police, each for a stated reason:

- `benchmarks/external/datascibench/run_eval.py` genuinely resumes: it appends every completed task
  to `raw_runs.partial.jsonl` and skips those task ids on restart. That is a real, working
  checkpoint, so `test_the_working_benchmark_checkpoint_stays_described` pins it as allowed rather
  than letting a future sweep delete a true statement.
- `CHANGELOG.md` records what each release claimed at the time. Rewriting a historical entry to
  match today's code would make the changelog lie about the past instead of the present; §76
  settled the same question for measurement literals.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A checkpoint mention and a resume verb in the same sentence, either order.
_RESUME_SHAPE = re.compile(
    r"(?:checkpoint|checkpointed|checkpointing|MemorySaver)"
    r"(?:[^.]|\\n){0,160}?\b(?:paus\w+|resum\w+|replay|replays|fork\w*)\b",
    re.IGNORECASE,
)
_RESUME_SHAPE_REVERSED = re.compile(
    r"\b(?:paus\w+|resum\w+|replay|replays|fork\w*)\b(?:[^.]|\n){0,160}?"
    r"(?:checkpoint|checkpointed|checkpointing|MemorySaver)",
    re.IGNORECASE,
)

# A sentence that denies the capability is the opposite of an over-claim, and the UI already says it
# three times ("no checkpoint API exists yet", "under construction"). Gating those would teach the
# next editor to write vaguer docs, so a disclaimer anywhere in the line clears it.
_DISCLAIMER = re.compile(
    r"(does not exist|do(es)? n.t exist|not wired|not implemented|under construction"
    r"|no checkpoint api|isn.t available|not available|planned|phase 9|not supported)",
    re.IGNORECASE,
)

# Surfaced to readers as current behaviour.
SCAN_GLOBS = (
    "README.md",
    "docs/**/*.md",
    "research/**/*.md",
    "apps/web/**/*.tsx",
    "apps/vscode/**/*.ts",
)

# Declared here, with the reason, so an exemption can never arrive silently.
EXEMPT_PREFIXES = (
    "site/",  # generated mirror of docs/ -- rebuilt, not edited
    "docs/v4_3/",
    "docs/v3/",
    "CHANGELOG.md",  # historical record of past release claims
    "AUDIT_LEDGER.md",
    "AUDIT_REPORT_PHASE5.md",
    "REPO_DIAGNOSIS_AND_IMPROVEMENT_PROMPT.md",
    "benchmarks/",  # its own resume is implemented and verified
    "data-science-agent/",  # a second local clone, not this repository
)


def _candidate_files() -> list[Path]:
    out: list[Path] = []
    for pattern in SCAN_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(EXEMPT_PREFIXES):
                continue
            out.append(path)
    return sorted(set(out))


def _line_offends(line: str) -> bool:
    """The whole decision, in one place, so the control below tests the guard and not a proxy."""
    if _DISCLAIMER.search(line):
        return False
    return bool(_RESUME_SHAPE.search(line) or _RESUME_SHAPE_REVERSED.search(line))


def _offenders() -> list[str]:
    found: list[str] = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if _line_offends(line):
                found.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()[:110]}")
    return found


def test_no_current_document_promises_run_resume_or_fork() -> None:
    files = _candidate_files()
    assert len(files) >= 20, f"only {len(files)} files scanned -- the glob broke"
    offenders = _offenders()
    assert not offenders, (
        "checkpoints are offered as pause/resume/replay/fork, which no shipped path "
        "implements:\n" + "\n".join(offenders)
    )


def test_the_guard_fires_on_the_shape_it_exists_to_stop() -> None:
    """Negative control, both directions, plus the true statements it must leave alone.

    Without this the guard could pass simply because the regex never matches anything -- the way
    four typed number rules in check_public_claims.py stayed green for months (§76). The third
    block matters as much as the first two: a gate that flags honest disclaimers teaches the next
    editor to write vaguer docs, so the exemption is tested against the strings the UI really uses.
    """
    forward = "`StateGraph` with MemorySaver checkpoints for pause/resume/replay/fork"
    backward = "Replay or fork is available; state persists through LangGraph MemorySaver."
    assert _line_offends(forward), "the documented doc/architecture.md shape must match"
    assert _line_offends(backward), "verb-first sentences must match"
    for honest in (
        "Checkpoint-grounded replay is under construction -- the trace inspector is fully working.",
        "Replay and fork need a checkpoint API that does not exist in this build.",
        "Replay and fork controls are not wired in this build: no checkpoint API exists yet.",
    ):
        assert not _line_offends(honest), f"an honest disclaimer was gated: {honest}"


def test_readme_interfaces_row_offers_no_unimplemented_replay() -> None:
    """README.md:222 advertised VS Code "analysis replay" while the extension registers no such
    command. The table is what a reader treats as the product surface, so the word is pinned out."""
    row = next(
        (
            line
            for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
            if "VS Code" in line and line.strip().startswith("|")
        ),
        None,
    )
    assert row is not None, "the interfaces table row vanished -- re-check README.md"
    assert "replay" not in row.lower(), row.strip()[:120]


def test_the_working_benchmark_checkpoint_stays_described() -> None:
    """The one resume that really is implemented must not be swept away by this guard.

    If this fails, either the partial-file resume was removed (then the changelog entry needs
    retiring, not this test) or the strings moved (then update the citation, do not relax the
    assertion).
    """
    source = ROOT / "benchmarks/external/datascibench/run_eval.py"
    assert source.is_file(), f"{source} moved -- this test would then check nothing"
    text = source.read_text(encoding="utf-8")
    assert "partial.jsonl" in text, "the per-task checkpoint file is gone from the driver"
    assert re.search(r"already checkpointed", text), "the resume log line is gone"
