# Contributing

> See `CONTRIBUTING.md` for the repository-wide gated checklist.

## Prerequisites

- Python `3.12` + `uv`, Node `20` (web).

## Start with a focused contribution

If you want to learn the evaluation system without changing the agent runtime, [Contribute a Benchmark Task](benchmark-task-contribution.md) walks through one task end to end: catalog schema, measurable criteria, single-task execution, evidence checks, and dataset licensing.

For plugin work, use the existing plugin issue/tutorial track rather than adding tool code directly to the benchmark.

## Gate checklist (must pass before PR)

```bash
uv sync --dev
uv run ruff check packages apps/api tests src apps/jupyter
uv run ruff format --check packages apps/api tests src apps/jupyter
uv run mypy packages apps/api src --ignore-missing-imports
uv run pytest -q
uv run python scripts/generate_sbom.py
uv run dsa --limit 5
uv run dsa demo
npm --prefix apps/web ci --legacy-peer-deps
npm --prefix apps/web audit --audit-level=high
npm --prefix apps/web run build
docker compose config
uv run python -m mkdocs build --strict
```

CI also builds the API/Web Docker images and verifies the packaged `dsa` CLI inside the API image.

Keep `uv.lock` pinned, do not commit private datasets or credentials, and preserve the local-first deterministic path for ordinary regression work. Security guidance lives in `SECURITY.md`.

Versioned workstream history lives in `CHANGELOG.md`; research artifacts should preserve the path from raw inputs to scripts to published outputs.
