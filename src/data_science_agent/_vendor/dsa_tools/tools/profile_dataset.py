from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from dsa_datasets.models import DatasetFormat
from dsa_datasets.validate import detect_format
from dsa_tools.base import BaseTool
from dsa_tools.errors import ToolExecutionError

#: Names whose whole purpose is to hold a secret. Deliberately short and closed: a list that grows
#: with every incident is a filter, and this one is meant to be read in a review.
_CREDENTIAL_NAMES = re.compile(
    r"^(?:\.env(?:\..+)?|\.netrc|\.htpasswd|\.pgpass|id_(?:rsa|dsa|ecdsa|ed25519)(?:\.pub)?"
    r"|.+\.(?:pem|key|p12|pfx|jks|keystore))$",
    re.IGNORECASE,
)

#: Directories whose contents are credentials by convention rather than by name.
_CREDENTIAL_DIRS = frozenset({".ssh", ".aws", ".gnupg", ".kube", ".docker"})


class ProfileDatasetInput(BaseModel):
    path: str = Field(description="Absolute path to dataset file")
    dataset_id: str | None = None
    filename: str | None = None


class ProfileDatasetOutput(BaseModel):
    dataset_id: str
    profile: dict[str, Any]


def _guard_path(path: Path) -> None:
    """Refuse the shapes this surface must not read, before any reader is chosen."""
    if path.is_symlink():
        raise ToolExecutionError("Refusing a symbolic link as a dataset path")
    if not path.is_file():
        raise ToolExecutionError(f"Not a regular file: {path.name}")
    if _CREDENTIAL_NAMES.match(path.name) or _CREDENTIAL_DIRS.intersection(path.parts):
        raise ToolExecutionError(f"Refusing a credential-shaped path: {path.name}")


def _fingerprint(path: Path) -> tuple[int, int, int]:
    """Size, modification time and inode: every one of them changes when a byte is written."""
    info = path.stat()
    return info.st_size, info.st_mtime_ns, info.st_ino


def _guard_unchanged(path: Path, before: tuple[int, int, int]) -> None:
    """Refuse the result when the input changed while it was being read.

    This decides the write capability for the one path a request names; it does not prevent a write
    and it observes nothing about a path the request never mentions.
    """
    if _fingerprint(path) != before:
        raise ToolExecutionError(f"Input changed while it was being profiled: {path.name}")


def _guard_request(path: Path, filename: str | None, raw: str) -> DatasetFormat:
    """Every refusal this surface makes before a reader runs, in the order a caller meets them.

    The format allowlist is part of the gate rather than a convenience after it: the reader is
    chosen from the allowlist, never from the file, so a format whose reader executes code cannot
    be reached through this surface at all.
    """
    if not path.exists():
        raise ToolExecutionError(f"File not found: {raw}")
    if ".." in raw or raw.count("//") > 0:
        raise ToolExecutionError("Path traversal detected")
    _guard_path(path)
    return detect_format(filename or path.name)


class ProfileDatasetTool(BaseTool[ProfileDatasetInput, ProfileDatasetOutput]):
    name = "profile_dataset"
    description = "Profile a dataset file (schema, missing, duplicates, cardinality, distribution)"
    input_model = ProfileDatasetInput
    output_model = ProfileDatasetOutput

    async def execute(self, inp: ProfileDatasetInput) -> ProfileDatasetOutput:
        p = Path(inp.path)
        fmt = _guard_request(p, inp.filename, inp.path)
        before = _fingerprint(p)
        # use dataset_id from input or filename-based
        ds_id = inp.dataset_id or p.stem
        # leverage profiler quick path
        from dsa_datasets.profiler import quick_profile_for_path

        _df, profile = quick_profile_for_path(p, fmt, ds_id)
        _guard_unchanged(p, before)
        return ProfileDatasetOutput(
            dataset_id=profile.dataset_id, profile=profile.model_dump(mode="json")
        )
