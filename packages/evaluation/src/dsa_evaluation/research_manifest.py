from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ExperimentManifest(BaseModel):
    experiment_id: str
    git_commit: str | None = None
    benchmark_version: str | None = None
    dataset_version: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    seed: int = 42
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    configuration: dict[str, Any] = Field(default_factory=dict)


def _git_commit(root: Path | None = None) -> str | None:
    try:
        r = root or Path(__file__).parents[3]
        # Walk up to .git
        for p in [r] + list(r.parents):
            if (p / ".git").exists():
                r = p
                break
        gp = shutil.which("git")
        if not gp:
            return None
        out = subprocess.run(
            [gp, "rev-parse", "HEAD"], cwd=str(r), capture_output=True, text=True, timeout=3
        )  # noqa: S603
        if out.returncode == 0:
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return None


def build_manifest(
    experiment_id: str,
    benchmark_version: str | None = None,
    dataset_version: str | None = None,
    model: str | None = None,
    prompt_version: str | None = None,
    seed: int = 42,
    configuration: dict[str, Any] | None = None,
    root: Path | None = None,
) -> ExperimentManifest:
    # Auto-detect benchmark version from catalog if not supplied
    bv = benchmark_version
    if bv is None and root is not None:
        try:
            bv = json.loads((root / "benchmarks/v2/catalog.json").read_text(encoding="utf-8")).get(
                "version"
            )
        except Exception:
            pass
    return ExperimentManifest(
        experiment_id=experiment_id,
        git_commit=_git_commit(root),
        benchmark_version=bv,
        dataset_version=dataset_version,
        model=model,
        prompt_version=prompt_version,
        seed=seed,
        configuration=configuration
        or {"platform": platform.platform(), "python": sys.version.split()[0]},
    )
