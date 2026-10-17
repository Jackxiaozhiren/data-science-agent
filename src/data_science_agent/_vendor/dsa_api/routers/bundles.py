"""One download that carries a run's whole reproducibility bundle.

The report endpoint gives a visitor prose, and the artifacts list gives them paths inside this container.
On a free instance those paths are the weak point: the host may clear the filesystem under a run that the
database still describes, so the list is accurate about what *was* produced and silent about what still
exists. A bundle turns that into one answer -- either the files are here, or the download says they are not
-- and it is the only thing a visitor can keep that survives the instance.

Two rules shape the implementation.

Containment: the artifact list is stored state, and state is data a future bug or a hand-edited row can
fill with anything. Every entry is resolved and required to sit under the configured artifact root before a
byte of it is read, so this route cannot be turned into a file reader for the host's filesystem. The root
path itself is published inside the manifest on purpose -- the audited report already carries evidence ids
and tool paths, so the layout is not the secret here, and `reproduce.sh` needs it to be useful.

Honesty about absence: a missing or unreadable entry is listed in `manifest.json` with its reason rather
than dropped quietly, and a run whose files are *all* gone answers 404 instead of shipping an empty zip.
An empty archive would read as success.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from dsa_api.core.database import get_session
from dsa_api.core.ownership import resolve_owner
from dsa_api.services.analysis_service import get_analysis_run

router = APIRouter(tags=["analysis"])

#: Run ids are generated (`run-<hex>`), and this route turns one into a filename. Anything else is a
#: not-found rather than a header-injection or path-shape question.
RUN_ID_SHAPE = re.compile(r"^run-[A-Za-z0-9_-]{1,64}$")

#: A bundle is assembled in memory. Past this, the honest answer is that the caller wants a stream.
MAX_BUNDLE_BYTES = 64 * 1024 * 1024


def _classify(
    artifact_root: Path, entries: list[Any]
) -> tuple[list[tuple[str, Path]], list[dict[str, str]]]:
    """Split the stored artifact list into (name, path) pairs safe to read, and the reasons for the rest."""
    include: list[tuple[str, Path]] = []
    excluded: list[dict[str, str]] = []
    for item in entries:
        raw = item.get("path") if isinstance(item, dict) else None
        kind = str(item.get("type") or "artifact") if isinstance(item, dict) else "artifact"
        if not isinstance(raw, str) or not raw.strip():
            excluded.append({"name": kind, "reason": "no path recorded"})
            continue
        candidate = Path(raw)
        name = candidate.name
        if not candidate.is_absolute():
            candidate = artifact_root / candidate
        resolved = candidate.resolve()
        if not resolved.is_relative_to(artifact_root):
            excluded.append({"name": name, "reason": "outside the artifact root"})
            continue
        if not resolved.is_file() or not os.access(resolved, os.R_OK):
            excluded.append({"name": name, "reason": "not present in this deployment"})
            continue
        include.append((name, resolved))
    return include, excluded


@router.get("/api/v1/analysis/{run_id}/bundle")
async def download_run_bundle(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    owner: str = Depends(resolve_owner),
) -> Response:
    """`report.md`, `experiment.json`, `reproduce.sh`, the notebook, the evidence graph and the charts.

    The artifact root is resolved through the same accessor the writer used, so a deployment that moved it
    with `DSA_ARTIFACT_ROOT` is bundled correctly and one that never set it is not silently re-derived.
    """
    from dsa_datasets.artifact_paths import artifact_root

    if not RUN_ID_SHAPE.match(run_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    row = await get_analysis_run(session, run_id, owner=owner)
    if row is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    state = row.get("state") or {}
    root = artifact_root().resolve()
    include, excluded = _classify(root, list(state.get("artifacts") or []))
    if not include:
        raise HTTPException(
            status_code=404,
            detail=(
                f"no artifact file of {run_id} is present in this deployment; "
                "the run's report text is still readable from /report"
            ),
        )

    manifest = {
        "run_id": run_id,
        "artifact_root": str(root),
        "included": sorted(name for name, _ in include),
        "excluded": sorted(excluded, key=lambda entry: (entry["name"], entry["reason"])),
        "storage": _storage_summary(),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in include:
            if buffer.tell() > MAX_BUNDLE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"bundle exceeds {MAX_BUNDLE_BYTES} bytes; fetch artifacts individually",
                )
            archive.write(path, arcname=f"{run_id}/{name}")
        archive.writestr(
            f"{run_id}/manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )

    payload = buffer.getvalue()
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{run_id}-bundle.zip"',
            "X-Bundle-Files": str(len(include)),
            "X-Bundle-Excluded": str(len(excluded)),
        },
    )


def _storage_summary() -> dict[str, Any]:
    """The same disclosure `/version` publishes, copied into the bundle the visitor keeps."""
    from dsa_api.core.storage_state import storage_report

    return storage_report()
