# Hosted Demo Deployment

The repository contains a Next.js web app (`apps/web`) and FastAPI service (`apps/api`). The public demo exposes both through HTTPS URLs.

## Current public deployment

The verified deployment shape is:

- **Web:** Vercel — `https://data-science-agent-web-rr93.vercel.app`
- **Try DSA:** `https://data-science-agent-web-rr93.vercel.app/datasets`
- **API:** Render Web Service — `https://data-science-agent-api-h43i.onrender.com`
- **API health:** `https://data-science-agent-api-h43i.onrender.com/health`

The full DSA Python package is intentionally not treated as a lightweight serverless function: the scientific stack is substantially larger than typical function bundles. The Web and API remain independently deployable and are connected with the public API URL.

The repository includes a root `render.yaml` Blueprint so the API can be provisioned from GitHub without recreating Docker, health-check, port, or demo-mode settings by hand.

### Which Render object is the live one

`render.yaml` declares one Web Service named `data-science-agent-api`. Render publishes it under a
suffixed hostname, so the deployed service is titled **`data-science-agent-api-h43i`** and the Blueprint
name you see under **Blueprints** is not that string -- searching the dashboard for
`data-science-agent-api` as a *Blueprint* name finds nothing, which is a dead end, not a missing service.

The dashboard may list more than one Blueprint instance pointing at this repository. Identify the live one
by the Web Service's **External URL**, which must read exactly
`https://data-science-agent-api-h43i.onrender.com`; the other instance owns a different hostname or is
suspended. Never resolve the ambiguity by creating a Blueprint instance -- that provisions a second public
service.

**A synced Blueprint is not a deployed service.** The Blueprint list reports `Synced`, which only means
Render's copy of `render.yaml` matches the repository. `autoDeploy` is `false` on this service, so merging
to `main` changes nothing visitors see until a **Manual Deploy → Deploy latest commit code** runs, and the
deploy row shows the commit it built.

The public demo runs in deterministic offline/heuristic mode so a visitor can complete the core product flow without requiring or exposing a model API key. Real-model evaluation is a separate, explicitly configured path.

## Verified product flow

The hosted deployment has been exercised through the complete browser path:

```text
Upload dataset
  → profile dataset
  → semantic planning
  → correlation / significance testing
  → feature importance
  → causal guard
  → visualization
  → verified evidence
  → validation
  → COMPLETED report
```

A canonical acceptance question is:

> Explain which features are most important for revenue, test whether the main associations are statistically significant, assess the impact of campaign_group on the outcome, and clearly distinguish association from causation. Include a visualization.

A successful run should show completed tool calls, evidence marked `verified`, no tool errors, and a final `COMPLETED` report. A causal check may deliberately return `causal_bar=fail`; that is a guardrail indicating that an observational difference is not sufficient to establish causation.

## The same path in Chinese, and by keyboard

The header offers English and 中文 (R-13). It is not a cosmetic switch: the starter questions are published in
both wordings, and **the wording the reader sees is the wording that is sent**, so a Chinese visitor's run has a
Chinese objective -- and the funnel's `starter_question_used` link matches either spelling, so choosing the other
language does not silently drop the click out of the measurement. The interface language never rewrites a
deliverable: a report stays in the language the run was asked in.

Measured on a local `dsa ui` instance at `127.0.0.1:3000`: the server renders `/datasets` and `/analysis` already
in Chinese (no English-then-Chinese re-paint), the landing's primary action carried
`对 Titanic 数据集做探索性分析，重点关注生还模式。`, and the run it started reached `COMPLETED`. The keyboard half is a
gate, not a screenshot: `apps/web/scripts/regression.mjs` walks the analyst's routes and requires a visible focus
indicator on every tab stop and that each `<details>` drill-down opens on Enter.

The public deployment above has not been redeployed since, so what it serves is still the earlier build.

## Product capture (30 s, recorded 2026-09-11 against the live deployment)

<video src="assets/demo/dsa-demo-30s.webm" controls preload="metadata" width="100%"></video>

