# Contributing

> See `CONTRIBUTING.md` for the repository-wide gated checklist.

## Prerequisites

- Python `3.12` + `uv`, Node `20` (web).

## Start with a focused contribution

If you want to learn the evaluation system without changing the agent runtime, [Contribute a Benchmark Task](benchmark-task-contribution.md) walks through one task end to end: catalog schema, measurable criteria, single-task execution, evidence checks, and dataset licensing.

If you want to learn the extension surface, [Build a Hello-World Plugin](plugin-walkthrough.md) provides an offline validate → install → discover → execute → evidence → remove example with an automated lifecycle test.

## Gate checklist (must pass before PR — mirrors `.github/workflows/ci.yml`;
`tests/test_ci_gate_integrity.py` pins the two together)

```bash
uv sync --dev
uv run python scripts/audit_facts.py --check
uv run python scripts/check_public_claims.py --require-released-tags
uv run ruff check packages apps/api tests src apps/jupyter scripts
uv run ruff format --check packages apps/api tests src apps/jupyter scripts
uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports
uv run pytest -q --cov --cov-report=term-missing
uv run python scripts/generate_sbom.py
uv run dsa --limit 5
uv run dsa demo
npm --prefix apps/web ci --legacy-peer-deps
npm --prefix apps/web audit --json > /tmp/npm-audit-web.json
uv run python scripts/check_npm_advisories.py /tmp/npm-audit-web.json
npm --prefix apps/web run build
docker compose config
uv run python -m mkdocs build --strict
```

CI also builds the API/Web Docker images and verifies the packaged `dsa` CLI inside the API image.

Keep `uv.lock` pinned, do not commit private datasets or credentials, and preserve the local-first deterministic path for ordinary regression work. Security guidance lives in `SECURITY.md`.

Versioned workstream history lives in `CHANGELOG.md`; research artifacts should preserve the path from raw inputs to scripts to published outputs.
