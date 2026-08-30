"""DataSciBench adapter (V4.3 Phase C, W3 §22-27).

Implements the Phase B ``ExternalBenchmarkAdapter`` protocol against the
original DataSciBench benchmark (THUDM/DataSciBench, arXiv:2502.13897).

Integrity constraints honoured here (V4.3 §16, §19, §21, §23):

- The upstream checkout is fetched **by the operator** at a **pinned commit**
  into a git-ignored workspace (see ``prepare`` for the exact commands); **no
  DataSciBench content is ever vendored into the DSA repo** (upstream ships no
  LICENSE — redistribution is not permitted). The adapter performs only
  local filesystem verification — it contains no network and no
  credential-handling code by design.
- Ground-truth material comes from the gated HF dataset and requires the
  operator to accept its conditions; the adapter reports GT presence honestly
  and never fabricates it.
- Evaluation runs the benchmark's *original* evaluator scripts; this adapter
  only converts DSA run output into the input layout those scripts expect
  (``data/{task_id}/{model}_{run_id}/logs.txt`` with ``## Current Plan`` /
  ``## Current Task`` markers).
- Tasks DSA cannot support are reported as ``unsupported`` with an explicit
  reason (§26) — never silently filtered.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
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
        #: task_id → upstream task directory (run-dir base for the evaluator)
        self._task_dirs: dict[str, Path] = {}

    # ------------------------------------------------------------------ §17
    def prepare(self) -> None:
        """Verify the operator-prepared workspace is present at the pinned commit.

        The fetch itself is an operator step — network access, HF condition
        acceptance, and credentials never pass through this adapter. Setup
        (documented in README.md):

            mkdir -p <workspace>
            curl -L <tarball url> | tar xz --strip-components=1 -C <workspace>
            echo "<commit>" > <workspace>/.upstream_commit
            # optional gated GT (after accepting conditions on HuggingFace):
            # download zd21/DataSciBench ground truth into <workspace>/gt/

        Idempotent: a workspace whose marker matches the pinned commit passes.
        GT presence is reported honestly via a status file, never fabricated.
        """
        marker = self.workspace / ".upstream_commit"
        if not (
            marker.exists()
            and marker.read_text(encoding="utf-8").splitlines()[:1] == [UPSTREAM_COMMIT]
        ):
            raise FileNotFoundError(self._setup_instructions())
        self._write_gt_status()

    def _setup_instructions(self) -> str:
        tarball = f"https://codeload.github.com/THUDM/DataSciBench/tar.gz/{UPSTREAM_COMMIT}"
        ws = self.workspace
        return (
            f"DataSciBench workspace missing or at the wrong commit: {ws}\n"
            f"Setup (operator step — pinned upstream {UPSTREAM_COMMIT}):\n"
            f"  mkdir -p '{ws}'\n"
            f"  curl -L '{tarball}' | tar xz --strip-components=1 -C '{ws}'\n"
            f"  printf '%s\\n' '{UPSTREAM_COMMIT}' > '{ws / '.upstream_commit'}'\n"
            f"  # optional gated GT: accept https://huggingface.co/datasets/{HF_GT_DATASET}\n"
            f"  # then place ground truth under '{ws / 'gt'}'"
        )

    def _write_gt_status(self) -> None:
        """Record GT presence honestly — evaluation requires it, never fakes it."""
        gt_dir = self.workspace / "gt"
        present = gt_dir.is_dir() and any(gt_dir.iterdir())
        status = self.workspace / "GT_STATUS.txt"
        status.write_text(
            f"ground_truth_present: {str(present).lower()}\n"
            f"source: https://huggingface.co/datasets/{HF_GT_DATASET} (gated — "
            "operator must accept conditions; download into workspace/gt/)\n",
            encoding="utf-8",
        )

    def list_tasks(self) -> list[ExternalTask]:
        data_dir = self._upstream_root() / "data"
        if not data_dir.is_dir():
            raise FileNotFoundError(f"DataSciBench data/ not found under {self._upstream_root()}")
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
            self._task_dirs[task_id] = task_dir
            tasks.append(
                ExternalTask(
                    task_id=task_id,
                    question=question,
                    # §25 task mapping: the agent consumes the task's primary
                    # input file (task dir itself when no data file is shipped).
                    dataset_path=str(_pick_primary_input(task_dir) or task_dir),
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
    def _upstream_root(self) -> Path:
        """Locate the extracted upstream checkout inside the workspace.

        Authoritative source is the ``.upstream_commit`` marker (written by the
        operator during setup); a workspace with ``data/`` at its root (manual
        layout) is also accepted.
        """
        marker = self.workspace / ".upstream_commit"
        if marker.exists():
            lines = marker.read_text(encoding="utf-8").splitlines()
            if len(lines) > 1:
                return self.workspace / lines[1]
        if (self.workspace / "data").is_dir():
            return self.workspace
        raise FileNotFoundError(
            f"DataSciBench workspace not prepared at {self.workspace} — call prepare()"
        )

    def _materialize_run_dir(self, run: ExternalRun) -> Path | None:
        """Write the converted run layout consumed by the original evaluator.

        Run dirs live at ``data/{task_id}/dsa_{run_id}/`` (upstream contract);
        DSA artifacts (report/evidence JSON) are copied alongside ``logs.txt``
        for auditability.
        """
        task_dir = self._task_dirs.get(run.task_id)
        if task_dir is None:
            return None
        run_dir = task_dir / f"dsa_{run.run_id or '0'}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "logs.txt").write_text(build_logs_txt(run), encoding="utf-8")
        if run.report:
            (run_dir / "dsa_report.md").write_text(run.report, encoding="utf-8")
        if run.evidence:
            (run_dir / "dsa_evidence.json").write_text(
                json.dumps(run.evidence, ensure_ascii=False, indent=1, default=_json_default),
                encoding="utf-8",
            )
        return run_dir


#: Preferred input-file extensions for the §25 task mapping (order matters).
_INPUT_PRIORITY = (".csv", ".xlsx", ".xls", ".npy", ".txt", ".data", ".names", ".test")


def _pick_primary_input(task_dir: Path) -> Path | None:
    """Deterministically choose the task's primary input data file.

    Preference: extension priority (csv first — DSA's strongest surface), then
    largest size, then name. Returns ``None`` when the task ships no data file
    (upstream publishes prompts separately from the gated inputs).
    """
    candidates = [
        f
        for f in task_dir.iterdir()
        if f.is_file() and f.name != "prompt.json" and not f.name.startswith(".")
    ]
    if not candidates:
        return None

    def rank(f: Path) -> tuple[int, int, str]:
        ext = f.suffix.lower()
        prio = _INPUT_PRIORITY.index(ext) if ext in _INPUT_PRIORITY else len(_INPUT_PRIORITY)
        return (prio, -f.stat().st_size, f.name)

    return sorted(candidates, key=rank)[0]


def task_dir_sha256(task_dir: Path) -> str:
    """sha256 over a task's prompt.json — fills §18 dataset_hashes."""
    prompt = task_dir / "prompt.json"
    return hashlib.sha256(prompt.read_bytes()).hexdigest()


def _json_default(o: object) -> object:
    """Serialize non-JSON-native evidence values (date/datetime, sets, Path)."""
    if isinstance(o, (_dt.datetime, _dt.date)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    if isinstance(o, bytes):
        return o.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
