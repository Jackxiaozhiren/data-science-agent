# VS Code — V4.1 §33-35 (Experimental Real MVP)

**MVP Flow (§33):** `Open Dataset → Ask DSA → Run Analysis → View Result → View Evidence → Open Report`

- `dsa.openDataset` (file picker `*.csv/*.parquet` → `lastDataset`, `runProfile`)
- `dsa.askAnalysis` (QuickPick dataset + InputBox task → `runAnalysisFlow`)
- `dsa.runAnalysis` (progress `Planner→...`)
- `dsa.viewResult` (Webview `ResultPanel` HTML: report + evidence table)
- `dsa.viewEvidence` (`EvidenceTreeProvider` 10 rows + webview)
- `dsa.openReport` (untitled Markdown)
- `dsa.doctor` (`dsa doctor --json`)

**Views:** `Dataset Explorer` (workspace `*.csv` 30) + `Evidence Explorer` (`dsa:hasResult`).

**Arch (§34):** `Extension (extension.ts/views.ts) → Public SDK/CLI (dsa.ts: uv run dsa ... --json via child_process) → Core` — no `dsa_agent` import.

**Failures (§35):** 5 gates `CheckResult` with `suggestion`: `LLM unavailable` (env `OPENAI_API_KEY` → `dsa doctor`), `Python unavailable` (`uv sync`), `Dataset missing` (`Open Dataset`), `Plugin failure` (`dsa plugin validate`), `Backend unavailable` (`uvicorn` or CLI fallback local-first).

**Build:** `npm --prefix apps/vscode install && npm run compile` → `out/extension.js` (tsc strict).

**Tests:** `tests/vscode` 7 (manifest, arch guard `!dsa_agent`, failure 5, flow, compile).

See `apps/vscode/README.md` + `W5_VSCODE.md`.
