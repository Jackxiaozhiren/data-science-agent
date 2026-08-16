from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_experiment_json(
    run_id: str,
    dataset_path: str | None,
    dataset_sha256: str | None,
    user_query: str,
    plan: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    insights: list[dict[str, Any]],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    # package versions best-effort
    pkg_versions: dict[str, str] = {}
    for pkg in ["fastapi", "pydantic", "sqlalchemy", "duckdb", "polars", "pyarrow", "numpy", "scipy", "scikit-learn", "matplotlib", "langgraph"]:
        try:
            import importlib.metadata

            pkg_versions[pkg] = importlib.metadata.version(pkg)
        except Exception:
            pass

    payload = {
        "run_id": run_id,
        "dataset_path": dataset_path,
        "dataset_sha256": dataset_sha256,
        "user_query": user_query,
        "plan": plan,
        "tool_calls": tool_calls,
        "evidence": evidence,
        "insights": insights,
        "environment": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "packages": pkg_versions,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = out_dir / "experiment.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def build_reproduce_sh(
    run_id: str,
    dataset_path: str | None,
    user_query: str,
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Minimal reproduce script that re-runs the analysis via python -m
    # Assumes Data agent at same path
    script = f"""#!/bin/bash
set -e
# Reproduce analysis {run_id}
# Dataset: {dataset_path}
# Query: {user_query!r}
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Reproducing with dataset: {dataset_path}"
# Example: re-run via API
# curl -X POST http://localhost:8000/api/v1/analysis/ -H 'Content-Type: application/json' -d '{{"dataset_id": "<dataset_id>", "user_query": {json.dumps(user_query)}}}'
# Or via direct graph:
python3 -c "
from dsa_agent.graph import run_analysis
import asyncio
state = asyncio.run(run_analysis(dataset_path={dataset_path!r}, dataset_id='repro', user_query={user_query!r}, run_id={run_id!r}))
print(state.model_dump_json(indent=2))
"
"""
    path = out_dir / "reproduce.sh"
    path.write_text(script, encoding="utf-8")
    try:
        path.chmod(0o755)
    except Exception:
        pass
    return path


def build_notebook_skeleton(run_id: str, out_dir: Path) -> Path:
    """Minimal analysis.ipynb skeleton; full notebook generation is Phase 11."""
    out_dir.mkdir(parents=True, exist_ok=True)
    nb = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": [f"# Analysis {run_id}\n", "Auto-generated skeleton — full notebook in Phase 11.\n"]},
            {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Reproduce\n", "from dsa_agent.graph import run_analysis\n", "import asyncio\n"]},
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = out_dir / "analysis.ipynb"
    path.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    return path
