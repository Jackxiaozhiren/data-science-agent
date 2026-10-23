from __future__ import annotations

import re
from pathlib import Path

from dsa_datasets.errors import FileTooLargeError, UnsupportedFormatError, ValidationError
from dsa_datasets.models import DatasetFormat

ALLOWED_EXTS: dict[str, DatasetFormat] = {
    ".csv": DatasetFormat.csv,
    ".parquet": DatasetFormat.parquet,
    ".json": DatasetFormat.json,
    ".jsonl": DatasetFormat.json,
    ".xlsx": DatasetFormat.excel,
    ".xls": DatasetFormat.excel,
}

MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB MVP limit per spec §44

_ARCHIVE_EXTS = {".zip", ".gz", ".tar", ".tgz", ".7z", ".rar"}

#: Leading bytes that identify a container format, checked against the file itself rather than its name.
_ARCHIVE_MAGICS: tuple[tuple[bytes, str], ...] = (
    (b"PK\x03\x04", "zip"),
    (b"\x1f\x8b", "gzip"),
    (b"7z\xbc\xaf\x27\x1c", "7z"),
    (b"Rar!\x1a\x07", "rar"),
)

#: `.xlsx` is a zip container by specification, so the zip signature is expected there and nowhere else.
_ZIP_IS_EXPECTED = {".xlsx"}


def validate_filename(filename: str) -> str:
    if not filename or len(filename) > 255:
        raise ValidationError("Invalid filename length")
    if ".." in filename:
        # The rule leads, because that is what the caller broke; the reason it exists is named after it, so a
        # file genuinely named `Q1..Q2.csv` is not accused of traversal while `../x.csv` still reads as one.
        raise ValidationError("Filename must not contain '..' (path traversal)")
    if "/" in filename or "\\" in filename:
        raise ValidationError("Filename must not contain path separators")
    # allow alnum, dot, dash, underscore, space, parens
    if not re.match(r"^[\w.\-() ]+$", filename):
        raise ValidationError(f"Unsafe filename characters: {filename!r}")
    return filename


def detect_format(filename: str) -> DatasetFormat:
    ext = Path(filename).suffix.lower()
    fmt = ALLOWED_EXTS.get(ext)
    if fmt is None:
        raise UnsupportedFormatError(
            f"Unsupported file extension: {ext!r}. Allowed: {sorted(ALLOWED_EXTS)}"
        )
    return fmt


def validate_size(size_bytes: int, limit: int = MAX_SIZE_BYTES) -> None:
    if size_bytes > limit:
        raise FileTooLargeError(f"File too large: {size_bytes} bytes > limit {limit} bytes")


def validate_file(
    filename: str, size_bytes: int, content_type: str | None = None, head: bytes | None = None
) -> DatasetFormat:
    validate_filename(filename)
    ext = Path(filename).suffix.lower()
    # Archive guard, part 1: a file named as an archive is never a dataset.
    if ext in _ARCHIVE_EXTS:
        raise ValidationError(f"Archive files not allowed: {filename!r}")
    fmt = detect_format(filename)
    validate_size(size_bytes)
    # Archive guard, part 2: the extension is the caller's claim, the leading bytes are the file's.
    # `head` is the first 4 KiB of what the upload route streamed to disk; a caller that cannot supply
    # it (a CLI path reading its own file) gets the name-only check.
    if head:
        for magic, label in _ARCHIVE_MAGICS:
            if label == "zip" and ext in _ZIP_IS_EXPECTED:
                continue
            if head.startswith(magic):
                raise ValidationError(f"Archive contents ({label}) in a file named {filename!r}")
        if head[257:262] == b"ustar":
            raise ValidationError(f"Archive contents (tar) in a file named {filename!r}")
    # MIME sniff — inlined logic to avoid execution/datasets cycle
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        # csv/json allow text/*; otherwise require exact allowlist
        allowed_by_ext = ALLOWED_EXTS.get(ext)
        # map extension to allowed mime set (duplicated from mime_sniff to avoid import cycle)
        ext_to_mime = {
            ".csv": {"text/csv", "text/plain", "application/csv", "application/vnd.ms-excel"},
            ".parquet": {"application/octet-stream", "application/parquet"},
            ".json": {"application/json", "text/plain"},
            ".jsonl": {"application/json", "text/plain"},
            ".xlsx": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
                "application/zip",
            },
            ".xls": {"application/vnd.ms-excel"},
        }
        allowed = ext_to_mime.get(ext)
        if allowed is not None:
            ok = False
            if ct in allowed or ext in (".csv", ".json", ".jsonl") and ct.startswith("text/"):
                ok = True
            if not ok:
                raise ValidationError(f"MIME type mismatch for {filename!r}: {content_type!r}")
    return fmt
