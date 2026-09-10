from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dsa_api.core.config import settings
from dsa_api.core.database import Base, engine

# Import ORM models so their tables register on Base.metadata before create_all.
from dsa_api.models import analysis as _analysis_models  # noqa: F401
from dsa_api.models import dataset as _dataset_models  # noqa: F401
from dsa_api.models import experiment as _experiment_models  # noqa: F401
from dsa_api.routers.analysis import router as analysis_router
from dsa_api.routers.datasets import router as datasets_router
from dsa_api.routers.experiments import router as experiments_router
from dsa_api.routers.health import router as health_router

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
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(datasets_router)
app.include_router(analysis_router)
app.include_router(experiments_router)
if mcp_app is not None:
    app.mount("/mcp", mcp_app)
if mcp_app_v4 is not None:
    app.mount("/mcp-app", mcp_app_v4)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version}
