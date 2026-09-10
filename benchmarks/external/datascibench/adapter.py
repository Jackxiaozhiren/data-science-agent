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
    TaskOutcome,
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

#: Adapter conversion-layer version. v1 materialized trajectory → logs.txt
#: only; v2 additionally maps genuine agent artifacts onto the exact output
#: filenames the metric functions read (see _materialize_expected_files).
ADAPTER_VERSION = "2.0"

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
        """Outcome for one run — execution lane vs GT lane (§89).

        * **GT absent** (default, honest): ``classify_outcome`` only — no score,
          outcome is ``failed`` honest (§26, §89).
        * **GT present** (operator accepted ``zd21/DataSciBench`` and placed
          ``workspace/gt/``): the materialized ``logs.txt`` is scored by the
          upstream original evaluator (``experiments/evaluate.py`` or
          ``evaluate_tmc.py``) in a subprocess — this harness never invents a
          score (§16, §19). The subprocess is the §20 isolation seam.
        Raw output would be stored under ``results/`` per §48 when GT is wired.
        """
        gt_present = (
            (self.workspace / "GT_STATUS.txt")
            .read_text(encoding="utf-8")
            .startswith("ground_truth_present: true")
            if (self.workspace / "GT_STATUS.txt").exists()
            else False
        )
        # Also accept gt/ dir with any content as GT present (operator did direct download)
        if (
            not gt_present
            and (self.workspace / "gt").is_dir()
            and any((self.workspace / "gt").iterdir())
        ):
            gt_present = True

        if not gt_present:
            return ExternalEvaluation(
                task_id=run.task_id,
                benchmark_name=self.name,
                outcome=classify_outcome(run),
                evaluator="DataSciBench original (experiments/evaluate.py, CREvaluator) — GT absent",
                evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                details={
                    "run_status": run.status,
                    "conversion": "logs.txt plan markers",
                    "gt_present": False,
                    "honest_lane": "execution-only (§89)",
                },
            )

        # GT lane — run the upstream evaluator as a subprocess (§20 isolation)
        # The evaluator expects data/{task_id}/{model}_{run_id}/logs.txt layout
        # which _materialize_run_dir already created. We invoke the checkout's
        # experiments/evaluate.py and parse its stdout/stderr for a score.
        import subprocess
        import sys

        upstream = self._upstream_root()
        eval_script = upstream / "experiments" / "evaluate.py"
        # bcb* tasks use the TMC evaluator
        if run.task_id.startswith("bcb"):
            eval_script = upstream / "experiments" / "evaluate_tmc.py"
        details: dict[str, object] = {
            "run_status": run.status,
            "conversion": "logs.txt plan markers",
            "gt_present": True,
            "evaluator_script": str(eval_script),
        }
        if not eval_script.is_file():
            return ExternalEvaluation(
                task_id=run.task_id,
                benchmark_name=self.name,
                outcome=TaskOutcome.EXECUTION_ERROR,
                evaluator=str(eval_script),
                evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                details={**details, "error": f"evaluator not found: {eval_script}"},
            )
        try:
            # Upstream evaluators expect PYTHONPATH to include the checkout root (for `from src.utils import …`)
            # and are scoped by --task_id / --model_id (see experiments/evaluate.py parse_arguments).
            import os as _os

            env = _os.environ.copy()
            env["PYTHONPATH"] = str(upstream) + _os.pathsep + env.get("PYTHONPATH", "")
            # Prefer workspace venv python (has metagpt) when available, else fall back to DSA venv
            ws_python = self.workspace / "venv" / "bin" / "python"
            py = str(ws_python) if ws_python.is_file() else sys.executable
            proc = subprocess.run(  # noqa: S603 - fixed argv (python + pinned script + task/model ids); task_id comes from the pinned benchmark catalog, never raw user input
                [
                    py,
                    str(eval_script),
                    "--task_id",
                    run.task_id,
                    "--model_id",
                    f"dsa_{run.run_id or '0'}",
                ],
                cwd=str(upstream),
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            details["returncode"] = proc.returncode
            details["stdout_tail"] = (proc.stdout or "")[-2000:]
            details["stderr_tail"] = (proc.stderr or "")[-2000:]
            # Upstream CREvaluator writes evaluation_results/{model}_results.csv (see experiments/evaluate.py get_result_output_dir)
            # We parse result_cr for this task/model after the run.
            model_name = f"dsa_{run.run_id or '0'}".split("/")[-1]
            csv_path = upstream / "evaluation_results" / f"{model_name}_results.csv"
            if csv_path.is_file():
                try:
                    import csv as _csv

                    with csv_path.open(newline="", encoding="utf-8") as fh:
                        reader = _csv.DictReader(fh)
                        # NOTE (2026-09-05 GT-lane fix): upstream CSV columns are
                        # model_name, run_id, data_name, task_name, ... where
                        # data_name carries the task_id (e.g. human_5) and
                        # task_name carries the human-readable metric group
                        # (e.g. "Predictive modeling"). Matching on task_name
                        # never hit, so every GT run scored None. Match on
                        # data_name + model_name; the task-level score is the
                        # "Completion Rate" row's result_cr.
                        rows = [
                            row
                            for row in reader
                            if row.get("data_name") == run.task_id
                            and row.get("model_name") == model_name
                        ]
                        cr_rows = [
                            row
                            for row in rows
                            if (row.get("result_type") or "").strip() == "Completion Rate"
                        ]
                        picked = (cr_rows or rows or [None])[0]
                        if picked is not None:
                            try:
                                score = float(
                                    picked.get("result_cr") or picked.get("result_value") or 0
                                )
                            except Exception:
                                score = 0.0
                            outcome = TaskOutcome.PASSED if score >= 0.5 else TaskOutcome.FAILED
                            details["csv_score"] = score
                            details["csv_metric"] = picked.get("metric_name")
                            details["csv_result_type"] = picked.get("result_type")
                            return ExternalEvaluation(
                                task_id=run.task_id,
                                benchmark_name=self.name,
                                outcome=outcome,
                                score=score,
                                evaluator=str(eval_script),
                                evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                                details=details,
                            )
                except Exception as csv_exc:
                    details["csv_error"] = f"{type(csv_exc).__name__}: {csv_exc}"
            # Fallback: heuristic stdout score
            import re as _re

            m = _re.search(r'"score"\s*:\s*([0-9.]+)', proc.stdout)
            if not m:
                m = _re.search(r"Completion Rate[^0-9]*([0-9.]+)", proc.stdout)
            if m and proc.returncode == 0:
                score = float(m.group(1))
                outcome = TaskOutcome.PASSED if score >= 0.5 else TaskOutcome.FAILED
                return ExternalEvaluation(
                    task_id=run.task_id,
                    benchmark_name=self.name,
                    outcome=outcome,
                    score=score,
                    evaluator=str(eval_script),
                    evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                    details=details,
                )
            # No score parsed but evaluator ran — treat non-zero as execution error, zero as failed honest
            # Special case: missing workspace deps (e.g. metagpt) is an environment gap, not a DSA failure — keep honest failed
            stderr = proc.stderr or ""
            if "ModuleNotFoundError" in stderr and "metagpt" in stderr:
                details["evaluator_unavailable"] = (
                    "workspace missing `metagpt` (see .workspace/requirements.txt) — GT present but original evaluator not runnable"
                )
                return ExternalEvaluation(
                    task_id=run.task_id,
                    benchmark_name=self.name,
                    outcome=TaskOutcome.FAILED,
                    evaluator=str(eval_script),
                    evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                    details=details,
                )
            outcome = TaskOutcome.FAILED if proc.returncode == 0 else TaskOutcome.EXECUTION_ERROR
            return ExternalEvaluation(
                task_id=run.task_id,
                benchmark_name=self.name,
                outcome=outcome,
                evaluator=str(eval_script),
                evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                details=details,
            )
        except Exception as exc:
            # GT lane wiring failure is environment, not DSA pipeline failure — honest failed
            return ExternalEvaluation(
                task_id=run.task_id,
                benchmark_name=self.name,
                outcome=TaskOutcome.FAILED,
                evaluator=str(eval_script),
                evaluator_version=f"upstream@{UPSTREAM_COMMIT[:8]}",
                details={
                    **details,
                    "error": f"{type(exc).__name__}: {exc}",
                    "honest_lane": "GT present but evaluator wiring failed",
                },
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
        file_map = self._materialize_expected_files(run, run_dir)
        if file_map:
            (run_dir / "dsa_file_map.json").write_text(
                json.dumps(file_map, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        return run_dir

    # ------------------------------------------------- adapter v2: file mapping
    def _expected_output_files(self, task_id: str) -> list[str]:
        """Filenames the metric functions read, parsed from metric YAML.

        Gold-isolation boundary (§19, §29): only string literals inside file
        I/O calls (read_csv/read_excel/to_csv/imread/open/savefig …) are
        extracted — i.e. the task's *I/O contract*. GT values, metric logic,
        and thresholds are never read here and never reach the agent (this
        runs on the evaluation side, after the agent run finished).
        """
        import re as _re

        metric = self._upstream_root() / "metric" / task_id / "metric.yaml"
        if not metric.is_file():
            return []
        try:
            text = metric.read_text(encoding="utf-8")
        except OSError:
            return []
        # Strip full-line comments: example snippets in metric YAML are often
        # commented out (e.g. a sample model_accuracy reading predictions.csv);
        # only live code defines the I/O contract.
        text = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        # Any quoted filename literal with a data/image extension: metric code
        # passes output names positionally too (e.g. vlm_vis_quality(gt,
        # "roc_curve.png")), so I/O-call scoping would miss them. Ground-truth
        # *values* are never read here — only filename strings, resolved
        # against the run dir (GT itself lives under data/{task}/gt/).
        pat = _re.compile(r"['\"]([^\"'(){}:\s]+?\.(?:csv|xlsx|xls|png|jpg|jpeg|parquet))['\"]")
        return sorted(set(pat.findall(text)))

    @staticmethod
    def _collect_genuine_artifacts(run: ExternalRun) -> tuple[list, list, dict]:
        """Genuine agent outputs eligible for file mapping.

        Returns (tabular, images, exports) where tabular entries are
        (n_rows, columns, rows, call_id) from tool outputs carrying
        columns+rows, images are (n_bytes, png_bytes, call_id) from
        successful chart outputs, and exports maps exported filenames to
        ``(path, call_id)`` for `export_artifact` results (ADR-002: the
        planner names these from the user question, so an exact-name match
        carries semantic intent). Nothing is synthesized: byte-identical
        agent content is only relocated under evaluator-expected names.
        """
        import base64 as _b64

        tabular: list = []
        images: list = []
        exports: dict[str, tuple[str, str | None]] = {}
        for tc in run.tool_calls or []:
            if not isinstance(tc, dict) or tc.get("status") != "ok":
                continue
            out = tc.get("output")
            if not isinstance(out, dict):
                continue
            cols, rows = out.get("columns"), out.get("rows")
            if (
                isinstance(cols, list)
                and cols
                and isinstance(rows, list)
                and all(isinstance(c, str) for c in cols)
            ):
                tabular.append((len(rows), cols, rows, tc.get("call_id")))
            b64 = out.get("base64_png")
            if isinstance(b64, str) and b64:
                try:
                    raw = _b64.b64decode(b64)
                except Exception:  # noqa: S112 - undecodable chart payload means "no image"; recorded by absence
                    continue
                if raw[:8] == b"\x89PNG\r\n\x1a\n":
                    images.append((len(raw), raw, tc.get("call_id")))
            if tc.get("tool") == "export_artifact" and out.get("filename") and out.get("path"):
                exports[str(out["filename"])] = (str(out["path"]), tc.get("call_id"))
        tabular.sort(key=lambda t: t[0], reverse=True)
        images.sort(key=lambda t: t[0], reverse=True)
        return tabular, images, exports

    def _materialize_expected_files(self, run: ExternalRun, run_dir: Path) -> dict[str, object]:
        """Map genuine agent artifacts onto evaluator-expected filenames.

        For every expected relative path: ``.csv`` ← largest tabular tool
        output; ``.xlsx``/``.xls`` ← same via openpyxl (skipped honestly when
        unavailable); ``.png``/``.jpg`` ← largest chart PNG bytes. Paths are
        confined to the run dir (absolute or ``..`` targets refused and
        recorded). Unmatched names stay absent (honest Error, not invented
        content). Returns the audit map written as ``dsa_file_map.json``.
        """
        import csv as _csv

        mapping: dict[str, object] = {
            "adapter_version": ADAPTER_VERSION,
            "task_id": run.task_id,
            "mapped": {},
            "skipped": {},
        }
        tabular, images, exports = self._collect_genuine_artifacts(run)
        if not tabular and not images and not exports:
            mapping["skipped"]["_all"] = "no genuine tabular/chart/export artifacts in run"
            return mapping
        import shutil as _shutil

        for rel in self._expected_output_files(run.task_id):
            if rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
                mapping["skipped"][rel] = "unsafe path refused"
                continue
            dest = run_dir / rel
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                mapping["skipped"][rel] = f"mkdir failed: {exc}"
                continue
            # Exact-name workspace export first (semantic intent: the planner
            # named this file for its purpose); generic largest-artifact
            # fallback second. Either way bytes are agent-computed.
            exp = exports.get(Path(rel).name)
            if exp is not None and Path(exp[0]).is_file():
                try:
                    _shutil.copyfile(exp[0], dest)
                    mapping["mapped"][rel] = f"workspace export from {exp[1]}"
                    continue
                except OSError as exc:
                    mapping["skipped"][rel] = f"export copy failed: {exc}"
                    continue
            suf = dest.suffix.lower()
            try:
                if suf == ".csv" and tabular:
                    _, cols, rows, cid = tabular[0]
                    with dest.open("w", newline="", encoding="utf-8") as fh:
                        w = _csv.writer(fh)
                        w.writerow(cols)
                        w.writerows(rows)
                    mapping["mapped"][rel] = f"tabular from {cid} ({len(rows)} rows)"
                elif suf in (".xlsx", ".xls") and tabular:
                    try:
                        import openpyxl as _oxl
                    except ImportError:
                        mapping["skipped"][rel] = "openpyxl unavailable"
                        continue
                    _, cols, rows, cid = tabular[0]
                    wb = _oxl.Workbook()
                    ws = wb.active
                    ws.append(list(cols))
                    for r in rows:
                        ws.append(list(r))
                    wb.save(dest)
                    mapping["mapped"][rel] = f"tabular-xlsx from {cid} ({len(rows)} rows)"
                elif suf in (".png", ".jpg", ".jpeg") and images:
                    _, raw, cid = images[0]
                    dest.write_bytes(raw)
                    mapping["mapped"][rel] = f"chart bytes from {cid} ({len(raw)} B)"
                else:
                    mapping["skipped"][rel] = "no matching genuine artifact"
            except Exception as exc:
                mapping["skipped"][rel] = f"{type(exc).__name__}: {exc}"
        return mapping


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
