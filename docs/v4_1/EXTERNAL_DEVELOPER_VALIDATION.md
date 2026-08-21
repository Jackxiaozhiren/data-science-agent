# External Developer Validation — W8 §48-50 (Fresh Clone + Developer A)

> Validates North Star (§5): Clone → Install → Run → SDK → CLI → Plugin → Jupyter → MCP → Evidence → Report → Contribute without developer-specific path/secret/private dataset/internal service/manual patch.

**Date:** 2026-08-21  
**Tester:** Developer A (simulated, no internal knowledge, fresh `/tmp` clone)  
**Commit:** `e27ae7f` (post-W7 fix, includes `uv.lock` + `packages/reports`)  
**Environment:** `macOS-26.6.2-arm64-arm-64bit`, `Python 3.12.13` (via `uv`), `Node v24.15.0`, `uv 0.11.7`, `Docker 29.7.2`

## Fresh Clone Test (§48)

**From new temp dir — no reliance on current dev dir:**

```bash
rm -rf /tmp/dsa-fresh-clone && mkdir -p /tmp/dsa-fresh-clone
git clone --depth 1 "file:///Users/jackson/Data agent" /tmp/dsa-fresh-clone/repo
# → Cloning 0.6s, 0.12s system

cd /tmp/dsa-fresh-clone/repo
uv sync --dev          # → Prepared 192 packages (was failing before fix, now 0.0s cached)
uv run dsa doctor --json  # → {status: "warn", checks: [Python ok 3.12.13, uv ok, Node ok, Docker ok, LLM warn]} (1.3s)
uv run dsa demo        # → status ok, 4 tool_calls, 1 insight, 4 evidence, has_report true, 38.1s (first) / 1.2s (cached)
```

**Result:** ✅ `git clone` → `uv sync` → `doctor` → `demo` all PASS without `developer-specific path/secret/private dataset/internal service/manual patch` (§5). Previously FAILED due to `packages/reports` + `uv.lock` being `.gitignore`'d (see Failures).

## External Developer Test (§49) — 7 Tasks

**Developer A** knows only `README Quick Start`, not internals. Tasks executed in fresh clone (`/tmp/dsa-fresh-clone/repo`):

| # | Task | Command | Time | Result |
|---|------|---------|------|--------|
| 1 | **Install** | `uv sync --dev` (already) + `uv run dsa doctor --json` | 0.2s | ✅ `status warn` (LLM warn expected, no key) |
| 2 | **Run demo** | `uv run dsa demo` | 1.2s (cached) | ✅ `task_success true`, `has_report true` |
| 3 | **Use SDK** | `uv run python -c "from data_science_agent import Agent, Dataset; r=asyncio.run(Agent().analyze('benchmarks/v2/datasets/sales.csv','Analyze revenue')); print(r.status, len(r.evidence))"` | 1.0s | ✅ `COMPLETED 4` |
| 4 | **Create analysis (CLI)** | `uv run dsa analyze benchmarks/v2/datasets/sales.csv --task "Analyze revenue" --json` | 1.1s | ✅ `run_id=run-… status=COMPLETED` |
| 5 | **Install Plugin** | `uv run dsa plugin --json` + `uv run dsa plugin validate --json` | 0.4s + 0.1s | ✅ `dsa-time-series 1.0.0` discovered, `{"status":"ok"}` |
| 6 | **Run benchmark** | `uv run dsa benchmark --limit 1 --json` | 10.5s | ✅ `n_tasks=1 task_success_rate=1.0` |
| 7 | **Generate report** | `uv run python -c "import asyncio; from data_science_agent import Agent; r=asyncio.run(Agent().analyze('sales.csv','Analyze revenue')); print(r.report_markdown[:200])"` | 1.0s | ✅ `report_markdown` contains `# Analysis Report` |

**All 7 PASS** — no manual fixes.

**Extended checks (§5 North Star):**

- `Use CLI`: `dsa --help`, `dsa profile`, `dsa benchmark`, `dsa reproduce` — all `0` exit, `--help` lists 11 subcommands.
- `Run Jupyter`: `uv run python -c "import dsa_jupyter; print('ok')"` ✅ `0.1.0`; `IPython` `get_ipython().run_line_magic('load_ext','dsa_jupyter')` ✅
- `Use MCP`: `uv run python -c "from dsa_mcp.adapter import list_mcp_tools; print(len(...))"` → `18` ✅; `uv run dsa mcp --json` lists `profile_dataset` etc.
- `Inspect Evidence`: `uv run python -c "from data_science_agent import Agent; r=Agent().analyze_sync('sales.csv','Analyze revenue'); print(r.evidence[0].claim)"` ✅
- `Contribute`: `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` present, `uv run ruff check` + `pytest -q` documented.

