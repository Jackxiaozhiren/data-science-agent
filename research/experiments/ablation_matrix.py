from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def ablation_configs() -> dict[str, dict[str, Any]]:
    """Ablation A–F (V2 §57) — each config maps to how the runner should drop components.

    In this codebase ablation is simulated by planner/tool filtering rather than model retraining.
    """
    return {
        "A": {"label": "LLM only", "tools": [], "planner": False, "critic": False, "evidence": False},
        "B": {"label": "LLM + Tools", "tools": ["run_sql", "run_python"], "planner": False, "critic": False, "evidence": False},
        "C": {"label": "LLM + Tools + Planner", "tools": ["run_sql", "correlation_analysis", "hypothesis_test"], "planner": True, "critic": False, "evidence": False},
        "D": {"label": "LLM + Tools + Planner + Critic", "tools": ["run_sql", "correlation_analysis", "hypothesis_test"], "planner": True, "critic": True, "evidence": False},
        "E": {"label": "LLM + Tools + Planner + Critic + Evidence", "tools": ["run_sql", "correlation_analysis", "hypothesis_test"], "planner": True, "critic": True, "evidence": True},
        "F": {"label": "Full System", "tools": ["run_sql", "run_python", "correlation_analysis", "hypothesis_test", "regression_analysis", "create_chart"], "planner": True, "critic": True, "evidence": True},
    }


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def run_ablation_stub(out_dir: Path, catalog: Path, datasets_dir: Path) -> Path:
    """Minimal ablation runner: writes research/results/ablation_<commit>.json stub (no fake metrics)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"experiment_id": f"ablation-{git_commit()[:8]}", "git_commit": git_commit(), "configs": ablation_configs(), "note": "Run with --catalog to populate metrics; this is a stub to define the matrix shape."}
    p = out_dir / f"ablation_{payload['experiment_id']}.json"
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p
