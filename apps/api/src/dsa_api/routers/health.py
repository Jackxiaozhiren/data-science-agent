from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/version")
async def version() -> dict[str, Any]:
    return {"version": "0.1.0"}
