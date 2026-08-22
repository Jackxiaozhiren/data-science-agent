# External Blind Reproduction — V4.2 W5 §34-39

> **Blind reproduction** — Tester only gets: `repository + instructions + dataset references` (§36) — no developer working directory, cache, database, secrets, or developer-specific paths (§35).

## Instructions for Evaluator (Blind)

You are given:

- **Repository:** `https://github.com/Jackxiaozhiren/data-science-agent` (or `file://` clone for local blind test)
- **Instructions:** This README + `docs/getting-started.md` + `README.md` Quick Start
- **Dataset references:** `benchmarks/v2/datasets/*.csv` (included), `case-studies/*/README.md`

You must, **without** reading source code or asking developer, execute:

```bash
# 1. Install
uv sync --dev

# 2. Run
uv run dsa doctor --json
uv run dsa demo
uv run dsa --limit 1 --json   # benchmark smoke
uv run python -c "from data_science_agent import Agent; import asyncio; r=asyncio.run(Agent().analyze('benchmarks/v2/datasets/sales.csv','Analyze revenue')); print(r.status, len(r.evidence))"  # SDK
uv run dsa analyze benchmarks/v2/datasets/sales.csv --task "Analyze revenue" --json  # CLI
uv run dsa plugin list --json  # Plugin
uv run dsa mcp --json | head   # MCP
uv run python -c "import dsa_jupyter; print('jupyter ok')"  # Jupyter
uv run dsa benchmark --limit 1 --json  # Benchmark
# Case Study (CS01)
uv run python -c "from data_science_agent import Agent; r=Agent().analyze_sync('benchmarks/v2/datasets/sales.csv','Analyze revenue trends by region and category'); print(r.report_markdown[:100])"
```

Then report metrics (§38): `Install Success / Demo Success / SDK Success / CLI Success / Plugin Success / Case Study Success / Reproduction Success / Documentation Clarity / Time to First Success / Manual Intervention Count`

No `developer working directory / cache / database / secrets / developer-specific paths` (§35).

## Environments (§37)

At least 3 independent:

- **Evaluator A:** macOS (host, `macOS-26.6.2-arm64-arm-64bit`, Python 3.12.13, uv 0.11.7) — `file://` clone to `/tmp/dsa-external-a`
- **Evaluator B:** Linux (Docker `python:3.12-slim`, `docker run --rm -v $(pwd):/repo -w /repo`) — Container 1
- **Evaluator C:** Container (Docker `python:3.12-slim` fresh, no cache) — Container 2 (or `uv` fresh)

If Windows not supported, must document.

## Outputs

Each evaluator produces `reproduction/external/evaluator-{A,B,C}.json` with metrics and `logs/`; aggregated in `docs/v4_2/EXTERNAL_VALIDATION.md` (anonymous A/B/C, no fabricated identities per §39).

See `reproduction/external/run.sh` for automated blind run.
