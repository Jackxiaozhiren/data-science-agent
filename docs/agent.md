# Agent

## Roles
- **Planner** — heuristics over dataset path + column schema; no LLM required for MVP.
- **Data Scientist** — sequential tool executor (profile → stats → viz → model).
- **Critic** — evidence & assumption review (unsupported causal claims blocked, typed errors).
- **Reporter** — `report.md` + `experiment.json` + `reproduce.sh` + `analysis.ipynb` under `artifacts/reports/<run_id>/`.

## Graph
- MVP: sequential `run_analysis` in `packages/agent/src/dsa_agent/graph.py`.
- LangGraph extension in `langgraph_graph.py` — `analyze_graph` imports `langgraph.graph.StateGraph` when available, falls back to MVP path.

## Evidence Contract
`Insight → Evidence → ToolCall → Dataset(hash)` — every written claim must carry at least one `Evidence` with `dataset_sha256`.
