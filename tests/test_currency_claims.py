"""The version detector must recognise *currency claims*, not version-shaped text.

`stale_version` was `\\b(4\\.0\\.0|3\\.0\\.0|2\\.0\\.0)\\b` -- a hand-maintained blacklist of three
retired releases. It could not see `v4.3.0` in README's latest-release badge, and would have
missed the successor to that too, so the detector was blind to the exact drift class it exists
for. Generalising to "any released version that is not current" is worse instead of better:
measured over the scanned surface it fires 160 times, of which 150 are CHANGELOG release records
and the rest are `cff-version: 1.2.0` (a metadata format number that happens to collide with a
tag), `references: version: 4.2.0` (a citation *for* an old release), and the two sub-apps' own
`"version": "0.1.0"`.

So the rule is structural: a small table of places where a document *asserts* which release is
current or upcoming, each evaluated against the tag set.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load(root: Path):
    script = root / "scripts" / "check_public_claims.py"
    spec = importlib.util.spec_from_file_location(f"cpc_{root.name}", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scratch(tmp_path: Path, *, tags: list[str], current: str, files: dict[str, str]) -> Path:
    root = tmp_path
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "check_public_claims.py").write_text(
        Path("scripts/check_public_claims.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    git = root / ".git"
    git.mkdir()
    (git / "packed-refs").write_text(
        "".join(f"{'0' * 40} refs/tags/{t}\n" for t in tags), encoding="utf-8"
    )
    init = root / "src/data_science_agent"
    init.mkdir(parents=True)
    (init / "__init__.py").write_text(f'__version__ = "{current}"\n', encoding="utf-8")
    for rel, body in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _issues(root: Path) -> list[str]:
    module = _load(root)
    return module.check_currency_claims(root)


def test_stale_latest_release_badge_is_flagged(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.3.0**](https://x.example/releases/tag/v4.3.0)\n"},
    )
    found = _issues(root)
    assert any("4.3.0" in issue for issue in found), found
    assert any("README.md" in issue for issue in found), found


def test_current_badge_is_not_flagged(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.4.0**](https://x.example/releases/tag/v4.4.0)\n"},
    )
    assert _issues(root) == []


def test_roadmap_must_point_at_an_unreleased_version(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={
            "ROADMAP.md": "- Track the next minor release through [v4.3.0 Release Readiness](x)\n"
        },
    )
    found = _issues(root)
    assert any("4.3.0" in issue for issue in found), found

    ok = _scratch(
        tmp_path / "ok",
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={
            "ROADMAP.md": "- Track the next minor release through [v4.5.0 Release Readiness](x)\n"
        },
    )
    assert _issues(ok) == []


def test_historical_and_foreign_versions_are_left_alone(tmp_path: Path) -> None:
    """The false positives that make a blanket rule unusable, pinned as non-issues."""
    root = _scratch(
        tmp_path,
        tags=["v1.2.0", "v4.2.0", "v0.1.0", "v4.4.0"],
        current="4.4.0",
        files={
            "CITATION.cff": (
                "cff-version: 1.2.0\nversion: 4.4.0\nreferences:\n"
                "  - type: software\n    version: 4.2.0\n"
            ),
            "CHANGELOG.md": "## 4.2.0 — old release\n- also mentions 1.2.0 here\n",
            "apps/web/package.json": '{"name": "web", "version": "0.1.0"}\n',
        },
    )
    assert _issues(root) == []


def test_the_detector_reads_the_tag_set_it_claims(tmp_path: Path) -> None:
    """Without this, an empty tag set would make every check pass by having nothing to compare."""
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.3.0**](https://x.example/releases/tag/v4.3.0)\n"},
    )
    module = _load(root)
    released = module.released_versions(root)
    assert "4.3.0" in released and "4.4.0" in released, released
    assert module.current_version(root) == "4.4.0"
    # peeled entries must not be counted as extra refs (same trap as the tag census)
    (root / ".git" / "packed-refs").write_text(
        "0" * 40 + " refs/tags/v4.4.0\n" + "0" * 40 + " refs/tags/v4.4.0^{}\n",
        encoding="utf-8",
    )
    assert module.released_versions(root) == {"4.4.0"}


def test_the_retired_blacklist_key_is_gone_from_patterns() -> None:
    """`stale_version` must no longer exist as a rule, checked on the AST.

    Asserting on file text would be both brittle (the comment above explains the old literal)
    and shallow (a string in a docstring is not a live rule).
    """
    import ast

    tree = ast.parse(Path("scripts/check_public_claims.py").read_text(encoding="utf-8"))
    patterns: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "PATTERNS" for target in node.targets
        ):
            patterns = {
                key.value: value
                for key, value in zip(node.value.keys, node.value.values, strict=False)
                if isinstance(key, ast.Constant)
            }
    assert patterns, "no PATTERNS dict found, so this test checks nothing"
    assert "stale_version" not in patterns, sorted(patterns)


def test_a_tagless_checkout_still_catches_a_stale_current_release(tmp_path: Path) -> None:
    """A default-depth CI checkout fetches no tags; the badge check must not go dark.

    Whether some *other* version is already released needs the tag set, but "is this the current
    release" is answerable from the declared version alone, and that is the higher-value half.
    """
    root = _scratch(
        tmp_path,
        tags=[],
        current="4.4.0",
        files={
            "README.md": "Docs at [**v4.3.0**](https://x.example/releases/tag/v4.3.0)\n",
            "ROADMAP.md": "- Track the next minor release through [v4.3.0 Release Readiness](x)\n",
        },
    )
    found = _issues(root)
    assert any("README.md" in issue and "4.3.0" in issue for issue in found), (
        f"the badge check disabled itself for want of tags: {found}"
    )
    assert not any("ROADMAP.md" in issue for issue in found), (
        "without a tag set there is no way to prove a version already shipped; guessing is worse "
        f"than silence: {found}"
    )
    assert _degradations(root), "the reduced coverage was invisible rather than reported"


def test_no_version_information_at_all_still_reports_disabled(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=[],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.4.0**](https://x.example/releases/tag/v4.4.0)\n"},
    )
    (root / "src/data_science_agent/__init__.py").write_text('name = "x"\n', encoding="utf-8")
    found = _issues(root)
    assert any("disabled" in issue for issue in found), found


def _degradations(root: Path) -> list[str]:
    return _load(root).currency_degradations(root)


def test_an_empty_tag_set_is_refused_when_tags_are_required(tmp_path: Path) -> None:
    """CI may not run this rule degraded: no refs means no verdict on "already shipped"."""
    root = _scratch(
        tmp_path,
        tags=[],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.4.0**](https://x.example/releases/tag/v4.4.0)\n"},
    )
    gate = getattr(_load(root), "require_released_tags", None)
    assert gate is not None, (
        "the checker has no tag requirement, so a shallow checkout silently drops half its rules"
    )
    message = gate(root)
    assert message and "tag" in message.lower(), f"empty tag set accepted: {message!r}"


def test_a_populated_tag_set_satisfies_the_requirement(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"README.md": "Docs at [**v4.4.0**](https://x.example/releases/tag/v4.4.0)\n"},
    )
    gate = getattr(_load(root), "require_released_tags", None)
    assert gate is not None, "the requirement helper is missing"
    assert gate(root) is None, "a real release line must satisfy the requirement"


def test_the_real_repository_carries_a_release_line() -> None:
    """The flag can only be enforced in CI if the checkout it runs against has refs."""
    module = _load(Path.cwd())
    assert module.released_versions(), "no tags readable from this checkout"
    gate = getattr(module, "require_released_tags", None)
    assert gate is not None, "the requirement helper is missing"
    assert gate() is None, "this checkout would fail its own CI flag"


# --- §136: the announcement copy is a currency surface ---------------------------------------
#
# `docs/announcements/` was exempted from the checker by directory, which put `latest.md` -- the page
# that tells readers which release to install -- outside the one rule built for stale-release claims.
# It named v4.2.10 across five published releases and nothing said anything. These cases run the whole
# surface off fixtures, because the shipped tree can only ever show the passing side.


def _announcement(version: str) -> str:
    return (
        f"# Data Science Agent v{version}\n\n"
        "> Released 2026-09-11 - Evidence-grounded autonomous data science.\n"
    )


def test_an_announcement_naming_an_older_release_is_flagged(tmp_path: Path) -> None:
    """The D-L4-13 state: latest.md said 4.2.10 while 4.4.0 was published."""
    root = _scratch(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"docs/announcements/latest.md": _announcement("4.2.10")},
    )
    found = _issues(root)
    assert any("latest.md" in issue for issue in found), found
    assert any("4.2.10" in issue and "4.4.0" in issue for issue in found), found


def test_an_announcement_naming_the_newest_release_is_clean(tmp_path: Path) -> None:
    root = _scratch(
        tmp_path,
        tags=["v4.2.10", "v4.3.0", "v4.4.0"],
        current="4.4.0",
        files={"docs/announcements/latest.md": _announcement("4.4.0")},
    )
    assert _issues(root) == []


def test_the_announcement_tracks_the_newest_release_not_the_declared_version(
    tmp_path: Path,
) -> None:
    """Why the reference is `newest`, which is what separates this rule from the README badge's.

    Between a version bump and its publish, `__version__` says 4.5.0 while the newest release is still
    4.4.0. Keying the copy to the declared version would call a truthful announcement stale at exactly
    the moment a release is pending, and a gate that fires on honest content gets quieted rather than
    read -- so the pending bump must stay clean here.
    """
    root = _scratch(
        tmp_path,
        tags=["v4.3.0", "v4.4.0"],
        current="4.5.0",
        files={"docs/announcements/latest.md": _announcement("4.4.0")},
    )
    assert _issues(root) == [], "a pending version bump made a truthful copy look stale"


def test_the_newest_release_helper_orders_numerically_and_skips_suffixes(tmp_path: Path) -> None:
    """A lexical max picks 4.9.0 over 4.10.0, and an rc ref is not a release line."""
    module = _load(_scratch(tmp_path, tags=["v4.4.0"], current="4.4.0", files={}))
    assert module._newest_release({"4.9.0", "4.10.0"}) == "4.10.0"
    assert module._newest_release({"4.4.0", "4.4.0-rc1"}) == "4.4.0"
    assert module._newest_release({"4.4.0", "nightly"}) == "4.4.0"
    assert module._newest_release(set()) == ""


def test_the_announcement_rule_reports_itself_undecidable_without_refs(tmp_path: Path) -> None:
    """No refs is not a pass: the rule names what it could not answer, and the CI flag refuses it."""
    root = _scratch(
        tmp_path,
        tags=[],
        current="4.4.0",
        files={"docs/announcements/latest.md": _announcement("4.4.0")},
    )
    degraded = _degradations(root)
    assert any("docs/announcements/latest.md" in line for line in degraded), degraded
    gate = _load(root).require_released_tags(root)
    assert gate is not None and "docs/announcements/latest.md" in gate, gate


def test_the_announcement_copy_is_no_longer_skipped_as_historical() -> None:
    """The exemption that hid it: a directory prefix, applied to a current-tense page."""
    module = _load(Path.cwd())
    scanned, skipped = module.scan_scope(Path.cwd())
    names = {str(p.relative_to(Path.cwd())) for p in scanned}
    skipped_names = {str(p.relative_to(Path.cwd())) for p in skipped}

    assert "docs/announcements/latest.md" in names, sorted(skipped_names)
    assert "docs/announcements/latest.md" not in skipped_names
    # The dated copies stay exempt, and the rule must still reach them or it is §113's dead prefix.
    assert "docs/announcements/v4.4.0.md" in skipped_names
    assert "docs/announcements/v" in module.HISTORICAL_PREFIXES


# --- §144: the README badge is a claim about the newest *release*, not about the declared version ---


def _badge_root(tmp_path: Path, *, tags: list[str], current: str, badge: str) -> Path:
    return _scratch(
        tmp_path,
        tags=tags,
        current=current,
        files={"README.md": f"Docs at [**v{badge}**](https://x.example/releases/tag/v{badge})\n"},
    )


def test_a_pending_bump_does_not_make_the_release_badge_look_stale(tmp_path: Path) -> None:
    """RED before §144: bumping `__init__.py` ahead of the tag demanded a link to a release that does not exist.

    Measured on a simulated tree (declared 4.5.0, newest tag 4.4.0, badge 4.4.0) the rule returned
    `README.md:1 cites '4.4.0', advertised as the current release, which it is not`. The badge was the
    truthful artefact there -- it names the release readers get from PyPI today -- and the gate was asking
    for a broken link to a tag no one has pushed. A bump could not land green without writing a false
    claim, which is the §16 drift class pointed at its own author.
    """
    root = _badge_root(
        tmp_path, tags=["v4.2.10", "v4.3.3", "v4.4.0"], current="4.5.0", badge="4.4.0"
    )

    assert _issues(root) == [], _issues(root)


def test_the_badge_must_still_track_the_newest_release(tmp_path: Path) -> None:
    """The bound on that relaxation: once a release exists, the badge has to name it."""
    root = _badge_root(
        tmp_path, tags=["v4.2.10", "v4.3.3", "v4.4.0"], current="4.4.0", badge="4.3.3"
    )

    found = _issues(root)
    assert any("README.md" in issue and "4.3.3" in issue for issue in found), found


def test_the_badge_still_answers_from_the_declared_version_with_no_refs(tmp_path: Path) -> None:
    """§121's guarantee kept through §144's relaxation, and the residual it leaves.

    With no refs the badge compares against the declared version, so a stale badge is still caught in a
    default-depth checkout. The cost is exact and accepted: a tagless checkout *during* a pending bump
    demands the newer number. CI cannot sit in that state -- `--require-released-tags` refuses a run with
    no refs -- and every real checkout of this repository has tags, so the residual is local-only and loud
    rather than silent.
    """
    root = _badge_root(tmp_path, tags=[], current="4.5.0", badge="4.4.0")

    found = _issues(root)
    assert any("README.md" in issue and "4.4.0" in issue for issue in found), found
    assert not any("README.md" in line for line in _degradations(root)), (
        "the badge went dark instead of answering from the declared version"
    )
