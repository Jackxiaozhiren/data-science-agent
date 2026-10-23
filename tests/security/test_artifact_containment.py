"""Every artifact path a caller can name goes through one rule, and nothing tested that rule.

`dsa_datasets.artifact_paths` exists because six writers used to derive the artifact directory from their own
installed location (§122), and `run_id` used to be interpolated raw into a write path. The rule is now: one
path component, `[A-Za-z0-9._-]`, not starting with a dot, and every writer and reader calls `artifact_root()`
which runs `_checked` on each argument. Verified true by reading -- and unowned by any test, which is what this
file fixes. `docs/tools.md` advertises "traversal block", so the claim needs a guard that can fail.

The interesting case is not `../x` in a filename, which the name blacklist catches: it is a symlink already
inside the artifact root, where only the `resolve()`/`relative_to()` layer stops the write.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from dsa_datasets.artifact_paths import artifact_root, is_safe_segment
from dsa_tools.tools.save_artifact import SaveArtifactInput, SaveArtifactTool

_UNSAFE = ["..", ".", ".hidden", "a/b", "a\\b", "/tmp/x", "", "x" * 129, "a b", "a\nb"]
_SAFE = ["run-1", "Run_2", "a.b-c", "x" * 128]


def test_the_segment_rule_names_exactly_what_one_component_may_be() -> None:
    for bad in _UNSAFE:
        assert not is_safe_segment(bad), f"{bad!r} must not name an artifact directory"
    for good in _SAFE:
        assert is_safe_segment(good), f"{good!r} is a legitimate run id and was refused"


def test_artifact_root_refuses_every_argument_that_is_not_one_component() -> None:
    """The rule runs at construction, so no caller can skip it by forgetting to validate."""
    for bad in _UNSAFE:
        with pytest.raises(ValueError):
            artifact_root("reports", bad, "report.md")


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    r = tmp_path / "artifacts"
    monkeypatch.setenv("DSA_ARTIFACT_ROOT", str(r))
    monkeypatch.chdir(tmp_path)
    return r


@pytest.mark.asyncio
async def test_a_writer_refuses_a_name_that_is_not_a_plain_file(root: Path) -> None:
    tool = SaveArtifactTool()
    for bad in ("../escape.md", "sub/dir.md", "..\\escape.md", "/tmp/absolute.md"):
        res = await tool.run({"run_id": "run-1", "type": "report", "filename": bad, "content": "x"})
        assert res.status == "error", f"{bad!r} was accepted as a filename"
    listed = sorted(p.name for p in (root / "run-1").glob("*")) if (root / "run-1").exists() else []
    assert listed == [], f"a refused write still produced a file: {listed}"
    assert not (root.parent / "escape.md").exists()


@pytest.mark.asyncio
async def test_the_writer_writes_inside_the_root_for_an_ordinary_name(root: Path) -> None:
    """Without this the refusal test could be satisfied by a tool that writes nothing at all."""
    res = await SaveArtifactTool().run(
        {"run_id": "run-1", "type": "report", "filename": "report.md", "content": "kept"}
    )
    assert res.status == "ok", res.error
    assert (root / "run-1" / "report.md").read_text(encoding="utf-8") == "kept"


@pytest.mark.asyncio
async def test_a_symlink_inside_the_root_does_not_become_a_write_outside_it(root: Path) -> None:
    """The name blacklist cannot see this one, and it is the case `resolve()` was added for."""
    target = root.parent / "outside.csv"
    target.write_text("do not overwrite me\n", encoding="utf-8")
    run_dir = artifact_root("run-9")
    run_dir.mkdir(parents=True, exist_ok=True)
    os.symlink(target, run_dir / "link.csv")

    res = await SaveArtifactTool().run(
        {"run_id": "run-9", "type": "dataset", "filename": "link.csv", "content": "clobbered"}
    )
    assert res.status == "error", "a symlink carried the write outside the artifact root"
    assert target.read_text(encoding="utf-8") == "do not overwrite me\n", (
        "the refused write landed anyway"
    )


@pytest.mark.asyncio
async def test_a_reader_refuses_a_run_id_that_would_climb_out_of_the_tree(root: Path) -> None:
    """`report://..` would resolve to <root>/report.md without the component rule.

    The sentinel is placed exactly where that climb would land, so removing `_checked` from `artifact_root`
    makes this return its text instead of a refusal -- the test fails on the escape rather than on the error
    string. `reports/` has to exist too: POSIX resolves `reports/..` left to right, so without that directory
    the climb fails for a reason that has nothing to do with the rule, and the test passes while proving nothing
    (measured -- that is how this file's first version got away with it).
    """
    from dsa_mcp.resources import read_resource

    sentinel = "SENTINEL-OUTSIDE-THE-RUN-DIRECTORY"
    root.mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    (root / "report.md").write_text(sentinel, encoding="utf-8")

    out = await read_resource("report://..")
    assert out.get("isError"), f"the reader returned a resource for a climbing run id: {out}"
    assert sentinel not in str(out.get("text", "")), "the climb read the file one level up"
