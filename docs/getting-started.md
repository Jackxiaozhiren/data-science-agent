# Getting Started — V3 W10 §48

> Structure: `docs/getting-started.md` · `docs/architecture.md` (§49 Mermaid 7 diagrams) · `docs/agent-system.md` · `docs/evidence.md` · `docs/evaluation.md` · `docs/benchmark.md` (§50) · `docs/reproducibility.md` · `docs/security.md` · `docs/mcp.md` · `docs/research.md` / `research/V3_RESEARCH_REPORT.md` (§51) · `docs/contributing.md` — see `mkdocs.yml`.

## Prerequisites
- Python 3.12, `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Node 20 (web app only) — `npm --prefix apps/web run build` is part of the release gate (§59)

## Install & Run (local-first)

```bash
uv sync --dev
uv run uvicorn dsa_api.main:app --reload --port 8000 --app-dir apps/api/src  # API at :8000
cd apps/web && npm install --legacy-peer-deps && npm run dev                # Web at :3000
```

## Quick Smoke (no UI)

```bash
curl -F "file=@examples/datasets/sales.csv;type=text/csv" http://localhost:8000/api/v1/datasets/
curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id":"<DATASET_ID>","user_query":"Analyze revenue trends"}'
curl "http://localhost:8000/api/v1/analysis/<RUN_ID>/report?format=markdown"
curl -H "Accept: text/event-stream" "http://localhost:8000/api/v1/analysis/<RUN_ID>/events"
```

## Docker

```bash
docker compose up                    # api :8000, web :3000, healthcheck on api
docker compose logs -f api
```

## Benchmark

```bash
uv run dsa --help
uv run dsa --limit 3                 # writes benchmarks/ds-agent-benchmark/results/
```

## Health

```bash
curl http://localhost:8000/health    # {status, details:{db,duckdb,polars,llm}, version}
curl http://localhost:8000/ready
curl http://localhost:8000/version
```
