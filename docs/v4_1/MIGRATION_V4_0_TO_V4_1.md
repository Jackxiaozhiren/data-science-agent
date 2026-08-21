# Migration Guide — V4.0 → V4.1 (§60)

## Breaking Changes

**None.** All `4.0.0` Stable APIs remain compatible (SemVer minor).

## New APIs

- `data_science_agent.sdk` version `4.1.0` (was `4.0.0`), docs §16 full.
- `dsa plugin` lifecycle `list/validate/status/disable/enable/remove/install` + `--json` (§21)
- `dsa` CLI `doctor/init/plugin/mcp` now `--json` (§20)
- `dsa_jupyter` (`apps/jupyter`) `0.1.0` — new workspace `dsa-jupyter`, magic `%dsa` + `display_analysis` (§28)
- `dsa-vscode` (`apps/vscode`) `0.1.0` — 7 commands + 2 views (§33)
- `dsa_mcp` §36 `analyze` tool (18th) + 5 resources `dataset://` etc. + explicit `run_id` (§38), App at `/mcp-app/` (§36)
- `pyproject.toml` `optional-dependencies` `jupyter = [dsa-jupyter, ...]` (§18)

## Deprecated APIs

None. `4.0.0` `from data_science_agent import Agent` still works; `dsa plugin` without args still lists (compat).

## Plugin Changes (§21-27)

- Manifest now requires `dsa.min_version/max_version` + `capabilities` + `hash` (optional) — old `requires: {dsa: ">=4.0,<5.0"}` still accepted.
- Permissions now `dataset.read` etc. (legacy `read/compute` still allowed via mapping, but new plugins should use granular).
- Validation now checks typosquat/dependency confusion (§45) — may reject previously accepted malicious names.

## SDK Changes

- `Agent._version` `4.0.0 → 4.1.0`, `CURRENT_DSA_VERSION` `4.0.0 → 4.1.0`.
- `Agent.analyze_sync` is still sync, but Jupyter should use `await agent.analyze` (nest-asyncio).

## CLI Changes (§20)

- `dsa doctor --json` now works (was `unrecognized arguments: --json` in 4.0.0).
- `dsa plugin` now takes `action` + `target` + `--json` (was just `list`).

## MCP Changes (§36-40)

- Tools `17 → 18` (+`analyze`).
- Resources `3 → 5` schemes.
- Server now also `GET /tools`, `GET /resources`, `POST /` aliases for mount at `/mcp`.
- App shell → real HTML/JS at `/mcp-app/` (was JSON `{"name":"..."}`).

## Jupyter Changes (§28-32)

- Was `stub` (`apps/jupyter/README.md` stub) → real `dsa-jupyter` with `%dsa` + rich display. No breaking — `from data_science_agent import Agent` now auto `_repr_html_`.

## VS Code Changes (§33-35)

- Was stub (`Stub until SDK`) → real extension `dsa-vscode 0.1.0` (compile via `tsc`). No breaking.

## To Upgrade

```bash
git pull
uv sync --dev
uv run dsa doctor --json  # should be ok/warn
uv run dsa plugin validate --json  # should be ok
uv run pytest -q  # 257 passed
```

No code change required for `4.0` users.
