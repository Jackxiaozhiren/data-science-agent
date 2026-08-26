# Contributing

> Phased, gate-controlled delivery — each release lands only when its gates (tests, mypy, ruff, docs build, `dsa verify-release`) pass. See [`CHANGELOG.md`](./CHANGELOG.md) for the release history and [`docs/contributing.md`](docs/contributing.md) for conventions.

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
uv run dsa demo                         # external validation smoke
uv run dsa external-validation          # installation metrics
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 5  # benchmark smoke
```

PRs must keep: `uv.lock` pinned, no private dataset/credential, local-first path (`stub LLM` + `DuckDB/Polars`) runnable (`Cloud $0`).

Security: see `SECURITY.md`. Docs build must pass `uv run python -m mkdocs build --strict` (see `mkdocs.yml`).
