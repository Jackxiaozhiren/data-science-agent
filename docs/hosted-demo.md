# Hosted Demo Deployment

The repository contains a Next.js web app (`apps/web`) and FastAPI service (`apps/api`). The hosted demo should expose both through public HTTPS URLs.

## Current reference deployment

The recommended public-demo shape for this repository is:

- **Web:** Vercel, built from `apps/web`.
- **API:** Render Web Service, built from the repository's full Docker API image.

The full DSA Python package is intentionally not treated as a lightweight serverless function: the scientific stack is substantially larger than typical function bundles. Keep the Web and API independently deployable and connect them with the public API URL.

The repository includes a root `render.yaml` Blueprint so the API can be provisioned from GitHub without recreating Docker, health-check, port, or demo-mode settings by hand.

The public demo runs in deterministic offline/heuristic mode so a visitor can complete the core product flow without requiring or exposing a model API key. Real-model evaluation is a separate, explicitly configured path.

## Deploy the API on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Jackxiaozhiren/data-science-agent)

Use the button above, or create a new Blueprint from this repository in the Render dashboard.

The Blueprint creates one Docker Web Service with:

- `docker/Dockerfile.api` and the repository root as Docker build context;
- the Render-provided `PORT` value at runtime;
- `/health` as the health-check path;
- `DSA_LLM_MODE=heuristic` and heuristic fallback;
- automatic deploys disabled so a public-demo instance is not rebuilt on every repository change;
- `DSA_CORS_ORIGINS` requested during Blueprint creation rather than committed to the repository.

For the initial deployment, set `DSA_CORS_ORIGINS` to the exact public Vercel frontend origin. Do not include a trailing path. If the frontend URL has not been created yet, you can temporarily use the intended Vercel origin and update the Render environment variable before the final smoke test.

Render's free Web Service is suitable for a public preview but has intentional limitations: it can spin down after inactivity and its local filesystem is ephemeral. Uploaded datasets and generated artifacts therefore must be treated as temporary demo data.

## Required configuration

### Web

Set this **at web build time**:

```bash
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

`NEXT_PUBLIC_API_URL` must be a URL the visitor's browser can reach. Do not use a Docker-only hostname such as `http://api:8000` for a public build.

### API

Allow the public web origin:

```bash
DSA_CORS_ORIGINS=https://your-demo.vercel.app
```

Multiple origins may be comma-separated:

```bash
DSA_CORS_ORIGINS=https://your-demo.vercel.app,https://your-preview.vercel.app
```

Keep provider/API credentials in the hosting platform's secret store. Never expose them through `NEXT_PUBLIC_*` variables. The default hosted demo does not require a provider credential.

For a public trial, prefer an isolated demo storage location and assume uploaded datasets are ephemeral unless the deployment explicitly provides durable storage. Do not promise persistence that the hosting configuration does not provide.

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

- [ ] Render API build completes from `docker/Dockerfile.api`.
- [ ] API is reachable over HTTPS.
- [ ] `/health` returns successfully.
- [ ] Web build uses the public Render API URL.
- [ ] API CORS allows the public web origin only.
- [ ] Uploading a small CSV succeeds.
- [ ] A canonical analysis question completes successfully.
- [ ] Analysis trace shows tool calls, evidence, validation, and artifacts.
- [ ] Report download works.
- [ ] File-size, request-rate, log-retention, and provider-spend limits are configured where applicable.
- [ ] README gets a `Try Live Demo` link only after the public URL passes this checklist.

The public demo should optimize for one reliable happy path rather than exposing every internal surface. A verified end-to-end demo is more valuable than a public URL that only renders the frontend.
