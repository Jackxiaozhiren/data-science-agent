import contextlib
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.core.ownership import resolve_owner
from dsa_api.services.dataset_service import get_dataset, list_datasets, save_dataset
from dsa_datasets.errors import (
    DatasetError,
    FileTooLargeError,
    UnsupportedFormatError,
    ValidationError,
)
from dsa_datasets.validate import MAX_SIZE_BYTES

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])

#: How many leading bytes the magic-byte guard gets to look at.
HEAD_BYTES = 4096


async def _write_upload_to_temp(
    file: UploadFile, limit: int = MAX_SIZE_BYTES
) -> tuple[Path, int, bytes]:
    """Stream a request body to a temp file, returning its path, size, and first `HEAD_BYTES` bytes.

    The head comes off the same chunks that reach the disk, so the body is never read twice -- the
    previous version re-opened the finished file and did `read_bytes()[:4096]`, which put a whole
    100 MB upload into memory to keep 4 KB of it. The size limit is applied *while* streaming, so an
    oversized body costs one chunk instead of a full write, and the temp file is removed on the way
    out either way. The caller owns the returned path.
    """
    head = bytearray()
    size = 0
    kept = False
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename or "").suffix) as tmp:
        path = Path(tmp.name)
        try:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                tmp.write(chunk)
                if len(head) < HEAD_BYTES:
                    head.extend(chunk[: HEAD_BYTES - len(head)])
                if size > limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large: {size} bytes > limit {limit} bytes",
                    )
            kept = True
        finally:
            if not kept:
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)
    return path, size, bytes(head)


@router.get("/")
async def list_datasets_route(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(resolve_owner),
) -> dict[str, Any]:
    items, total = await list_datasets(session, limit=limit, offset=offset, owner=owner)
    return {"datasets": items, "total": total}


@router.get("/{dataset_id}")
async def get_dataset_route(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(resolve_owner),
) -> dict[str, Any]:
    ds = await get_dataset(session, dataset_id, owner=owner)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.post("/", status_code=201)
async def create_dataset_route(
    response: Response,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(resolve_owner),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    tmp_path, size, head = await _write_upload_to_temp(file)
    ct = file.content_type
    try:
        result = await save_dataset(
            session, file.filename, tmp_path, size, content_type=ct, head=head, owner=owner
        )
        response.headers["Location"] = f"/api/v1/datasets/{result['id']}"
        return result
    except (ValidationError, UnsupportedFormatError, FileTooLargeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DatasetError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        with contextlib.suppress(OSError):
            tmp_path.unlink(missing_ok=True)
