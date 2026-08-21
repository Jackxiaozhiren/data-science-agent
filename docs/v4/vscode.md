# VS Code — V4 W5 Real Integration (§33–35)

**Maturity: Experimental (Real MVP)** — replaces stub (`apps/vscode/README.md` “Stub until SDK”).

## MVP Flow (§33)

`Open Dataset → Ask DSA → Run Analysis → View Result → View Evidence → Open Report`

- **Open Dataset**: `dsa.openDataset` file picker → `lastDataset`, triggers `dsa.runProfile`.
- **Ask DSA**: `dsa.askAnalysis` QuickPick dataset + InputBox task → `runAnalysisFlow`.
- **Run Analysis**: `dsa.runAnalysis` with progress `Planner→Scientist→Critic→Report`.
- **View Result**: `ResultPanel` Webview HTML (`run_id`, `status`, `report_markdown`, `evidence` table, buttons).
- **View Evidence**: `EvidenceTreeProvider` (10 rows) + webview, `setContext dsa:hasResult`.
- **Open Report**: opens `report_markdown` as untitled Markdown.

## Architecture (§34)

```
Extension (src/extension.ts, views.ts)
    ↓
Public SDK/CLI (src/dsa.ts → `uv run dsa analyze/profile/doctor/plugin --json`)
    ↓
Core Engine (packages/agent, packages/tools)
```

Extension never imports `dsa_agent` — only CLI via `child_process.exec`. Config `dsa.pythonPath` / `dsa.apiUrl` for §35.

## Failure Handling (§35)

5 gates in `src/dsa.ts` (`CheckResult` with `suggestion`):

- **LLM unavailable**: env check → warning `Set OPENAI_API_KEY / run Ollama` (§35)
- **Python unavailable**: `python --version` + `uv run python` → error `Install Python 3.12+`
- **Dataset missing**: `fs.existsSync` + ext check → `Use Open Dataset`
- **Plugin failure**: `dsa plugin --json` → `Run dsa plugin validate`
- **Backend unavailable**: `fetch /health` → `uv run uvicorn …` or CLI fallback (local-first, not fatal)

All `runAnalysis` pre-checks before `exec`; errors show `showErrorMessage` with action button (Open Dataset / Doctor).

## Build

```bash
npm --prefix apps/vscode install --legacy-peer-deps
npm --prefix apps/vscode run compile  # tsc strict → out/extension.js
```

Package: `npm --prefix apps/vscode run package` (vsce).

## Tests

`tests/vscode/test_vscode_extension.py` — 7 tests: package manifest, commands/views, dsa wrapper arch guard, failure handling, views, compile.

See `apps/vscode/README.md` and `docs/v4_1/W5_VSCODE.md`.
