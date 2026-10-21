#!/usr/bin/env bash
# The two live web gates, runnable as one command anywhere -- including inside the gate mirror.
#
# Why this file exists: two instruments measure things that only exist on a live, seeded run --
# `inspector-a11y.mjs` needs a disclosure to open on Enter and focus stops to show a ring; the run-page half of
# `locale-chrome-acceptance.mjs` needs the validation card to be mounted, and its labels live in `main li strong`,
# outside the selector the offline routes are checked with. The static tour (`regression.mjs`) runs with no backend
# on purpose, so on `/analysis` it finds nothing to open and no card to read, and reports zero truthfully. An
# instrument that needs a stack and is invoked without one either fails forever or gets skipped, and
# skipped-without-a-stack is a gate that passes by doing nothing.
# `scripts/run_gates.sh` and CI must run the *same* command (audit §113.5: a locally-green claim built from a
# narrower list than CI runs is the failure this repo keeps paying for), so the lifecycle lives here rather
# than being duplicated between a workflow and a contributor's shell.
#
# Ports are not free choices. The web bundle resolves the API origin at build time (`apps/web/lib/api.ts`,
# default `http://localhost:8000`), so the API has to answer on 8000 for the page to reach it; the web server
# gets a scratch port. A taken 8000 is a refusal, never a silent skip -- a gate that cannot fail is not a gate.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 9

API_PORT=${DSA_A11Y_API_PORT:-8000}
WEB_PORT=${DSA_A11Y_WEB_PORT:-3399}
API=http://127.0.0.1:${API_PORT}
WEB=http://127.0.0.1:${WEB_PORT}
WORK=$(mktemp -d)
PIDS=()

