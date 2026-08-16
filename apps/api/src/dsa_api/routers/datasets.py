import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.services.dataset_service import get_dataset, list_datasets, save_dataset
from dsa_datasets.errors import (
    DatasetError,
    FileTooLargeError,
    UnsupportedFormatError,
    ValidationError,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.get("/")
async def list_datasets_route(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    items = await list_datasets(session)
    return {"datasets": items}


@router.get("/{dataset_id}")
async def get_dataset_route(dataset_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    ds = await get_dataset(session, dataset_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds


@router.post("/")
async def create_dataset_route(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
    # read to temp file to avoid holding all in memory twice
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        size = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            tmp.write(chunk)
    # Capture head for MIME sniff + archive bomb heuristic
    head: bytes | None = None
    try:
        head = tmp_path.read_bytes()[:4096] if tmp_path.exists() else None
    except Exception:
        head = None
    ct = file.content_type
    try:
        result = await save_dataset(session, file.filename, tmp_path, size, content_type=ct, head=head)
        return result
    except (ValidationError, UnsupportedFormatError, FileTooLargeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DatasetError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
