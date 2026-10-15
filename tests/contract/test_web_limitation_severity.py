"""A caveat the reader sees on every run is a caveat the reader learns to ignore.

Found while capturing R-01's acceptance evidence (2026-10-15): the example report the landing page links -- a
clean run, 11/11 validation checks passed, no tool errors -- opened with a red "1 caveat (1 critical)" banner.
The word that made it critical was "causation", and the sentence was ``"Association does not imply
causation."``, which `dsa_agent/graph.py:295` and `langgraph_graph.py:131` attach to *every* insight that comes
from a correlation or a hypothesis test. So the loudest tier in the UI fired on the product's own standing
disclaimer, on effectively every report, which is the same as never firing.

The guard is two-sided on purpose. Reading only the TypeScript would let someone empty the keyword list and
pass; reading only the Python would let someone add a new boilerplate limitation that trips the list and pass.
So the strings come from the code that emits them and the words come from the file that decides severity.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "apps/web/app/lib/limitations.ts"
INSPECTOR = ROOT / "apps/web/app/analysis/[runId]/RunInspector.tsx"

#: Every place that writes a `limitation` onto an insight, or onto the evidence a report renders from it.
EMITTERS = (
    ROOT / "packages/agent/src/dsa_agent/graph.py",
    ROOT / "packages/agent/src/dsa_agent/langgraph_graph.py",
)
TOOL_DIR = ROOT / "packages/tools/src/dsa_tools/tools"


def _severe_words() -> list[str]:
    source = LIB.read_text(encoding="utf-8")
    block = re.search(r"SEVERE_LIMITATIONS\s*=\s*\[(.*?)\]", source, re.DOTALL)
    assert block, "no SEVERE_LIMITATIONS list in the owner file -- where did severity move to?"
    words = re.findall(r'"([^"]+)"', block.group(1))
    assert words, "the severity list is empty: every caveat would be a warning, including a leak"
    return words


def _emitted_limitations() -> dict[str, str]:
    """`file:line` -> the literal limitation text the shipped code puts on an insight."""
    found: dict[str, str] = {}
    for path in [*EMITTERS, *sorted(TOOL_DIR.glob("*.py"))]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = re.search(r'limitation(?:s)?\s*(?::\s*str\s*)?=\s*"([^"]+)"', line)
            if match and path != LIB:
                found[f"{path.relative_to(ROOT)}:{number}"] = match.group(1)
    assert found, (
        "no emitted limitation strings found -- the emitters moved and this guard went blind"
    )
    return found


def _classifies_as_error(text: str, words: list[str]) -> bool:
    """The owner file's rule, restated: lowercased substring match. Keep in step with `limitationSeverity`."""
    lower = text.lower()
    return any(word.lower() in lower for word in words)


def test_a_standing_disclaimer_is_not_a_critical_finding() -> None:
    """The causal sentence is the product behaving correctly; the causal *claim* gate is a validation check."""
    words = _severe_words()
    offenders = {
        where: text
        for where, text in _emitted_limitations().items()
        if _classifies_as_error(text, words)
    }
    assert not offenders, (
        "these shipped limitation strings would render as CRITICAL on every report that carries them, "
        f"which trains the reader to skip the banner: {offenders}\n"
        "Either the emitter is naming a real defect (then the severity is right and this list is the "
        "problem), or it is boilerplate (then the sentence belongs nowhere near these words)."
    )


def test_the_severe_words_still_catch_a_real_defect() -> None:
    """The other direction: the list must not have been emptied to make the assertion above pass."""
    words = _severe_words()
    for sample in (
        "Possible label leakage between train and test.",
        "The model overfits the small sample.",
        "Treatment assignment was confounded by season.",
    ):
        assert _classifies_as_error(sample, words), (
            f"{sample!r} is a defect in the analysis and no keyword in the severity list catches it"
        )


def test_the_causal_gate_lives_where_claims_are_checked() -> None:
    """Removing "causal" from the caveat banner must not remove the product's causal-claim protection.

    The protection is the `unsupported_claim` validation check, which the run page renders in its own panel. If
    that check is ever renamed or dropped, the banner is the only thing left saying anything about causation --
    so this pins the alternative rather than trusting a comment.
    """
    sources = list((ROOT / "packages/agent/src/dsa_agent").glob("*.py")) + list(
        (ROOT / "packages/validation/src/dsa_validation").glob("*.py")
    )
    hits = [
        path.relative_to(ROOT).as_posix()
        for path in sources
        if path.is_file() and "unsupported_claim" in path.read_text(encoding="utf-8")
    ]
    assert hits, (
        "no code names the unsupported_claim check any more, and the caveat banner just lost the only "
        "causation word it had"
    )


def test_severity_has_one_owner_and_the_inspector_uses_it() -> None:
    """The list was inline in the component; a second copy elsewhere would drift the same way twice."""
    inspector = INSPECTOR.read_text(encoding="utf-8")
    assert "SEVERE_LIMITATIONS" not in inspector, (
        "RunInspector keeps its own severity list again -- the copy that caused this bug"
    )
    assert 'from "@/app/lib/limitations"' in inspector, (
        "the inspector no longer reads the owner file"
    )
    owners = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.joinpath("apps/web").rglob("*.ts*")
        if "SEVERE_LIMITATIONS" in path.read_text(encoding="utf-8")
        and "components/generated" not in str(path)
    ]
    assert owners == ["apps/web/app/lib/limitations.ts"], (
        f"more than one file declares the severity words: {owners}"
    )
