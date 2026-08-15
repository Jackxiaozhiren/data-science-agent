from fastapi import FastAPI

from dsa_api.routers.datasets import router as datasets_router
from dsa_api.routers.health import router as health_router

app = FastAPI(title="Data Science Agent API", version="0.1.0")

app.include_router(health_router)
app.include_router(datasets_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Data Science Agent API", "version": "0.1.0"}
