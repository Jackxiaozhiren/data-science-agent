# VS Code Extension — V4 W5 Real Integration (§33–35)

**Maturity: Experimental (Real MVP)** — replaces stub. Minimal closed loop, not full IDE.

## Flow (§33) — 6-step MVP

```
Open Dataset
↓
Ask DSA
↓
Run Analysis
↓
View Result
↓
View Evidence
↓
Open Report
```

## Commands (§33)

| Command | Title | Action |
|---------|-------|--------|
| `DSA: Open Dataset` | `dsa.openDataset` | File picker (`*.csv`, `*.parquet`) → sets `lastDataset`, auto `dsa profile` |
| `DSA: Ask Analysis` | `dsa.askAnalysis` | Input box for question → `runAnalysisFlow` |
| `DSA: Run Analysis` | `dsa.runAnalysis` | Uses `lastDataset` + prompts task → `dsa.runAnalysis` |
| `DSA: View Result` | `dsa.viewResult` | Webview `ResultPanel` with report + evidence table |
| `DSA: View Evidence` | `dsa.viewEvidence` | Tree `Evidence Explorer` + webview |
| `DSA: Open Report` | `dsa.openReport` | Opens `report_markdown` as untitled Markdown |
| `DSA: Doctor` | `dsa.doctor` | Runs `dsa doctor --json` via CLI |

## Views (§33)

- **Dataset Explorer** (`dsa.datasetExplorer`): Tree of workspace `*.csv` + `benchmarks/v2/datasets/*.csv` (30 limit), click to view result. Icon `table`, command `dsa.viewResult`.
- **Evidence Explorer** (`dsa.evidenceExplorer`): Shows `Evidence` (10 max) after analysis, `verified` icon, visible when `dsa:hasResult`.

## Architecture (§34)

```
Extension (TypeScript, src/extension.ts)
    ↓ Public SDK / CLI (not duplicated)
    ↓ Core Engine (dsa_agent.graph)
```

- `src/extension.ts`: `activate` registers providers/commands, handles progress `vscode.window.withProgress`, updates `EvidenceTreeProvider` via `setContext`.
- `src/dsa.ts`: Wrapper over **Public CLI** `uv run dsa analyze/profile/doctor/plugin` via `child_process.exec` (§34 — no Agent logic duplicated). All calls via `exec` with JSON parse.
- `src/views.ts`: `DatasetTreeProvider`, `EvidenceTreeProvider`, `ResultPanel` (Webview HTML with report + evidence table + buttons).

No `dsa_agent` import in extension — only CLI.

## Failure Handling (§35)

All 5 cases return `CheckResult {ok, message, suggestion}` and show `showWarningMessage`/`showErrorMessage` with action:

| Case | Check | Message | Suggestion |
|------|-------|---------|------------|
| LLM unavailable | `checkLLM()` env `OPENAI_API_KEY` etc. | `LLM unavailable — running in stub/Ollama fallback` | `Set OPENAI_API_KEY or run Ollama. See dsa doctor.` |
| Python unavailable | `checkPython()` `python --version` / `uv run python` | `Python unavailable` | `Install Python 3.12+ and uv sync` |
| Dataset missing | `checkDataset(path)` `fs.existsSync` | `Dataset not found: …` | `Use DSA: Open Dataset` |
| Plugin failure | `checkPlugin()` `dsa plugin --json` | `Plugin failure` | `Run dsa plugin validate` |
| Backend unavailable | `checkBackend()` `fetch /health` | `Backend unavailable at http://127.0.0.1:8000` | `uv run uvicorn dsa_api.main:app --app-dir apps/api/src` or CLI mode (local-first fallback) |

Progress and errors never crash extension — `try/catch` with `showErrorMessage` and suggestion button (e.g., Open Dataset / Doctor).

## Build / Install

```bash
npm --prefix apps/vscode install --legacy-peer-deps
npm --prefix apps/vscode run compile  # → out/extension.js
# In VS Code:
# code --install-extension apps/vscode  (or F5 Launch Extension)
# Or package:
# npm --prefix apps/vscode run package  # via vsce
```

Dev: `F5` launches Extension Development Host with `DSA` view.

## Tests

```bash
npm --prefix apps/vscode run compile  # tsc strict pass
uv run pytest tests/vscode -v  # 6 tests: manifest, commands, views, dsa wrapper, failure handling, arch guard
```
