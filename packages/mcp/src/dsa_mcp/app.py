"""MCP Apps shell — Dataset→Question→Analysis→Evidence→Viz (§31 W4)."""

from fastapi import FastAPI

app = FastAPI(title="DSA MCP App", version="0.1.0")


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "DSA MCP App", "flow": "Dataset -> Question -> Analysis -> Evidence -> Viz"}


@app.get("/app")
async def app_info() -> dict[str, str]:
    return {"app": "mcp-data-science", "version": "0.1.0", "levels": "Tools/Resources/Apps/Tasks"}
