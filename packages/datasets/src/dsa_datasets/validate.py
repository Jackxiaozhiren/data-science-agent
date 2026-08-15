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
        raise UnsupportedFormatError(f"Unsupported file extension: {ext!r}. Allowed: {sorted(ALLOWED_EXTS)}")
    return fmt


def validate_size(size_bytes: int, limit: int = MAX_SIZE_BYTES) -> None:
    if size_bytes > limit:
        raise FileTooLargeError(f"File too large: {size_bytes} bytes > limit {limit} bytes")


def validate_file(filename: str, size_bytes: int) -> DatasetFormat:
    validate_filename(filename)
    fmt = detect_format(filename)
    validate_size(size_bytes)
    return fmt
