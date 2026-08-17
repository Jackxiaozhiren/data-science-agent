# Demo Question

Analyze correlation between price and revenue

Dataset: `benchmarks/v2/datasets/sales.csv` (copied to `demo/datasets/sales.csv`)

```bash
uv run dsa demo
# or via API:
# curl -F "file=@demo/datasets/sales.csv;type=text/csv" http://127.0.0.1:8000/api/v1/datasets/
# curl -X POST http://127.0.0.1:8000/api/v1/analysis/ -H 'Content-Type: application/json' -d '{"dataset_id":"<id>","user_query":"Analyze correlation between price and revenue"}'
```
