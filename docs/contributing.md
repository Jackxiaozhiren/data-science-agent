# Contributing

> See `CONTRIBUTING.md` (gated checklist) — phased, gate-controlled delivery.

## Prerequisites

- Python `3.12` + `uv`, Node `20` (web).

## Gate checklist (must pass before PR)

```bash
uv sync --dev
uv run ruff check packages apps/api tests
uv run ruff format --check packages apps/api tests
uv run mypy packages apps/api --ignore-missing-imports
uv run pytest -q
uv run pytest --cov   # 81% gate
uv run dsa --limit 5
uv run dsa demo                  # one-command demo (§40/47)
uv run dsa external-validation   # install metrics (§42)
npm --prefix apps/web run build  # 13/13 routes
docker compose config            # valid
# optional: uv run python -m mkdocs build --strict  (see mkdocs.yml; W10 docs strict has pre-existing strict warnings outside reval scope)
```

Keep `uv.lock` pinned, no private dataset/credential, local-first (`stub LLM + DuckDB/Polars`, `Cloud $0`). Security: see `SECURITY.md`.

Versioned workstream history lives in `CHANGELOG.md`; research packaging in `research/V3_RESEARCH_REPORT.md` (reports keep provenance: raw → script → artifact).
