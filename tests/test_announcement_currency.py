"""§146: the announcement copy is checked against what a checkout can actually know.

§136 put `docs/announcements/latest.md` in `CURRENCY_ASSERTIONS` keyed to the newest release **tag**.
That was wrong in a way only a real release could show: the copy is generated *from a published release*
(`generate_release_announcement.py` renders the release body and `published_at`), and `publish.yml` runs
the test suite before it publishes anything. So the moment a tag exists ahead of its release, the gate
demands a document that cannot honestly be written yet -- and v4.5.0 stopped at exactly that step, with
both the release run and `main` red on `latest.md:1 cites '4.4.0' … newest release tag is '4.5.0'`.

The replacement keeps both halves of the original finding without that deadlock. The workflow writes
`v<X>.md` and `latest.md` together, so a copy that never landed is a released tag with no file, and a
handed-forward `latest.md` is a version no tag names. The one window the checker cannot see is the newest
tag, whose copy is legitimately still in the future -- and that window is closed at the only point where
it can be: `publish.yml` verifies, right after the generator step, that the default branch's copy opens
with the tag being released. A skipped copy is then a red *release*, not a quiet gap discovered months
later the way D-L4-13 was.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_public_claims.py"
PUBLISH = ROOT / ".github" / "workflows" / "publish.yml"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("cpc_announcement", str(SCRIPT))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COPY = "# Data Science Agent v{v}\n\n> Released 2026-01-02 · notes\n"


def _tree(tmp_path: Path, *, tags: list[str], copies: list[str], latest: str | None) -> Path:
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "check_public_claims.py").write_bytes(SCRIPT.read_bytes())
    git = tmp_path / ".git"
    git.mkdir()
    (git / "packed-refs").write_text(
        "".join("0" * 40 + " refs/tags/" + t + "\n" for t in tags), encoding="utf-8"
    )
    ann = tmp_path / "docs" / "announcements"
    ann.mkdir(parents=True)
    for version in copies:
        (ann / f"v{version}.md").write_text(COPY.format(v=version), encoding="utf-8")
    if latest is not None:
        (ann / "latest.md").write_text(COPY.format(v=latest), encoding="utf-8")
    return tmp_path


def _issues(root: Path) -> list[str]:
    return _load().announcement_currency_issues(root)


def test_a_released_tag_whose_copy_never_landed_is_reported(tmp_path: Path) -> None:
    """D-L4-13's shape: v4.3.0 published, no announcement file, and a newer release since."""
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0"],
        copies=["4.2.10", "4.4.0"],
        latest="4.4.0",
    )

    found = _issues(root)
    assert any("v4.3.0.md is missing" in i for i in found), found


def test_a_copy_naming_an_untagged_version_is_reported(tmp_path: Path) -> None:
    """The copy is generated from a release, so one ahead of the tags is a written-up claim."""
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.4.0"],
        copies=["4.2.10", "4.4.0", "4.5.0"],
        latest="4.5.0",
    )

    found = _issues(root)
    assert any("v4.5.0, which no release tag exists for" in i for i in found), found


def test_the_copy_and_its_dated_file_must_agree(tmp_path: Path) -> None:
    """The generator writes both at once, so a hand-edited latest.md is the pair coming apart."""
    root = _tree(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        copies=["4.3.0", "4.4.0"],
        latest="4.3.0",
    )

    found = _issues(root)
    assert any("names v4.3.0 but the newest dated copy is v4.4.0" in i for i in found), found


def test_a_coherent_history_is_clean(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0"],
        copies=["4.2.10", "4.3.0", "4.4.0"],
        latest="4.4.0",
    )

    assert _issues(root) == []


def test_the_newest_tag_without_a_copy_is_the_one_window_left_open(tmp_path: Path) -> None:
    """Pinned as a decision, not a gap in the test: tag exists, release does not yet.

    Demanding the copy here is what deadlocked v4.5.0 -- the generator cannot render a release that has
    not been created, and `publish.yml` runs the suite before creating it. `publish.yml`'s own
    verification step closes the window at the moment the release is cut.
    """
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0", "v4.5.0"],
        copies=["4.2.10", "4.3.0", "4.4.0"],
        latest="4.4.0",
    )

    assert _issues(root) == []


def test_no_readable_refs_is_reported_rather_than_passing(tmp_path: Path) -> None:
    root = _tree(tmp_path, tags=[], copies=["4.4.0"], latest="4.4.0")

    found = _issues(root)
    assert len(found) == 1 and "no release tags readable" in found[0], found


def test_the_shipped_announcements_satisfy_the_rule() -> None:
    """The live tree, checked by the shipped entry point -- §135 and §146's own claims included.

    Before §146's backfill this reported the four 4.3.x releases whose copies never landed, which is the
    state D-L4-13 left behind and which no rule caught between August and October.
    """
    assert _load().announcement_currency_issues(ROOT) == []


def test_the_floor_names_the_era_the_pipeline_started_in() -> None:
    """The bound is a decision with a reason, so it must not silently widen or narrow."""
    module = _load()
    floor = module.ANNOUNCEMENT_FLOOR
    assert re.fullmatch(r"\d+\.\d+\.\d+", floor), floor
    assert module._as_version(floor) is not None
    assert floor == "4.3.0", "changing the floor changes which releases must carry a copy; say why"


# --- the release-time half ------------------------------------------------------------------


def test_publish_verifies_the_copy_lands_on_the_release_being_cut() -> None:
    """The checker cannot see this window; the workflow that produces the copy can."""
    text = PUBLISH.read_text(encoding="utf-8")

    assert "Verify the announcement copy names this release" in text, (
        "the release no longer verifies its own announcement copy, so a skipped generation is silent"
    )
    generate = text.index("name: Generate release announcement")
    verify = text.index("name: Verify the announcement copy names this release")
    assert generate < verify, "the verification has to run after the step whose output it checks"
    tail = text[verify:]
    assert re.search(r"contents/docs/announcements/latest\.md\?ref=\$\{branch\}", tail), tail[:400]
    assert "# Data Science Agent ${GITHUB_REF_NAME}" in tail, (
        "the step must compare against the tag being released, not a version someone typed"
    )


def test_the_release_step_validates_event_derived_values_before_use() -> None:
    """`GITHUB_REF_NAME` and the API's default branch reach a shell: both are checked first."""
    tail = PUBLISH.read_text(encoding="utf-8")
    step = tail[tail.index("name: Verify the announcement copy") :]

    assert '"${GITHUB_REF_NAME}" =~ ^v[0-9]' in step, step[:600]
    assert '"${branch}" =~ ^[A-Za-z0-9._/-]+$' in step, step[:600]


def test_the_control_a_step_that_compares_nothing_is_caught(tmp_path: Path) -> None:
    """The wiring guard above must be able to fail on a gutted workflow."""
    text = PUBLISH.read_text(encoding="utf-8")
    gutted = re.sub(
        r"# Data Science Agent \$\{GITHUB_REF_NAME}",
        "something else entirely",
        text,
    )
    scratch = tmp_path / "publish.yml"
    scratch.write_text(gutted, encoding="utf-8")
    assert scratch.read_text(encoding="utf-8") != text, "the planted edit did not land"

    assert (
        "# Data Science Agent ${GITHUB_REF_NAME}"
        not in gutted[gutted.index("Verify the announcement") :]
    )