Flow: upload `ads.csv` → ask “Does spend predict conversions?” → run → COMPLETED evidence report. Waiting time edited out; no step staged or simulated.

Still frames: [upload](assets/demo/01-upload.png), [question](assets/demo/02-question.png), [report](assets/demo/03-report.png).

## Deploy the API on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Jackxiaozhiren/data-science-agent)

Use the button above, or create a new Blueprint from this repository in the Render dashboard.

The Blueprint creates one Docker Web Service with:

- `docker/Dockerfile.api` and the repository root as Docker build context;
- the Render-provided `PORT` value handled by the image entrypoint;
- `/health` as the health-check path;
- `DSA_LLM_MODE=heuristic` and heuristic fallback;
- an ephemeral SQLite database at `/tmp/dsa.db` for the public preview;
- automatic deploys disabled so a public-demo instance is not rebuilt on every repository change.

No model credential or CORS value is required to get the API itself healthy. First verify the public API and `/health`. After the final Vercel frontend URL exists, set `DSA_CORS_ORIGINS` manually on the Render Web Service to that exact origin.

For the current public deployment:

```bash
DSA_CORS_ORIGINS=https://data-science-agent-web-rr93.vercel.app
DSA_DATABASE_URL=sqlite+aiosqlite:////tmp/dsa.db
DSA_DATASET_DIR=/tmp/datasets
DSA_ARTIFACT_ROOT=/tmp/artifacts
```

All three writable roots sit on the free instance's container filesystem, which is ephemeral: a restart, an
idle shutdown or a redeploy clears them together. They are named explicitly rather than left to the image
default because `/app/...` is not a path the app recognises as throwaway, and the disclosure in `/version` --
the `not kept` badge in the shell -- reports only the roots it can tell apart. Unsetting them would make the
badge quieter, not the storage safer. `deploy/render-persistent.example.yaml` is the configuration that moves
all three onto a real disk.

If an existing Blueprint has a failed deploy, keep the same Blueprint and use **Manual sync** or **Manual Deploy** after the repository fix is merged. Do not create a second Blueprint for the same service.

### Product events are off on the demo unless the operator turns them on

The API can count the funnel -- arrival, then a starter question used, then run started, run completed,
export taken -- and the vocabulary that defines every one of them is
`apps/api/src/dsa_api/services/product_events.json`. Nothing is recorded unless the operator asks for it, and
because the first link is something only a browser can know, **counting it takes two deliberate acts, one on
each service.** Setting only one is a real and easy mistake: it yields a live counter that reports zero for
the step nobody configured.

