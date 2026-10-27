from __future__ import annotations

import hashlib
import json as _json
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from dsa_agent.critic import (
    correction_message,
    critic_validate,
    evidence_critic_enabled,
    should_retry,
)
from dsa_agent.planner import plan_analysis
from dsa_agent.report import build_markdown_report, write_report_artifacts
from dsa_agent.state import (
    AnalysisState,
    AnalysisStatus,
    Artifact,
    Insight,
    ReasoningRecord,
    ToolCallRecord,
    ValidationResult,
)
from dsa_agent.tool_evidence import build_tool_evidence
from dsa_datasets.artifact_paths import artifact_root
from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format
from dsa_llm.providers import resolve_llm_mode


def _get_columns(dataset_path: str | None) -> list[str]:
    if not dataset_path:
        return []
    p = Path(dataset_path)
    if not p.exists():
        return []
    try:
        fmt = detect_format(p.name)
        df = load_dataframe(p, fmt)
        return list(df.columns)
    except Exception:
        return []


#: Checks whose failure must change the reported status. A check that is recorded
#: and displayed but never consulted cannot protect the product's guarantee, so the
#: terminal status reads this set. ``evidence_coverage`` is deliberately absent:
#: including it also fails early-stage ablation runs pinned by
#: ``tests/test_critic_ablation.py``, which is an unresolved status-semantics
#: decision, not an oversight.
HARD_FAIL_CHECKS = frozenset({"budget", "evidence_bundle", "tool_errors", "unsupported_claim"})

_TOOL_CACHE: dict[tuple[str, str], tuple[Any, bool, str | None]] = {}


