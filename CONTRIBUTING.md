# Contributing

> Phased, gate-controlled delivery — each release lands only when its gates (tests, mypy, ruff, docs build, `dsa verify-release`) pass. See [`CHANGELOG.md`](./CHANGELOG.md) for the release history and [`docs/contributing.md`](docs/contributing.md) for conventions.

Before PR — these mirror `.github/workflows/ci.yml` verbatim, and
`tests/test_ci_gate_integrity.py` fails if the two ever drift apart:

```bash
uv sync --dev
uv lock --check                                  # §46 dependency pinning
uv run python scripts/audit_facts.py --check
uv run python scripts/sync_vendor.py --check     # vendored dsa_* must match source
uv run python scripts/check_npm_workspace_lock.py
uv run python scripts/check_public_claims.py --require-released-tags
uv run python scripts/find_orphan_reads.py --check
uv run ruff check packages apps/api tests src apps/jupyter scripts
uv run ruff format --check packages apps/api tests src apps/jupyter scripts
uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports
uv run pytest -q --cov --cov-report=term-missing
uv run dsa --limit 5 --out /tmp/ci-bench --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets
npm --prefix apps/web ci --legacy-peer-deps       # installs what the two lines below consume
npm --prefix apps/web audit --json > /tmp/npm-audit-web.json
uv run python scripts/check_npm_advisories.py /tmp/npm-audit-web.json
npm --prefix apps/web run build
node apps/web/scripts/regression.mjs             # boots `next start`, tours every static route
uv run python scripts/generate_sbom.py && test -f release/sbom.json   # §47 SBOM
docker compose config
uv run python -m mkdocs build --strict
```

`node apps/web/scripts/regression.mjs` needs the build above and Playwright's browsers; CI hosts
the Docker image builds and the packaged-CLI smoke inside them, which are not on this list.

One command for the whole list: `scripts/run_gates.sh` (add `--list` to print the gate commands
without running them). `tests/test_command_surface.py` fails if that runner and `ci.yml` ever
cover different gates, which is what keeps this list from becoming a second, smaller truth.

Run the list, do not sample it. `scripts/run_gates.sh` ends with `scripts/sync_vendor.py --check`, and
a format pass rewrites the sources the `_vendor` mirrors were copied from: mirror **after** formatting,
and let the check be the last thing before you commit. Skipping a gate because it is already red for
someone else's file removes the only thing that could catch yours -- `--check` names the drifted files
now, so read that list and compare it against what you do not own (§127.1 cost a red `main`).

Also verify (when touching relevant areas):

```bash
uv run dsa demo                         # external validation smoke
uv run dsa external-validation          # installation metrics
uv run dsa --catalog benchmarks/v2/catalog.json --datasets benchmarks/v2/datasets --limit 5  # benchmark smoke
```

PRs must keep: `uv.lock` pinned, no private dataset/credential, local-first path (`stub LLM` + `DuckDB/Polars`) runnable (`Cloud $0`).

Security: see `SECURITY.md`. Docs build must pass `uv run python -m mkdocs build --strict` (see `mkdocs.yml`).
