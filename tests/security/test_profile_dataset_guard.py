"""`profile_dataset` accepts one path, so every refusal it can make is attached to that one value.

ADR-004's D1 asks for a request-time decision on three capabilities that the first boundary reading
recorded as `undecidable` because nothing refused them: process spawn, filesystem write, and
credential read. This file pins the three refusals to behaviour rather than to prose.

The three are not the same kind of claim and the tests keep them apart:

* **process spawn** — the reader is chosen from a six-format allowlist, never from the file, so a
  format whose loader executes code has no path into this surface. The test refuses a `.pkl` name.
* **credential read** — names and directories that exist to hold secrets are refused before the
  reader is chosen.
* **filesystem write** — the input's size, mtime and inode are captured before the read and compared
  after it. The test mutates the file between the two observations, which is the only way to watch
  the check fire without a writer.

What is *not* claimed here: that no write happens, or that a path the request never names is
observed. The record's residual text says the same thing.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from dsa_datasets.errors import UnsupportedFormatError
from dsa_tools.errors import ToolExecutionError
from dsa_tools.tools.profile_dataset import (
    ProfileDatasetInput,
    ProfileDatasetTool,
    _fingerprint,
    _guard_path,
    _guard_request,
    _guard_unchanged,
)

CSV_BODY = "region,units\nnorth,3\nsouth,5\n"


def _csv(tmp_path: Path, name: str = "data.csv") -> Path:
    path = tmp_path / name
    path.write_text(CSV_BODY, encoding="utf-8")
    return path


@pytest.mark.parametrize("name", [".env", ".env.local", "id_rsa", "server.pem", "client.p12"])
def test_a_credential_shaped_name_is_refused(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("secret\n", encoding="utf-8")
    with pytest.raises(ToolExecutionError, match="credential"):
        _guard_path(path)


def test_a_data_file_inside_a_credential_directory_is_refused(tmp_path: Path) -> None:
    hidden = tmp_path / ".ssh"
    hidden.mkdir()
    path = hidden / "known_hosts.csv"
    path.write_text(CSV_BODY, encoding="utf-8")
    with pytest.raises(ToolExecutionError, match="credential"):
        _guard_path(path)


def test_a_symlink_is_refused_even_when_its_target_is_a_csv(tmp_path: Path) -> None:
    target = _csv(tmp_path)
    link = tmp_path / "link.csv"
    link.symlink_to(target)
    with pytest.raises(ToolExecutionError, match="symbolic link"):
        _guard_path(link)


def test_a_directory_is_not_a_dataset(tmp_path: Path) -> None:
    with pytest.raises(ToolExecutionError, match="Not a regular file"):
        _guard_path(tmp_path)


def test_a_format_whose_loader_executes_code_is_not_reachable(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    with pytest.raises(UnsupportedFormatError):
        _guard_request(path, "payload.pkl", str(path))


def test_the_reader_is_chosen_from_the_allowlist_not_from_the_file(tmp_path: Path) -> None:
    """A pickle named `.csv` reaches the CSV reader: the allowlist decides, the suffix does not."""
    path = _csv(tmp_path, "payload.csv")
    fmt = _guard_request(path, None, str(path))
    assert fmt.value == "csv"


def test_a_mutated_input_is_refused(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    before = _fingerprint(path)
    path.write_text(CSV_BODY + "east,7\n", encoding="utf-8")
    with pytest.raises(ToolExecutionError, match="changed"):
        _guard_unchanged(path, before)


def test_an_untouched_input_passes_the_same_check(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    before = _fingerprint(path)
    _guard_unchanged(path, before)


def test_a_credential_inside_the_tool_path_is_refused_before_the_reader(tmp_path: Path) -> None:
    """The tool's own entry point refuses, not just the helper a test can call directly."""
    path = tmp_path / ".env"
    path.write_text("DSA_TOKEN=1\n", encoding="utf-8")
    with pytest.raises(ToolExecutionError, match="credential"):
        asyncio.run(ProfileDatasetTool().execute(ProfileDatasetInput(path=str(path))))


async def test_a_plain_csv_still_profiles(tmp_path: Path) -> None:
    path = _csv(tmp_path)
    out = await ProfileDatasetTool().execute(ProfileDatasetInput(path=str(path)))
    assert out.dataset_id == "data"
    assert out.profile
