# Contributing

See `ARCHITECTURE_FREEZE_V0.1.md` — phased, gate-controlled delivery. V3.0 workstreams in `DATA_SCIENCE_AGENT_V3_0.md` §7.

Before PR:

```bash
uv sync --dev
uv run ruff check packages apps/api tests
uv run ruff format --check packages apps/api tests
uv run mypy packages apps/api --ignore-missing-imports
uv run pytest -q
uv run dsa --limit 5
npm --prefix apps/web run build
docker compose config
```

Also verify (when touching relevant areas):

```bash
uv run dsa demo                         # W8 external validation (§40/47)
uv run dsa external-validation          # W8 §42 installation metrics
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 5  # W3 v2 smoke
```

PRs must keep: `uv.lock` pinned, no private dataset/credential, local-first path (`stub LLM` + `DuckDB/Polars`) runnable (`Cloud $0`).

Security: see `SECURITY.md`. Docs build must pass `uv run python -m mkdocs build --strict` (see `mkdocs.yml`).
