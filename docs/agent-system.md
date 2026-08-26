# Agent System

> `docs/agent.md` (roles + graph) + `docs/architecture.md` (Agent Graph Mermaid) + `research/V3_RESEARCH_REPORT.md` (RQ1–RQ5).

## Graph

`Planner → DataScientist → Critic → Report` (LangGraph `StateGraph`, `MemorySaver` checkpoints). Budgets `max_steps 20 / max_tool_calls 40 / max_retries 3`.

## Reliability (W5)

`4 configs` (`Single / Planner+Agent / Planner+Agent+Critic / Full Evidence-Grounded`) × `7` metrics + `Critic Benefit` + `Tool Selection Accuracy` + `Agent Efficiency` — see `docs/evaluation.md` and `research/V3_RESEARCH_REPORT.md` (ablation A–F).

## Failures

Taxonomy `F01–F15` (`packages/evidence/src/dsa_evidence/failure_taxonomy.py`), observability `Trace/Span` (`observability.py`), frontend `/failures`.
