from fastapi import FastAPI

from dsa_api.routers.analysis import router as analysis_router
from dsa_api.routers.datasets import router as datasets_router
from dsa_api.routers.health import router as health_router

try:
    from dsa_mcp.server import app as mcp_app
except Exception:  # pragma: no cover - fallback if mcp not installed
    mcp_app = None  # type: ignore[assignment]

app = FastAPI(title="Data Science Agent API", version="0.1.0")

app.include_router(health_router)
app.include_router(datasets_router)
app.include_router(analysis_router)
if mcp_app is not None:
    app.mount("/mcp", mcp_app)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Data Science Agent API", "version": "0.1.0"}
