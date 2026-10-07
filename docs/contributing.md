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
uv lock --check
uv run python scripts/audit_facts.py --check
uv run python scripts/sync_vendor.py --check
uv run python scripts/check_npm_workspace_lock.py
uv run python scripts/check_public_claims.py --require-released-tags
uv run python scripts/find_orphan_reads.py --check
uv run ruff check packages apps/api tests src apps/jupyter scripts
uv run ruff format --check packages apps/api tests src apps/jupyter scripts
uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports
uv run pytest -q --cov --cov-report=term-missing
uv run dsa --limit 5 --out /tmp/ci-bench --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets
uv run dsa demo
npm --prefix apps/web ci --legacy-peer-deps
npm --prefix apps/web audit --json > /tmp/npm-audit-web.json
uv run python scripts/check_npm_advisories.py /tmp/npm-audit-web.json
npm --prefix apps/web run build
node apps/web/scripts/regression.mjs
uv run python scripts/generate_sbom.py && test -f release/sbom.json
docker compose config
uv run python -m mkdocs build --strict
```

`node apps/web/scripts/regression.mjs` boots `next start` itself and needs the build above plus
Playwright's browsers. CI also builds the API/Web Docker images and verifies the packaged `dsa` CLI
inside the API image; those are the only gated checks a contributor is not asked to reproduce, and
`tests/test_ci_gate_integrity.py` names each one with its reason rather than leaving it unclassified.

One command for the whole list: `scripts/run_gates.sh` (add `--list` to print the gate commands
without running them). `tests/test_command_surface.py` fails if that runner and `ci.yml` ever cover
different gates, and checks that every command the runner names is a real invocation in this tree --
which is what stops the list from becoming a second, smaller truth.

Run the list, do not sample it. `scripts/run_gates.sh` ends with `scripts/sync_vendor.py --check`, and a
format pass rewrites the sources the `_vendor` mirrors were copied from: mirror **after** formatting, and
let the check be the last thing before you commit. Skipping a gate because it is already red for someone
else's file removes the only thing that could catch yours -- `--check` names the drifted files now, so
read that list and compare it against what you do not own (§127.1 cost a red `main`).

Keep `uv.lock` pinned, do not commit private datasets or credentials, and preserve the local-first deterministic path for ordinary regression work. Security guidance lives in `SECURITY.md`.

Versioned workstream history lives in `CHANGELOG.md`; research artifacts should preserve the path from raw inputs to scripts to published outputs.