def _resolve_refs(inputs: dict[str, Any], prior_calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve cross-step references against already-recorded tool calls (ADR-002).

    Three forms, in order of how much they can be trusted:

    - ``{"$from_step_id": "s03"}`` -- the plan step that produced the result. This is the only form that is
      unambiguous once the run is not a straight line: a retried step appends a second record, and the leading
      independent batch is executed with ``gather``, so a position in ``prior_calls`` is not a step number.
    - ``{"$from_tool": "run_sql"}`` -- the latest successful call of that tool. Position-independent, but two
      calls of the same tool leave the choice to recency.
    - ``{"$from_step": i}`` -- the i-th record in execution order, 0-based, failures included. Kept for
      compatibility; a planner cannot know this index before the run, so it is not recommended.

    A reference whose target did not succeed is not skipped past: it comes back as the original key plus
    ``$reference_reason``, and ``export_artifact`` refuses it with that reason. Silently moving on to the next
    successful call is how a run exported a table nobody asked for and still reported clean -- measured
    2026-10-26 over ``[run_sql ok, create_chart error, run_sql ok]``, where the old successful-only counting made
    ``{"$from_step": 1}`` return the third call's rows and the export succeed. Anything else passes through
    untouched; an unresolvable reference is left in place so the tool fails honestly instead of inventing content.
    """
    calls = [c for c in prior_calls if isinstance(c, dict)]
    by_step: dict[str, Any] = {}
    for c in calls:
        sid = c.get("step_id")
        if isinstance(sid, str) and c.get("status") == "ok":
            by_step[sid] = c.get("output") or {}

    def _resolve(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value.keys()) == {"$from_step_id"} and isinstance(value["$from_step_id"], str):
                sid = value["$from_step_id"]
                if sid in by_step:
                    return by_step[sid]
                return {
                    "$from_step_id": sid,
                    "$reference_reason": f"step {sid} produced no successful result",
                }
            if set(value.keys()) == {"$from_step"} and isinstance(value["$from_step"], int):
                i = value["$from_step"]
                if 0 <= i < len(calls):
                    target = calls[i]
                    if target.get("status") != "ok":
                        return {
                            "$from_step": i,
                            "$reference_reason": (
                                f"call {i} ({target.get('tool', 'unknown tool')}) did not succeed, "
                                "so it has no result to relocate"
                            ),
                        }
                    return target.get("output") or {}
                return value
            if set(value.keys()) == {"$from_tool"} and isinstance(value["$from_tool"], str):
                for c in reversed(calls):
                    if c.get("tool") == value["$from_tool"] and c.get("status") == "ok":
                        return c.get("output") or {}
                return value
            return {k: _resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_resolve(v) for v in value]
        return value

    return {k: _resolve(v) for k, v in inputs.items()}


def _export_workspace(run_id: str | None) -> str:
    root = artifact_root(run_id or "run-local")
    return str(root / "exports")


def _tool_cache_key(tool_name: str, inputs: dict[str, Any]) -> tuple[str, str]:
    try:
        raw = _json.dumps(inputs, sort_keys=True, default=str)
    except Exception:
        raw = str(sorted(inputs.items()))
    return (tool_name, hashlib.sha256(raw.encode()).hexdigest()[:24])


async def _run_tool(tool_name: str, inputs: dict[str, Any]) -> tuple[Any, bool, str | None]:
    key = _tool_cache_key(tool_name, inputs)
    if key in _TOOL_CACHE:
        return _TOOL_CACHE[key]
    from dsa_tools import get as get_tool

    tool = get_tool(tool_name)
    result = await tool.run(inputs)
    if result.status != "ok":
        # A failure stored under this key would be replayed to every later call
        # for the life of the process, so only successes are cached.
        return (None, False, result.error)
    val: tuple[Any, bool, str | None] = (result.output, True, None)
    _TOOL_CACHE[key] = val
    return val


def _tool_inputs_for_step(
    step_tool: str, step_inputs: dict[str, Any], dataset_path: str | None
) -> dict[str, Any]:
    inp = dict(step_inputs)
    if dataset_path:
        if step_tool in (
            "run_sql",
            "run_python",
            "correlation_analysis",
            "hypothesis_test",
            "assumption_check",
            "causal_check",
            "regression_analysis",
            "train_model",
            "evaluate_model",
            "feature_importance",
            "forecast",
            "create_chart",
        ):
            if "dataset_path" not in inp:
                inp["dataset_path"] = dataset_path
        if step_tool == "profile_dataset" and "path" not in inp:
            inp["path"] = dataset_path
        if step_tool == "run_sql" and "sql" not in inp:
            inp["sql"] = "SELECT COUNT(*) as n FROM dataset"
    return inp


async def run_analysis(
    dataset_path: str | None,
    dataset_id: str,
    user_query: str,
    run_id: str | None = None,
    on_update: Callable[[AnalysisState], Awaitable[None]] | None = None,
) -> AnalysisState:
    """Run one analysis to completion.

    ``on_update`` is awaited with the live state at each stage boundary (plan set, one tool call recorded,
    validation entered). It exists for the API, which now persists the row *while* this runs so a client can
    watch it (R-03); it is not a progress bar inside the graph, and nothing here reads it back. A failure in
    the callback is not swallowed -- if the store cannot be written to, the run cannot be recorded anyway,
    and the caller's own error path is the honest place for that to surface.
    """
    from dsa_tools import bootstrap as tools_bootstrap

    # ensure tools registered (idempotent)
    try:
        from dsa_tools import list_tools

        if not list_tools():
            tools_bootstrap()
    except Exception:
        tools_bootstrap()

    rid = run_id or f"run-{uuid.uuid4().hex[:10]}"
    resolved_mode = resolve_llm_mode()
    state = AnalysisState(
        run_id=rid,
        dataset_id=dataset_id,
        dataset_path=dataset_path,
        user_query=user_query,
        objective=user_query[:500],
        status=AnalysisStatus.UNDERSTANDING,
        reasoning=ReasoningRecord(
            mode=resolved_mode.mode,
            provider=resolved_mode.provider,
            model=resolved_mode.model,
            source=resolved_mode.source,
            stub=resolved_mode.stub,
            error=resolved_mode.error,
        ),
    )

    # UNDERSTANDING -> PLANNING
    async def _notify() -> None:
        if on_update is not None:
            await on_update(state)

    state.status = AnalysisStatus.PLANNING
    state.touch()
    cols = _get_columns(dataset_path)
    plan = await plan_analysis(user_query, dataset_path, cols)
    state.plan = plan.steps
    state.objective = plan.objective
    from dsa_agent.state import AgentMessage

    state.agent_messages = [
        AgentMessage(
            agent="planner",
            content=f"Planned {len(plan.steps)} steps: {', '.join(s.tool for s in plan.steps)}",
        )
    ]
    await _notify()

    # DATA_PROFILING -> ANALYSIS -> MODELING loop
    # batch independent steps (no depends_on) via gather; sequential for dependent tail
    import asyncio as _asyncio

    _PARALLEL_TOOLS = {
        "correlation_analysis",
        "hypothesis_test",
        "assumption_check",
        "create_chart",
        "run_sql",
    }
    state.status = AnalysisStatus.ANALYSIS

    async def _exec_one(step: Any) -> tuple[Any, Any, Any, Any, Any, float]:
        inputs = _tool_inputs_for_step(step.tool, step.inputs, dataset_path)
        prior = []
        for c in state.tool_calls:
            try:
                prior.append(c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c))
            except Exception:  # noqa: S112 - unserializable prior call skipped from ref scope
                continue
        inputs = _resolve_refs(inputs, prior)
        if step.tool == "export_artifact" and "workspace" not in inputs:
            inputs["workspace"] = _export_workspace(rid)
        t0 = time.perf_counter()
        output, ok, err = await _run_tool(step.tool, inputs)
        dur = int((time.perf_counter() - t0) * 1000)
        return step, inputs, output, ok, err, dur

    # identify leading independent batch (consecutive independent steps at start)
    indep_batch: list[Any] = []
    rest: list[Any] = []
    seen_dep = False
    for s in state.plan:
        is_indep = not getattr(s, "depends_on", None) and s.tool in _PARALLEL_TOOLS
        if not seen_dep and is_indep:
            indep_batch.append(s)
        else:
            if not is_indep:
                seen_dep = True
            # once dependent seen, don't batch further
            if indep_batch and not seen_dep:
                indep_batch.append(s) if is_indep else None  # no-op
                if not is_indep:
                    rest.append(s)
            else:
                rest.append(s)
    # fallback: if classification failed, treat all independent as batch
    if len(indep_batch) <= 1:
        indep_batch = [
            s
            for s in state.plan
            if not getattr(s, "depends_on", None) and s.tool in _PARALLEL_TOOLS
        ][:4]
        rest = [s for s in state.plan if s not in indep_batch]

    async def _record(step: Any, inputs: Any, output: Any, ok: Any, err: Any, dur: Any) -> None:
        call_id = f"TC-{uuid.uuid4().hex[:8]}"
        rec = ToolCallRecord(
            call_id=call_id,
            tool=step.tool,
            step_id=getattr(step, "id", None),
            input=inputs,
            output=output.model_dump(mode="json")
            if hasattr(output, "model_dump")
            else (dict(output) if isinstance(output, dict) else None),
            status="ok" if ok else "error",
            error=err,
            duration_ms=dur,
        )
        state.tool_calls.append(rec)
        state.tool_call_count += 1
        if ok and output is not None:
            ev = build_tool_evidence(step.tool, call_id, output)
            if ev:
                state.evidence.append(ev)
                if step.tool in (
                    "correlation_analysis",
                    "hypothesis_test",
                    "regression_analysis",
                    "forecast",
                    "feature_importance",
                    "assumption_check",
                    "causal_check",
                ):
                    iid = f"I-{uuid.uuid4().hex[:8]}"
                    state.insights.append(
                        Insight(
                            id=iid,
                            finding=ev.claim,
                            evidence_ids=[ev.id],
                            limitation="Association does not imply causation.",
                        )
                    )
        state.current_step += 1
        state.touch()
        await _notify()

    if (
        indep_batch
        and len(indep_batch) > 1
        and state.current_step < state.budget.max_steps
        and state.tool_call_count + len(indep_batch) <= state.budget.max_tool_calls
    ):
        allowance = state.budget.max_steps - state.current_step
        results = await _asyncio.gather(*[_exec_one(s) for s in indep_batch[:allowance]])
        for step, inputs, output, ok, err, dur in results:
            await _record(step, inputs, output, ok, err, dur)
        for step in rest:
            if state.current_step >= state.budget.max_steps:
                break
            if state.tool_call_count >= state.budget.max_tool_calls:
                state.status = AnalysisStatus.FAILED
                state.error = "Tool call budget exceeded"
                break
            step2, inputs2, output2, ok2, err2, dur2 = await _exec_one(step)
            await _record(step2, inputs2, output2, ok2, err2, dur2)
    else:
        for step in state.plan:
            if state.current_step >= state.budget.max_steps:
                break
            if state.tool_call_count >= state.budget.max_tool_calls:
                state.status = AnalysisStatus.FAILED
                state.error = "Tool call budget exceeded"
                break
            step2, inputs2, output2, ok2, err2, dur2 = await _exec_one(step)
            await _record(step2, inputs2, output2, ok2, err2, dur2)

    if len(state.plan) > state.current_step and state.current_step >= state.budget.max_steps:
        state.status = AnalysisStatus.FAILED
        state.error = "Step budget exceeded"

    # VALIDATION (Critic)
    if evidence_critic_enabled():
        state.status = AnalysisStatus.VALIDATION
        vresults = critic_validate(state)
        state.validation_results = vresults
        await _notify()
        # retry logic: if should_retry and we have failures, attempt one re-run of failed statistical steps (max 3)
        if should_retry(vresults, state.retry_count, state.budget.max_retries):
            # simple retry: re-run error tool calls once
            state.retry_count += 1
            state.agent_messages.append(
                AgentMessage(
                    agent="critic",
                    content=f"Validation failed, retry {state.retry_count}: {correction_message(vresults)}",
                )
            )
            # retry failed tool calls
            for rec in list(state.tool_calls):
                if rec.status == "error" and state.tool_call_count < state.budget.max_tool_calls:
                    # attempt retry with same inputs
                    t0 = time.perf_counter()
                    output, ok, err = await _run_tool(rec.tool, rec.input)
                    dur = int((time.perf_counter() - t0) * 1000)
                    new_id = f"TC-{uuid.uuid4().hex[:8]}"
                    new_rec = ToolCallRecord(
                        call_id=new_id,
                        tool=rec.tool,
                        step_id=rec.step_id,
                        input=rec.input,
                        output=output.model_dump(mode="json")
                        if hasattr(output, "model_dump")
                        else None,
                        status="ok" if ok else "error",
                        error=err,
                        duration_ms=dur,
                    )
                    state.tool_calls.append(new_rec)
                    state.tool_call_count += 1
                    if ok and output is not None:
                        ev = build_tool_evidence(rec.tool, new_id, output)
                        if ev:
                            state.evidence.append(ev)
            # re-validate
            state.validation_results = critic_validate(state)

    else:
        state.validation_results = []
        state.agent_messages.append(
            AgentMessage(
                agent="critic",
                content="Evidence critic disabled for evaluation ablation.",
            )
        )

    # Check if still failing hard
    failed = [r for r in state.validation_results if not r.passed and r.check in ("budget",)]
    if failed:
        state.status = AnalysisStatus.FAILED
        state.error = correction_message(state.validation_results)
        return state

    # SYNTHESIS + REPORTING
    state.status = AnalysisStatus.SYNTHESIS
    # Insights already scaffolded; add summary insight if missing
    if not state.insights and state.evidence:
        state.insights.append(
            Insight(
                id=f"I-{uuid.uuid4().hex[:8]}",
                finding=f"Analysis of {len(state.evidence)} evidence items for: {state.objective[:120]}",
                evidence_ids=[e.id for e in state.evidence[:3]],
                limitation="Evidence-grounded; see validation.",
            )
        )

    state.status = AnalysisStatus.REPORTING
    md = build_markdown_report(state)
    state.report_markdown = md
    # persist artifacts + reproducibility bundle (experiment.json + reproduce.sh + notebook)
    report_unpersisted = False
    try:
        paths = write_report_artifacts(state)
        state.report_id = state.run_id
        state.artifacts.append(
            Artifact(
                id=f"A-{uuid.uuid4().hex[:8]}",
                type="report",
                path=paths["markdown"],
                metadata={"kind": "markdown"},
            )
        )
        state.artifacts.append(
            Artifact(
                id=f"A-{uuid.uuid4().hex[:8]}",
                type="report",
                path=paths["experiment"],
                metadata={"kind": "experiment"},
            )
        )
        # enrich with full evidence bundle
        try:
            from dsa_evidence.graph import build_evidence_graph
            from dsa_evidence.repro import build_experiment_json, build_notebook, build_reproduce_sh
            from dsa_evidence.validator import validate_evidence_graph

            g = build_evidence_graph(
                state.run_id,
                state.dataset_id,
                state.dataset_path,
                state.evidence,
                state.insights,
                state.tool_calls,
            )
            v = validate_evidence_graph(g)
            # append validation for traceability
            for item in v:
                state.validation_results.append(
                    ValidationResult(
                        check=item["check"],
                        passed=bool(item["passed"]),
                        message=item["message"],
                        details={
                            k: v for k, v in item.items() if k not in ("check", "passed", "message")
                        },
                    )
                )
            # ensure report dir has evidence graph + enhanced bundle
            report_dir = Path(paths["markdown"]).parent
            (report_dir / "evidence_graph.json").write_text(
                g.model_dump_json(indent=2), encoding="utf-8"
            )
            state.artifacts.append(
                Artifact(
                    id=f"A-{uuid.uuid4().hex[:8]}",
                    type="evidence",
                    path=str(report_dir / "evidence_graph.json"),
                    metadata={"kind": "evidence_graph"},
                )
            )
            # full experiment/repro may already exist; ensure they are also enriched
            sha = g.dataset_sha256
            exp_path = build_experiment_json(
                state.run_id,
                state.dataset_path,
                sha,
                state.user_query,
                [s.model_dump(mode="json") for s in state.plan],
                [c.model_dump(mode="json") for c in state.tool_calls],
                [e.model_dump(mode="json") for e in state.evidence],
                [i.model_dump(mode="json") for i in state.insights],
                report_dir,
            )
            repro_path = build_reproduce_sh(
                state.run_id, state.dataset_path, state.user_query, report_dir
            )
            nb_path = build_notebook(
                state.run_id,
                state.dataset_path,
                state.user_query,
                [s.model_dump(mode="json") for s in state.plan],
                [c.model_dump(mode="json") for c in state.tool_calls],
                report_dir,
            )
            # dedup artifacts by path
            existing_paths = {a.path for a in state.artifacts}
            for p, kind in [
                (exp_path, "experiment"),
                (repro_path, "reproduce"),
                (nb_path, "notebook"),
            ]:
                sp = str(p)
                if sp not in existing_paths:
                    state.artifacts.append(
                        Artifact(
                            id=f"A-{uuid.uuid4().hex[:8]}",
                            type="report" if kind == "experiment" else kind,
                            path=sp,
                            metadata={"kind": kind},
                        )
                    )
        except Exception as exc:
            state.validation_results.append(
                ValidationResult(
                    check="evidence_bundle",
                    passed=False,
                    message=(
                        "Reproducibility bundle incomplete: evidence graph, experiment.json, "
                        f"reproduce.sh or notebook was not written ({type(exc).__name__}: {exc})"
                    ),
                )
            )
    except Exception as e:
        state.error = f"Report write failed: {e}"
        report_unpersisted = True

    # A run that could not put its report on disk did not deliver, whatever the critic thought:
    # publishing it as COMPLETED while `error` says otherwise is D-L4-08 (§125).
    has_hard_fail = any(
        not r.passed for r in state.validation_results if r.check in HARD_FAIL_CHECKS
    )
    state.status = (
        AnalysisStatus.FAILED if (has_hard_fail or report_unpersisted) else AnalysisStatus.COMPLETED
    )
    state.touch()
    return state
