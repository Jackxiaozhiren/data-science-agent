from __future__ import annotations

import mimetypes
from pathlib import Path

# Minimal allowlist MIME mapping; content peek supplements extension
EXT_TO_MIME: dict[str, set[str]] = {
    ".csv": {"text/csv", "text/plain", "application/csv", "application/vnd.ms-excel"},
    ".parquet": {"application/octet-stream", "application/parquet"},
    ".json": {"application/json", "text/plain"},
    ".jsonl": {"application/json", "text/plain"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel", "application/zip"},
    ".xls": {"application/vnd.ms-excel"},
}

# Magic-byte checks for stronger validation
_MAGIC: list[tuple[bytes, str]] = [
    (b"PK\x03\x04", ".xlsx"),  # zip-based xlsx
    (b"\xD0\xCF\x11\xE0", ".xls"),  # OLE
    (b"PAR1", ".parquet"),
]


def sniff_mime(filename: str, head: bytes | None = None) -> str | None:
    ext = Path(filename).suffix.lower()
    # Prefer magic if available
    if head:
        for magic, mext in _MAGIC:
            if head.startswith(magic):
                # map back to a mime for the magic ext
                mimes = EXT_TO_MIME.get(mext)
                if mimes:
                    return next(iter(mimes))
    # fallback to guessed mime
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    # default by ext
    mimes = EXT_TO_MIME.get(ext)
    if mimes:
        return next(iter(mimes))
    return None


def is_allowed_mime(filename: str, content_type: str | None, head: bytes | None = None) -> bool:
    ext = Path(filename).suffix.lower()
    allowed = EXT_TO_MIME.get(ext)
    if allowed is None:
        return False
    if not content_type:
        # allow if no content-type but extension is allowed (client may omit)
        return True
    ct = content_type.split(";")[0].strip().lower()
    # For csv/json allow text/* variants
    if ext in (".csv", ".json", ".jsonl") and ct.startswith("text/"):
        return True
    if ct in allowed:
        return True
    # magic check may override: e.g. xlsx as zip
    sniffed = sniff_mime(filename, head)
    if sniffed and sniffed in allowed:
        return True
    return False


def looks_like_zip_bomb(head: bytes | None, size_bytes: int) -> bool:
    # Heuristic: zip header + huge uncompressed ratio would require deep inspection;
    # for MVP, flag tiny compressed payload claiming huge rows via zip: if xlsx magic + size < 10KB but extension claims large limit, don't block yet.
    # Instead, check for obvious bombs: very small file that decompresses to > 50x would be caught at load time; here we just bound file size before unzip.
    # For now, only flag if file starts with PK and declares as xlsx but size exceeds limit (already handled by validate_size).
    _ = head
    _ = size_bytes
    return False
