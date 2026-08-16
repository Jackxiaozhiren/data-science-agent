from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from dsa_api.core.config import settings
from dsa_api.core.database import engine

router = APIRouter()


def _probe_import(name: str) -> dict[str, Any]:
    try:
        __import__(name)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


@router.get("/health")
async def health() -> dict[str, Any]:
    db: dict[str, Any] = {"status": "unknown"}
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        db = {"status": "ok"}
    except Exception as e:
        db = {"status": "error", "error": str(e)[:300]}
    duck = _probe_import("duckdb")
    polars = _probe_import("polars")
    llm: dict[str, Any] = {}
    try:
        from dsa_llm.providers import EnvLLMProvider

        prov = EnvLLMProvider()
        llm = {"active": prov.active_provider, "status": "ok"}
    except Exception as e:
        llm = {"status": "error", "error": str(e)[:300]}
    details: dict[str, Any] = {"db": db, "duckdb": duck, "polars": polars, "llm": llm}
    overall = "ok" if all(v.get("status") == "ok" for v in details.values()) else "degraded"
    return {"status": overall, "details": details, "version": settings.version}


@router.get("/ready")
async def ready() -> dict[str, Any]:
    return await health()


@router.get("/version")
async def version() -> dict[str, Any]:
    return {"version": settings.version}
