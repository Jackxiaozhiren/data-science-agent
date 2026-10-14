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
DSA_CORS_ORIGINS=https://data-science-agent-web.vercel.app
```

If an existing Blueprint has a failed deploy, keep the same Blueprint and use **Manual sync** or **Manual Deploy** after the repository fix is merged. Do not create a second Blueprint for the same service.

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
idle. The dataset listing is expected to be empty after a deploy -- see the storage note below -- so an
empty list is the healthy answer, not a failure.

`/version` also answers `storage`, and on the free demo it says so out loud:

```bash
curl -s https://data-science-agent-api-h43i.onrender.com/version \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['storage'])"
# {'durable': False, 'ephemeral_roots': ['database']}
```

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
