# Agent

## Roles
- **Planner** — heuristics over dataset path + column schema; no LLM required for MVP.
- **Data Scientist** — sequential tool executor (profile → stats → viz → model).
- **Critic** — evidence & assumption review (unsupported causal claims blocked, typed errors).
- **Reporter** — `report.md` + `experiment.json` + `reproduce.sh` + `analysis.ipynb` under `artifacts/reports/<run_id>/`.

## Graph
- MVP: sequential `run_analysis` in `packages/agent/src/dsa_agent/graph.py`. This is the engine every shipped surface uses.
- LangGraph variant in `langgraph_graph.py`: `run_analysis_langgraph` drives a `StateGraph` and
  falls back to the sequential engine when the graph cannot run or its state will not validate.
  `langgraph` is a hard dependency imported unconditionally, not an optional extra. **Nothing in
  `src/`, `apps/` or the public package APIs reaches this variant** — it is currently exercised only
  by `tests/unit/test_langgraph.py`, so treat it as unreleased rather than as a supported runtime.

## Evidence Contract
`Insight → Evidence → ToolCall → Dataset(hash)` — every written claim must carry at least one `Evidence` with `dataset_sha256`.