cleanup() {
  # The port is the source of truth, not `$!`: `uv run` does not forward SIGTERM to the process it spawns and
  # `next start` execs a server child, so killing the recorded pid leaves a listener that would become the next
  # run's phantom red. Guarded on the count because macOS bash 3.2 errors on an empty-array expansion under
  # `set -u`, and this runs on every exit path including the refusals that start nothing.
  if ((${#PIDS[@]})); then
    for pid in "${PIDS[@]}"; do
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true # reaped here, so the shell reports no "Terminated" line in a passing gate's log
    done
  fi
  for _ in 1 2 3 4 5 6 7 8; do
    local holders
    holders="$(listening "$API_PORT")$(listening "$WEB_PORT")"
    [[ -z "$holders" ]] && break
    for pid in $holders; do
      kill "$pid" 2>/dev/null || true
    done
    sleep 0.5
    holders="$(listening "$API_PORT")$(listening "$WEB_PORT")"
    [[ -z "$holders" ]] && break
    for pid in $holders; do
      kill -9 "$pid" 2>/dev/null || true
    done
    sleep 0.5
  done
  local left
  left="$(listening "$API_PORT")$(listening "$WEB_PORT")"
  rm -rf "$WORK"
  # Leaving a listener behind has to be the run's verdict, so this exits from inside the trap rather than only
  # printing.
  if [[ -n "$left" ]]; then
    echo "TEARDOWN INCOMPLETE: still listening -> ${left}" >&2
    exit 3
  fi
}

listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN -t 2>/dev/null | tr '\n' ' '
}

fail() {
  echo "LIVE_GATES_REFUSED: $*" >&2
  exit 1
}

# The browser cookie inside the instrument is bound to 127.0.0.1, so the web address is not negotiable either.
if [[ -n "$(listening "$API_PORT")" ]]; then
  fail "port ${API_PORT} is already serving -- the page's baked API origin points there, so stop whatever holds it (DSA_A11Y_API_PORT only helps if you also rebuild apps/web)"
fi
if [[ -n "$(listening "$WEB_PORT")" ]]; then
  fail "port ${WEB_PORT} is already serving (DSA_A11Y_WEB_PORT picks another)"
fi

# CI builds before this runs; a contributor's fresh clone has not. Building here keeps the gate self-contained
# instead of skipping when the artifact is missing -- which would be a gate that passes by doing nothing.
if [[ ! -f apps/web/.next/BUILD_ID ]]; then
  echo "no apps/web/.next/BUILD_ID -- building the web app (first run is slow)"
  npm --prefix apps/web run build >"$WORK/build.log" 2>&1 || {
    tail -n 12 "$WORK/build.log" >&2
    fail "web build failed; see the tail above"
  }
fi

command -v uv >/dev/null 2>&1 || fail "uv is not on PATH -- the gate mirror's setup step needs it"

# Three causes, three answers. `apps/web/scripts/browser-state.mjs` resolves Playwright from its own directory --
# the same directory the instruments resolve from -- so this cannot disagree with them the way a cwd-dependent probe
# did: in CI's `ci` job, which installs apps/web and apps/vscode but never a root node_modules, a root-context probe
# could not resolve the package and refused for a reason that was not true. A gate that refuses for the wrong reason
# gets deleted instead of fixed, so the remedy each state names is different.
BROWSER_STATE=$(node apps/web/scripts/browser-state.mjs 2>/dev/null)
if [[ "$BROWSER_STATE" == "UNRESOLVABLE" ]]; then
  fail "playwright is not installed in apps/web (run \`npm --prefix apps/web ci --legacy-peer-deps\`)"
fi
if [[ "$BROWSER_STATE" != "INSTALLED" ]]; then
  fail "Playwright's chromium browser is missing (run \`cd apps/web && npx playwright install --with-deps chromium\`)"
fi

# Installed before the first process: a failure on the way up must still tear the stack down, or this script
# becomes the thing that leaves a listener on port 8000 for the next run to blame.
trap cleanup EXIT

export DSA_DATABASE_URL="sqlite+aiosqlite:///${WORK}/demo.db"
export DSA_ARTIFACT_ROOT="${WORK}/artifacts"
export DSA_LLM_MODE=heuristic # no provider, no spend: the example runs are seeded with the stub engine
export DSA_DEMO_SEEDING=on
export DSA_CORS_ORIGINS="http://127.0.0.1:${WEB_PORT},http://localhost:${WEB_PORT}"

# `--frozen` because a bare `uv run` re-resolves and rewrites uv.lock in the tree it runs from, which would make
# this gate dirty the repository it is measuring.
uv run --frozen uvicorn dsa_api.main:app --app-dir apps/api/src --host 127.0.0.1 --port "$API_PORT" >"$WORK/api.log" 2>&1 &
PIDS+=("$!")

for _ in $(seq 1 60); do
  curl -sf --max-time 2 "${API}/health" >/dev/null && break
  kill -0 "${PIDS[0]}" 2>/dev/null || {
    tail -n 12 "$WORK/api.log" >&2
    fail "the API process exited during startup"
  }
  sleep 1
done
curl -sf --max-time 2 "${API}/health" >/dev/null || {
  tail -n 12 "$WORK/api.log" >&2
  fail "no /health after 60s"
}

# Boot seeding schedules the example runs rather than completing them inline, so wait for one to land: the
# instrument takes the first row and needs a finished run's report to have disclosures to operate.
SEEN=""
for _ in $(seq 1 120); do
  SEEN=$(curl -sf --max-time 5 -H 'X-DSA-Owner: a11y-acceptance' "${API}/api/v1/analysis/" |
    python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
rows = d.get("analyses") if isinstance(d, dict) else d
rows = rows or []
done = [r for r in rows if (r or {}).get("status") == "COMPLETED" and (r or {}).get("state")]
print(done[0]["id"] if done else "")' 2>/dev/null)
  [[ -n "$SEEN" ]] && break
  sleep 1
done
[[ -n "$SEEN" ]] || fail "no COMPLETED seeded run after 120s -- the keyboard gate has nothing to open"

(cd apps/web && npx next start -p "$WEB_PORT") >"$WORK/web.log" 2>&1 &
WEB_PID=$!
PIDS+=("$WEB_PID")

READY=no
for _ in $(seq 1 60); do
  if curl -sf --max-time 3 "${WEB}/" >/dev/null; then
    READY=yes
    break
  fi
  kill -0 "$WEB_PID" 2>/dev/null || {
    tail -n 12 "$WORK/web.log" >&2
    fail "the web server exited before it served a page"
  }
  sleep 1
done
[[ "$READY" == yes ]] || {
  tail -n 12 "$WORK/web.log" >&2
  fail "no page from ${WEB} after 60s"
}

echo "seeded run ${SEEN}; stack up: ${WEB} against ${API}"
# Two instruments, one stack. Both need a live seeded run and both were manual until now: the keyboard gate owns
# "a disclosure opens on Enter", the chrome acceptance owns "every region the interface speaks is in the reader's
# language" -- including the validation card, whose labels sit in `main li strong` and are therefore outside the
# static selector the offline routes are checked with.
STATUS=0
for instrument in inspector-a11y.mjs locale-chrome-acceptance.mjs; do
  printf '\n=== %s\n' "$instrument"
  R13I_WEB="$WEB" R13I_API="$API" node "apps/web/scripts/${instrument}" || STATUS=1
done
if [[ "$STATUS" -eq 0 ]]; then
  echo "WEB_LIVE_GATES_PASS -- both instruments green on one booted stack"
else
  echo "WEB_LIVE_GATES_FAIL -- at least one instrument failed (see its section above)" >&2
fi
exit "$STATUS"
