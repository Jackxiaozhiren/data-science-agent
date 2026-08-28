"""External benchmark adapter architecture (V4.3 W2, §15-21).

Phase B delivers the adapter *layer* only — no specific benchmark is integrated
here (DataSciBench is Phase C, DSAgentBench is Phase D). The layer enforces the
three invariants the spec makes non-negotiable:

1. **Gold leakage firewall (§19)** — the agent runtime receives an
   :class:`AgentTaskView` and nothing else. Gold answers, gold code, metrics and
   rubrics live on :class:`ExternalTask` *behind* the evaluation boundary and
   are structurally absent from the view the runner serialises into prompts.
2. **Original evaluator preserved (§16)** — ``evaluate`` consumes an
   :class:`ExternalRun` only. Gold is applied inside the adapter, on the far
   side of the boundary; the harness never mediates between agent output and
   gold material.
3. **Honest outcome taxonomy (§26)** — every task ends as passed, failed,
   unsupported or execution_error. Unsupported tasks are reported, never
   silently filtered.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AgentTaskView",
    "AgentBackedRunner",
    "ExternalBenchmarkAdapter",
    "ExternalBenchmarkManifest",
    "ExternalEvaluation",
    "ExternalRun",
    "ExternalTask",
    "RunConfig",
    "TaskOutcome",
    "classify_outcome",
    "assert_gold_isolation",
    "dataset_sha256",
]

#: §21 — benchmark integrity constraints. Enforced socially here (code review,
#: ADR) and structurally in Phase C via the adapter contract; violations of any
#: listed behaviour invalidate the benchmark run.
INTEGRITY_RULES: tuple[str, ...] = (
    "no prompt tuning on held-out test cases",
    "no hard-coded benchmark answers in agent runtime",
    "no inspection of evaluator output mid-task",
    "no retry-until-pass unless the benchmark protocol allows retries",
    "no silent exclusion of unsupported tasks",
    "no modification of evaluator thresholds",
)


class TaskOutcome(str, Enum):
    """§26 — mutually exclusive task outcomes (no silent unsupported filtering)."""

    PASSED = "passed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    EXECUTION_ERROR = "execution_error"


class RunConfig(BaseModel):
    """§41 — per-experiment isolation metadata captured with every run."""

    model: str = ""
    provider: str = ""
    seed: int | None = None
    temperature: float | None = None
    prompt_version: str = ""
    timeout_s: float = 600.0
    extra: dict[str, Any] = Field(default_factory=dict)


class AgentTaskView(BaseModel):
    """§19 — the *only* task projection the agent runtime may receive.

    Deliberately has no gold fields; construction goes through
    :meth:`ExternalTask.agent_view` so gold material cannot leak in by accident.
    ``extra="forbid"`` turns any attempt to smuggle extra fields (including gold
    keys) into a construction error instead of a silent drop.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str
    question: str
    dataset_path: str
    permitted_tools: tuple[str, ...] = ()
    benchmark_name: str = ""
    benchmark_task_ref: str = ""


class ExternalTask(BaseModel):
    """Full task definition — lives behind the evaluation boundary (§19)."""

    task_id: str
    question: str
    dataset_path: str
    benchmark_name: str = ""
    benchmark_task_ref: str = ""
    permitted_tools: tuple[str, ...] = ()
    #: gold answer / code / metric / rubric material. Never enters AgentTaskView.
    gold: dict[str, Any] = Field(default_factory=dict)
    supported: bool = True
    unsupported_reason: str | None = None

    def agent_view(self) -> AgentTaskView:
        """Project the task onto the agent-visible view, dropping all gold."""
        if not self.supported and self.unsupported_reason is None:
            raise ValueError(f"task {self.task_id!r}: unsupported tasks need a reason (§26)")
        return AgentTaskView(
            task_id=self.task_id,
            question=self.question,
            dataset_path=self.dataset_path,
            permitted_tools=self.permitted_tools,
            benchmark_name=self.benchmark_name,
            benchmark_task_ref=self.benchmark_task_ref,
        )


class ExternalRun(BaseModel):
    """What the agent produced for one task — no gold, no evaluator state."""

    task_id: str
    benchmark_name: str
    agent_view: AgentTaskView
    status: str = "pending"
    run_id: str | None = None
    report: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    latency_s: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    error: str | None = None


