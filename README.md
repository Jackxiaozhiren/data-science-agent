# Data Science Agent — v2.0.0-alpha.1 (Research Grade)

> **An Evidence-Grounded Autonomous Data Science System.**
> Turn natural-language questions into reproducible statistical analysis, machine learning experiments, visualizations, and research reports.
> V2 adds: Evaluation Framework · Scientific Benchmark v2 (30 datasets / 100 tasks) · Reliability & Reproducibility · Failure Analysis · Observability · MCP 2026-07-28 Stateless · Security Hardening · Research Package.

## Documentation

Docs: [Getting Started](./docs/getting-started.md) · [Agent](./docs/agent.md) · [Tools](./docs/tools.md) · [Evidence](./docs/evidence.md) · [API](./docs/api.md) · [MCP](./docs/MCP_DESIGN.md) · [Frontend IA](./docs/FRONTEND_IA.md) · [Research](./docs/research.md) · [Changelog](./CHANGELOG.md)
V2: [Baseline Report](./docs/v2/Baseline%20Report.md) · [Evaluation](./docs/v2/evaluation.md) · [MCP 2026-07-28](./docs/v2/MCP_2026_Audit.md) · [Security (W9)](./docs/v2/security.md) · [Benchmark v2](./benchmarks/v2/README.md) · Benchmark baseline: [benchmarks/baseline](./benchmarks/baseline/README.md)
MkDocs: `uv run mkdocs serve` / `uv run mkdocs build --strict` (see [mkdocs.yml](./mkdocs.yml)) — Architecture Freeze at [ARCHITECTURE_FREEZE_V0.1.md](./ARCHITECTURE_FREEZE_V0.1.md)

## Stack

Next.js 15 + TypeScript + Tailwind + shadcn/ui · FastAPI + Pydantic v2 + SQLAlchemy · LangGraph · DuckDB + Polars + PyArrow · SQLite · LLM Abstraction (OpenAI/Anthropic/Google/OpenRouter/Ollama) · Scikit-learn + SciPy + Matplotlib

## Quick Start

```bash
# Python
uv sync --dev
uv run pytest -q          # ~86+ tests
uv run ruff check .
uv run mypy packages apps/api --ignore-missing-imports  # 81 source files clean

# API (port 8000) — local-first, no cloud required
uv run uvicorn dsa_api.main:app --reload --port 8000 --app-dir apps/api/src

# Web (port 3000)
cd apps/web && npm install --legacy-peer-deps && npm run dev
# Build — V2: 13 routes (/benchmarks /evaluations /runs /runs/[id] /runs/[id]/replay /failures /research /mcp)
npm run build --workspace=dsa-web  # 13 routes green

# Benchmark v1 (20 datasets / 50 tasks) — frozen baseline: benchmarks/baseline — 50/50 @1.0
# Benchmark v2 (30 datasets / 100 tasks) — benchmarks/v2 (Evaluation Framework + Evidence Validation)
uv run dsa --help
uv run dsa --limit 3
uv run dsa --limit 50
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 50 --out /tmp/v2-bench
```

## Demo (One-Command Smoke)

```bash
# Start API
uv run uvicorn dsa_api.main:app --host 127.0.0.1 --port 8000 --app-dir apps/api/src &

# Upload sales.csv (note: explicit MIME needed with curl)
curl -F "file=@examples/datasets/sales.csv;type=text/csv" http://127.0.0.1:8000/api/v1/datasets/
# -> {"id": "<dataset_id>", "rows": 500, "cols": 6, ...}

# Run analysis (numeric correlation + evidence)
curl -X POST http://127.0.0.1:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id": "<dataset_id>", "user_query": "Analyze correlation between price and revenue"}'
# -> {"id": "run-...", "status": "COMPLETED", "state": {"evidence": [...], "report_markdown": "..."}}

# Check report and SSE trace
curl http://127.0.0.1:8000/api/v1/analysis/<run_id>/report?format=markdown
curl -H "Accept: text/event-stream" http://127.0.0.1:8000/api/v1/analysis/<run_id>/events

# Or via frontend: http://localhost:3000/datasets -> upload -> Analyze -> trace
```

## API

