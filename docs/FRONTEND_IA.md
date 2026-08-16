# Frontend IA — Phase 7 (Decision)

## Routes
- /            Dashboard (recent analyses, quick upload)
- /datasets    Datasets list + upload (drag-drop, 100MB guard, allows csv/parquet/json/xlsx)
- /datasets/[id] Dataset detail: profile table (rows/cols/missing/dup/cardinality), schema, sample rows
- /analysis    Analysis workspace: select dataset + natural language task + run
- /analysis/[runId] Trace: Agent progress (UNDERSTANDING→REPORTING), Tool calls (status/duration), Evidence, Validation, Report (markdown), Artifacts, Evidence Graph
- /reports     Reports index (run_id, status, created_at)
- (Settings hidden until auth)

## Data Flow (API → UI)
- POST /api/v1/datasets (multipart) → dataset_id
- POST /api/v1/analysis {dataset_id, user_query} → run_id (sync MVP)
- GET /api/v1/analysis/{id} polling or GET .../events (SSE) → progress
- GET .../report?format=markdown for download
- GET .../evidence/{eid} for trace drawer

## UI Principles
- Evidence before claim: every Insight shows Evidence pill linking to tool call + dataset
- Trace is read-only; no chain-of-thought spill — concise agent messages only
- Local-first: no external deps; Tailwind + shadcn-style cards; no Plotly CDN (charts are artifact PNGs + base64)

## Phase 7 Scope (V0.1)
- Implement: Dashboard, Datasets, Analysis workspace, Trace, Reports with SSE fallback to polling
- Defer: auth, projects, streaming push (MVP sync)
