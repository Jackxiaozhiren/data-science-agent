# Frontend information architecture

The spec of record for `apps/web`. It describes the app as it is shipped, route by route.

An earlier version of this file described a smaller application -- five routes, a `Settings` page "hidden until
auth", a synchronous `POST /api/v1/analysis` -- and stayed the documented IA while the app grew past it (audit
B12). Where this file and the code disagree, the code is authoritative and this file is the defect.

## Deployment shapes

Both shapes serve the same routes; only the origin of the API and the lifetime of storage differ.

| | Local | Hosted demo |
|---|---|---|
| Web | `dsa ui`, or `npm run dev` / `next start` on `:3000` | Vercel |
| API | `dsa ui` (supervised), or `uvicorn dsa_api.main:app` on `:8000` | Render free instance |
| API origin | `NEXT_PUBLIC_API_URL`, baked at web build time | same, pointing at the Render URL |
| CORS | `DSA_CORS_ORIGINS` must list the web origin, per port | set in the service env |
| Reasoning mode | whatever `DSA_LLM_MODE` says | `heuristic`: no model is called, so a run costs nothing |
| Disk | persists | **wiped on every deploy and on idle suspension** |

The last row is the one the interface is built around. Because the free instance holds no files, the sample
datasets and the example report are rebuilt at startup rather than uploaded once, and a visitor's first request
after a pause can take about a minute to answer. Both are handled below ("Cold start", "The demo's own data").

## Navigation

One declaration owns the navigation: `NAV_GROUPS` in `app/components/layout/Sidebar.tsx`. The sidebar and the
top bar both read it, and `tests/contract/test_web_navigation_groups.py` compares the rendered order against
it, so a link cannot appear in one place and not the other.

Two groups, in this order:

1. **Your work** -- the loop the product teaches: `Ask` (`/analysis`), `Runs` (`/runs`), `Reports`
   (`/reports`), `Datasets` (`/datasets`).
2. **About this system** -- measurements *of the agent* rather than of the visitor's data, labelled as such in
   the group's own hint: `Benchmarks`, `Evaluations`, `Failures`, `Research`, `Compare runs`,
   `Compare datasets`, `MCP`.

The sidebar renders on every route (it lives in the root layout, and on the routes it previously skipped there
was no workspace navigation at all). The top bar carries the first two analyst entries plus the external links;
on small screens it expands to both groups. Nothing in the diagnostic group is hidden or removed -- those
routes back the published case studies, the leaderboard and the audit trail -- they are grouped and named so a
reader knows which side of the glass they are on.

## Routes

| Route | What it is | Reached from |
|---|---|---|
| `/` | Landing: the promise, the live counts, and a first action that needs no upload | logo |
| `/datasets` | Bring your data: upload, the sample panel, the profiled list | Ask · Runs · Reports |
| `/datasets/[id]` | One dataset: profile, schema, sample rows, the runs made against it | dataset row |
| `/datasets/compare` | Two datasets side by side | system group |
| `/analysis` | Ask: pick a dataset, phrase the question, review the plan, run | analyst group, starter questions |
| `/analysis/[runId]` | Inspect: plan timeline, trace, evidence, insights, validation, artifacts, report, exports | any run row |
| `/runs` | Every run this instance holds, with its status | analyst group |
| `/runs/[id]` | A run read straight from the row | run row |
| `/runs/[id]/replay` | The event stream of a run, replayed | run page |
| `/runs/compare` | Two runs side by side, with the parent/child link | system group |
| `/reports` | Report index and downloads | analyst group |
| `/benchmarks` | Leaderboard | system group |
| `/evaluations` | Evaluation runs | system group |
| `/failures` | Failure inventory | system group |
| `/research` | Experiment history | system group |
| `/mcp` | MCP tool surface | system group |

## Data flow

The browser talks to the API only; no page reads a file from the repository.

- `GET /api/v1/datasets/`, `GET /api/v1/datasets/{id}` -- lists and profiles.
- `POST /api/v1/datasets/` (multipart) -- the only write a visitor makes to the dataset side.
- `POST /api/v1/analysis/` `{dataset_id, user_query}` -- **202** with the run id, and the task executes in the
  API process. A second identical request while one is in flight returns **200** and the same run, so a double
  click is one run.
