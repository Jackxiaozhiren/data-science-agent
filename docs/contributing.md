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
uv lock --check
uv sync --dev
uv run python scripts/audit_facts.py --check
uv run python scripts/sync_vendor.py --check
uv run python scripts/check_npm_workspace_lock.py
uv run python scripts/check_public_claims.py --require-released-tags
uv run python scripts/find_orphan_reads.py --check
uv run python scripts/check_ledger_identifiers.py --check
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
node apps/web/scripts/locale-chrome-inventory.mjs
bash scripts/run_web_live_gates.sh
uv run python scripts/generate_sbom.py --check   # §47 SBOM, §139: compares, writes nothing
docker compose config
uv run python -m mkdocs build --strict
```

`node apps/web/scripts/regression.mjs` boots `next start` itself and needs the build above plus
Playwright's browsers. `bash scripts/run_web_live_gates.sh` boots its own throwaway stack -- an API on a
temporary SQLite file in heuristic mode, then the built web app on a scratch port -- and runs each of its
instruments against that one stack: `inspector-a11y.mjs` (every disclosure in a run's report opens on Enter, every
focus stop shows a ring), `locale-chrome-acceptance.mjs` (every interface-owned region on the routes it loads speaks
the reader's language, including the run page's validation card, whose labels sit in `main li strong` and so are
outside the selector the offline routes are examined with), and `mcp-app-page.mjs` (the page an MCP client opens
actually runs its own script: the dataset list it renders is the list its server publishes, the run button drives a
real analysis to completion, the resource read fills card 6 without raising a dialog, and the report it embeds
arrives styled -- `h1` computed at 24px, the value the report's own CSS gives -- with its drill-downs). The static
tour has no backend on purpose, so on `/analysis` it
finds nothing to open and no card to read. The runner refuses, rather than skipping, when port 8000 is taken: the
web bundle resolves the API origin at build time, so a different port would measure a page that cannot reach its
own backend. Every instrument needs
`npx playwright install --with-deps chromium` in `apps/web`. CI also builds the API/Web Docker images and
verifies the packaged `dsa` CLI inside the API image; those are the only gated checks a contributor is not
asked to reproduce, and `tests/test_ci_gate_integrity.py` names each one with its reason rather than leaving
it unclassified.

One command for the whole list: `scripts/run_gates.sh` (add `--list` to print the gate commands
without running them). `tests/test_command_surface.py` fails if that runner and `ci.yml` ever cover
different gates, and checks that every command the runner names is a real invocation in this tree --
which is what stops the list from becoming a second, smaller truth.

Run the list, do not sample it. `scripts/run_gates.sh` runs `scripts/sync_vendor.py --check` third -- before its
own `ruff format --check`, and a format pass rewrites the sources the `_vendor` mirrors were copied from: mirror
**after** formatting, and re-run that check before you commit, because the one in the list has already passed by
then. Skipping a gate because it is already red for someone
else's file removes the only thing that could catch yours -- `--check` names the drifted files now, so
read that list and compare it against what you do not own (§127.1 cost a red `main`).

Keep `uv.lock` pinned, do not commit private datasets or credentials, and preserve the local-first deterministic path for ordinary regression work. Security guidance lives in `SECURITY.md`.

Versioned workstream history lives in `CHANGELOG.md`; research artifacts should preserve the path from raw inputs to scripts to published outputs.
