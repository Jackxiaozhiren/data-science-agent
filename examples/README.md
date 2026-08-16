# Examples

## Datasets

- `datasets/sales.csv` — 500 rows, region/category/price/units/revenue
- `datasets/titanic.csv` — 900 rows, pclass/sex/age/fare/survived (synthetic)

Full benchmark datasets: `benchmarks/ds-agent-benchmark/datasets/` (20 CSVs, 8,770 rows, 50 tasks — `uv run dsa --limit 50` → 50/50 @1.0)

## Analyses

`analyses/` — reserved for saved report exports (`report.md`, `experiment.json`, evidence_graph).
Reproducibility per-run: `artifacts/reports/<run_id>/` contains `report.md` (with `![chart]`), `experiment.json`, `reproduce.sh`, `analysis.ipynb` (executable: profile + per-tool cells + `run_analysis`).

## Health

```
GET /health → {status, details:{db,duckdb,polars,llm:{active,status}}, version}
GET /ready  (mirrors health)
```

## Try it

```bash
# Upload + analyze via API
curl -F "file=@examples/datasets/sales.csv;type=text/csv" http://localhost:8000/api/v1/datasets/
# -> {"id": "<dataset_id>", ...}

curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id": "<dataset_id>", "user_query": "Analyze correlation between price and revenue"}'

curl "http://localhost:8000/api/v1/analysis/<RUN_ID>/report?format=markdown"
curl -H "Accept: text/event-stream" "http://localhost:8000/api/v1/analysis/<RUN_ID>/events"

# Or via benchmark CLI
uv run dsa --limit 3
uv run dsa --limit 50
```