- `GET /api/v1/analysis/{id}/progress` -- the lightweight poll the inspector uses while a run is non-terminal;
  `GET .../events` is the SSE stream for clients that want the sequence itself.
- `GET /api/v1/analysis/` -- the run list behind `/runs`, `/reports`, `/failures` and the landing counts.
- `GET /api/v1/analysis/{id}/report?format=markdown[&mode=findings]`, `GET .../bundle` -- exports, one owner in
  `dsa_agent.report_export`.
- `GET /health` -- the cold-start probe (below); `GET /version` and `/metrics` are linked from the footer.

## Cold start

`app/lib/backendProbe.ts` owns one probe for the whole document, shared by every screen and by the status dot,
so a waking instance is not asked four times by one page load. Phases: `probing` → `warming` → `ready`, or
`unreachable`. Four attempts with a 12 s timeout and 2/4/8 s backoff is a 62 s budget, measured against the
44.5 s a Render cold start actually took. While a probe is in flight the screen says so in the same words the
dot uses; after 15 s of silence it adds the expectation ("this can take about a minute"). An empty list and a
backend that has not answered are different states and never share a sentence.

## The demo's own data

`dsa_api.services.demo_seed` runs at startup and puts two things on screen: the committed sample datasets in
`examples/datasets/`, created through the same upload path a visitor uses, and one finished report per
dataset. Each seeded row carries a `dsa_sample_dataset` marker in its metadata, which is how the UI says
"this one is the demo's" and how it knows to offer no delete.

- The starter questions are this project's own benchmark tasks: `benchmarks/v2/catalog.json` names a dataset
  per task, and a task is offered for a sample only when `benchmarks/v2/datasets/<name>` is byte-identical to
  it. Questions are never written for a page.
- The example report is a run the instance makes itself at startup, in a mode that calls no model and spends
  nothing. It is linked only if its own row shows no errored tool call and no failing validation check;
  recorded runs from the benchmark history are not replayed, because the ones on these bytes are stale --
  they complete with four errored calls under the planner that existed when they were captured.
- When the instance is configured to reason with a model, no run is started unasked and only the questions are
  offered.

## UI principles

- Evidence before claim: every insight shows the evidence ids it rests on, and each one links to the tool call
  and the dataset behind it.
- A caveat is sized to what it means. "Association does not imply causation" is a standing limit of the method
  and reads as a warning; a leak, a confound or an overfit is a defect in the analysis and reads as critical.
  One owner: `app/lib/limitations.ts`. Claiming a causal conclusion is a different gate -- the
  `unsupported_claim` validation check.
- The trace is read-only and carries no chain-of-thought: concise agent messages, tool calls, evidence.
- Failures are shown, not smoothed over: a run with gaps says so on the same page that shows its findings.

## Deferred

Deliberately not built, each with the reason, so the next reader finds a decision rather than an omission.

- **Auth, accounts, projects, settings.** There are no accounts. R-08 gave every row an owner -- a random id in a
  first-party cookie, sent as `X-DSA-Owner`, which keeps one visitor's uploads and runs away from the next
  visitor's, and `docs/hosted-demo.md` states what it does not do. It is still not an identity: no login, no
  recovery, nothing to sign a token against, so a settings surface has no subject to store preferences under.
  Ownership is the precondition for that surface, and this is the half of it that ships.
- **Deleting a dataset.** There is no `DELETE` route and no delete control; `tests/integration/test_demo_seeding.py`
  pins both surfaces refusing one until seeded rows get an explicit read-only rule.
- **Queue or worker execution.** Runs execute in the API process. A broker would be a new dependency and a new
  thing to operate for a single-server demo; the cost is that a process that dies mid-run leaves a row that
  `sweep_abandoned_runs` closes out at the next boot.
- **Push streaming to the browser.** The inspector polls `/progress` because a poll survives a buffering proxy
  and costs one small row read; `/events` is live for clients that want the sequence.
- **A persistent artifact store.** Object storage would make a redeploy keep its charts, and it is not free.
  Reports therefore render from the database row, and the artifact links on a page are the instance's own.
- **Per-run evidence coverage on the landing page.** The stat card shows `—` until a query exists that
  computes it across runs; the number is per-run today, on the run page.
