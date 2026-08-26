"""Reproducibility metadata for Notebook (§31)."""

from __future__ import annotations

import hashlib
import importlib.metadata
import uuid
from pathlib import Path
from typing import Any


def dataset_hash(path: str | Path) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    try:
        # hash first 1MB + size + mtime for speed, plus full if small
        stat = p.stat()
        h.update(str(stat.st_size).encode())
        h.update(str(int(stat.st_mtime)).encode())
        with p.open("rb") as f:
            # read first 1MB
            chunk = f.read(1024 * 1024)
            h.update(chunk)
            # if small file, hash full
            if stat.st_size < 5 * 1024 * 1024:
                f.seek(0)
                h.update(f.read())
        return h.hexdigest()[:16]
    except Exception:
        return None


def collect_notebook_metadata(
    dataset: str | Path | None = None,
    task: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Collect §31 metadata: dataset_hash, agent_version, sdk_version, prompt_version, tool_version, experiment_id."""
    try:
        try:
            sdk_version = importlib.metadata.version("jack-data-science-agent")
        except importlib.metadata.PackageNotFoundError:
            try:
                sdk_version = importlib.metadata.version("data-science-agent")
            except importlib.metadata.PackageNotFoundError:
                sdk_version = importlib.metadata.version("dsa-jupyter")
    except Exception:
        sdk_version = "4.2.2"
    try:
        agent_version = importlib.metadata.version("dsa-agent")
    except Exception:
        agent_version = "0.1.0"
    # prompt_version = hash of task
    prompt_version = hashlib.sha256(task.encode()).hexdigest()[:12] if task else None
    # tool_version — hash of tool registry? use dsa-tools version if available
    try:
        tool_version = importlib.metadata.version("dsa-tools")
    except Exception:
        tool_version = "0.1.0"
    return {
        "dataset_hash": dataset_hash(dataset) if dataset else None,
        "agent_version": agent_version,
        "sdk_version": sdk_version,
        "prompt_version": prompt_version,
        "tool_version": tool_version,
        "experiment_id": run_id or f"exp-{uuid.uuid4().hex[:8]}",
    }
