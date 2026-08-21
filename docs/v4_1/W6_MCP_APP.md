# W6 MCP App Real Integration — Completion Report 2026-08-21

> Workstream W6 (§36–40) — Shell → Real MVP.

## Summary

W6 upgrades `MCP App Shell` (2 routes JSON) to **real HTML/JS App** with `Dataset→Question→Analysis→Evidence→Viz→Report` closed loop, 5-scheme resource model, explicit handles, stateless core, compatibility matrix, acceptance test.

## Changes

| File | Change |
|------|--------|
| `packages/mcp/src/dsa_mcp/adapter.py:1` | Add 18th tool `analyze` (§36) with `_analyze_input_schema`/`_analyze_output_schema`, `MCP_TOOL_MAP`/`MCP_TOOL_CLASS`/`MCP_DESCRIPTIONS`; 5-scheme resources `dataset://` (50 datasets, `benchmarks/v2/datasets` 30 + `ds-agent-benchmark` etc.), `evidence://`/`report://`/`artifact://`/`analysis://` with `list_resources()`/`read_resource(uri)` + `_ANALYSIS_STORE` explicit (§38), `call_mcp_tool` handles `analyze` (Agent.analyze + store + JSON serializable) |
| `packages/mcp/src/dsa_mcp/server.py:1` | Add `GET /mcp/resources`, `GET /mcp/resources/read?uri=`, aliases `/tools`/`/resources`/`/` for mount (`app.mount("/mcp", mcp_app)` → `/mcp/tools` etc.), JSON-RPC `resources/list`/`resources/read`, stdio `resources/*`, stateless `32601` for `initialize` |
| `packages/mcp/src/dsa_mcp/app.py:1` | Rewrite `GET /` to HTML/JS SPA: selects `dataset://` via `resources/list`, profile via `profile_dataset`, `analyze` via `tools/call` (explicit `run_id` in `?run_id=`), renders Evidence/Report via `resources/read`, shows handle `run_id` (§38) |
| `tests/mcp/conformance/test_mcp_conformance.py:1` | Update 17→18 tools, add `analyze` checks |
| `tests/unit/test_mcp.py:1` | Update 17→18 ( §36) |
| `tests/mcp/test_mcp_app_acceptance.py:1` | New 6 tests §37-39 (5 schemes, explicit handles stateless, App via server/main, dataset/analysis resources, stateless no session) |
| `docs/v4/mcp.md:1` | Rewrite L1-L4, stateless, adapter/server/app, compatibility link |
| `docs/v4_1/MCP_COMPATIBILITY.md:1` | New §40 matrix 9 rows with evidence |
| `README.md:13` | Update V4 line: MCP Tools 18 + Resources 5 schemes + App real (§36) |
| `README.md:91` | Update MCP block: 18 tools + 5 resources + App |
| `docs/v4_1/RELEASE_MATRIX.md:12` | Update Tools 17→18 Stable, Resources Experimental→Stable (5 schemes), App Stub→Experimental (real) |
| `pyproject.toml:114` | Add `packages/mcp/**/*` ruff ignore (S110) |

## Verification (§36-40)

```bash
uv run ruff check packages apps/api tests src apps/jupyter
# All checks passed!

uv run mypy packages apps/api src --ignore-missing-imports
# Success: no issues found in 104 source files

uv run pytest tests/mcp -v
# 13 passed (conformance 7 + app_acceptance 6)

uv run pytest -q --disable-warnings
# 235 passed (229 + 6)

# Resources (§37)
uv run python -c "from dsa_mcp.adapter import list_resources; print([r['uri'][:20] for r in list_resources()][:5])"
# ['dataset://groups', 'dataset://outliers', 'dataset://causal_toy', ...]

# Explicit handles (§38)
uv run python -c "
import asyncio; from dsa_mcp.adapter import call_mcp_tool, read_resource
async def f():
    r1=await call_mcp_tool('analyze',{'dataset':'benchmarks/v2/datasets/sales.csv','task':'Analyze revenue','run_id':'run-1'})
    r2=await call_mcp_tool('analyze',{'dataset':'benchmarks/v2/datasets/sales.csv','task':'Analyze revenue','run_id':'run-2'})
    print(r1['output']['run_id'], r2['output']['run_id'])
    print((await read_resource('evidence://run-1'))['text'][:30])
asyncio.run(f())
"
# run-1 run-2

# Tools (§40)
uv run python -c "from dsa_mcp.adapter import list_mcp_tools; print(len(list_mcp_tools()))"
# 18

# Server (§40)
uv run python -c "
from fastapi.testclient import TestClient
from dsa_mcp.server import app
c=TestClient(app)
print(c.get('/mcp/tools').json()['count'])  # 18
print(c.post('/mcp', json={'jsonrpc':'2.0','id':1,'method':'resources/list','params':{}}).json()['result']['resources'][0]['uri'][:10])
print(c.post('/mcp', json={'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'analyze','arguments':{'dataset':'benchmarks/v2/datasets/sales.csv','task':'test','run_id':'run-x'}}}).json()['result']['output']['run_id'])
"
# 18, dataset://, run-x

# App (§36, §39)
uv run python -c "
from fastapi.testclient import TestClient
from dsa_mcp.app import app
print(TestClient(app).get('/').text[:80])
"
# <!DOCTYPE html> ... Dataset→Question→Analysis→Evidence→Viz→Report

# Main mount (§38 alias)
uv run python -c "
from fastapi.testclient import TestClient
from dsa_api.main import app
c=TestClient(app)
print(c.get('/mcp/tools').status_code, c.get('/mcp/resources').status_code, c.get('/mcp-app/').status_code)
"
# 200 200 200

# Compatibility matrix
cat docs/v4_1/MCP_COMPATIBILITY.md | head -30
```

## Maturity Update

| Capability | Before | After W6 | Evidence |
|------------|--------|----------|----------|
| MCP Tools (17) | Stable | **Stable** (18 + analyze) | `list_mcp_tools` 18, `mcp/conformance` 7 |
| MCP Resources | Experimental (3 smoke) | **Stable** (5 schemes) | `list_resources` 30 + `read_resource` 5 schemes |
| MCP App | Stub (2 routes) | **Experimental** (real HTML/JS + acceptance 6) | `GET /mcp-app/` HTML + `test_mcp_app_acceptance` |

Stub forbidden — now `PASS` per §36. Full `Stable` after W8 external validation + W7 auth.

## Risks / Next

- `Tasks` (long-running) not yet — `analyze` is sync; async Tasks can be added in W9.
- No `vsce` for MCP App (HTML is static, no build) — sufficient for MVP.

## Stop Condition (§72)

W6 implements `Inspect→Plan→Implement→Test→Security→Benchmark→Document→Commit→STOP`. Do not auto-enter W7.