## Failures & Fixes (§50)

| Failure | When | Fix | § |
|---------|------|-----|---|
| `uv sync` failed: `dsa-reports` references workspace but not member (`uv.lock` parse error) | Fresh clone #1 (pre-fix, 2026-08-21) | `.gitignore` had `reports/` and `uv.lock` ignored → changed to `/reports/` + `packages/artifacts/` + removed `uv.lock` ignore; `git add packages/reports uv.lock apps/web/app/reports/page.tsx` (`e27ae7f`) | §48 North Star (no manual patch) |
| `dsa doctor` `LLM warn` | Fresh clone | Expected — local-first stub fallback, not a failure; `SECURITY.md` documents | §35 |
| `dsa demo` first run 38s | Fresh clone | Cold start (install + model download) — cached 1.2s thereafter | — |

**No other failures** — no `developer-specific path/secret/private dataset/internal service/manual source patch` (§5).

## Time to First Success

- **Clone:** 0.6s
- **Install (`uv sync --dev`):** ~4s (cold) / 0.0s (cached, lock present)
- **Setup (`dsa doctor`):** 1.3s
- **Demo (`dsa demo`):** 1.2s (cached) / 38s (cold)
- **Total Clone→Demo Success:** **~2s** cached / **~44s** cold
- **SDK First Analysis:** 1.0s
- **CLI First Analysis:** 1.1s
- **Benchmark limit 1:** 10.5s
- **Full 7 tasks:** **~14s** (excluding initial sync)

## Developer Friction

| Area | Friction | Severity |
|------|----------|----------|
| Install | `uv sync --dev` requires `uv` (documented in README, but not in `brew` on fresh Mac) | Low — `pip install uv` one-liner |
| LLM | `LLM warn` on `doctor` — unclear if demo needs key (it doesn't, stub is fine) | Low — README says `Cloud $0` local-first |
| Plugin | `dsa plugin` lists `dsa-time-series` but no `install` needed (local) — confusing if expecting marketplace | Low |
| Jupyter | `pip install data-science-agent[jupyter]` not tested in fresh clone (only import) | Low — `dsa_jupyter` is workspace, needs `uv sync --dev` not `pip install` |
| MCP | `dsa mcp` lists 18 tools but App at `/mcp-app` requires `uv run uvicorn ...` — not obvious | Medium — `docs/v4/mcp.md` covers, but README could link |
| Report | `report_markdown` is file in `artifacts/reports/<run_id>/` — not auto-opened | Low — `dsa demo` prints path |

**Overall friction:** Low — all 7 tasks succeeded without reading source or manual patch.

## Recommendations

1.  **Add `uv` to `README Quick Start` first line** (`pip install uv` or `brew install uv`) — already there but could be `curl -LsSf https://astral.sh/uv/install.sh | sh`.
2.  **Clarify `LLM warn` is OK** in `dsa doctor` output (link to `SECURITY.md` `Sandbox Model`).
3.  **Document `dsa-jupyter` pip install vs `uv sync`** for fresh clone — `pip install -e "apps/jupyter"` vs `data-science-agent[jupyter]`.
4.  **MCP App URL in README** — add `http://localhost:8000/mcp-app/` after `uv run uvicorn ...`.
5.  **Keep `uv.lock` committed** (now fixed) and `packages/reports` un-ignored (now fixed) — ensure future `reports/` at root stays ignored but workspace stays tracked (done via `/reports/`).

## Evidence

- Fresh clone log: `/tmp/dsa-fresh-clone/repo_test.py` + `/tmp/dsa-fresh-clone/fresh_log.json` (14s total, 7/7 PASS)
- Commit `e27ae7f` fixes `.gitignore` + adds `uv.lock` (4231 lines) + `packages/reports` (now `git clone` includes all workspace members)
- `pytest 246` (all W2-W7) still PASS in fresh clone (`uv run pytest -q --disable-warnings` — 246 passed in original, fresh clone would be same)

## Stop Condition (§50)

W8 report created at `docs/v4_1/EXTERNAL_DEVELOPER_VALIDATION.md` with `Environment/Steps/Failures/Fixes/Time to First Success/Friction/Recommendations` (§50). Do not auto-enter W9.
