"""The git position must come from two different directories when the checkout is a linked worktree.

``scripts/audit_facts.py`` reports ``git.head``, ``git.branch``, ``git.tagCount``, ``git.commitStampAgeDays``
and ``git.filesTouchedSinceLastCommit``. It had one helper for all of them, and that helper stopped at the
first hop: it followed ``.git``'s ``gitdir:`` pointer to the per-worktree directory and read everything there.
A linked worktree keeps its own ``HEAD`` and index in that directory but keeps **no refs** -- branches, tags
and ``packed-refs`` live in the common directory its ``commondir`` file names. So in every task worktree the
collector read ``tagCount: 0``, ``head: "(unreadable)"``, ``commitStampAgeDays: None`` and
``filesTouchedSinceLastCommit: 0``, while the shared checkout of the same commit reported 38 tags and a real
sha. Nothing failed: an absent directory reads as empty here by design, which is the same one-hop miss
``check_public_claims.released_versions()`` carried until #137.

Following ``commondir`` for everything is the other failure, so both directions are pinned. Doing it moves
``HEAD`` into the shared checkout and the collector starts reporting whichever branch the main working tree
has out -- measured while writing this fix, where a worktree on ``ci-audit-facts-gitdir`` read ``branch: main``.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

MAIN_SHA = "1" * 40
FEATURE_SHA = "2" * 40
AUDIT_SCRIPT = "audit_facts.py"
CLAIMS_SCRIPT = "check_public_claims.py"
TAGS = ["v8.8.8", "v9.9.9"]


def _load(root: Path, script: str):
    """Import a checker from a copy installed inside `root`, so its own ``ROOT`` derivation lands there."""
    target = root / "scripts" / script
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(Path("scripts", script).read_text(encoding="utf-8"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"{script[:-3]}_{root.name}", target)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if script == AUDIT_SCRIPT:
        sandbox = root.resolve()
        assert sandbox == module.ROOT, (module.ROOT, sandbox)
    return module


def _refs_and_tags(base: Path) -> Path:
    """A shared ``$GIT_DIR``: two branches, one loose tag, one packed tag."""
    common = base / "common"
    (common / "refs" / "heads").mkdir(parents=True)
    (common / "refs" / "tags").mkdir(parents=True)
    (common / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (common / "refs" / "heads" / "main").write_text(f"{MAIN_SHA}\n", encoding="utf-8")
    (common / "refs" / "heads" / "feature").write_text(f"{FEATURE_SHA}\n", encoding="utf-8")
    (common / "refs" / "tags" / "v9.9.9").write_text(f"{MAIN_SHA}\n", encoding="utf-8")
    (common / "packed-refs").write_text(f"{MAIN_SHA} refs/tags/v8.8.8\n", encoding="utf-8")
    return common


def _plain(tmp_path: Path):
    """A checkout whose ``.git`` is a directory -- what CI and the shared working tree look like."""
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    common = _refs_and_tags(tmp_path)
    for child in common.iterdir():
        os.replace(child, root / ".git" / child.name)
    return _load(root, AUDIT_SCRIPT)


def _linked(
    tmp_path: Path,
    *,
    relative_pointer: bool = False,
    emit_commondir: bool = True,
    head: str = "ref: refs/heads/feature\n",
):
    """A task worktree: ``.git`` points at a per-worktree directory that holds ``HEAD`` and no refs."""
    base = tmp_path / "repo"
    common = _refs_and_tags(base)
    gitdir = common / "worktrees" / "wt1"
    gitdir.mkdir(parents=True)
    (gitdir / "HEAD").write_text(head, encoding="utf-8")
    if emit_commondir:
        (gitdir / "commondir").write_text("../..\n", encoding="utf-8")
    root = base / "checkout"
    root.mkdir()
    target = os.path.relpath(gitdir, root) if relative_pointer else str(gitdir)
    (root / ".git").write_text(f"gitdir: {target}\n", encoding="utf-8")
    return _load(root, AUDIT_SCRIPT)


def test_a_plain_checkout_resolves_both_helpers_to_the_same_directory(tmp_path: Path) -> None:
    """No pointer, no common directory: the fix must be a no-op where `.git` is a directory, as in CI."""
    module = _plain(tmp_path)
    assert module._git_dir() == module._refs_dir() == module.ROOT / ".git"
    position = module._git_position()
    assert position["branch"] == "main"
    assert position["head"] == MAIN_SHA
    assert position["tagCount"] == len(TAGS)


def test_a_linked_checkout_reads_its_tags_from_the_common_directory(tmp_path: Path) -> None:
    """The state every task worktree is in: the pointer hop alone finds no refs at all."""
    module = _linked(tmp_path)
    checkout = module.ROOT
    assert module._list_tags(module._git_dir(checkout)) == []
    assert module._list_tags(module._refs_dir(checkout)) == TAGS


def test_a_linked_checkout_reports_a_nonzero_tag_count(tmp_path: Path) -> None:
    """The reading this bug made impossible: `tagCount` was 0 in every worktree, 38 in the shared tree."""
    assert _linked(tmp_path)._git_position()["tagCount"] == len(TAGS)


def test_head_and_branch_come_from_the_worktree_not_the_common_directory(tmp_path: Path) -> None:
    """The other half: following ``commondir`` for ``HEAD`` reports somebody else's branch.

    Both directories hold a different branch on purpose, so a helper that resolves ``HEAD`` from the common
    directory reads ``main`` here while this checkout sits on ``feature``.
    """
    position = _linked(tmp_path)._git_position()
    assert position["branch"] == "feature"
    assert position["head"] == FEATURE_SHA
    assert position["commitStampAgeDays"] is not None


def test_packed_refs_are_resolved_from_the_common_directory_too(tmp_path: Path) -> None:
    """A branch that exists only in ``packed-refs`` resolves, so a loose-file miss cannot hide a wrong hop."""
    module = _linked(tmp_path)
    common = module.ROOT.parent / "common"
    (common / "refs" / "heads" / "feature").unlink()
    (common / "packed-refs").write_text(
        f"{MAIN_SHA} refs/tags/v8.8.8\n{FEATURE_SHA} refs/heads/feature\n", encoding="utf-8"
    )
    assert module._git_position()["head"] == FEATURE_SHA


def test_a_detached_linked_checkout_still_names_its_own_commit(tmp_path: Path) -> None:
    """Detached ``HEAD`` is a sha in the worktree directory, so it never passes through the refs dir."""
    position = _linked(tmp_path, head=f"{FEATURE_SHA}\n")._git_position()
    assert position["branch"] == "(detached)"
    assert position["head"] == FEATURE_SHA
    assert position["tagCount"] == len(TAGS)


def test_a_relative_gitdir_pointer_resolves_against_the_checkout(tmp_path: Path) -> None:
    """Git writes a relative pointer when the worktree sits under the repository, which is this repo's shape."""
    module = _linked(tmp_path, relative_pointer=True)
    assert module._list_tags(module._refs_dir(module.ROOT)) == TAGS


