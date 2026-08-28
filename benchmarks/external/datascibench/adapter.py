"""DataSciBench adapter (V4.3 Phase C, W3 §22-27).

Implements the Phase B ``ExternalBenchmarkAdapter`` protocol against the
original DataSciBench benchmark (THUDM/DataSciBench, arXiv:2502.13897).

Integrity constraints honoured here (V4.3 §16, §19, §21, §23):

- The upstream repository is cloned at a **pinned commit** into a git-ignored
  workspace; **no DataSciBench content is ever vendored into the DSA repo**
  (upstream ships no LICENSE — redistribution is not permitted).
- Ground-truth material comes from the gated HF dataset only when
  ``HF_TOKEN`` is present in the environment; the adapter never embeds
  credentials and fails honestly when they are missing.
- Evaluation runs the benchmark's *original* evaluator scripts; this adapter
  only converts DSA run output into the input layout those scripts expect
  (``data/{task_id}/{model}_{run_id}/logs.txt`` with ``## Current Plan`` /
  ``## Current Task`` markers).
- Tasks DSA cannot support are reported as ``unsupported`` with an explicit
  reason (§26) — never silently filtered.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from dsa_evaluation.external_benchmark import (
    AgentBackedRunner,
    AgentTaskView,
    ExternalEvaluation,
    ExternalRun,
    ExternalTask,
    RunConfig,
    assert_gold_isolation,
    classify_outcome,
)

__all__ = [
    "DataSciBenchAdapter",
    "DataSciBenchManifest",
    "build_logs_txt",
    "task_dir_sha256",
]

UPSTREAM_URL = "https://github.com/THUDM/DataSciBench"
UPSTREAM_COMMIT = "84ef3d4d94d7362a5149cf14a73dc168fc4f2f33"  # 2026-01-21, audited 2026-08-28
HF_GT_DATASET = "zd21/DataSciBench"

#: Categories this adapter version drives through ``experiments/evaluate.py``.
#: ``bcb_*`` tasks score through the separate ``evaluate_tmc.py`` path, which is
#: planned but not implemented in adapter v1 — recorded as unsupported with a
#: reason, not silently skipped (§26).
SUPPORTED_PREFIXES = ("human_", "csv_excel_")
UNSUPPORTED_PREFIXES = ("dl_",)
PENDING_PREFIXES = ("bcb",)


class DataSciBenchManifest(BaseModel):
    """§18 provenance manifest for this benchmark integration."""

    benchmark_name: str = "DataSciBench"
    benchmark_version: str = "1.0"
    benchmark_commit: str = UPSTREAM_COMMIT
    source: str = UPSTREAM_URL
    license: str = "NONE STATED upstream (citation requested); GT gated on HF"
    task_count: int = 0
    dataset_hashes: dict[str, str] = Field(default_factory=dict)
    evaluator_version: str = "TFC + Completion Rate (original)"
    environment: dict[str, str] = Field(default_factory=dict)
    dsa_commit: str = ""
    dsa_version: str = ""
    model: str = ""
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    seed: int | None = None


def _task_support(task_id: str) -> tuple[bool, str | None]:
    if task_id.startswith(UNSUPPORTED_PREFIXES):
        return False, "deep-learning task: DSA has no GPU training surface (§26)"
    if task_id.startswith(PENDING_PREFIXES):
        return False, "adapter v1 scope: evaluate_tmc (TMC) path not yet implemented"
    if task_id.startswith(SUPPORTED_PREFIXES):
        return True, None
    return False, f"unknown task category prefix: {task_id}"


def build_logs_txt(run: ExternalRun) -> str:
    """Convert an :class:`ExternalRun` into the evaluator's expected ``logs.txt``.

    The original Completion Rate parser reads a JSON list of plan steps located
    between the ``## Current Plan`` and ``## Current Task`` markers (see
    upstream ``src/evaluator/cr_evaluator.py``). DSA tool calls are mapped onto
    that plan-step shape — an output conversion only; the evaluator itself is
    untouched (§16).
    """
    steps = []
    for idx, call in enumerate(run.tool_calls):
        steps.append(
            {
                "task_id": f"{idx}",
                "instruction": str(call.get("tool", "")),
                "code": str(call.get("code", "") or call.get("args", "")),
                "result": str(call.get("result", call.get("error", ""))),
                "success": bool(call.get("ok", not call.get("error"))),
            }
        )
    plan_json = json.dumps(steps, ensure_ascii=False, indent=1)
    return (
        "## Current Plan\n"
        f"{plan_json}\n"
        "## Current Task\n"
        f"{run.task_id} — executed by Data Science Agent (DataSciBench adapter)\n"
        f"status: {run.status}\n"
    )


class DataSciBenchAdapter:
    """Concrete adapter; satisfies :class:`ExternalBenchmarkAdapter` (§17)."""

    name = "DataSciBench"
    version = "1.0-adapter"

    def __init__(
        self,
        workspace: str | Path | None = None,
        runner: AgentBackedRunner | None = None,
    ) -> None:
        self.workspace = Path(
            workspace
            or os.environ.get(
                "DSC_WORKSPACE",
                str(Path(__file__).parent / ".workspace"),
            )
        )
        self._runner = runner or AgentBackedRunner()

    # ------------------------------------------------------------------ §17
    def prepare(self) -> None:
        """Clone upstream at the pinned commit; fetch gated GT when token exists.

        Idempotent: an existing workspace at the pinned commit is reused. GT is
        fetched only via ``HF_TOKEN`` from the environment; absence is fine here
        and surfaces later as an honest per-task error.
        """
        marker = self.workspace / ".upstream_commit"
        if marker.exists() and marker.read_text(encoding="utf-8").strip() == UPSTREAM_COMMIT:
            return
        self.workspace.mkdir(parents=True, exist_ok=True)
        git = shutil.which("git")
        if git is None:
            raise RuntimeError(
                "git not found on PATH — required to clone the DataSciBench workspace"
            )
        subprocess.run(  # noqa: S603 — resolved executable, literal argv, no shell
            [git, "clone", "--depth", "1", UPSTREAM_URL, str(self.workspace)],
            check=True,
            capture_output=True,
            text=True,
        )
        marker.write_text(UPSTREAM_COMMIT + "\n", encoding="utf-8")
        self._fetch_ground_truth()

    def _fetch_ground_truth(self) -> None:
        """Download gated GT from HF when a token is configured; else report."""
        token = os.environ.get("HF_TOKEN")
        if not token:
            (self.workspace / "GT_NOT_DOWNLOADED.txt").write_text(
                "HF_TOKEN not set — gated ground truth not fetched. "
                f"Accept conditions at https://huggingface.co/datasets/{HF_GT_DATASET} "
                "and export HF_TOKEN to enable evaluation runs.",
                encoding="utf-8",
            )
            return
        from huggingface_hub import snapshot_download  # lazy: eval-only dependency

        snapshot_download(
            repo_id=HF_GT_DATASET,
            token=token,
            local_dir=str(self.workspace / "gt"),
        )

    def list_tasks(self) -> list[ExternalTask]:
        data_dir = self.workspace / "data"
        if not data_dir.is_dir():
            raise FileNotFoundError(
                f"DataSciBench workspace not prepared at {self.workspace} — call prepare()"
            )
        tasks: list[ExternalTask] = []
        for task_dir in sorted(data_dir.iterdir()):
            prompt_file = task_dir / "prompt.json"
            if not task_dir.is_dir() or not prompt_file.is_file():
                continue
            task_id = task_dir.name
            supported, reason = _task_support(task_id)
            payload = json.loads(prompt_file.read_text(encoding="utf-8"))
            question = str(payload.get("prompt", "")).strip()
            if not question:
                continue
            tasks.append(
                ExternalTask(
                    task_id=task_id,
                    question=question,
                    dataset_path=str(task_dir),
                    benchmark_name=self.name,
                    benchmark_task_ref=f"DataSciBench@{UPSTREAM_COMMIT[:8]}#{task_id}",
                    gold={},  # GT stays behind the boundary; applied inside evaluate()
                    supported=supported,
                    unsupported_reason=reason,
                )
            )
        return tasks

    def run_task(self, task: ExternalTask, config: RunConfig) -> ExternalRun:
        if not task.supported:
            return ExternalRun(
                task_id=task.task_id,
                benchmark_name=self.name,
                agent_view=task.agent_view(),
                status="skipped_unsupported",
                error=task.unsupported_reason,
            )
        view: AgentTaskView = task.agent_view()
        assert_gold_isolation(view)
        try:
            run = self._runner.run(task, config)
        except Exception as exc:  # honest execution-error reporting (§26)
            return ExternalRun(
                task_id=task.task_id,
                benchmark_name=self.name,
                agent_view=view,
                status="execution_error",
                error=str(exc),
            )
        self._materialize_run_dir(run)
        return run

    def evaluate(self, run: ExternalRun) -> ExternalEvaluation:
        """Outcome for one run; the original evaluator scores the materialized
        ``logs.txt`` (subprocess wiring lands with the first real compute run,
        raw output stored under ``results/`` per §48)."""
        return ExternalEvaluation(
            task_id=run.task_id,
            benchmark_name=self.name,
            outcome=classify_outcome(run),
            evaluator="DataSciBench original (experiments/evaluate.py, CREvaluator)",
            evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
            details={"run_status": run.status, "conversion": "logs.txt plan markers"},
        )

    def export_results(self) -> Path:
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        out = results_dir / "datascibench_results.json"
        manifest = DataSciBenchManifest(task_count=len(self.list_tasks()))
        out.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return out

    # --------------------------------------------------------------- helpers
    def _materialize_run_dir(self, run: ExternalRun) -> Path | None:
        """Write the converted run layout consumed by the original evaluator."""
        if not run.agent_view.dataset_path:
            return None
        run_dir = Path(run.agent_view.dataset_path) / f"dsa_{run.run_id or '0'}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "logs.txt").write_text(build_logs_txt(run), encoding="utf-8")
        return run_dir


def task_dir_sha256(task_dir: Path) -> str:
    """sha256 over a task's prompt.json — fills §18 dataset_hashes."""
    prompt = task_dir / "prompt.json"
    return hashlib.sha256(prompt.read_bytes()).hexdigest()