| What you set | What the instance records |
|---|---|
| neither (the state of the current deployment) | nothing. No file is created, and the web bundle sends no event request at all |
| `DSA_TELEMETRY=on` on the Render service only | the server-observed steps (`run_started`, `run_completed`, `export_taken`, and `starter_question_used` when a run's question matches a published one). `arrival` stays zero, because the deployed web bundle was not built to report it |
| `NEXT_PUBLIC_TELEMETRY=on` in Vercel's build environment only | nothing. The browser posts, and the API's own gate discards every post |
| both | the whole funnel, including arrivals |

`NEXT_PUBLIC_*` values are inlined when Vercel builds the site, so changing it means a **rebuild**, not a
restart -- a bundle built without it cannot reach the events endpoint even if the API is counting. Set it in
Vercel's Environment Variables (Production), then deploy, and confirm the deployed JS actually contains the
change rather than assuming the setting took effect.

On the API side, `DSA_TELEMETRY=on` appends one JSONL line per event to `DSA_EVENT_LOG` (default
`data/events/events.jsonl`), which on the free tier sits on the ephemeral disk -- so the log vanishes on
restart, exactly like the runs table. A count you have not read out of the instance is a count you do not
have.

Counting arrivals is a decision about a stranger's session, not a deployment detail, and it is left to the
maintainer for that reason. If you turn it on, say so where a visitor can read it: the event carries only a
short page label from the vocabulary's own choice list -- no URL, referrer, user agent, cookie or identifier
is accepted, and the relay refuses values it was never told about -- but "we count page views on this demo"
still has to be written down somewhere a person can see. The payload contract itself does not change with
consent: query text, dataset content and user-identifying values are refused at emit time, before the consent
check, whether or not counting is on.

The cheapest check that the running container is the code the repository has is the route census, and it needs
no credentials and no deploy: compare the two OpenAPI path sets.

```bash
curl -s https://data-science-agent-api-h43i.onrender.com/openapi.json > /tmp/hosted.json
uv run --frozen python -c "
import json
from fastapi.testclient import TestClient
from dsa_api.main import app
h=set(json.load(open('/tmp/hosted.json'))['paths'])
l=set(TestClient(app).get('/openapi.json').json()['paths'])
print('hosted', len(h), 'local', len(l), '| hosted-only', sorted(h-l), '| local-only', sorted(l-h))"
```

Both sides answered the same path set when measured on 2026-10-21, so the deployed API is not behind the
repository at the route level. It can still be behind at the *content* level, and that is the half a path census
cannot see: a route that exists in both may render differently. The content check needs no credentials either --
ask a published run for its report and look at what the product itself says:

```bash
RID=$(curl -s https://data-science-agent-api-h43i.onrender.com/api/v1/analysis/ \
  | python3 -c "import json,sys; a=json.load(sys.stdin)['analyses']; print(a[0]['id'])")
curl -s "https://data-science-agent-api-h43i.onrender.com/api/v1/analysis/$RID/report?format=html" \
  | python3 -c "import re,sys; h=sys.stdin.read(); print(re.findall(r'<h2>(.*?)</h2>', h)); print(bool(re.search(r'<strong>[a-z]+_[a-z_]+</strong>', h)))"
```

The second line prints whether any validation check is being named by the engine's identifier instead of by the
word the report owns (`Evidence coverage`, 证据覆盖率). Measured on 2026-10-21 the answer was `True`: the running
container predates that change, which is the evidence a redeploy is owed -- and the reason `identical: True` above
is a route claim, not a currency claim. Run the same probe again after a deploy; when it prints `False`, the
artifact the visitors download matches the repository.

### Verify a deploy from the outside

A deploy is not confirmed by the dashboard going green; confirm the artifact answers. Run these after the
service reports `Live`, and read what comes back rather than the build status:

```bash
curl -s https://data-science-agent-api-h43i.onrender.com/version
curl -s https://data-science-agent-api-h43i.onrender.com/health
curl -s https://data-science-agent-api-h43i.onrender.com/api/v1/datasets/
```

`/version` reports the version of the distribution actually installed in the running container, read from
its package metadata, plus the effective reasoning mode (`/health` stays import-free and I/O-free, so the
mode is not published there). A first request may take tens of seconds: the free instance spins down when
idle.

What the two listings contain depends on who owns the rows, and this changed when the demo grew its own
published content, so the old "expect an empty list" note is gone. As measured on 2026-10-21, the instance
answers `2` datasets and `2` analyses, every one of them `owner: shared` -- the sample datasets and the
example runs the first screen is built from, seeded so a visitor never lands on an empty product (R-01,
R-08). Their ids are different on every cold start, because the database is not durable: a *visitor's* rows
are the ones that disappear, and the shared rows are re-created. So a non-empty list is the healthy answer,
and a run id copied from an earlier check is expected to 404.

`/version` also answers `storage`, and on the free demo it says so out loud:

```bash
curl -s https://data-science-agent-api-h43i.onrender.com/version \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['storage'])"
```

Read the output rather than transcribing it -- the value names whichever roots sit on a path the host may
clear, and it grows as the container layout changes (measured 2026-10-21: `durable: False` with all three of
`artifacts`, `database`, `datasets` listed).

`ephemeral_roots` names which of `database` / `datasets` / `artifacts` sit on a path the host may clear, and
the web header renders "not kept" whenever `durable` is false -- so a visitor who returns to an empty run
list sees a stated property of the instance rather than an unexplained loss. It publishes roles, not paths,
because the route is unauthenticated; and after Stage 1 in
[Production Persistence Hardening](production-hardening.md) it is the check that the mount is actually
configured, since a `/var/data` database with `/app/artifacts` charts reports `["artifacts"]`.

To confirm which build the API is serving, read its own schema rather than the dashboard:

```bash
curl -s https://data-science-agent-api-h43i.onrender.com/openapi.json \
  | python3 -c "import json,sys; p=json.load(sys.stdin)['paths']['/api/v1/analysis/{run_id}/report']['get']['parameters']; print([q['name'] for q in p])"
```

Some networks cannot reach `*.vercel.app` at all: DNS answers an address outside Vercel's ranges and TCP to
port 443 times out, while `vercel.com` itself still connects. That is an environment condition, not a product
defect, and it does not block a deploy check -- the API census above runs from anywhere. To confirm the web
half without a browser, check the commit the platform built (`git show <sha>:<file>` for the change you
expect) together with the `web-regression` CI job for that commit, and say plainly that the rendered page was
not observed.

## Dataset storage behavior

Runtime uploads are stored under the API dataset directory. The default resolves to:

```text
/app/data/datasets
```

You can override it with:

```bash
DSA_DATASET_DIR=/your/durable/path
```

On the current free Render preview, local storage is ephemeral. A restart or redeploy may remove uploaded files even if an old database record existed previously. The API therefore filters out dataset records whose backing file is missing, and analysis creation rejects a missing dataset before running tools.

For the public demo, visitors should assume:

- uploaded datasets are temporary;
- generated chart/report files are temporary;
- a restart or redeploy may require re-uploading the dataset;
- the free instance sleeps when idle, and the first request after an idle period was measured at 44.5 s to answer `/health`. The web app now says this up front and shows a bounded "waking up" retry rather than a spinner; see R-11 in the changelog.

A production deployment should replace ephemeral local dataset/artifact storage with durable object storage, a persistent disk, or another explicitly managed persistence layer.

For the recommended low-risk path from the current single-instance demo to durable storage, see [Production Persistence Hardening](production-hardening.md). The first stage deliberately keeps SQLite and local-file semantics, but moves them under one persistent `/var/data` mount before introducing Postgres or object storage.

## Visitors are separated by an id, not by an account

R-08 does not add a sign-in. It adds an owner to every stored row. The sample datasets and the example runs this
project publishes are marked `shared`; anything a visitor uploads or runs is marked with an id that belongs to
that one browser.

- **Where the id comes from.** The web app's proxy mints a random id and sets it in a **first-party cookie**
  before the first render, and every API call carries it in the `X-DSA-Owner` header. The three report links
  that open in a new tab carry it as `?owner=` instead, because a browser navigation cannot add a header -- that
  is the only place it appears in a URL. There is nothing for an operator to configure.
- **What no id means.** A request with no header -- `curl`, the CLI, a browser that refused the cookie -- acts as
  the `local` owner, which is also the value every pre-R-08 row was backfilled to. So a plain `curl` reads the
  published sample and whatever was uploaded without an id, and none of what a scoped visitor uploaded.
- **What this stops.** The next visitor listing your datasets, opening your run, reading your report, downloading
  your bundle, or approving your run. Every one of those answers with the same `404` and the same words an id
  that was never issued would get, so a stranger cannot even learn that your run exists. Starting a run on
  someone else's dataset is refused the same way, and one visitor's duplicate-submit suppression never answers
  for another's.
- **What this does not stop.** Anyone holding your cookie, or reading the `owner=` parameter out of a shared
  machine's browser history. It is a bearer value with nothing behind it: there is no password to check, because
  the free demo has no user table to check it against. Clearing site data loses the rows for you as well -- the
  files sit on the instance until it restarts, and nothing lets you reclaim them under a fresh id.
- **`shared` is reserved.** A client that sends `X-DSA-Owner: shared` is normalised to `local`, so a visitor can
  read the published sample but cannot publish their own file to everyone, and cannot claim the reserved rows.
- **The promise a deployment can make** is "visitors cannot see each other's uploads", not "your data is private
  on this server". `/datasets` says it in the browser, at the upload control, in those terms.

### The demo takes no model key, and says so on the page

`PUT /api/v1/provider` answers 403 on this deployment, and `/settings` renders the refusal rather than a form
that would fail. The rule is mechanical: the API accepts a credential only when `DSA_PROVIDER_CONFIG` names a
file to keep it in, and the hosted service never sets it. An instance with nowhere to store a secret between
visits should not collect one -- accepting a key, holding it in memory, and losing it at the next idle restart
is a worse experience than refusing, and a stranger's key sitting in a shared process is the same exposure R-08
just closed for data.

Consequences an operator should state rather than imply: the public demo runs on the deterministic planner
(`heuristic`), so what a visitor sees is the product's reasoning *shape* without a model's; provider
credentials belong to a private instance started with `dsa ui`, where the key is stored 0600 in that user's own
data directory. `GET /version`'s `reasoning_mode.source` tells a reader which knob decided the mode on the
instance they are talking to.

## Required configuration

### Web

Set this **at web build time**:

```bash
NEXT_PUBLIC_API_URL=https://data-science-agent-api.onrender.com
```

`NEXT_PUBLIC_API_URL` must be a URL the visitor's browser can reach. Do not use a Docker-only hostname such as `http://api:8000` for a public build.

### API

Allow the stable Vercel production origin:

```bash
DSA_CORS_ORIGINS=https://data-science-agent-web.vercel.app
```

Multiple origins may be comma-separated when preview deployments also need API access:

```bash
DSA_CORS_ORIGINS=https://data-science-agent-web.vercel.app,https://your-preview.vercel.app
```

Keep provider/API credentials in the hosting platform's secret store. Never expose them through `NEXT_PUBLIC_*` variables. The default hosted demo does not require a provider credential.

## Troubleshooting the browser demo

If the browser displays `TypeError: Failed to fetch`, check these in order:

1. Open the Render `/health` URL directly and confirm the API is healthy.
2. Confirm the browser is using the stable production Vercel origin allowed by `DSA_CORS_ORIGINS`.
3. If upload succeeded before a restart/redeploy but analysis later says the file is unavailable, re-upload the dataset because local demo storage is ephemeral.
4. Check Render logs for a restart, memory pressure, or process exit before changing frontend configuration.

The frontend deliberately reports transport failures separately from normal API `4xx/5xx` responses so network/CORS failures are not confused with analysis errors.

## Local Docker check

Copy the environment template and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- Web: `http://localhost:3000`
- API health: `http://localhost:8000/health`

The expected visitor path is:

```text
Landing page
  → upload dataset
  → inspect profile
  → ask a natural-language question
  → inspect tool trace and evidence
  → open/download report
```

## Launch checklist

Verified for the current public preview:

- [x] Render API builds and reaches `Live`.
- [x] API is reachable over HTTPS.
- [x] `/health` returns successfully.
- [x] Vercel web build uses the public Render API URL.
- [x] API CORS allows the stable public web origin.
- [x] Uploading CSV succeeds.
- [x] Uploading modern Excel (`.xlsx`) succeeds.
- [x] A canonical multi-tool analysis completes successfully.
- [x] Semantic planner selects the expected outcome/group analysis path.
- [x] Correlation, Welch significance test, feature importance, causal guard, and visualization can complete in one run.
- [x] Evidence reaches a terminal `verified` state.
- [x] Validation can complete with no tool errors.
- [x] Final report status reaches `COMPLETED`.
- [x] README contains a public `Try Live Demo` link.

Operational hardening still recommended before treating this as a durable production service:

- [ ] Move datasets and generated artifacts to durable storage.
- [ ] Move demo metadata from ephemeral SQLite to a managed/persistent database if retention is required.
- [ ] Add production-grade request-rate and abuse limits.
- [ ] Add explicit monitoring/alerting for API availability and resource pressure.
- [ ] Decide whether preview Vercel origins should be admitted by CORS.
- [ ] Configure a real-model provider only when credentials, cost controls, and evaluation policy are ready.

The public demo should optimize for one reliable, transparent happy path rather than pretending the free preview infrastructure provides durable production guarantees.
