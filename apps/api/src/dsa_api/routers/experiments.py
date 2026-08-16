from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.services.experiment_service import compare_experiments, create_experiment, get_experiment, list_experiments

router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


class CreateExpBody(BaseModel):
    run_id: str
    dataset_id: str
    name: str
    params: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    artifact_path: str | None = None


@router.post("/")
async def create_exp(body: CreateExpBody, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    if not body.run_id or not body.dataset_id or not body.name.strip():
        raise HTTPException(status_code=400, detail="run_id, dataset_id and name required")
    return await create_experiment(session, body.run_id, body.dataset_id, body.name, body.params, body.metrics, body.artifact_path)


@router.get("/")
async def list_exp(run_id: str | None = None, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    items = await list_experiments(session, run_id=run_id)
    return {"experiments": items}


@router.get("/{exp_id}")
async def get_exp(exp_id: str, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    row = await get_experiment(session, exp_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return row


@router.post("/compare")
async def compare_exp(body: dict[str, Any], session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    ids: list[str] = body.get("ids") or []
    if not ids:
        raise HTTPException(status_code=400, detail="ids required")
    items = []
    for eid in ids:
        row = await get_experiment(session, eid)
        if row:
            items.append(row)
    if not items:
        raise HTTPException(status_code=404, detail="No experiments found")
    return compare_experiments(items)
