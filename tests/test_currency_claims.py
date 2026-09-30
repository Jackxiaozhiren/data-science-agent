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

import pytest


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
