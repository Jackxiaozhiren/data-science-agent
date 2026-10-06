#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
uv --project "$ROOT" run uvicorn dsa_api.main:app --reload --port 8000 --app-dir "$ROOT/apps/api/src" &
API_PID=$!
(cd "$ROOT/apps/web" && npm run dev) &
WEB_PID=$!
trap "kill $API_PID $WEB_PID 2>/dev/null || true" INT TERM
wait
