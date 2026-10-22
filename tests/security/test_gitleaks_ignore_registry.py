"""What `.gitleaksignore` forgives must stay explainable, or the list becomes a mute button.

gitleaks matches a finding by fingerprint -- ``<commit>:<path>:<rule>:<line>`` -- against a file at the
repository root, and the action consults that file without reporting what it contains. So the ignore list is
only honest while three things hold: every forgiven fingerprint has a written reason, that reason still
describes the tree, and the reason does not itself carry a credential. Each of those is a channel here, and
the forged pair in ``test_a_forged_pair_redens_every_channel_it_covers`` proves they can all fire.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
IGNORE = REPO / ".gitleaksignore"
REGISTRY = REPO / "docs" / "audit" / "gitleaks-ignore-registry.json"
WORKFLOW = REPO / ".github" / "workflows" / "secret-scan.yml"

#: The shape upstream documents and the gate prints; a line that is not this matches nothing and hides
#: a finding by silently doing nothing, which is the failure worth refusing.
FINGERPRINT = re.compile(r"^[0-9a-f]{40}:[^\s:]+:[a-z0-9][a-z0-9-]*:\d+$")

#: A run of opaque characters long enough to be a key body *and* carrying digits, which is what separates a
#: secret from a file path. Requiring both keeps the honest prose fields from tripping their own tripwire.
CREDENTIAL_SHAPED_RUN = re.compile(r"(?=[A-Za-z0-9+/_-]*\d[A-Za-z0-9+/_-]*\d)[A-Za-z0-9+/_-]{25,}")

#: Fields that must stay prose. ``fingerprint`` and ``found_in_commit`` legitimately hold 40-hex shas.
DESCRIPTIVE_FIELDS = (
    "_purpose",
    "_format",
    "_how_to_add",
    "_verified_by",
    "why_not_a_secret",
    "exposure",
)


def _registry_entries(registry: dict) -> list[dict]:
    return [entry for entry in registry.get("entries", []) if isinstance(entry, dict)]


def _problems(ignore_text: str, registry: dict, today: date) -> list[str]:
    """Every way the pair can stop meaning something, collected in one pass.

    Collecting rather than asserting on the first finding is deliberate: one bad line should not hide the
    others behind whichever check happens to run first.
    """
    out: list[str] = []
    forgiven: list[str] = []

    for line in ignore_text.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            out.append(
                f"ignore list carries a comment ({line[:40]!r}); upstream's own file has none"
            )
            continue
        if not FINGERPRINT.match(line):
            out.append(f"ignore list line is not a gitleaks fingerprint: {line!r}")
        forgiven.append(line)

    for fingerprint in sorted({line for line in forgiven if forgiven.count(line) > 1}):
        out.append(f"ignore list forgives the same fingerprint twice: {fingerprint}")

    explained = {str(entry.get("fingerprint")) for entry in _registry_entries(registry)}
    for orphan in sorted(set(forgiven) - explained):
        out.append(f"fingerprint forgiven with no recorded reason: {orphan}")
    for unexploited in sorted(explained - set(forgiven)):
        out.append(
            f"reason recorded for a fingerprint the ignore list does not forgive: {unexploited}"
        )

    for entry in _registry_entries(registry):
        fingerprint = str(entry.get("fingerprint"))
        why = str(entry.get("why_not_a_secret") or "")
        if len(why) < 60:
            out.append(f"{fingerprint}: why_not_a_secret is {len(why)} chars, too thin to review")

        marker = str(entry.get("head_marker") or "")
        target = entry.get("file")
        path = REPO / str(target) if target else None
        if not target or path is None or not path.is_file():
            out.append(f"{fingerprint}: names a file that is not in the tree: {target!r}")
        elif marker and marker not in path.read_text(encoding="utf-8"):
            out.append(
                f"{fingerprint}: {marker!r} no longer appears in {target} -- the ignored text is gone, "
                "so delete the entry instead of letting it forgive a finding nobody planted"
            )

        review_by = str(entry.get("review_by") or "")
        try:
            when = date.fromisoformat(review_by)
        except ValueError:
            out.append(f"{fingerprint}: review_by={review_by!r} is not an ISO date")
        else:
            if when < today:
                out.append(
                    f"{fingerprint}: exemption expired {review_by} -- re-read it or delete it"
                )

    for field in DESCRIPTIVE_FIELDS:
        values = [str(registry.get(field))] if registry.get(field) else []
        values += [
            str(entry.get(field)) for entry in _registry_entries(registry) if entry.get(field)
        ]
        for value in values:
            hit = CREDENTIAL_SHAPED_RUN.search(value)
            if hit:
                out.append(
                    f"registry field {field!r} carries a credential-shaped run: {hit.group()[:8]}..."
                )

    return out


def test_the_ignore_list_and_its_registry_are_one_explained_set() -> None:
    problems = _problems(
        IGNORE.read_text(encoding="utf-8"), json.loads(REGISTRY.read_text()), date.today()
    )
    assert problems == [], "\n".join(problems)


def test_a_forged_pair_redens_every_channel_it_covers() -> None:
    """Each defect below is planted in a copy; the tree itself has none of them, by the test above."""
    clean = IGNORE.read_text(encoding="utf-8")
    registry = json.loads(REGISTRY.read_text())
    first = clean.splitlines()[0]
    today = date(2026, 10, 21)

    assert _problems(clean, registry, today) == [], "the real pair must be the control that passes"

    channels = {
        "comment line": (f"# not a fingerprint\n{clean}", registry),
        "line that is not a fingerprint": (f"src/x.py:generic-api-key:1\n{clean}", registry),
        "duplicate forgiveness": (f"{first}\n{clean}", registry),
        "forgiven without a reason": (clean, {"entries": []}),
        "reason without a fingerprint": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": "f" * 40 + ":docs/hosted-demo.md:generic-api-key:1",
                        "file": "docs/hosted-demo.md",
                        "head_marker": "DSA_TELEMETRY",
                        "why_not_a_secret": "x" * 80,
                        "review_by": "2027-01-15",
                    }
                ]
            },
        ),
        "thin reason": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "tests/contract/test_provider_settings.py",
                        "head_marker": "CREDENTIAL_CANARY",
                        "why_not_a_secret": "it is fine",
                        "review_by": "2027-01-15",
                    }
                ]
            },
        ),
        "marker gone from the file": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "docs/hosted-demo.md",
                        "head_marker": "a_string_nobody_writes_anywhere",
                        "why_not_a_secret": "x" * 80,
                        "review_by": "2027-01-15",
                    }
                ]
            },
        ),
        "missing file": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "tests/contract/no_such_file.py",
                        "head_marker": "CREDENTIAL_CANARY",
                        "why_not_a_secret": "x" * 80,
                        "review_by": "2027-01-15",
                    }
                ]
            },
        ),
        "expired exemption": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "tests/contract/test_provider_settings.py",
                        "head_marker": "CREDENTIAL_CANARY",
                        "why_not_a_secret": "x" * 80,
                        "review_by": "2026-01-01",
                    }
                ]
            },
        ),
        "unparsable review date": (
            clean,
            {
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "tests/contract/test_provider_settings.py",
                        "head_marker": "CREDENTIAL_CANARY",
                        "why_not_a_secret": "x" * 80,
                        "review_by": "next spring",
                    }
                ]
            },
        ),
        "registry that quotes a secret": (
            clean,
            {
                "_purpose": "x" * 30,
                "entries": [
                    {
                        "fingerprint": first,
                        "file": "tests/contract/test_provider_settings.py",
                        "head_marker": "CREDENTIAL_CANARY",
                        "why_not_a_secret": "the value is sk-or-v1-"
                        + "4" * 32
                        + " which is invented",
                        "review_by": "2027-01-15",
                    }
                ],
            },
        ),
    }

    for name, (text, data) in channels.items():
        found = _problems(text, data, today)
        assert found, f"the {name} channel cannot fire -- nothing in this list reports that defect"


def test_the_scanner_itself_is_pinned() -> None:
    """Unset, the action installs whatever gitleaks release is current at run time.

    A gate whose rule set can move with no commit is not the gate this ledger describes, so the version
    belongs to the finding record as much as the exceptions do.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "GITLEAKS_VERSION:" in text, (
        "secret-scan.yml leaves GITLEAKS_VERSION unset, so the action resolves upstream's latest release on "
        "every run and this gate's verdict can change with a commit that touched nothing here"
    )
    pinned = re.search(r'GITLEAKS_VERSION:\s*"([0-9]+\.[0-9]+\.[0-9]+)"', text)
    assert pinned, "the pin must be a quoted three-part version, not a range or a latest tag"