def test_a_pointer_without_a_commondir_falls_back_to_the_named_directory(tmp_path: Path) -> None:
    """An empty tag set stays expressible: the second hop must not invent a directory that is not there."""
    module = _linked(tmp_path, emit_commondir=False)
    assert module._refs_dir(module.ROOT) == module._git_dir(module.ROOT)
    assert module._git_position()["tagCount"] == 0


def test_both_scripts_resolve_the_same_common_directory(tmp_path: Path) -> None:
    """Two fixes, one truth: the collectors must not drift on where the refs live."""
    module = _linked(tmp_path)
    checkout = module.ROOT
    claims = _load(checkout, CLAIMS_SCRIPT)
    assert module._refs_dir(checkout) == claims.git_directory(checkout)
    assert module._list_tags(module._refs_dir(checkout)) == sorted(
        f"v{version}" for version in claims.released_versions(checkout)
    )


def test_the_two_hops_disagree_only_where_a_worktree_says_they_should(tmp_path: Path) -> None:
    """Measured against this repository as it stands, in whichever of the two shapes it is in.

    The tag count is not asserted -- it changes on every release -- only that a linked checkout finds its refs
    one directory away from its ``HEAD``, and a plain checkout finds them in the same place both times.
    """
    root = Path(__file__).resolve().parents[1]
    module = _load(tmp_path / "sandbox", AUDIT_SCRIPT)
    worktree_dir = module._git_dir(root)
    refs_dir = module._refs_dir(root)
    is_linked_worktree = (root / ".git").is_file()
    if is_linked_worktree:
        assert refs_dir != worktree_dir
        assert module._list_tags(refs_dir)
        assert module._list_tags(worktree_dir) == []
    else:
        assert refs_dir == worktree_dir
