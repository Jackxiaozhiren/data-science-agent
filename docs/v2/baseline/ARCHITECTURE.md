# Baseline Evidence — Architecture / ERD / Security / Tool Registry (W1 Supplement)

> Mirrors `ARCHITECTURE_FREEZE_V0.1.md` §1–12 + `docs/v2/Baseline Report.md` — frozen 2026-08-16, tree `587c4bf`.

## Architecture (live)

See `docs/v2/Baseline Report.md` §1–2 for the layered diagram and frozen repo tree. Spec authority is `ARCHITECTURE_FREEZE_V0.1.md`; runtime verification is `uv run pytest -v` / `docker compose config` / `npm run build` (see baseline report Appendix).

## Agent Graph

`packages/agent/src/dsa_agent/graph.py` (`run_analysis`) + `langgraph_graph.py` (`StateGraph` with `MemorySaver`):

```
START → UNDERSTANDING (Supervisor) → PLANNING (objective/assumptions/steps/tools/outputs)
      → DATA_PROFILING → ANALYSIS → MODELING → VALIDATION (Critic) ─┬─ FAIL → Correction → retry (≤3)
                                                                    └─ PASS → SYNTHESIS → REPORTING → COMPLETED
      ERROR → RECOVERY → RETRY → else HUMAN_REVIEW
```

Cost guard: `max_tokens / max_steps / max_tool_calls / max_time → STOP`. V0.1 implements 4 agents: Planner, Data Scientist, Critic, Report.

## ERD (SQLite MVP, verified `apps/api/src/dsa_api/models/`)

```
projects(id) 1──n datasets(id, project_id FK, filename, path, hash, format, rows, cols, metadata, created_at)
          1──n analysis_runs(id, project_id FK, dataset_id FK, user_query, objective, status ENUM, plan JSON, current_step, report_id FK, error, budget JSON, created_at)
                1──n agent_steps(id, run_id FK, agent, state, input, output, duration_ms, status)
                1──n tool_calls(id, run_id FK, step_id FK, tool_name, input, output, status, duration_ms, error)
                1──n artifacts(id, run_id FK, type ENUM[dataset|code|sql|table|chart|model|notebook|report|evidence], path, metadata, created_by, created_at)
                1──n evidence(id, run_id FK, claim, source_type ENUM[sql|python|statistical_test|model|visualization], source_id FK, result JSON, confidence, validation_status)
                1──n insights(id, run_id FK, finding, evidence_ids JSON, magnitude, significance, limitation, created_at)
                1──1 reports(id, run_id FK, markdown_path, html_path, pdf_path, notebook_path, experiment_json_path, created_at)
```

Indexes: `analysis_runs(status)`, `tool_calls(run_id, tool_name)`, `evidence(run_id)`.

## Tool Registry (17, verified `dsa_tools.list_tools()`)

| Tool | Category |
|---|---|
| profile_dataset, run_sql, run_python, correlation_analysis, hypothesis_test, assumption_check, causal_check, regression_analysis, train_model, evaluate_model, feature_importance, forecast, create_chart, save_artifact, create_evidence, validate_result, generate_report | Data/SQL/Python/Stats/ML/Viz/Evidence |

MCP aliases: `inspect_dataset→profile_dataset`, `query_dataset→run_sql`, `run_statistical_test→hypothesis_test`, `create_visualization→create_chart`, `get_evidence→create_evidence|validate_result`.

## Evidence Flow

```
Insight → Evidence(id, claim, source_type, source_id, result, confidence, validation_status)
        → ToolCall(call_id, tool, input, output, status, error, duration_ms)
        → Dataset(hash sha256)
artifact graph: build_evidence_graph(state) → evidence_graph.json + validate_evidence_graph (traceability + unsupported_claim)
repro bundle: experiment.json + reproduce.sh + analysis.ipynb under artifacts/reports/<runId>/
```

## Security Boundary

File (100 MB, allowlist ext + MIME sniff + traversal block + archive bomb), SQL (read-only allowlist, 11 denied patterns, row limit), Python AST (deny os/subprocess/socket/requests/eval/exec/open + introspection, allowlist polars/numpy/math/...; exec in safe globals), Prompt injection (UNTRUSTED DATA tag + pattern scan), Output guard (causal → association rewrite), Resource budget, HITL (`WAITING_FOR_APPROVAL`), JSON structured logging (no secrets).

## Benchmark

`benchmarks/ds-agent-benchmark/README.md` — 20 synthetic CSVs (seed 42) + 50 tasks (EDA 8 / SQL 7 / Stats 8 / Regression 6 / Classification 6 / TS 5 / Viz 5 / DQ 5) + ground truth + runner `dsa_evaluation.runner` / `uv run dsa --limit 50` → frozen snapshot in `benchmarks/baseline/`.

## Roadmap gate (per-phase test-gated)

Phase 0 Freeze → 1 Scaffold → 2 Data Layer → 3 Tool Layer → 4 Agent Graph → 5 Evidence → 6 API → 7 Frontend → 8 Security → 9 Benchmark → 10 MCP → 11 Docs — see `ARCHITECTURE_FREEZE_V0.1.md` §12. Each phase gate: Implement → Test → Run → Review → Fix → Commit; quality gates before report: Data → Statistical → Code → Model → Evidence → UnsupportedClaim → Report.
