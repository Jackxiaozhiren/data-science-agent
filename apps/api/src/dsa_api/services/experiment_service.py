from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.models.experiment import ExperimentORM


async def _ensure(session: AsyncSession) -> None:
    from dsa_api.core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_experiment(
    session: AsyncSession,
    run_id: str,
    dataset_id: str,
    name: str,
    params: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    await _ensure(session)
    exp_id = f"exp-{uuid.uuid4().hex[:10]}"
    orm = ExperimentORM(
        id=exp_id,
        run_id=run_id,
        dataset_id=dataset_id,
        name=name,
        params_json=json.dumps(params or {}),
        metrics_json=json.dumps(metrics or {}),
        artifact_path=artifact_path,
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)
    return orm.to_dict()


async def list_experiments(
    session: AsyncSession, run_id: str | None = None
) -> list[dict[str, Any]]:
    await _ensure(session)
    q = select(ExperimentORM).order_by(ExperimentORM.created_at.desc())
    if run_id:
        q = q.where(ExperimentORM.run_id == run_id)
    rows = (await session.execute(q)).scalars().all()
    return [r.to_dict() for r in rows]


async def get_experiment(session: AsyncSession, exp_id: str) -> dict[str, Any] | None:
    await _ensure(session)
    row = (
        (await session.execute(select(ExperimentORM).where(ExperimentORM.id == exp_id)))
        .scalars()
        .first()
    )
    return row.to_dict() if row else None


def compare_experiments(items: list[dict[str, Any]]) -> dict[str, Any]:
    # naive: rank by first numeric metric
    if not items:
        return {"ranking": []}
    # pick metric with most presence
    from collections import Counter

    keys: Counter[str] = Counter()
    for it in items:
        for k in it.get("metrics") or {}:
            keys[k] += 1
    if not keys:
        return {"ranking": [x["id"] for x in items]}
    top_metric = keys.most_common(1)[0][0]
    ranked = sorted(
        items, key=lambda x: float(x.get("metrics", {}).get(top_metric, 0) or 0), reverse=True
    )
    return {
        "metric": top_metric,
        "ranking": [x["id"] for x in ranked],
        "values": {x["id"]: x.get("metrics", {}).get(top_metric) for x in ranked},
    }
