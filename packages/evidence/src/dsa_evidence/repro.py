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


def build_notebook(
    run_id: str,
    dataset_path: str | None,
    user_query: str,
    plan: list[dict[str, Any]] | None,
    tool_calls: list[dict[str, Any]] | None,
    out_dir: Path,
) -> Path:
    """Executable notebook: dataset load + per-tool cells derived from plan/tool_calls."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cells: list[dict[str, Any]] = []
    cells.append({"cell_type": "markdown", "metadata": {}, "source": [f"# Analysis {run_id}\n", f"**Query:** {user_query}\n", f"**Dataset:** `{dataset_path}`\n"]})
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Setup — requires repo root on PYTHONPATH\n", "import json, sys\n", "from pathlib import Path\n", f"DATASET = {dataset_path!r}\n", f"QUERY = {user_query!r}\n"]})
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Profile\n", "from dsa_datasets.loader import load_dataframe\n", "from dsa_datasets.validate import detect_format\n", "from dsa_datasets.profiler import profile\n", "if DATASET:\n", "    p = Path(DATASET)\n", "    fmt = detect_format(p.name)\n", "    df = load_dataframe(p, fmt)\n", "    print(df.head())\n", "    print(profile(df))\n"]})
    plan_tools = [p.get("tool", "") for p in (plan or [])]
    tc_by_tool: dict[str, Any] = {}
    for tc in (tool_calls or []):
        tc_by_tool.setdefault(tc.get("tool", ""), tc)
    for tool in plan_tools:
        tc_any: Any = tc_by_tool.get(tool)
        inp: dict[str, Any] = (tc_any or {}).get("input") or {}
        if tool == "run_sql":
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [f"# SQL — {inp.get('sql','SELECT 1')[:80]}\n", "from dsa_tools import get as get_tool\n", "import asyncio\n", f"sql = {inp.get('sql','SELECT COUNT(*) as n FROM dataset')!r}\n", "inp = {'dataset_path': DATASET, 'sql': sql}\n", "tool = get_tool('run_sql')\n", "res = asyncio.run(tool.run(inp))\n", "print(res.output)\n"]})
        elif tool == "correlation_analysis":
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [f"# Correlation {inp}\n", "from dsa_tools import get as g; import asyncio\n", f"inp = {inp!r}\n", "if 'dataset_path' not in inp: inp['dataset_path']=DATASET\n", "res = asyncio.run(g('correlation_analysis').run(inp))\n", "print(res.output)\n"]})
        elif tool in ("hypothesis_test", "regression_analysis", "train_model", "evaluate_model", "forecast", "assumption_check", "causal_check", "feature_importance"):
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [f"# {tool}\n", "from dsa_tools import get as g; import asyncio\n", f"inp = {inp!r}\n", "if 'dataset_path' not in inp and DATASET: inp['dataset_path']=DATASET\n", f"res = asyncio.run(g({tool!r}).run(inp))\n", "print(res.output)\n"]})
        elif tool == "create_chart":
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [f"# Chart {inp}\n", "from dsa_tools import get as g; import asyncio, base64\n", f"inp = {inp!r}\n", "if 'dataset_path' not in inp: inp['dataset_path']=DATASET\n", "res = asyncio.run(g('create_chart').run(inp))\n", "print(res.output.artifact_path if hasattr(res.output,'artifact_path') else res.output)\n"]})
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Full run\n", "from dsa_agent.graph import run_analysis\n", "import asyncio\n", "state = asyncio.run(run_analysis(dataset_path=DATASET, dataset_id='repro', user_query=QUERY))\n", "print(state.model_dump_json(indent=2)[:4000])\n"]})
    nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}
    path = out_dir / "analysis.ipynb"
    path.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    return path


def build_notebook_skeleton(run_id: str, out_dir: Path) -> Path:
    return build_notebook(run_id, None, "", None, None, out_dir)
