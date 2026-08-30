from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.models.dataset import DatasetORM
from dsa_datasets.hash_utils import sha256_file
from dsa_datasets.models import DatasetFormat
from dsa_datasets.validate import validate_file


def _storage_dir() -> Path:
    # relative to project root (Data agent)
    return Path(__file__).resolve().parents[4] / "data" / "datasets"


async def ensure_tables(session: AsyncSession) -> None:
    from dsa_api.core.database import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_dataset(
    session: AsyncSession,
    filename: str,
    tmp_path: Path,
    size_bytes: int,
    content_type: str | None = None,
    head: bytes | None = None,
) -> dict[str, Any]:
    fmt = validate_file(filename, size_bytes, content_type=content_type, head=head)
    # hash from temp file
    sha = sha256_file(tmp_path)
    dataset_id = str(uuid.uuid4())
    storage = _storage_dir()
    storage.mkdir(parents=True, exist_ok=True)
    # persist file as {id}_{safe_filename}
    safe_name = f"{dataset_id}_{filename}"
    dest = storage / safe_name
    shutil.copyfile(tmp_path, dest)

    # Keep the scientific dataframe stack off the API import path so lightweight
    # health checks can start reliably on memory-constrained demo instances.
    from dsa_datasets.loader import load_dataframe
    from dsa_datasets.profiler import build_profile

    # load + profile (raises DatasetError -> caller maps to 400)
    df = load_dataframe(dest, fmt)
    profile = build_profile(
        df, dataset_id, filename, fmt if isinstance(fmt, DatasetFormat) else DatasetFormat(fmt)
    )

    orm = DatasetORM(
        id=dataset_id,
        filename=filename,
        format=profile.format.value,
        path=str(dest),
        sha256=sha,
        size_bytes=size_bytes,
        rows=profile.rows,
        cols=profile.columns,
        profile_json=profile.model_dump_json(),
        meta_json=json.dumps({}),
    )
    session.add(orm)
    await session.commit()
    await session.refresh(orm)
    d = orm.to_dict()
    # ensure profile is dict (already)
    return d


async def list_datasets(session: AsyncSession) -> list[dict[str, Any]]:
    await ensure_tables(session)
    result = await session.execute(select(DatasetORM).order_by(DatasetORM.created_at.desc()))
    rows = result.scalars().all()
    return [r.to_dict() for r in rows]


async def get_dataset(session: AsyncSession, dataset_id: str) -> dict[str, Any] | None:
    await ensure_tables(session)
    result = await session.execute(select(DatasetORM).where(DatasetORM.id == dataset_id))
    row = result.scalars().first()
    return row.to_dict() if row else None
