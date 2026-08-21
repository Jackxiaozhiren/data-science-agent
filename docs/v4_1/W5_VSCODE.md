# W5 VS Code Real Integration — Completion Report 2026-08-21

> Workstream W5 (§33–35) — Stub → Real MVP.

## Summary

W5 replaces `apps/vscode` stub with **real MVP**: 6-step closed loop, architecture `Extension → Public SDK/CLI → Core`, 5 failure handlers, tree + webview.

## Changes

| File | Change |
|------|--------|
| `apps/vscode/package.json:1` | New `dsa-vscode 0.1.0` with 7 commands (`openDataset/askAnalysis/runAnalysis/viewResult/viewEvidence/openReport/doctor`), 2 views (`datasetExplorer/evidenceExplorer`), 2 configs (`pythonPath/apiUrl`), `out/extension.js` |
| `apps/vscode/tsconfig.json:1` | Strict TS 5.9, outDir `out` |
| `apps/vscode/src/dsa.ts:1` | CLI wrapper (§34): `checkPython/LLM/Dataset/Plugin/Backend` (§35) with `suggestion`, `runAnalysis`/`runProfile`/`runDoctor` via `uv run dsa ... --json` (`child_process.exec`), never duplicates Agent |
| `apps/vscode/src/views.ts:1` | `DatasetTreeProvider` (workspace `*.csv` + `benchmarks/v2/datasets` 30 max), `EvidenceTreeProvider` (10 rows), `ResultPanel` Webview HTML (report + evidence table) |
| `apps/vscode/src/extension.ts:1` | `activate` registers providers/commands, `withProgress` Planner→…, updates `EvidenceTreeProvider`, handles 5 failures with `showErrorMessage` + action (Open Dataset/Doctor), auto-check §35 on activate |
| `apps/vscode/README.md:1` | Stub → real (flow table, views, arch, failure table, build) |
| `docs/v4/vscode.md:1` | New doc (MVP flow, arch, failure table, build, tests) |
| `tests/vscode/test_vscode_extension.py:1` | 7 tests §33-35 (manifest, arch guard, failure 5, flow, compile, config, no stub) |

## Verification (§33-35)

```bash
# Build (§34)
npm --prefix apps/vscode install --legacy-peer-deps
npm --prefix apps/vscode run compile  # tsc → out/extension.js, dsa.js, views.js
# All TS strict pass
ls apps/vscode/out/extension.js  # exists

# Arch guard (§34)
grep -r "from dsa_agent" apps/vscode/src  # no match (only CLI)
grep -r "uv run dsa" apps/vscode/src/dsa.ts  # found

# Failure handling (§35)
grep -E "LLM unavailable|Python unavailable|Dataset missing|Plugin failure|Backend unavailable" apps/vscode/src/dsa.ts  # 5 found

# Flow (§33)
uv run pytest tests/vscode -v  # 7 passed
# Commands: openDataset/askAnalysis/runAnalysis/viewResult/viewEvidence/openReport/doctor
# Views: datasetExplorer + evidenceExplorer with dsa:hasResult
```

## Flow Test (manual in Extension Host)

- F5 Launch → DSA view → Dataset Explorer shows `sales.csv`
- `DSA: Open Dataset` → pick CSV → profile shows rows/cols
- `DSA: Ask Analysis` → input `Analyze revenue` → progress `Planner→Scientist→Critic→Report` → Webview `Analysis run-… COMPLETED (4 evidence)` + report + evidence table
- `DSA: View Evidence` → Evidence Explorer + webview
- `DSA: Open Report` → untitled Markdown with report
- Disconnect backend → still works via CLI (local-first) with info `Backend unavailable — running via CLI`
- Remove dataset → error `Dataset not found — Use Open Dataset` with button
- Unset Python → error `Python unavailable — Install Python 3.12+`

## Maturity Update

| Capability | Before | After W5 | Evidence |
|------------|--------|----------|----------|
| VS Code Integration | Stub | **Experimental (Real MVP)** → Stable after W8 | `apps/vscode/out/extension.js` + 7 tests, `npm run compile` pass, 5 failure handlers |

Stub forbidden — now `PASS` per §33. Full `Stable` after external validation.

## Risks / Next

- No `vsce package` yet (requires `vsce` + publisher) — W10.
- Webview is HTML string, not React — sufficient for MVP (§33).
- No `onLanguage` activation, only view-contributed — launch via F5 is ok.

## Stop Condition (§72)

W5 implements `Inspect→Plan→Implement→Test→Security→Benchmark→Document→Commit→STOP`. Do not auto-enter W6.
