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


async def _database_status() -> dict[str, Any]:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


@router.get("/health")
async def health() -> dict[str, Any]:
    """Minimal process liveness check for hosting-platform probes.

    This route intentionally avoids database I/O and optional scientific/LLM
    imports so a small demo instance can prove that the web process is alive
    immediately. Use /ready for database readiness and /health/dependencies for
    the deeper optional-dependency diagnostic.
    """
    return {
        "status": "ok",
        "details": {"process": {"status": "ok"}},
        "version": settings.version,
    }


@router.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness check that verifies the configured database."""
    db = await _database_status()
    overall = "ok" if db.get("status") == "ok" else "degraded"
    return {
        "status": overall,
        "details": {"process": {"status": "ok"}, "db": db},
        "version": settings.version,
    }


@router.get("/health/dependencies")
async def dependency_health() -> dict[str, Any]:
    """Deep dependency diagnostic, intentionally separate from liveness."""
    duck = _probe_import("duckdb")
    polars = _probe_import("polars")
    llm: dict[str, Any]
    try:
        from dsa_llm.providers import EnvLLMProvider

        prov = EnvLLMProvider()
        llm = {"active": prov.active_provider, "status": "ok"}
    except Exception as e:
        llm = {"status": "error", "error": str(e)[:300]}
    details: dict[str, Any] = {"duckdb": duck, "polars": polars, "llm": llm}
    overall = "ok" if all(v.get("status") == "ok" for v in details.values()) else "degraded"
    return {"status": overall, "details": details, "version": settings.version}


_STARTED = __import__("time").monotonic()


@router.get("/version")
async def version() -> dict[str, str]:
    return {"version": settings.version}


@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    import os
    import time

    uptime = time.monotonic() - _STARTED
    rss_mb: float | None = None
    try:
        import resource

        rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 2)
        # macOS reports bytes, Linux reports KB — normalize
        if os.uname().sysname == "Darwin":
            rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 2)
    except Exception:
        pass
    # tool_calls_total best-effort from in-memory cache size if available
    tool_calls_total: int | None = None
    try:
        from dsa_agent.graph import _TOOL_CACHE

        tool_calls_total = len(_TOOL_CACHE)
    except Exception:
        pass
    return {
        "version": settings.version,
        "uptime_s": round(uptime, 1),
        "rss_mb": rss_mb,
        "tool_cache_size": tool_calls_total,
        "pid": os.getpid(),
    }
