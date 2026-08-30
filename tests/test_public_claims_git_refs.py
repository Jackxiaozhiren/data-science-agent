from __future__ import annotations

from scripts import check_public_claims as public_claims


def test_latest_local_version_tag_reads_loose_refs(tmp_path) -> None:
    tags = tmp_path / ".git" / "refs" / "tags"
    tags.mkdir(parents=True)
    (tags / "v4.2.10").write_text("a" * 40 + "\n", encoding="utf-8")
    (tags / "v4.1.1").write_text("b" * 40 + "\n", encoding="utf-8")

    assert public_claims._latest_local_version_tag(tmp_path) == "v4.2.10"


def test_latest_local_version_tag_reads_packed_refs(tmp_path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled fully-peeled sorted\n"
        + ("a" * 40)
        + " refs/tags/v4.2.10\n"
        + ("b" * 40)
        + " refs/tags/v4.3.0\n",
        encoding="utf-8",
    )

    assert public_claims._latest_local_version_tag(tmp_path) == "v4.3.0"
