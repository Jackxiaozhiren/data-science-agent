# Examples

## Datasets

- `datasets/sales.csv` — 500 rows, region/category/price/units/revenue
- `datasets/titanic.csv` — 900 rows, pclass/sex/age/fare/survived (synthetic)

Full benchmark datasets: `benchmarks/ds-agent-benchmark/datasets/` (20 CSVs)

## Analyses

`analyses/` — reserved for saved report exports (`report.md`, `experiment.json`, evidence_graph).

## Try it

```bash
# Upload + analyze via API
curl -F file=@examples/datasets/sales.csv http://localhost:8000/api/v1/datasets/
# -> {"id": "<dataset_id>", ...}

curl -X POST http://localhost:8000/api/v1/analysis/ \
  -H 'Content-Type: application/json' \
  -d '{"dataset_id": "<dataset_id>", "user_query": "Analyze correlation between price and revenue"}'

# Or via benchmark CLI
uv run dsa --limit 3
```
