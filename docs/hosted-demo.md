# Hosted Demo Deployment

The repository contains a Next.js web app (`apps/web`) and FastAPI service (`apps/api`). The hosted demo should expose both through public HTTPS URLs.

## Current reference deployment

The recommended public-demo shape for this repository is:

- **Web:** Vercel, built from `apps/web`.
- **API:** a container/full-Python host such as Replit that can install the complete scientific-computing dependency set used by DSA.

The full DSA Python package is intentionally not treated as a lightweight serverless function: the scientific stack is substantially larger than typical function bundles. Keep the Web and API independently deployable and connect them with the public API URL.

The public demo may run in the deterministic offline/heuristic mode so a visitor can complete the core product flow without requiring or exposing a model API key. Real-model evaluation is a separate, explicitly configured path.

## Required configuration

### Web

Set this **at web build time**:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com
```

`NEXT_PUBLIC_API_URL` must be a URL the visitor's browser can reach. Do not use a Docker-only hostname such as `http://api:8000` for a public build.

### API

Allow the public web origin:

```bash
DSA_CORS_ORIGINS=https://demo.example.com
```

Multiple origins may be comma-separated:

```bash
DSA_CORS_ORIGINS=https://demo.example.com,https://preview.example.com
```

Keep provider/API credentials in the hosting platform's secret store. Never expose them through `NEXT_PUBLIC_*` variables.

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

- [ ] API is reachable over HTTPS.
- [ ] `/health` returns successfully.
- [ ] Web build uses the public API URL.
- [ ] API CORS allows the public web origin only.
- [ ] Uploading a small CSV succeeds.
- [ ] A canonical analysis question completes successfully.
- [ ] Analysis trace shows tool calls, evidence, validation, and artifacts.
- [ ] Report download works.
- [ ] File-size, request-rate, log-retention, and provider-spend limits are configured where applicable.
- [ ] README gets a `Try Live Demo` link only after the public URL passes this checklist.

The public demo should optimize for one reliable happy path rather than exposing every internal surface. A verified end-to-end demo is more valuable than a public URL that only renders the frontend.
