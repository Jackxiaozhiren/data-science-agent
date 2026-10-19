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
- Each marker carries the questions twice: `starter_questions` and `starter_questions_zh`, position-for-position,
  the second derived from `starter_questions_zh.json` keyed by catalog task id (R-13). The button the reader
  sees is the sentence that gets sent, so a Chinese interface starts a Chinese run rather than putting a label
  over different content -- and `is_starter_question` matches either spelling, because a funnel that recognised
  only English would keep counting the half that stayed English and read as a smaller product instead of a
  broken measurement.
- The example report is a run the instance makes itself at startup, in a mode that calls no model and spends
  nothing. It is linked only if its own row shows no errored tool call and no failing validation check;
  recorded runs from the benchmark history are not replayed, because the ones on these bytes are stale --
  they complete with four errored calls under the planner that existed when they were captured.
- When the instance is configured to reason with a model, no run is started unasked and only the questions are
  offered.

## UI principles

- Two languages, one owner for the words. `apps/web/lib/locale.ts` declares `en` and `zh`, and the choice is a
  first-party `dsa_locale` cookie read by the server before render -- `<html lang>`, the tab title and the page
  copy all come from that one answer, because a language the server cannot see produces English markup that
  re-paints in Chinese. A key no locale defines renders visibly as `⟨key⟩`: the failure is meant to be seen,
  not quietly downgraded to the other language. What the owner holds is everything the interface says -- the
  first-run copy, the fetch-outcome vocabulary (`failurePresentation` in `apps/web/lib/api.ts` builds it per
  locale from these keys, and each page's transport override names a key rather than a sentence), the backend
  probe's four phases, and the upload queue's per-file notes. `tests/contract/test_web_locale_parity.py` sweeps
  every sentence the dictionary owns against the page sources, so a moved string that stayed behind in a page
  cannot ship. The deliverable is not translated -- a report keeps the language the run was asked in, and
  `dsa_agent.report_export.report_language()` is what honors that: the run's question decides, by counting
  words (a Chinese sentence naming an English column stays Chinese; an English sentence pasting a Chinese
  file name stays English), and only the product's own words -- headings, field names, the document `lang`
  -- follow it. Findings, claims, messages and numbers are reproduced verbatim, and
  `tests/contract/test_report_language_pair.py` holds the two halves apart.
  The three limitation sentences the report composes are part of that table too -- the caveat a reader acts
  on must not arrive in a language nobody chose -- while the critic's own `limitation` text, stored on the
  insight at analysis time, stays the run's byte: changing it would edit what the run said, which is a
  decision about data and is left open rather than half-taken.
- The keyboard is a supported input, not a fallback. `apps/web/scripts/regression.mjs` walks the analyst's
  routes and requires every tab stop to show a *visible* indicator (style, width and colour -- a transparent
  outline is not one) and every `<details>` drill-down to open on Enter.
- Evidence before claim: every insight shows the evidence ids it rests on, and each one links to the tool call
  and the dataset behind it.
- A caveat is sized to what it means. "Association does not imply causation" is a standing limit of the method
  and reads as a warning; a leak, a confound or an overfit is a defect in the analysis and reads as critical.
  One owner: `app/lib/limitations.ts`, which carries the defect words in both languages the product runs in --
  the Chinese ones are deliberately narrower than the English, because an over-matching keyword makes the loud
  tier fire on everything, which is the failure this bullet exists to prevent. Claiming a causal conclusion is a
  different gate -- the `unsupported_claim` validation check.
- The trace is read-only and carries no chain-of-thought: concise agent messages, tool calls, evidence.
- Failures are shown, not smoothed over: a run with gaps says so on the same page that shows its findings.

## Deferred

Deliberately not built, each with the reason, so the next reader finds a decision rather than an omission.

- **Accounts, projects, and a per-visitor settings surface.** There are no accounts. R-08 gave every row an
  owner -- a random id in a first-party cookie, sent as `X-DSA-Owner`, which keeps one visitor's uploads and
  runs away from the next visitor's, and `docs/hosted-demo.md` states what it does not do. It is still not an
  identity: no login, no recovery, nothing to sign a token against, so preferences have no subject to live
  under. R-05 shipped the one setting that is not per-visitor: `/settings` configures the instance's own model
  provider, and only when the instance is a private one. What stays deferred is a settings page belonging to a
  person rather than to a machine.
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
- **Translated failure prose -- closed, and what it revealed.** The vocabulary of things going wrong is now
  bilingual: `failurePresentation()` in `apps/web/lib/api.ts` builds the five fetch-outcome lines from
  `lib/locale.ts`, each page's transport override names a key instead of holding a sentence, the backend probe's
  four phases and the upload queue's per-file notes do the same, and so does the browser-tab title and the
  completion notification a live run writes. The English-only constant that used to own them is gone; a page may
  no longer keep its own copy, which `tests/contract/test_web_locale_parity.py` sweeps and
  `tests/contract/test_web_fetch_outcome_vocabulary.py` pins per locale.
- **Page chrome past the first-run path: closed, and measured twice.** The shell is bilingual. `States.tsx` (the
  error heading, its Retry, the two skeleton labels), the route-level `loading.tsx` and `error.tsx`,
  `DataTable.tsx`'s empty state and every sortable column's accessible name, the dialog's close labels, the
  language switch's group name, the hero caption and node labels, the sidebar's groups and every one of its links,
  the header nav and mobile menu button, the footer tagline and landmark names, both run/report tables' search,
  filter and empty-line text, the plan timeline's empty line, the whole run inspector (67 strings) and the rest of
  the loop -- the runs list, the reports list, the run-detail header and stats, the dataset comparison screen,
  the settings and failures screens, the MCP reference, the six evaluation levels, the replay page, the benchmarks
  page and its copy button -- read `apps/web/lib/locale.ts` (603 keys per locale, the two blocks key-identical).
  The last tier was the one the first counters could not see: **every table column head and caption, the eleven
  run-status labels, and the short labels of the secondary pages.** Two measures are quoted because they answer
  different questions. In the source, `apps/web/scripts/locale-chrome-inventory.mjs` walks the TypeScript AST and reports
  reader-position string literals; it went from **57 multi-word candidates in 19 files to 2**, and both survivors
  are declared identifiers (`dataset_id ·`, the Ollama endpoint placeholder). On the rendered page,
  `apps/web/scripts/locale-chrome-acceptance.mjs` reads only the regions the interface owns -- `th`, `option`, `summary`,
  `label`, `h1`–`h3`, `button`, nav/header/footer -- on every route a seeded instance can answer, in 中文 and in
  English (the runner prints its own route and region counts with the verdict, so the coverage is reported rather
  than retyped here): **zero chrome regions show a Latin-only string outside the declared identifier set, and
  74–94% of the chrome regions carry CJK.** Its
  exemption list is printed with every run (4–10 regions per route, and they are GitHub, the language switch's
  endonym "English", endpoint paths, provider ids from the API, and uploaded file names), because an instrument
  that exempts everything would also report a clean page.
- **Three detectors, each blind in a way the next one had to fix.** The first R-13 counter was a line-matching
  scan: it could not see a JSX text node wrapped over three lines ("No runs match — adjust the search or status
  filter." in `RunsTable`) and it could not see a string attribute at all. The AST pass fixed that, and its own
  exemption -- "this value already exists in the dictionary, so it is not an orphan" -- hid the actual defect
  class: `/failures` kept its own copy of "Evaluation · Step 3" while the dictionary owned the sentence, and seven
  pages were doing that. Reporting duplicates instead of skipping them found all seven. Then the page-wide text
  comparison had to go, because it cannot tell chrome from data: a seeded run's own English report is not a leak.
  The region selector is what made the claim decidable, and it caught one more leak none of the others could
  (`RunInspector`'s caveat banner, `{n} caveat{s} (m critical) — review limitations…`), which is now four keys.
  `test_no_dictionary_sentence_is_also_written_into_a_page` was widened from a 40-character floor to **12 plus a
  required space**, with whole-line comments stripped so a comment quoting a dictionary line is not a second
  owner; both that sweep and the new `test_every_declared_status_has_a_label_in_both_locales` were falsified by
  planting the failure and restoring by hash.
- **Two English strings changed visible text, on purpose.** The status chip used to render the raw enum token, so
  `COMPLETED` appeared in capitals and the in-flight filter option said `Data_profiling`; both now come from
  `statusLabel()`, so the chip says "Completed" and the option says "Data profiling". The settings readout lines
  moved from `word <strong>value</strong> word <strong>value</strong>` into one dictionary sentence with
  placeholders, which drops the inline bold -- punctuation belongs to the sentence, and a Chinese sentence needs
  Chinese punctuation, so fragments around markup could not carry both. A status the enum does not declare is
  still rendered as the token it arrived with: labelling a state nobody declared would invent one.
- **The locale provider wraps the whole shell, and that was a bug.** `LocaleProvider` used to sit around
  `{children}` inside `<main>`, while the sidebar is a sibling of `<main>` and a client component reading that
  context -- so on a 中文 page the sidebar, and anything else outside the provider, rendered the dictionary's
  default language. The header looked translated because it takes `locale` as a prop, which is what made the
  screen read as half-done rather than broken. No source guard and no single-page browser check could see it:
  the parity guards read the dictionary and the page files, and the tour asserts layout rather than language.
  `test_the_provider_wraps_the_shell_not_just_the_route` now pins the nesting, and the live navigation check
  (`build/r13f-nav-acceptance.mjs`) reads header, sidebar and footer text in both languages.
- **The regression tour reads English.** `apps/web/scripts/regression.mjs` asserts or locates on nine English
  strings (measured 2026-10-19: `Browse files`, `Waking… n/n`, `Attempt n of n`, `waking up`, `API unreachable`,
  `nothing answered`, `Checking API`, `Loading table`, `Loading page`) and every one of them is a dictionary
  value -- which is why these requirements kept the `en` values byte-for-byte while moving them. The parity sweep
  walks `apps/web/app/**` and does not see `scripts/`, so the coupling is real and unstated by any gate: rewording
  one of those nine is a change to the tour as well as to the dictionary.
- **The language rule is decided once, and CI runs it.** `apps/web/scripts/locale-chrome-rules.mjs` owns the
  answer to "which regions of a page does the interface speak through": the region selector, the identifier list,
  the data-in-chrome pattern and the leak decision. Two runners ask it rather than each deciding. `regression.mjs`,
  the web job GitHub Actions already runs, adds one check per static route per locale -- each route is loaded under
  a `dsa_locale=zh` and an `=en` cookie and fails on an English chrome region or a `⟨missing-key⟩` marker, and the
  tour's own summary line prints that pass's count. `locale-chrome-acceptance.mjs` needs a seeded backend and so
  runs by hand, covering what the tour cannot see: the column heads that only exist once a table has rows, and the
  three routes that need a real run or dataset id. `test_the_two_language_runners_share_one_rule_owner` is what
  keeps them the same test -- it refuses a runner that re-declares `IDENTIFIERS` or `CHROME_SELECTOR` beside its
  import, and it floors the identifier list at 25 entries, because a rule owner emptied of entries would let both
  runners report a clean tree. The wiring was falsified from both sides: forcing the tour's cookie to `en` reddened
  every 中文 route naming `a:"Ask" | a:"Try DSA" | ...`, and replacing the acceptance's import with a local stub
  tripped the owner guard.
- **A third-party accessibility scanner.** The web lane's a11y checks are implemented in
  `apps/web/scripts/regression.mjs` against real DOM and name the axe rule each reproduces. Running axe itself
  would add a devDependency, and dependency changes are the user's call, not the agent's.