class ExternalEvaluation(BaseModel):
    """Evaluator verdict for one run, produced on the far side of the boundary."""

    task_id: str
    benchmark_name: str
    outcome: TaskOutcome
    score: float | None = None
    evaluator: str = ""
    evaluator_version: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class ExternalBenchmarkManifest(BaseModel):
    """§18 — provenance manifest every adapter must emit with its results."""

    benchmark_name: str
    benchmark_version: str
    benchmark_commit: str
    source: str
    license: str
    task_count: int
    dataset_hashes: dict[str, str] = Field(default_factory=dict)
    evaluator_version: str = ""
    environment: dict[str, str] = Field(default_factory=dict)
    dsa_commit: str = ""
    dsa_version: str = ""
    model: str = ""
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    tool_versions: dict[str, str] = Field(default_factory=dict)
    seed: int | None = None

    def write(self, path: Path) -> Path:
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return path


def dataset_sha256(path: str | Path) -> str:
    """sha256 of a benchmark dataset file — used to fill manifest dataset_hashes."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def assert_gold_isolation(view: AgentTaskView | str) -> None:
    """Raise if any gold material is detectable in the agent-visible payload (§19).

    Cheap runtime tripwire: serialise the view and assert none of the known gold
    keys survive. Adapters with exotic gold vocabularies should extend the key
    list via ``extra_forbidden`` rather than bypassing the check.
    """
    forbidden = (
        "gold",
        "ground_truth",
        "reference_answer",
        "solution",
        "rubric",
        "expected_result",
        "gold_metric",
    )
    payload = view if isinstance(view, str) else view.model_dump_json()
    lowered = payload.lower()
    for key in forbidden:
        if f'"{key}"' in lowered:
            raise ValueError(
                f"gold leakage firewall (§19): agent view carries forbidden key {key!r}"
            )


def classify_outcome(
    run: ExternalRun,
    evaluation: ExternalEvaluation | None = None,
) -> TaskOutcome:
    """Resolve the §26 outcome for a run; unsupported beats everything else."""
    if run.status == "skipped_unsupported":
        return TaskOutcome.UNSUPPORTED
    if evaluation is not None:
        return evaluation.outcome
    if run.error:
        return TaskOutcome.EXECUTION_ERROR
    # Completed-but-unevaluated is not a pass — §26 keeps the taxonomy honest.
    return TaskOutcome.FAILED


@runtime_checkable
class ExternalBenchmarkAdapter(Protocol):
    """§17 — the contract every external benchmark adapter implements.

    ``prepare`` must be idempotent and license-respecting (§23); ``evaluate``
    applies the benchmark's *original* evaluator (§16) using gold held inside
    the adapter, never passed through the harness.
    """

    name: str
    version: str

    def prepare(self) -> None: ...

    def list_tasks(self) -> list[ExternalTask]: ...

    def run_task(self, task: ExternalTask, config: RunConfig) -> ExternalRun: ...

    def evaluate(self, run: ExternalRun) -> ExternalEvaluation: ...

    def export_results(self) -> Path: ...


class AgentBackedRunner:
    """Reference runner: turns an :class:`AgentTaskView` into an :class:`ExternalRun`.

    This is the only sanctioned bridge between the external-benchmark layer and
    the DSA agent runtime — callers pass the *view*, never the full task, so the
    gold firewall (§19) holds by construction. The DSA import is lazy so the
    module stays importable in evaluator-only processes (§20 isolation seam).
    """

    def __init__(self, agent_factory: Any | None = None) -> None:
        self._agent_factory = agent_factory

    def _build_agent(self) -> Any:
        if self._agent_factory is not None:
            return self._agent_factory()
        from data_science_agent import Agent  # lazy: keeps eval processes agent-free

        return Agent()

    def run(self, task: ExternalTask, config: RunConfig) -> ExternalRun:
        if not task.supported:
            return ExternalRun(
                task_id=task.task_id,
                benchmark_name=task.benchmark_name,
                agent_view=task.agent_view(),
                status="skipped_unsupported",
                error=task.unsupported_reason,
            )
        view = task.agent_view()
        assert_gold_isolation(view)
        agent = self._build_agent()
        result = agent.analyze_sync(view.dataset_path, view.question)
        return ExternalRun(
            task_id=task.task_id,
            benchmark_name=task.benchmark_name,
            agent_view=view,
            status=str(getattr(result, "status", "unknown")),
            run_id=str(getattr(result, "run_id", "") or "") or None,
            evidence=list(getattr(result, "evidence", []) or []),
            report=getattr(result, "report", None),
            latency_s=float(getattr(result, "elapsed_s", 0.0) or 0.0),
        )
