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

_UNSAFE_PATTERNS = re.compile(r"(\.\.|//|\\\\)")

_ARCHIVE_EXTS = {".zip", ".gz", ".tar", ".tgz", ".7z", ".rar"}


def validate_filename(filename: str) -> str:
    if not filename or len(filename) > 255:
        raise ValidationError("Invalid filename length")
    if _UNSAFE_PATTERNS.search(filename):
        raise ValidationError("Path traversal detected in filename")
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
    # archive bomb guard
    if Path(filename).suffix.lower() in _ARCHIVE_EXTS:
        raise ValidationError(f"Archive files not allowed: {filename!r}")
    fmt = detect_format(filename)
    validate_size(size_bytes)
    # MIME sniff — inlined logic to avoid execution/datasets cycle
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        ext = Path(filename).suffix.lower()
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