```
POST /api/v1/datasets/              upload (multipart, 100MB, MIME sniff, traversal block)
GET  /api/v1/datasets/{id}          profile + metadata
POST /api/v1/analysis/              {dataset_id, user_query} -> run_id (Agent graph)
GET  /api/v1/analysis/{id}          AnalysisState (polling)
GET  /api/v1/analysis/{id}/events   SSE: agent/tool/validation/report/completed (JSON fallback via Accept)
GET  /api/v1/analysis/{id}/progress progress_pct + counts
GET  /api/v1/analysis/{id}/report   ?format=json|markdown
GET  /api/v1/analysis/{id}/artifacts artifacts + tool_calls + progress
GET  /api/v1/analysis/{id}/evidence/{evidence_id}  evidence → tool_call → insights → dataset trace
POST /api/v1/analysis/{id}/approve  HUMAN_REVIEW approval (HITL)
GET  /health  GET /ready  GET /version  GET /

MCP (adapter over Tool Layer, stateless 2026-07-28):
  GET  /mcp/tools  POST /mcp/call  POST /mcp (JSON-RPC: initialize/tools/list/tools/call)
  Tools: 17 — profile_dataset, inspect_dataset, query_dataset, run_sql, run_python,
         run_statistical_test, correlation_analysis, train_model, evaluate_model,
         create_visualization, get_evidence, generate_report, save_artifact,
         forecast, assumption_check, feature_importance, causal_check — see docs/MCP_DESIGN.md
```

## Frontend

```
 /              Dashboard (recent analyses)
 /datasets      Upload + list (drag-drop, 100MB guard)
 /datasets/[id] Profile (schema, missing, duplicates, cardinality)
 /analysis      Workspace (select dataset + natural language task)
 /analysis/[runId]  Trace (plan/tool calls/evidence/insights/validation/artifacts/report + evidence graph)
 /reports       Reports index
```

## Evidence & Reproducibility

Every important claim traces to executable computation:

```
Insight → Evidence → ToolCall → Dataset (hash)
```

Artifacts under `artifacts/reports/<runId>/`: `report.md` (with `![chart]` embeds), `experiment.json`, `reproduce.sh`, `analysis.ipynb` (executable cells: profile + per-tool + `run_analysis`), `evidence_graph.json`.
`uv run mkdocs serve` / `build --strict` · health: `GET /health → {status, details:{db,duckdb,polars,llm:{active,status}}, version}` + `GET /ready`.

## Benchmark

```
benchmarks/ds-agent-benchmark/
  datasets/   20 synthetic CSVs (seed 42, 8,770 rows)
  catalog.json  50 tasks (EDA 8 / SQL 7 / Statistics 8 / Regression 6 / Classification 6 / Time Series 5 / Visualization 5 / Data Quality 5)
  results/    (generated via dsa benchmark)
```

```bash
uv run dsa --limit 3 --out /tmp/bench
cat benchmarks/ds-agent-benchmark/catalog.json | jq '.tasks | length'  # 50
```

Metrics: Task Success Rate, Statistical Accuracy, SQL Accuracy, Code Execution Success, Evidence Coverage, Unsupported Claim Rate, Mean Latency, By-Category breakdown.

## Security Boundary

File (MIME sniff + archive bomb guard), SQL (read-only allowlist + row limit), Python (AST allowlist + _safe_import, introspection block), Prompt Injection (dataset UNTRUSTED DATA, detection), Output (unsupported causal claim rewrite), Resource limits (tool call budget), HITL approval.

## Project Structure

```
data-science-agent/ (monorepo)
  apps/api   FastAPI
  apps/web   Next.js 15
  packages/agent, tools, execution, statistics, ml, visualization, evidence, reports, datasets, llm, mcp, evaluation
  benchmarks/ds-agent-benchmark
  tests/unit, integration, security
  docs/
```

## Development Roadmap

Phase 0 Architecture Freeze ✓  Phase 1 Scaffold ✓  Phase 2 Data Layer ✓  Phase 3 Tool Layer ✓  Phase 4 Agent Graph ✓  Phase 5 Evidence ✓  Phase 6 API ✓  Phase 7 Frontend ✓  Phase 8 Security ✓  Phase 9 Benchmark ✓  Phase 10 MCP ✓  Phase 11 Docs ✓

## Testing

```bash
uv run pytest -q           # ~86+ tests (unit + integration + security)
uv run pytest --cov --cov-report=term-missing  # 74% cov
uv run mypy packages apps/api --ignore-missing-imports  # strict, 81 files clean
uv run ruff check .
docker compose config && npm run build --workspace=dsa-web  # compose healthcheck + 7 routes
uv run dsa --limit 50      # 50/50 @1.0
```

## Docker

```bash
docker compose up  # api :8000, web :3000
```

## Contributing / Security

See [CONTRIBUTING.md](./CONTRIBUTING.md) · [SECURITY.md](./SECURITY.md) · [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) · [LICENSE](./LICENSE) (MIT)
