from __future__ import annotations

import hashlib
import json as _json
import time
import uuid
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
    Evidence,
    Insight,
    ToolCallRecord,
    ValidationResult,
)
from dsa_datasets.loader import load_dataframe
from dsa_datasets.validate import detect_format


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


_TOOL_CACHE: dict[tuple[str, str], tuple[Any, bool, str | None]] = {}


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
    val: tuple[Any, bool, str | None] = (
        (result.output, True, None) if result.status == "ok" else (None, False, result.error)
    )
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


def _evidence_for_tool_call(tool: str, call_id: str, output: Any) -> Evidence | None:
    eid = f"E-{uuid.uuid4().hex[:8]}"
    claim = ""
    source_type: Any = "python"
    confidence = 0.7
    result: dict[str, Any] = {}
    try:
        if tool == "run_sql" and output is not None:
            source_type = "sql"
            result = {
                "columns": getattr(output, "columns", []),
                "row_count": getattr(output, "row_count", 0),
                "rows": getattr(output, "rows", [])[:5],
            }
            claim = f"SQL returned {result.get('row_count', 0)} rows"
            confidence = 0.85
        elif tool == "correlation_analysis" and output is not None:
            source_type = "statistical_test"
            result = {
                "r": getattr(output, "r", None),
                "p_value": getattr(output, "p_value", None),
                "method": getattr(output, "method", ""),
            }
            claim = f"Correlation {getattr(output, 'x', '')} vs {getattr(output, 'y', '')}: r={getattr(output, 'r', 0):.3f}"
            confidence = 0.8
        elif tool == "hypothesis_test" and output is not None:
            source_type = "statistical_test"
            result = {
                "statistic": getattr(output, "statistic", None),
                "p_value": getattr(output, "p_value", None),
                "test": getattr(output, "test", ""),
            }
            claim = f"Hypothesis test {getattr(output, 'test', '')}: p={getattr(output, 'p_value', 0):.4g}"
            confidence = 0.8
        elif tool == "regression_analysis" and output is not None:
            source_type = "model"
            result = {
                "metrics": getattr(output, "metrics", {}),
                "model": getattr(output, "model", ""),
            }
            claim = f"Regression {getattr(output, 'model', '')} metrics {getattr(output, 'metrics', {})}"
            confidence = 0.75
        elif tool in ("train_model", "evaluate_model") and output is not None:
            source_type = "model"
            result = {
                "metrics": getattr(output, "metrics", getattr(output, "cv_scores", {})),
                "model": getattr(output, "model", ""),
            }
            claim = f"Model {getattr(output, 'model', '')} evaluated"
            confidence = 0.75
        elif tool == "forecast" and output is not None:
            source_type = "model"
            result = {
                "forecast": getattr(output, "forecast", [])[:5],
                "mae": getattr(output, "metrics", {}).get("mae"),
                "method": getattr(output, "method", ""),
            }
            claim = f"Forecast {getattr(output, 'method', '')}: next {len(getattr(output, 'forecast', []))} periods, MAE={getattr(output, 'metrics', {}).get('mae', 0):.2f}"
            confidence = 0.7
        elif tool == "feature_importance" and output is not None:
            source_type = "model"
            imps = getattr(output, "importances", [])[:3]
            result = {"top_features": imps}
            claim = f"Top features for {getattr(output, 'target', '')}: {', '.join(i.get('feature', '') for i in imps)}"
            confidence = 0.7
        elif tool == "assumption_check" and output is not None:
            source_type = "statistical_test"
            result = {
                "checks": getattr(output, "checks", []),
                "passed": getattr(output, "passed", True),
            }
            claim = f"Assumption check: {getattr(output, 'recommendation', '')[:120]}"
            confidence = 0.75
        elif tool == "causal_check" and output is not None:
            source_type = "statistical_test"
            result = {
                "estimate": getattr(output, "estimate", 0),
                "method": getattr(output, "method", ""),
                "passes_causal_bar": getattr(output, "passes_causal_bar", False),
                "confidence_note": getattr(output, "confidence_note", ""),
            }
            claim = f"Causal check ({getattr(output, 'method', '')}): estimate={getattr(output, 'estimate', 0):.3f}, causal_bar={'pass' if getattr(output, 'passes_causal_bar', False) else 'fail'} — {getattr(output, 'confidence_note', '')[:100]}"
            confidence = 0.5
        elif tool == "create_chart" and output is not None:
            source_type = "visualization"
            result = {
                "artifact_path": getattr(output, "artifact_path", ""),
                "chart_type": getattr(output, "chart_type", ""),
            }
            claim = f"Chart {getattr(output, 'chart_type', '')} created"
            confidence = 0.7
        elif tool == "profile_dataset" and output is not None:
            source_type = "python"
            prof = getattr(output, "profile", {}) or {}
            result = {"rows": prof.get("rows"), "columns": prof.get("columns")}
            claim = f"Profile: {result.get('rows')} rows, {result.get('columns')} cols"
            confidence = 0.9
        elif tool == "run_python" and output is not None:
            source_type = "python"
            result = {
                "stdout": getattr(output, "stdout", "")[:500],
                "error": getattr(output, "error", None),
            }
            claim = "Python execution completed"
            confidence = 0.6
        else:
            return None
    except Exception:
        return None
    return Evidence(
        id=eid,
        claim=claim,
        source_type=source_type,
        source_id=call_id,
        result=result,
        confidence=confidence,
        validation_status="pending",
    )


