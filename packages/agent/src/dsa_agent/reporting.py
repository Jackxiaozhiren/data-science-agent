"""Report composition for a finished analysis (audit §115, Phase 4 target 2 seam #7).

Split out of ``dsa_agent.langgraph_graph._node_report``, which had grown to 179 lines -- the largest
function in the shipped tree -- by stacking six jobs inside one graph node: rebuilding the state model,
rendering markdown, persisting artifacts, building the reproducibility bundle, merging its validation
results and shaping the graph's return envelope. The node is now an adapter over
:func:`compose_report`; this module is the composition.

Behaviour is unchanged, and the claim is tested rather than asserted: a capture of the node driven by
three real runs' own ``run_result`` payloads (``raw_runs.json``) is byte-identical across the split,
with ``uuid4`` and the generated-at timestamps pinned -- see ``AUDIT_LEDGER.md`` §115.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from dsa_agent.state import AnalysisStatus


def compose_report(state: Mapping[str, Any]) -> dict[str, Any]:
    analysis = state.get("analysis_state") or {}
    run_id = state.get("run_id") or f"run-{uuid.uuid4().hex[:10]}"
    dataset_id = state.get("dataset_id", "ds")
    dataset_path = state.get("dataset_path")
    user_query = state.get("user_query", "")
    try:
        from dsa_agent.report import build_markdown_report, write_report_artifacts
        from dsa_agent.state import AnalysisState as AS
        from dsa_agent.state import Evidence, Insight, ToolCallRecord, ValidationResult

        def _load_list(key: str, model: Any) -> list[Any]:
            return [model.model_validate(x) for x in (analysis.get(key) or [])]

        as_obj = AS(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_path=dataset_path,
            user_query=user_query,
            objective=state.get("objective", user_query[:500]),
            plan=[],
            tool_calls=_load_list("tool_calls", ToolCallRecord),
            evidence=_load_list("evidence", Evidence),
            insights=_load_list("insights", Insight),
            validation_results=_load_list("validation_results", ValidationResult),
            status=AnalysisStatus.REPORTING,
        )
        md = build_markdown_report(as_obj)
        analysis2 = {
            **analysis,
            "report_markdown": md,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "dataset_path": dataset_path,
            "user_query": user_query,
            "objective": state.get("objective", ""),
            "status": "COMPLETED",
        }
        # persist artifacts (best-effort)
        try:
            tmp_state = AS(
                run_id=run_id,
                dataset_id=dataset_id,
                dataset_path=dataset_path,
                user_query=user_query,
                objective=state.get("objective", ""),
                tool_calls=_load_list("tool_calls", ToolCallRecord),
                evidence=_load_list("evidence", Evidence),
                insights=_load_list("insights", Insight),
                validation_results=_load_list("validation_results", ValidationResult),
                report_markdown=md,
                status=AnalysisStatus.REPORTING,
            )
            paths = write_report_artifacts(tmp_state)
            arts = list(analysis2.get("artifacts") or [])
            arts.append(
                {
                    "id": f"A-{uuid.uuid4().hex[:8]}",
                    "type": "report",
                    "path": paths["markdown"],
                    "metadata": {"kind": "markdown"},
                }
            )
            arts.append(
                {
                    "id": f"A-{uuid.uuid4().hex[:8]}",
                    "type": "report",
                    "path": paths["experiment"],
                    "metadata": {"kind": "experiment"},
                }
            )
            analysis2["artifacts"] = arts
            # evidence bundle
            try:
                from dsa_agent.state import Evidence as Ev
                from dsa_agent.state import Insight as Ins
                from dsa_agent.state import ToolCallRecord as TC
                from dsa_agent.state import ValidationResult as VR
                from dsa_evidence.graph import build_evidence_graph
                from dsa_evidence.repro import (
                    build_experiment_json,
                    build_notebook,
                    build_reproduce_sh,
                )
                from dsa_evidence.validator import validate_evidence_graph

                evs = [Ev.model_validate(x) for x in (analysis2.get("evidence") or [])]
                iss = [Ins.model_validate(x) for x in (analysis2.get("insights") or [])]
                tcs = [TC.model_validate(x) for x in (analysis2.get("tool_calls") or [])]
                g = build_evidence_graph(run_id, dataset_id, dataset_path, evs, iss, tcs)
                v = validate_evidence_graph(g)
                vjs = [
                    VR(
                        check=item["check"], passed=bool(item["passed"]), message=item["message"]
                    ).model_dump(mode="json")
                    for item in v
                ]
                existing_v = list(analysis2.get("validation_results") or [])
                analysis2["validation_results"] = existing_v + vjs
                from pathlib import Path as _P

                report_dir = _P(paths["markdown"]).parent
                (report_dir / "evidence_graph.json").write_text(
                    g.model_dump_json(indent=2), encoding="utf-8"
                )
                arts2 = list(analysis2.get("artifacts") or [])
                arts2.append(
                    {
                        "id": f"A-{uuid.uuid4().hex[:8]}",
                        "type": "evidence",
                        "path": str(report_dir / "evidence_graph.json"),
                        "metadata": {"kind": "evidence_graph"},
                    }
                )
                sha = g.dataset_sha256
                # plan for notebook cells comes from outer plan (if any) — best-effort
                outer_plan = state.get("plan") or []
                exp_path = build_experiment_json(
                    run_id,
                    dataset_path,
                    sha,
                    user_query,
                    outer_plan,
                    [c.model_dump(mode="json") for c in tcs],
                    [e.model_dump(mode="json") for e in evs],
                    [i.model_dump(mode="json") for i in iss],
                    report_dir,
                )
                repro_path = build_reproduce_sh(run_id, dataset_path, user_query, report_dir)
                nb_path = build_notebook(
                    run_id,
                    dataset_path,
                    user_query,
                    outer_plan,
                    [c.model_dump(mode="json") for c in tcs],
                    report_dir,
                )
                existing = {a.get("path") for a in arts2}
                for pth, kind in [
                    (exp_path, "experiment"),
                    (repro_path, "reproduce"),
                    (nb_path, "notebook"),
                ]:
                    sp = str(pth)
                    if sp not in existing:
                        arts2.append(
                            {
                                "id": f"A-{uuid.uuid4().hex[:8]}",
                                "type": "report" if kind == "experiment" else kind,
                                "path": sp,
                                "metadata": {"kind": kind},
                            }
                        )
                analysis2["artifacts"] = arts2
            except Exception as exc:
                bundle_v = list(analysis2.get("validation_results") or [])
                bundle_v.append(
                    {
                        "check": "evidence_bundle",
                        "passed": False,
                        "message": (
                            "Reproducibility bundle incomplete: evidence graph, experiment.json, "
                            f"reproduce.sh or notebook was not written ({type(exc).__name__}: {exc})"
                        ),
                    }
                )
                analysis2["validation_results"] = bundle_v
        except Exception as exc:
            analysis2["error"] = f"Report write failed: {exc}"
            analysis2["status"] = "FAILED"
        persisted = analysis2["status"] == "COMPLETED"
        return {
            "analysis_state": analysis2,
            "status": analysis2["status"],
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        "Report generated"
                        if persisted
                        else f"Report could not be persisted: {analysis2['error']}"
                    ),
                }
            ],
        }
    except Exception as e:
        return {
            "messages": [{"role": "assistant", "content": f"Report error: {e}"}],
            "status": "FAILED",
        }
