# Demo Package — V3 W8 §46

> **One-Command Demo (§47) must run on a clean installation without developer-only paths, private datasets, or internal env.**

## Quick run

```bash
uv sync --dev
uv run dsa demo                          # → demo/runs/demo/{report.md, state.json, manifest.json}
# Alternative (API):
# uv run uvicorn dsa_api.main:app --reload --port 8000 --app-dir apps/api/src &
# curl -F "file=@demo/datasets/sales.csv;type=text/csv" http://127.0.0.1:8000/api/v1/datasets/
# curl -X POST http://127.0.0.1:8000/api/v1/analysis/ -H 'Content-Type: application/json' -d '{"dataset_id":"<id>","user_query":"Analyze correlation between price and revenue"}'
```

## Contents (§46)

```
demo/
├── datasets/      sales.csv (from benchmarks/v2/datasets/sales.csv, stable synthetic, seed 42)
├── questions/     demo-question.md  — the demo question
├── runs/demo/     generated on `dsa demo` → {report.md, state.json, manifest.json}
├── reports/       demo-report.md (copy of last run's report)
├── evidence/      state.json (evidence graph / tool trace snapshot)
├── screenshots/   (optional UI captures)
└── README.md
```

## Validation metrics (§42)

```bash
uv run dsa external-validation   # → InstallationMetrics JSON: python/node/platform, install_present, demo_pass, first_launch/benchmark/demo timings
```

Recorded on macOS `26.6.1 arm64` (this repo):

| Metric | Value |
|--------|-------|
| Cold Install Time | `time uv sync --dev` on a fresh clone (not measured here; see `docs/v3/EXTERNAL_VALIDATION.md`) |
| First Launch Time | `~20–100ms` (import + tool bootstrap) |
| Demo Execution Time | `~1.8s` single run (`4 tool_calls`, `1 insight`, `4 evidence`, report `true`) |
| Benchmark Setup Time | `~2ms` catalog load (50→100 tasks, seed 42) |

## Clean install policy (§39/41)

- Requires only: `git clone` → `uv sync --dev` → `uv run dsa demo`
- No private dataset, no API key, no internal path — local-first: `stub/small LLM` + `DuckDB + Polars` + `data/ + artifacts/` (`Cloud API Cost = $0`, §34)
- Tested: Linux (uv stub), macOS (Darwin `26.6`, this repo) — Windows not tested, documented as limitation (§41, `docs/v3/EXTERNAL_VALIDATION.md`)