async def run_analysis(
    dataset_path: str | None,
    dataset_id: str,
    user_query: str,
    run_id: str | None = None,
) -> AnalysisState:
    from dsa_tools import bootstrap as tools_bootstrap

    # ensure tools registered (idempotent)
    try:
        from dsa_tools import list_tools

        if not list_tools():
            tools_bootstrap()
    except Exception:
        tools_bootstrap()

    rid = run_id or f"run-{uuid.uuid4().hex[:10]}"
    state = AnalysisState(
        run_id=rid,
        dataset_id=dataset_id,
        dataset_path=dataset_path,
        user_query=user_query,
        objective=user_query[:500],
        status=AnalysisStatus.UNDERSTANDING,
    )

    # UNDERSTANDING -> PLANNING
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
            ev = _evidence_for_tool_call(step.tool, call_id, output)
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

    if (
        indep_batch
        and len(indep_batch) > 1
        and state.tool_call_count + len(indep_batch) <= state.budget.max_tool_calls
    ):
        results = await _asyncio.gather(*[_exec_one(s) for s in indep_batch])
        for step, inputs, output, ok, err, dur in results:
            await _record(step, inputs, output, ok, err, dur)
        for step in rest:
            if state.tool_call_count >= state.budget.max_tool_calls:
                state.status = AnalysisStatus.FAILED
                state.error = "Tool call budget exceeded"
                break
            step2, inputs2, output2, ok2, err2, dur2 = await _exec_one(step)
            await _record(step2, inputs2, output2, ok2, err2, dur2)
    else:
        for step in state.plan:
            if state.tool_call_count >= state.budget.max_tool_calls:
                state.status = AnalysisStatus.FAILED
                state.error = "Tool call budget exceeded"
                break
            step2, inputs2, output2, ok2, err2, dur2 = await _exec_one(step)
            await _record(step2, inputs2, output2, ok2, err2, dur2)

    # VALIDATION (Critic)
    if evidence_critic_enabled():
        state.status = AnalysisStatus.VALIDATION
        vresults = critic_validate(state)
        state.validation_results = vresults
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
                        ev = _evidence_for_tool_call(rec.tool, new_id, output)
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
        except Exception:
            pass
    except Exception as e:
        state.error = f"Report write failed: {e}"

    # Final status
    has_hard_fail = any(not r.passed for r in state.validation_results if r.check == "budget")
    state.status = AnalysisStatus.FAILED if has_hard_fail else AnalysisStatus.COMPLETED
    state.touch()
    return state
