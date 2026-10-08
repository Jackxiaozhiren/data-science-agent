#!/usr/bin/env bash
# Run the whole pre-PR gate set in one command (audit §121, Phase 4 target 6).
#
# Why this exists: CI runs 17 gate steps, `CONTRIBUTING.md` asks a contributor to copy 23 lines, and
# §113.5 recorded what the gap costs -- a locally-green claim built from a narrower list than the one
# CI runs. `tests/test_command_surface.py` compares this GATES array against `ci.yml` through the same
# derived classifier §120 introduced, so adding a gate to the workflow without adding it here reddens
# the suite. The commands are written out literally rather than extracted from the YAML at run time:
# a reader should see exactly what executes, and nothing here evaluates workflow text.
#
#   scripts/run_gates.sh          run setup, then every gate, report each exit code
#   scripts/run_gates.sh --list   print the gate commands and exit 0 without running anything
set -uo pipefail

cd "$(dirname "$0")/.." || exit 9

SETUP=(
  "uv sync --dev"
  "npm --prefix apps/web ci --legacy-peer-deps"
  "npm --prefix apps/web audit --json > /tmp/npm-audit-web.json || true"
)

GATES=(
  "uv lock --check"
  "uv run python scripts/audit_facts.py --check"
  "uv run python scripts/sync_vendor.py --check"
  "uv run python scripts/check_npm_workspace_lock.py"
  "uv run ruff check packages apps/api tests src apps/jupyter scripts"
  "uv run ruff format --check packages apps/api tests src apps/jupyter scripts"
  "uv run mypy packages apps/api src apps/jupyter --ignore-missing-imports"
  "uv run pytest -q --cov --cov-report=term-missing"
  "uv run python scripts/check_public_claims.py --require-released-tags"
  "uv run python scripts/find_orphan_reads.py --check"
  "uv run dsa --limit 5 --out /tmp/ci-bench --catalog benchmarks/ds-agent-benchmark/catalog.json --datasets benchmarks/ds-agent-benchmark/datasets"
  "npm --prefix apps/web run build"
  "node apps/web/scripts/regression.mjs"
  "uv run python scripts/check_npm_advisories.py /tmp/npm-audit-web.json"
  "uv run python scripts/generate_sbom.py --check"
  "docker compose config"
  "uv run python -m mkdocs build --strict"
)

if [[ "${1:-}" == "--list" ]]; then
  printf '%s\n' "${GATES[@]}"
  exit 0
fi

for cmd in "${SETUP[@]}"; do
  printf '\n=== setup: %s\n' "$cmd"
  if ! bash -c "$cmd"; then
    printf 'SETUP FAILED: %s -- the gates below need this to succeed\n' "$cmd" >&2
    exit 1
  fi
done

failed=()
for cmd in "${GATES[@]}"; do
  printf '\n=== gate: %s\n' "$cmd"
  bash -c "$cmd"
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    failed+=("$cmd")
    # `$?` inside `if ! bash -c ...` is the status of the negated test, which is 0; the code has to
    # be read from the command itself, or the runner reports "FAILED (exit 0)" -- §113.5's habit of
    # quoting a status that was never the gate's, in shell form.
    printf 'FAILED (exit %d): %s\n' "$rc" "$cmd" >&2
  fi
done

printf '\n%d gate(s) run, %d failed.\n' "${#GATES[@]}" "${#failed[@]}"
for cmd in "${failed[@]}"; do
  printf '  - %s\n' "$cmd"
done
[[ "${#failed[@]}" -eq 0 ]] || exit 1
