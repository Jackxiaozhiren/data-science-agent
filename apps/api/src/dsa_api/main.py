from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dsa_api.core.config import settings
from dsa_api.core.database import init_db
from dsa_api.core.security import AuthMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware

# Import ORM models so their tables register on Base.metadata before create_all.
from dsa_api.models import analysis as _analysis_models  # noqa: F401
from dsa_api.models import dataset as _dataset_models  # noqa: F401
from dsa_api.models import experiment as _experiment_models  # noqa: F401
from dsa_api.routers.analysis import router as analysis_router
from dsa_api.routers.artifacts import router as artifacts_router
from dsa_api.routers.bundles import router as bundles_router
from dsa_api.routers.datasets import router as datasets_router
from dsa_api.routers.events import router as events_router
from dsa_api.routers.experiments import router as experiments_router
from dsa_api.routers.health import router as health_router
from dsa_api.routers.provider import router as provider_router

try:
    from dsa_mcp.server import app as mcp_app
except Exception:  # pragma: no cover - fallback if mcp not installed
    mcp_app = None  # type: ignore[assignment]

try:
    from dsa_mcp.app import app as mcp_app_v4  # MCP Apps (W4)
except Exception:  # pragma: no cover
    mcp_app_v4 = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Create ORM tables on startup so fresh databases (e.g. Render sqlite)
    accept writes immediately. Safe on existing databases (checkfirst)."""
    import logging

    from dsa_api.services.demo_seed import ensure_demo_data_at_boot
    from dsa_api.services.run_lifecycle import sweep_abandoned_runs

    await init_db()
    # A run executes in this process now, so a row left non-terminal by the previous one has no task that
    # will ever finish it. Closing it out here is what keeps "failed" and "frozen" distinguishable.
    abandoned = await sweep_abandoned_runs()
    if abandoned:
        logging.getLogger(__name__).info(
            "closed out %d abandoned analysis run(s) from a previous process", abandoned
        )
    # The free demo's storage is ephemeral, so the sample data cannot be uploaded once and kept: it is
    # rebuilt from committed files on every boot (web plan R-01, and the durability limit in §176).
    seeded = await ensure_demo_data_at_boot()
    if seeded:
        logging.getLogger(__name__).info(
            "demo data ready: %d dataset(s), example run %s",
            seeded["seeded_datasets"] + seeded["kept_datasets"],
            seeded["example_run_id"] or "none",
        )
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(health_router)
app.include_router(datasets_router)
app.include_router(events_router)
app.include_router(analysis_router)
app.include_router(bundles_router)
app.include_router(experiments_router)
app.include_router(provider_router)
app.include_router(artifacts_router)
if mcp_app is not None:
    app.mount("/mcp", mcp_app)
if mcp_app_v4 is not None:
    # R-14: a client opening a report should see the runs this product actually has. Until now the App could
    # only show what the same process had produced through its own tools, so a stored, COMPLETED run answered
    # 404 here while the web rendered it. The host owns how a run is read, so the reading is handed over rather
    # than duplicated -- and it is scoped to the published rows, because this surface carries no visitor
    # identity and must not become a way around R-08.
    from dsa_api.core import database
    from dsa_api.core.ownership import OWNER_SHARED
    from dsa_api.services.analysis_service import get_analysis_run
    from dsa_mcp.app import set_stored_run_loader

    async def _published_run(run_id: str) -> dict[str, Any] | None:
        # Attribute lookup at call time, not a name bound here: every suite that boots this app rebinds
        # ``database.AsyncSessionLocal`` to its own temp file after import, and a from-import would have
        # captured the developer's real database at import time and quietly read that instead.
        async with database.AsyncSessionLocal() as session:
            return await get_analysis_run(session, run_id, owner=OWNER_SHARED)

    set_stored_run_loader(_published_run)
    app.mount("/mcp-app", mcp_app_v4)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version}
