"""§146's currency rule, re-keyed by §151 for a copy that is written before its tag exists.

§136 put `docs/announcements/latest.md` in `CURRENCY_ASSERTIONS` keyed to the newest release **tag**.
That was wrong in a way only a real release could show: the copy was generated *from a published release*
(`generate_release_announcement.py` rendered the release body and `published_at`), and `publish.yml` runs
the test suite before it publishes anything. So the moment a tag existed ahead of its release, the gate
demanded a document that could not honestly be written yet -- and v4.5.0 stopped at exactly that step.

§146 replaced that with two offline invariants and one deliberate exemption: every released tag has its
dated copy *except the newest*, because that copy was still in the future. §151 removes the reason for
the exemption. The copy is now rendered by `--preview` from the CHANGELOG section of the release being
prepared, committed on the release branch, and merged before the tag is cut -- so it is on the default
branch while the tag is still pending. The rules therefore move the other way:

* a tag without its dated copy is a defect (the exemption is gone);
* a copy may lead the tags by exactly one version -- the one this tree declares;
* `publish.yml` reads the tree it checked out and never asks the API for main's state.
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


def _tree(
    tmp_path: Path,
    *,
    tags: list[str],
    copies: list[str],
    latest: str | None,
    declared: str | None = None,
) -> Path:
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "check_public_claims.py").write_bytes(SCRIPT.read_bytes())
    git = tmp_path / ".git"
    git.mkdir()
    (git / "packed-refs").write_text(
        "".join("0" * 40 + " refs/tags/" + t + "\n" for t in tags), encoding="utf-8"
    )
    if declared is not None:
        package = tmp_path / "src" / "data_science_agent"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(f'__version__ = "{declared}"\n', encoding="utf-8")
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


def test_a_copy_ahead_of_the_tags_with_no_declared_version_is_reported(tmp_path: Path) -> None:
    """The allowance in §151 hangs off the version this tree declares; with none, nothing is allowed."""
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.4.0"],
        copies=["4.2.10", "4.4.0", "4.5.0"],
        latest="4.5.0",
    )

    found = _issues(root)
    assert any("v4.5.0, which no release tag exists for" in i for i in found), found


def test_a_copy_for_the_version_being_released_may_lead_the_tags(tmp_path: Path) -> None:
    """§151: the copy is prepared on the release branch, so it exists before its tag does.

    §146 had to exempt this state because only a *published* release could supply the copy. Now the
    tree supplies it, so a copy naming the declared version is the release being prepared, not a
    written-up claim.
    """
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.4.0"],
        copies=["4.2.10", "4.4.0", "4.5.0"],
        latest="4.5.0",
        declared="4.5.0",
    )

    assert _issues(root) == []


def test_a_copy_beyond_the_declared_version_is_reported(tmp_path: Path) -> None:
    """The allowance is bounded by the declared version, not by goodwill."""
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.4.0"],
        copies=["4.2.10", "4.4.0", "4.7.0"],
        latest="4.7.0",
        declared="4.5.0",
    )

    found = _issues(root)
    assert any("v4.7.0, which no release tag exists for" in i for i in found), found
    assert any("names v4.7.0 as the latest release" in i for i in found), found


def test_the_copy_and_its_dated_file_must_agree(tmp_path: Path) -> None:
    """The copy is written as a pair, so a hand-edited latest.md is the pair coming apart."""
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


def test_the_newest_tag_without_its_copy_is_now_a_defect(tmp_path: Path) -> None:
    """§146's one deliberate exemption is closed by §151, and this assertion is the flip.

    A tag whose copy never landed used to be indistinguishable from a release still in flight, because
    demanding the copy deadlocked the release (§146). With the copy riding the release PR there is no
    such window left: tag without dated file means the PR shipped without it.
    """
    root = _tree(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0", "v4.5.0"],
        copies=["4.2.10", "4.3.0", "4.4.0"],
        latest="4.4.0",
        declared="4.5.0",
    )

    found = _issues(root)
    assert any("v4.5.0.md is missing" in i for i in found), found


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


def test_publish_verifies_the_copy_that_ships_with_the_tag() -> None:
    """§151: the release reads its own tree instead of trying to write a protected branch."""
    text = PUBLISH.read_text(encoding="utf-8")

    assert "Verify the announcement copy ships with this release" in text, (
        "the release no longer verifies its own announcement copy, so a copy that never rode the "
        "release PR is silent"
    )
    step = text[text.index("name: Verify the announcement copy ships") :]
    assert '"docs/announcements/${GITHUB_REF_NAME}.md"' in step, step[:600]
    assert 'expected="# Data Science Agent ${GITHUB_REF_NAME}"' in step, step[:600]
    assert "generate_release_announcement.py --preview" in step, (
        "the failure must name the command that fixes it"
    )
    assert "gh api" not in step, (
        "the step must read the tree this run checked out, not ask the API what main holds"
    )
    assert "contents/" not in text, (
        "a contents-API path is back: the write that step performed is what §149 proved impossible"
    )


def test_the_release_step_validates_the_event_derived_tag_before_use() -> None:
    """`GITHUB_REF_NAME` reaches a shell and a filename: it is pattern-checked first."""
    step = PUBLISH.read_text(encoding="utf-8")
    step = step[step.index("name: Verify the announcement copy ships") :]

    assert '"${GITHUB_REF_NAME}" =~ ^v[0-9]' in step, step[:600]


def test_the_control_a_step_that_compares_nothing_is_caught(tmp_path: Path) -> None:
    """The wiring guard above must be able to fail on a gutted workflow."""
    text = PUBLISH.read_text(encoding="utf-8")
    gutted = text.replace('expected="# Data Science Agent ${GITHUB_REF_NAME}"', 'expected=""')
    scratch = tmp_path / "publish.yml"
    scratch.write_text(gutted, encoding="utf-8")
    assert gutted != text, "the planted edit did not land"

    tail = gutted[gutted.index("Verify the announcement copy ships") :]
    assert "# Data Science Agent ${GITHUB_REF_NAME}" not in tail, (
        "the plant left the comparison in place, so the guard above proves nothing"
    )
