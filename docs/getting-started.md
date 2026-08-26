# Getting Started

Three steps: install → run your first analysis → use the SDK, API, or dashboard.

## Prerequisites

- **Python ≥ 3.12** and [uv](https://astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node 20+** — only needed for the web dashboard

## 1. Install

```bash
uv sync --dev                     # from a clone of this repository
# or, for just the Python SDK:
pip install jack-data-science-agent
```

## 2. First analysis

```bash
# One-command demo: demo dataset → analysis → evidence → report
uv run dsa demo

# Or run it on your own CSV:
uv run dsa analyze examples/datasets/sales.csv --task "Does price predict revenue?"
```

Every result is evidence-grounded: each claim is linked to a specific tool call and
the `sha256` of the dataset it ran on. Output also includes a reproducibility bundle
(`reproduce.sh`, `analysis.ipynb`, `experiment.json`).

## 3. Use it as a library

```python
import asyncio
from data_science_agent import Agent

result = asyncio.run(Agent().analyze(
    "examples/datasets/sales.csv",
    "What drives revenue by region?",
))
print(result.report_markdown)  # prose + charts, every claim cited
print(result.evidence)         # Insight → Evidence → ToolCall → Dataset(hash)
```

## Run the API server

```bash
uv run uvicorn dsa_api.main:app --app-dir apps/api/src --port 8000

# upload a dataset, then create an analysis run
curl -F "file=@examples/datasets/sales.csv;type=text/csv" http://localhost:8000/api/v1/datasets/
curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"<DATASET_ID>","user_query":"Analyze revenue trends"}'
curl "http://localhost:8000/api/v1/analysis/<RUN_ID>/report?format=markdown"
curl -H "Accept: text/event-stream" "http://localhost:8000/api/v1/analysis/<RUN_ID>/events"
```

## Web dashboard

```bash
cd apps/web && npm ci --legacy-peer-deps && npm run dev   # :3000
```

## Docker

```bash
docker compose up                  # api :8000, web :3000
docker compose logs -f api
```

## Health

```bash
curl http://localhost:8000/health    # {status, details:{db,duckdb,polars,llm}, version}
curl http://localhost:8000/ready
curl http://localhost:8000/version
```

## Where to go next

- [Architecture](architecture.md) — agent graph, tool layer, storage, security boundary
- [Tools](tools.md) — the 18 typed tools
- [Statistics](statistics.md) — statistical methods and guardrails
- [Evidence](evidence.md) — how claims are traced to data
- [API](api.md) — REST endpoints
- [MCP](mcp.md) — MCP server over the same tool layer
- [Benchmark](benchmark.md) / [Evaluation](evaluation.md) — how the system is measured
- [Reproducibility](reproducibility.md) — reproduce any run
- [Research](research.md) — published results and gap analysis
- [Security](security.md) · [Contributing](contributing.md)