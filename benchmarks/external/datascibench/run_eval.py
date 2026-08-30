"""One-shot real evaluation runner for DataSciBench Phase C (§48 raw output).

Runs the 45 supported tasks (human_*/csv_excel_*) through the DSA agent
(deterministic local pipeline, no LLM key — same surface as the V4.2 case
studies), materializes evaluator-layout run dirs, and writes raw results JSON.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

from dsa_evaluation.external_benchmark import RunConfig

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # repo root (datascibench → external → benchmarks → root)
spec = importlib.util.spec_from_file_location(
    "datascibench_adapter",
    HERE / "adapter.py",
)
assert spec and spec.loader
dsc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsc)

adapter = dsc.DataSciBenchAdapter()
_json_default = dsc._json_default
adapter.prepare()
tasks = adapter.list_tasks()
supported = [t for t in tasks if t.supported]
print(f"tasks: {len(tasks)} | supported: {len(supported)}", flush=True)

config = RunConfig(model="deterministic-local", prompt_version="adapter-1.0", seed=42)
records = []
t0 = time.time()
for i, task in enumerate(supported, 1):
    ts = time.time()
    run = adapter.run_task(task, config)
    ev = adapter.evaluate(run)
    records.append(
        {
            "task_id": task.task_id,
            "dataset_path": run.agent_view.dataset_path,
            "status": run.status,
            "outcome": ev.outcome.value,
            "run_id": run.run_id,
            "latency_s": run.latency_s,
            "n_evidence": len(run.evidence),
            "n_tool_calls": len(run.tool_calls),
            "report_chars": len(run.report or ""),
            "error": (run.error or "")[:300] or None,
        }
    )
    print(
        f"[{i:02d}/{len(supported)}] {task.task_id}: {run.status} -> {ev.outcome.value} ({time.time() - ts:.1f}s)",
        flush=True,
    )

summary = {
    "benchmark": "DataSciBench",
    "upstream_commit": dsc.UPSTREAM_COMMIT,
    "runner": "dsa AgentBackedRunner (deterministic local pipeline, no LLM key)",
    "config": config.model_dump(),
    "wall_s": round(time.time() - t0, 1),
    "total_supported": len(supported),
    "by_status": {},
    "by_outcome": {},
    "runs": records,
}
for r in records:
    summary["by_status"][r["status"]] = summary["by_status"].get(r["status"], 0) + 1
    summary["by_outcome"][r["outcome"]] = summary["by_outcome"].get(r["outcome"], 0) + 1

out = REPO / "benchmarks" / "external" / "datascibench" / "results" / "raw_runs.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=_json_default), encoding="utf-8")
print("WALL", round(time.time() - t0, 1), "s ->", out, flush=True)
print(json.dumps({k: v for k, v in summary.items() if k != "runs"}, indent=1, default=_json_default), flush=True)
